"""The Tier-C model contradiction check — doc 08 §5.3, feeding §4.2's veto.

The deterministic same-endpoint scan decides the pairs whose incompatibility
falls out of the closed relation vocabulary alone. This module is the other
input doc 08 §4.2 names: the one that needs a model to tell "postgres was
replaced by mysql" from "postgres and mysql are both in use", and therefore the
one that may never run anywhere near capture or retrieval (invariant 15).

**The generator is combined, and both halves are load-bearing.** For each fact
needing a check, candidates come from two cheap SQL arms on the one Postgres
(invariant 1):

1. **same-endpoint** — live facts in the same project sharing ``subject_name``
   or ``object_name``. Structural adjacency: two claims about the same thing.
2. **``pg_trgm``-on-``fact``** — the trigram shortlist over the fact text.
   Lexical adjacency: two claims phrased alike about endpoints that were
   canonicalised differently, which the first arm cannot see at all.

Neither is a superset of the other, so the pool is interleaved rather than
concatenated: a per-fact cap that drained the first arm before looking at the
second would silently degrade to a same-endpoint-only generator on any fact
with more than ``top_k`` structural neighbours, and nothing would report it.
There is deliberately **no vector arm** — ``triple_embeddings`` stays
template-only until a *measured* undercount of this generator justifies its
writer (doc 04 §5.3, doc 08 §5.3), and that measurement is a separate task's.

**The overlap filter is a pushdown, not a post-filter.** Disjoint validity
windows are legitimate succession (doc 08 §3.1), and scoring them manufactures
disputes, so the half-open overlap predicate rides both arms' WHERE clause and
a disjoint pair is never transported at all. It is a second spelling of
``windows_overlap``; ``tests/test_contradiction_scan.py`` sweeps the two
against each other so the copy cannot drift silently.

**Adjudication has exactly one door.** ``VerificationJudge.judge`` is the only
thing in this module that can produce a verdict — no similarity floor stands in
for one, no string comparison, no fallback when the judge refuses. That refusal
is the safety property rather than an obstacle: while no qualification record
exists the judge raises unconditionally, and this module's response is to abort
the run *without advancing its watermark*, so nothing is silently consumed and
nothing is adjudicated on an unqualified judge. The refusal is a global
precondition failure, not a poisonous row, which is why it is one of the two
failures this module declines to skip past — the opposite of the per-fact
isolation the verification recompute's arms use, and deliberately so.

**A verdict that did not reach the journal did not happen** — the second such
failure. ``record_event`` degrades loudly and never raises, which is right for
a side-channel and wrong here: this journal row is the job's whole output, so a
swallowed insert would otherwise be tallied as a recorded dispute while the
veto never sees it, and the run would report full coverage with no miss. Every
verdict is therefore read back out of ``events`` in its own write session
before that session commits, and a shortfall stops the run with the watermark
standing still. The treatment matches the refusal's because the failure class
does: a journal insert cannot fail on the strength of one fact's content, so
whatever broke it — a missing monthly partition above all — will still be
broken for every fact left in the batch.

**What the scan does not do is apply its own finding.** It journals a verdict
per fact it checked; the veto reads the standing verdict back at recompute
time and the ladder is what writes ``disputed``. Emitting a ``sources_changed``
event to hurry that along would be the obvious shortcut and it is a trap: this
module *drains* that stream, so an emit would feed its own input and the job
would scan the same fact forever. The dispute therefore lands on the recompute
job's next pass over the fact — its slow arm rotates over every live
non-confirmed fact, so the delay is bounded and the loss is nil, which is the
sanctioned direction of error (doc 08 §5.3's precision-first asymmetry).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import lease_llm
from app.models.config import Config
from app.repositories.fact_sources import FactSourceRepository
from app.services.events import CONTRADICTION_SCANNED, record_event
from app.services.job_registry import FieldDescriptor
from app.services.verification_judge import (
    CONTRADICTION_ROLE,
    JudgeNotQualifiedError,
    VerificationJudge,
)

logger = logging.getLogger(__name__)

# The verdict this consumer is qualified on. Spelled once, and pinned to the
# judge's own vocabulary by test rather than by hope — a typo here would read
# as "no contradiction ever found" and pass every happy-path assertion.
#
# It is also the whole of this module's discrimination, which is why the scan
# asks the judge as the `contradiction` role: `entailed` and `unsupported` are
# one bucket here, and that role is unqualified and stays so, so every call
# below still refuses (doc 17 §6, amended 2026-08-12).
CONTRADICTED_VERDICT = "contradicted"

# ── config (operator-facing, validated by JobRegistry.set_config) ─────────

# Both keys, defaults and bounds are carried verbatim from the T2.08
# placeholder schema: `set_config` merges `{**cfg.config, **partial}` and never
# drops a key, so an operator who already tuned either value keeps a value that
# still means exactly what it meant before this swap. Doc 08 §5.3 names these
# two rows by value and no third: an extra knob here would be a cost lever the
# design did not sanction.
SCAN_BATCH_KEY = "contradiction_scan_batch"
CANDIDATE_TOP_K_KEY = "contradiction_candidate_top_k"

DEFAULT_SCAN_BATCH = 20
MAX_SCAN_BATCH = 500
DEFAULT_CANDIDATE_TOP_K = 10
MAX_CANDIDATE_TOP_K = 100

CONTRADICTION_SCAN_CONFIG_SCHEMA: list[FieldDescriptor] = [
    FieldDescriptor(
        key=SCAN_BATCH_KEY, label="Facts Per Cycle",
        default=DEFAULT_SCAN_BATCH, min=1, max=MAX_SCAN_BATCH,
        help=(
            "Facts drained and checked per run. It caps the sources_changed "
            "events read past the watermark, so it is a ceiling on facts per "
            "cycle: a run that drains several events for one fact checks "
            "fewer facts, never more."
        ),
    ),
    FieldDescriptor(
        key=CANDIDATE_TOP_K_KEY, label="Candidates Per Fact",
        default=DEFAULT_CANDIDATE_TOP_K, min=1, max=MAX_CANDIDATE_TOP_K,
        help=(
            "Size of the combined candidate pool per fact, drawn alternately "
            "from the same-endpoint and trigram arms so the cap can never "
            "starve one of them."
        ),
    ),
]

# Internal bookkeeping, never reachable through JobRegistry.set_config. Same
# reasoning verification_recompute records for its own watermark: a queue
# position is not a tunable an operator should be able to set through
# `PUT /api/v1/jobs/{key}/config`, and routing it through the job's config dict
# would either be rejected as an unknown key or, if added to the schema to make
# it pass, become editable there.
_STATE_CONFIG_KEY = "contradiction_scan_state"

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

# The commit-skew margin, for the identical reason verification_recompute
# carries one: `created_at` is transaction *start* time, so an earlier-started,
# later-committing producer can land behind a watermark advanced by a drain
# that ran in between. Never reading an event newer than this keeps that
# headroom.
_COMMIT_SKEW_MARGIN = timedelta(seconds=5)

# The trigram floor the shortlist is drawn above. A module constant rather than
# a config row on purpose: it selects *candidates*, never verdicts, and doc 08
# §5.3 sanctions exactly two operator knobs for this job. Lowering it widens
# the shortlist and costs model calls; raising it narrows the generator, which
# is the sanctioned direction of error but still a design change rather than a
# tuning dial.
_TRIGRAM_FLOOR = 0.3


# ── persisted state ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class _State:
    watermark_created_at: datetime | None = None
    watermark_id: int | None = None

    def to_dict(self) -> dict:
        return {
            "watermark_created_at": (
                self.watermark_created_at.isoformat()
                if self.watermark_created_at is not None else None
            ),
            "watermark_id": self.watermark_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "_State":
        raw = data.get("watermark_created_at")
        moment = None
        if raw:
            moment = datetime.fromisoformat(raw)
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
        return cls(watermark_created_at=moment, watermark_id=data.get("watermark_id"))


async def _load_state(session: AsyncSession) -> _State:
    row = (
        await session.execute(select(Config).where(Config.key == _STATE_CONFIG_KEY))
    ).scalar_one_or_none()
    if row is None or not isinstance(row.value, dict):
        return _State()
    return _State.from_dict(row.value)


async def _save_state(session: AsyncSession, state: _State) -> None:
    row = (
        await session.execute(select(Config).where(Config.key == _STATE_CONFIG_KEY))
    ).scalar_one_or_none()
    if row is None:
        session.add(Config(key=_STATE_CONFIG_KEY, value=state.to_dict()))
    else:
        row.value = state.to_dict()


# ── the drain ───────────────────────────────────────────────────────────

# The same tuple compare verification_recompute's fast arm uses, and for the
# same two reasons: `created_at >= :wm_ts` is a plain comparison on the
# range-partition key so the planner prunes on it directly, and the OR clause
# is what makes same-transaction ties (identical created_at, distinct id)
# unmissable. This watermark is deliberately its own row rather than shared
# with the recompute's: two consumers of one stream that shared a position
# would each advance the other past unread work.
_DRAIN_EVENTS = text("""
    SELECT id, created_at, payload
    FROM events
    WHERE event_type = 'sources_changed'
      AND object_type = 'fact'
      AND created_at >= CAST(:wm_ts AS timestamptz)
      AND (created_at > CAST(:wm_ts AS timestamptz) OR id > CAST(:wm_id AS bigint))
      AND created_at <= CAST(:safe_until AS timestamptz)
    ORDER BY created_at, id
    LIMIT CAST(:batch AS integer)
""")

# Servable and not already disputed (doc 08 §5.3). `confirmed` is excluded for
# the reason the recompute's slow arm excludes it: doc 08 §4.4 makes a ratified
# fact immune to the veto, so a model call spent on one can change nothing.
# `disputed` is excluded because it is already at the destination this scan can
# reach; recovery out of `disputed` is the recompute's, driven by the standing
# verdict this job already wrote.
_SERVABLE_FACTS = text("""
    SELECT id, project, subject_name, rel_type, object_name, fact,
           valid_at, invalid_at
    FROM knowledge_triples
    WHERE id = ANY(CAST(:ids AS uuid[]))
      AND expired_at IS NULL
      AND invalid_at IS NULL
      AND verification_status NOT IN ('disputed', 'confirmed')
    ORDER BY created_at, id
""")


# ── the combined candidate generator ────────────────────────────────────

# The half-open overlap predicate of doc 08 §3.1, pushed into both arms so a
# disjoint pair is never transported. NULL `valid_at` reads as unbounded-past
# and NULL `invalid_at` as open-ended, which is why every comparison is guarded
# by an IS NOT NULL: a guard that evaluates false makes its whole conjunct
# false rather than NULL, so the predicate is total.
#
# `s_` names the fact being checked; the bare column names are the candidate's.
# This is a second spelling of `windows_overlap`, and the two are swept against
# each other in the test module rather than trusted to stay aligned.
_OVERLAP_PREDICATE = """
      NOT (CAST(:s_invalid AS timestamptz) IS NOT NULL
           AND valid_at IS NOT NULL
           AND valid_at >= CAST(:s_invalid AS timestamptz))
      AND NOT (invalid_at IS NOT NULL
               AND CAST(:s_valid AS timestamptz) IS NOT NULL
               AND CAST(:s_valid AS timestamptz) >= invalid_at)
"""

_CANDIDATE_COLUMNS = (
    "id, project, subject_name, rel_type, object_name, fact, valid_at, invalid_at"
)

# Arm 1. `expired_at IS NULL` rather than the narrower open-belief predicate,
# matching the deterministic scan's own liveness rule: a window-closed row is
# retained history that can still overlap, and the overlap predicate above is
# what decides that, not a liveness filter standing in for it.
#
# `ORDER BY created_at, id` makes the draw deterministic, and under saturation
# it is the *newest* structural neighbours that fall past the LIMIT. That is a
# selection-quality choice, so it is stated rather than left to be inferred:
# the subject is a fact whose sources just changed, so its counterparts skew
# older than it, and what the cap drops is counted by `CandidatePool.truncated`
# rather than lost quietly. Reordering by recency would be a retrieval-quality
# change, and this generator's coverage has no measurement behind it yet
# (T2.52's), so there is nothing to judge such a change against.
_SAME_ENDPOINT_SQL = text(f"""
    SELECT {_CANDIDATE_COLUMNS}
    FROM knowledge_triples
    WHERE project = CAST(:project AS text)
      AND expired_at IS NULL
      AND id <> CAST(:fact_id AS uuid)
      AND (subject_name = CAST(:subject_name AS text)
           OR object_name = CAST(:object_name AS text))
      AND {_OVERLAP_PREDICATE}
    ORDER BY created_at, id
    LIMIT CAST(:k AS integer)
""")

# Arm 2. The `%` operator rather than `similarity(...) >= floor` is what lets
# the GIN trigram index on `fact` serve the shortlist at all — the function
# form is not indexable and degrades to a sequential scan of the whole table,
# which is the one thing doc 08 §5.3's "cheap SQL" rules out. `%` compares
# against `pg_trgm.similarity_threshold`, which `set_limit` below pins per run
# so the arm never inherits whatever a previous statement left on the session.
_TRIGRAM_SQL = text(f"""
    SELECT {_CANDIDATE_COLUMNS}, similarity(fact, CAST(:fact_text AS text)) AS sim
    FROM knowledge_triples
    WHERE project = CAST(:project AS text)
      AND expired_at IS NULL
      AND id <> CAST(:fact_id AS uuid)
      AND fact % CAST(:fact_text AS text)
      AND {_OVERLAP_PREDICATE}
    ORDER BY sim DESC, created_at, id
    LIMIT CAST(:k AS integer)
""")

ARM_SAME_ENDPOINT = "same_endpoint"
ARM_TRIGRAM = "trigram"


@dataclass(frozen=True)
class Candidate:
    fact_id: str
    subject_name: str
    rel_type: str
    object_name: str
    fact: str
    arms: tuple[str, ...]


@dataclass(frozen=True)
class CandidatePool:
    candidates: tuple[Candidate, ...]
    generated: int
    truncated: int
    arm_counts: dict[str, int] = field(default_factory=dict)


def _interleave(
    ordered_arms: list[tuple[str, list[dict]]], top_k: int
) -> CandidatePool:
    """Round-robin the arms into one capped pool, deduplicating by fact id.

    Concatenating instead would make the cap arm-ordered: a fact with `top_k`
    structural neighbours would never see a trigram candidate, and the
    generator would degrade to half of itself with nothing reporting it. A
    candidate both arms found keeps both names, so the pool can say which arm
    reached a finding rather than only that something did.
    """
    seen: dict[str, list[str]] = {}
    order: list[dict] = []
    arm_counts = {name: len(rows) for name, rows in ordered_arms}
    cursors = {name: 0 for name, _ in ordered_arms}
    while True:
        progressed = False
        for name, rows in ordered_arms:
            index = cursors[name]
            if index >= len(rows):
                continue
            cursors[name] = index + 1
            progressed = True
            row = rows[index]
            key = str(row["id"])
            if key in seen:
                if name not in seen[key]:
                    seen[key].append(name)
                continue
            seen[key] = [name]
            order.append(row)
        if not progressed:
            break

    kept = order[:top_k]
    return CandidatePool(
        candidates=tuple(
            Candidate(
                fact_id=str(row["id"]),
                subject_name=row["subject_name"],
                rel_type=row["rel_type"],
                object_name=row["object_name"],
                fact=row["fact"],
                arms=tuple(seen[str(row["id"])]),
            )
            for row in kept
        ),
        generated=len(order),
        truncated=max(0, len(order) - len(kept)),
        arm_counts=arm_counts,
    )


async def generate_candidates(
    session: AsyncSession, fact: dict, *, top_k: int
) -> CandidatePool:
    """Both arms, then one interleaved pool capped at ``top_k``.

    Each arm is drawn at the full cap so neither is starved before the
    interleave decides what survives it — **plus one row**, whose only job is
    to make the cap's bite observable. Drawn at exactly the cap, an arm that
    saturates its own ``LIMIT`` is indistinguishable from one that returned
    everything there was, and ``CandidatePool.truncated`` would read zero on
    precisely the facts where the generator undercounted most. The peek row
    makes ``truncated`` a **floor** on the candidates left unexamined rather
    than an exact count; an exact one would mean transporting the whole
    neighbourhood, which is what the cap exists to avoid.
    """
    limit = top_k + 1
    window = {
        "s_valid": fact["valid_at"],
        "s_invalid": fact["invalid_at"],
    }
    same_endpoint = (await session.execute(
        _SAME_ENDPOINT_SQL,
        {
            "project": fact["project"],
            "fact_id": str(fact["id"]),
            "subject_name": fact["subject_name"],
            "object_name": fact["object_name"],
            "k": limit,
            **window,
        },
    )).mappings().all()

    # `set_limit`, not `SET LOCAL`: the GUC form takes no bind parameter, and
    # spelling the constant into the statement text would put a literal where a
    # parameter belongs for no gain.
    await session.execute(
        text("SELECT set_limit(CAST(:floor AS real))"), {"floor": _TRIGRAM_FLOOR}
    )
    trigram = (await session.execute(
        _TRIGRAM_SQL,
        {
            "project": fact["project"],
            "fact_id": str(fact["id"]),
            "fact_text": fact["fact"],
            "k": limit,
            **window,
        },
    )).mappings().all()

    return _interleave(
        [
            (ARM_SAME_ENDPOINT, list(same_endpoint)),
            (ARM_TRIGRAM, list(trigram)),
        ],
        top_k,
    )


# ── the echo test ───────────────────────────────────────────────────────


async def _attributable(session: AsyncSession, fact_id: str) -> set[str]:
    """The origins that identify a witness for a fact.

    Reads through ``origin_profile`` rather than counting ``fact_sources``
    rows, so the unknown-origin folding rule is applied exactly once in the
    codebase: an unattributable source carries no session identity and can
    therefore never *be* the distinct witness a non-echo contradiction needs.
    """
    profile = await FactSourceRepository(session).origin_profile(fact_id)
    return {
        origin.origin_key
        for origin in profile.attributable_origins
        if origin.origin_key is not None
    }


def _witness(challenger_origins: set[str], asserting: set[str]) -> str | None:
    """The first origin the challenger brings that the fact does not have.

    Asymmetric on purpose, and the asymmetry is the doctrine: the question is
    asked of the challenger, because "the contradicting source is a distinct
    origin, not the same one re-stating itself" is a claim about who is
    objecting. A symmetric rule would dispute both rows on one witness's
    say-so, which is a vote, and the veto is not a vote.
    """
    fresh = sorted(challenger_origins - asserting)
    return fresh[0] if fresh else None


# ── the outcome ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ScanOutcome:
    """Every fact the run touched, and every one it could not finish.

    The miss buckets are separate fields rather than one number because they
    have different remedies: a truncated pool wants a larger `top_k`, a refusal
    wants a qualification record, a judge failure wants the provider looked at,
    a journal failure wants the events partitions looked at.

    ``misses`` is their sum, and it is a **detector, not a quantity**: the
    buckets count different things (facts, candidates, pairs, and a per-run
    refusal flag), and one undecided pair increments two of them — its own
    `judge_failed` and the `facts_incomplete` it caused. So `misses > 0` means
    "this run's coverage was incomplete", and nothing about the size of the
    gap; the size question is the individual buckets', and the coverage of the
    generator itself is a measurement no counter here attempts.
    """

    events_scanned: int = 0
    facts_touched: int = 0
    facts_skipped_unservable: int = 0
    facts_checked: int = 0
    candidates_generated: int = 0
    pairs_echo: int = 0
    pairs_judged: int = 0
    disputes_recorded: int = 0
    clears_recorded: int = 0
    watermark_advanced: bool = False
    skipped_reason: str | None = None

    # ── the miss buckets ──
    facts_incomplete: int = 0
    facts_unscanned: int = 0
    candidates_truncated: int = 0
    judge_refused: int = 0
    judge_failed: int = 0
    judge_invalid: int = 0
    journal_failed: int = 0

    @property
    def misses(self) -> int:
        return (
            self.facts_incomplete
            + self.facts_unscanned
            + self.candidates_truncated
            + self.judge_refused
            + self.judge_failed
            + self.judge_invalid
            + self.journal_failed
        )


@dataclass(frozen=True)
class _FactWork:
    """One fact's whole SQL-side preparation, carried out of the read
    transaction so the model phase holds no session."""

    fact: dict
    pool: CandidatePool
    asserting: set[str]
    challengers: dict[str, set[str]]


@dataclass
class _Tally:
    """The mutable accumulator behind the frozen outcome."""

    counts: dict[str, int] = field(default_factory=dict)

    def add(self, key: str, amount: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + amount


# ── the tick ────────────────────────────────────────────────────────────

# The verdict count-back, on the same `(object_type, object_id, created_at)`
# index the veto's own read-back uses. The window is generous because it exists
# only to prune partitions, not to filter: `scan_run_id` is what identifies the
# row, and no run outlives a day's worth of clock skew.
_READBACK_WINDOW = timedelta(days=1)

# The question is existence rather than a count because at most one row can
# carry this `(fact, run)` pair — one verdict per fact per run — so a count
# would only be an existence test with a constant to compare against, and a
# numeric comparison is the one thing this module may not contain.
_VERDICT_READBACK = text("""
    SELECT EXISTS (
        SELECT 1
        FROM events
        WHERE object_type = 'fact'
          AND event_type = CAST(:kind AS text)
          AND object_id = CAST(:fact_id AS uuid)
          AND created_at >= CAST(:floor AS timestamptz)
          AND payload ->> 'scan_run_id' = CAST(:run_id AS text)
    )
""")


async def _journal(
    session: AsyncSession,
    fact: dict,
    pool: CandidatePool,
    finding: dict[str, Any] | None,
    *,
    pairs_judged: int,
    run_id: str,
) -> bool:
    """One row per completed check — the channel the veto reads back.

    Returns whether the row actually landed. ``record_event`` swallows its own
    insert failures by design, so a caller that assumed success would count a
    dispute nobody can read; the read-back below is what makes that assumption
    unnecessary. It runs in the caller's write session before the commit, where
    the row is visible to its own transaction and to nothing else yet, and it
    matches on ``scan_run_id`` because an earlier run's verdict on the same
    fact is also a row of this type on this object.

    The payload carries the counterpart's ids and its triple, never the
    counterpart's ``fact`` text: the triple already states the competing claim
    and this journal is append-only, so every copied column is permanent. The
    judge's one-sentence reason is the exception and is carried deliberately —
    doc 08 §6 serves a disputed fact labelled with both sides and gates it on
    nobody's review, so a dispute a reader cannot understand is a dispute
    nobody can resolve, and the ids alone do not say why the pair conflicts.
    ``scan_run_id`` is the other addition and copies no content at all: it is
    the handle that read-back matches on, and it groups one run's verdicts
    for an operator besides.
    """
    payload: dict[str, Any] = {
        "contradicted": finding is not None,
        "candidates_considered": len(pool.candidates),
        "candidates_truncated": pool.truncated,
        "pairs_judged": pairs_judged,
        "arm_counts": pool.arm_counts,
        "scan_run_id": run_id,
    }
    if finding is not None:
        payload.update(finding)
    await record_event(
        session,
        event_type=CONTRADICTION_SCANNED,
        object_type="fact",
        object_id=fact["id"],
        project=fact["project"],
        source="job",
        payload=payload,
    )
    return bool((await session.execute(
        _VERDICT_READBACK,
        {
            "kind": CONTRADICTION_SCANNED,
            "fact_id": str(fact["id"]),
            # Real wall clock rather than the caller's injected `now`: the row
            # lands at the server's own clock whatever the caller believes the
            # time to be, and the bound is what prunes this read to one or two
            # monthly children of the partitioned table.
            "floor": datetime.now(timezone.utc) - _READBACK_WINDOW,
            "run_id": run_id,
        },
    )).scalar_one())


async def run_contradiction_scan(
    session_factory,
    llm_provider,
    *,
    batch_size: int = DEFAULT_SCAN_BATCH,
    top_k: int = DEFAULT_CANDIDATE_TOP_K,
    now: datetime | None = None,
) -> ScanOutcome:
    """One scan tick: drain, generate, filter, adjudicate, journal.

    Owns its sessions rather than taking one, because the adjudication phase is
    a model fan-out: a read transaction held across it would sit ``idle in
    transaction`` for as long as the provider takes. The drain and generation
    run in one short transaction, each judge call gets its own, and each fact's
    verdict is committed as soon as it is decided, so a run interrupted halfway
    keeps the work it finished.
    """
    moment = now or datetime.now(timezone.utc)
    tally = _Tally()
    run_id = str(uuid4())

    llm = llm_provider() if callable(llm_provider) else llm_provider
    with lease_llm(llm):
        if llm is None:
            return ScanOutcome(skipped_reason="no LLM orchestrator configured")

        async with session_factory() as session:
            state = await _load_state(session)
            rows = (await session.execute(
                _DRAIN_EVENTS,
                {
                    "wm_ts": state.watermark_created_at or _EPOCH,
                    "wm_id": state.watermark_id if state.watermark_id is not None else -1,
                    "safe_until": moment - _COMMIT_SKEW_MARGIN,
                    "batch": batch_size,
                },
            )).mappings().all()

            if not rows:
                return ScanOutcome()

            fact_ids: list[str] = []
            seen: set[str] = set()
            for row in rows:
                fact_id = (row["payload"] or {}).get("fact_id")
                if not fact_id:
                    # Unreachable from any producer — `fact_lift`,
                    # `fact_provenance`, `document_door` and the Tier-C citation
                    # re-verifier (named in words: a tree-wide scan owns its
                    # module basename) all write the key — so this is a guard,
                    # not a counter: a bucket that can only ever read zero would
                    # dilute `misses` rather than inform it. It is loud instead,
                    # because an event this drain cannot act on is a producer
                    # having changed shape, and the drain still consumes it.
                    logger.warning(
                        "contradiction scan: sources_changed event %s names no "
                        "fact_id and was drained without a check",
                        row["id"],
                    )
                    continue
                if fact_id not in seen:
                    seen.add(fact_id)
                    fact_ids.append(fact_id)

            facts = [
                dict(row) for row in (await session.execute(
                    _SERVABLE_FACTS, {"ids": fact_ids}
                )).mappings().all()
            ]
            # Candidate generation and the echo test both run here, in the one
            # short transaction, so the model phase below holds no session at all.
            work: list[_FactWork] = []
            for fact in facts:
                pool = await generate_candidates(session, fact, top_k=top_k)
                work.append(_FactWork(
                    fact=fact,
                    pool=pool,
                    asserting=await _attributable(session, str(fact["id"])),
                    challengers={
                        candidate.fact_id: await _attributable(
                            session, candidate.fact_id
                        )
                        for candidate in pool.candidates
                    },
                ))
            advanced_to = (int(rows[-1]["id"]), rows[-1]["created_at"])

        tally.add("events_scanned", len(rows))
        tally.add("facts_touched", len(fact_ids))
        tally.add("facts_skipped_unservable", len(fact_ids) - len(facts))

        judge = VerificationJudge(llm)
        refused = False
        verdict_lost = False
        checked = 0

        for index, item in enumerate(work):
            fact, pool = item.fact, item.pool
            tally.add("candidates_generated", len(pool.candidates))
            tally.add("candidates_truncated", pool.truncated)

            finding: dict[str, Any] | None = None
            pairs_judged = 0
            incomplete = False

            for candidate in pool.candidates:
                witness = _witness(
                    item.challengers[candidate.fact_id], item.asserting
                )
                if witness is None:
                    tally.add("pairs_echo")
                    continue
                try:
                    async with session_factory() as probe_session:
                        verdict = await judge.judge(
                            probe_session, candidate.fact, fact["fact"],
                            role=CONTRADICTION_ROLE,
                        )
                except JudgeNotQualifiedError:
                    refused = True
                    break
                except Exception:
                    logger.exception(
                        "contradiction check failed for fact %s against %s",
                        fact["id"], candidate.fact_id,
                    )
                    tally.add("judge_failed")
                    incomplete = True
                    continue
                pairs_judged += 1
                tally.add("pairs_judged")
                if not verdict.valid:
                    tally.add("judge_invalid")
                    incomplete = True
                    continue
                if verdict.verdict == CONTRADICTED_VERDICT:
                    finding = {
                        "counterpart_id": candidate.fact_id,
                        "witness_origin": witness,
                        "counterpart_subject": candidate.subject_name,
                        "counterpart_rel_type": candidate.rel_type,
                        "counterpart_object": candidate.object_name,
                        "arms": list(candidate.arms),
                        "reason": verdict.reason,
                    }
                    break

            if refused:
                tally.add("judge_refused")
                tally.add("facts_unscanned", len(work) - index)
                break

            # An incomplete pass writes nothing rather than writing a clean
            # verdict: the journal row is what the veto reads back, so a "clean"
            # written over an undecided pair would resolve a standing dispute on
            # evidence that was never gathered. Leaving the previous verdict alone
            # is the conservative reading, and the fact is counted as a miss.
            if incomplete and finding is None:
                tally.add("facts_incomplete")
                continue

            async with session_factory() as write_session:
                landed = await _journal(
                    write_session, fact, pool, finding,
                    pairs_judged=pairs_judged, run_id=run_id,
                )
                if landed:
                    await write_session.commit()

            # A verdict the journal did not take is a verdict that did not happen:
            # counting it as recorded would report the job's only output as
            # delivered while the veto has nothing to read back.
            if not landed:
                logger.error(
                    "contradiction scan: the verdict for fact %s did not reach the "
                    "journal; the run stops with its watermark held",
                    fact["id"],
                )
                tally.add("journal_failed")
                tally.add("facts_unscanned", len(work) - index - 1)
                verdict_lost = True
                break

            checked += 1
            tally.add("disputes_recorded" if finding is not None else "clears_recorded")

        tally.add("facts_checked", checked)

        # The watermark stands still on a refusal, and on a lost verdict. A refusal
        # is a global precondition failure — no qualification record exists — not a
        # poisonous row, so advancing past the drained events would silently
        # discard a whole backlog that becomes checkable the moment the record is
        # minted. A journal insert that failed is the same class: it cannot have
        # failed because of this one fact's content, so it will fail for the rest
        # of the batch too, and the events must stay unconsumed. Every other
        # failure IS per-fact and is settled by the counters instead, exactly as
        # the recompute settles its own.
        if not refused and not verdict_lost:
            async with session_factory() as session:
                state = await _load_state(session)
                await _save_state(
                    session,
                    replace(
                        state,
                        watermark_created_at=advanced_to[1],
                        watermark_id=advanced_to[0],
                    ),
                )
                await session.commit()

        return ScanOutcome(
            watermark_advanced=not (refused or verdict_lost),
            skipped_reason=(
                "the verification judge is not qualified" if refused
                else "a verdict could not be journalled" if verdict_lost
                else None
            ),
            **{
                name: tally.counts.get(name, 0)
                for name in (
                    "events_scanned", "facts_touched", "facts_skipped_unservable",
                    "facts_checked", "candidates_generated", "pairs_echo",
                    "pairs_judged", "disputes_recorded", "clears_recorded",
                    "facts_incomplete", "facts_unscanned", "candidates_truncated",
                    "judge_refused", "judge_failed", "judge_invalid",
                    "journal_failed",
                )
            },
        )
