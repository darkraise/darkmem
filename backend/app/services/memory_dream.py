"""Consolidation's dreaming pass — subsume, associate, refine (doc 08 §5.4).

**Tier C, and nothing may reach it from capture or retrieval** (invariant 15).
The umbrella's source scan derives its forbidden module set from
`dream_jobs.py`'s own imports, so wiring this module up is what puts it under
the guard.

**Three actions, and none of them removes or rewrites a memory.**

- *Subsume* flips an older memory to `superseded` through the T2.45 primitive.
- *Associate* writes one `memory_relations` edge carrying a near-duplicate
  marker for the hygiene queue.
- *Refine* rewrites derived enrichment — `summary` and tags — and provably
  never `content`.

Doc 08 §7 makes every action undoable from its journalled before/after payload,
so `content` is the line the refine arm may not cross: an action whose inverse
needs the original content is one the digest cannot undo, because content is not
journalled anywhere and must not be (journal payloads outlive their memory).
Three independent layers enforce it — a module-level column allowlist the
`UPDATE` is *built from*, a parser with no field that could carry content, and
an AST scan over this file.

**Three phases, and the ordering is the safety argument** — the shape
`memory_community_detection` established.

- *Phase R* reads: state, the seed slice, the seed vectors, the ANN candidates,
  the refine work set. Read-only, so it takes no row locks, and it commits
  before Phase C so a pooled connection does not sit `idle in transaction` for
  the length of an LLM fan-out.
- *Phase C* computes with no transaction open. Every fallible step lives here —
  a missing provider, a timeout, a truncation, an unparseable body — where it
  holds no transaction and touches no row.
- *Phase W* writes in bounded batches, one savepoint per action, each
  re-validating its precondition under `FOR UPDATE` before it writes.

**The fingerprint comes from a canary `embed()`, never `llm_fingerprint()`.**
That method returns a `model|0` sentinel when the embedding purpose's
`dimensions` is unset — a legal configuration — and this job never embeds
anything else. Reading the sentinel partition would drop every seed into a skip
counter and report a green run, every night, forever, with no exception and no
log line. Every real read path takes the fingerprint from `embed()`'s return
value instead, and so does this one; a sentinel or a failed canary stops the
whole run loudly rather than per seed.

**The judge never chooses a direction.** The pair is ordered by
`successor_is_newer` — the same predicate the primitive re-evaluates — and the
model is asked one question about an already-ordered pair. Letting a
plausible-sounding wrong answer pick the direction is exactly the mutual flip
the epic's ordering amendment exists to block.

Doc 11 §6 puts dream-refine's merge/rewrite judgments on the `reasoning`
purpose at "the lowest stakes (its actions are undoable, doc 08)", so these
calls take no qualification gate, unlike the verification judge's.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.repositories.relational import PostgresMemoryRepository
from app.repositories.memory_relations import (
    get_edge,
    pass_block_of,
    upsert_edge,
)
from app.repositories.vector import MemoryFilter, PostgresVectorRepository
from app.services.embedder_registry import child_table
from app.services.events import record_event
from app.services.extraction_clean import _content_seed, _loads_extraction
from app.services.supersede import successor_is_newer, supersede
from app.utils.ids import new_id

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 50
MAX_BATCH_SIZE = 1000
DEFAULT_PAIR_CANDIDATES = 5
DEFAULT_NEAR_DUPLICATE_THRESHOLD_PCT = 92
DEFAULT_JUDGE_FANOUT = 25
DEFAULT_REFINE_BATCH = 25
DEFAULT_WRITE_BATCH = 25
DEFAULT_LLM_CONCURRENCY = 4

# The pass's own key under `memory_relations.properties.dream`. Keyed by pass
# name so a sibling derivation pass can coexist on the one row the UNIQUE forces
# them to share.
NEAR_DUPLICATE_PASS = "near_duplicate"

HYGIENE_STATE_OPEN = "open"

# Internal bookkeeping, never an operator knob: `JobRegistry.set_config`
# validates against the job's schema and would reject it.
_STATE_CONFIG_KEY = "memory_dream_state"

SKIPPED_LLM_UNAVAILABLE = "llm_unavailable"
SKIPPED_FINGERPRINT_UNRESOLVED = "fingerprint_unresolved"
SKIPPED_NO_SEED_VECTORS = "no_seed_vectors"

# What the canary embeds. Its content is irrelevant — only the fingerprint the
# call returns is used — but it is short so the probe costs one small request.
_CANARY_TEXT = "fingerprint canary"

# The sentinel `llm_fingerprint()` emits under an unset `dimensions`. A canary
# that comes back wearing it means no real vector was measured.
_SENTINEL_DIMS_SUFFIX = "|0"


def content_sha(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MemoryRow:
    """One eligible memory, as Phase R read it."""

    memory_id: str
    project: str
    created_at: datetime
    content: str
    summary: str | None
    metadata: dict
    tags: tuple[str, ...]

    @property
    def content_sha(self) -> str:
        return content_sha(self.content)


@dataclass(frozen=True)
class PairCandidate:
    """An ordered near-duplicate candidate. ``older``/``newer`` are decided by
    :func:`order_pair`, never by the model."""

    older: MemoryRow
    newer: MemoryRow
    score: float

    @property
    def key(self) -> frozenset[str]:
        return frozenset({self.older.memory_id, self.newer.memory_id})


@dataclass
class DreamOutcome:
    cycle_id: str = ""
    seeds_visited: int = 0
    pairs_considered: int = 0
    pairs_skipped_no_vector: int = 0
    judged: int = 0
    judge_failed: int = 0
    subsumed: int = 0
    associated: int = 0
    associate_unchanged: int = 0
    refined: int = 0
    refine_failed: int = 0
    stale_skipped: int = 0
    failed: int = 0
    refused_already_superseded: int = 0
    refused_terminal: int = 0
    refused_not_newer: int = 0
    refused_cross_project: int = 0
    refused_self_reference: int = 0
    refused_not_found: int = 0
    skipped_reason: str | None = None
    cursor_created_at: datetime | None = None
    cursor_id: str | None = None
    wrapped: bool = False


# ── persisted cursor state ───────────────────────────────────────────────


@dataclass(frozen=True)
class _State:
    seed_created_at: datetime | None = None
    seed_id: str | None = None

    @classmethod
    def from_dict(cls, raw: dict) -> "_State":
        stamp = raw.get("seed_created_at")
        parsed: datetime | None = None
        if isinstance(stamp, str):
            try:
                parsed = datetime.fromisoformat(stamp)
            except ValueError:
                parsed = None
        seed_id = raw.get("seed_id")
        return cls(
            seed_created_at=parsed,
            seed_id=str(seed_id) if seed_id else None,
        )

    def to_dict(self) -> dict:
        return {
            "seed_created_at": (
                self.seed_created_at.isoformat() if self.seed_created_at else None
            ),
            "seed_id": self.seed_id,
        }


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


# ── Phase R: the fingerprint, the seed slice, the pairs ──────────────────


async def resolve_fingerprint(llm) -> str | None:
    """The active partition's fingerprint, measured rather than configured.

    ``None`` means the run must stop: either the canary raised, or it came back
    carrying the zero-dimension sentinel, which says the configured dimensions
    are unset and no real vector was ever measured. Both are run-level failures
    — a probe against the sentinel partition finds nothing and looks exactly
    like a store with no near-duplicates in it.
    """
    try:
        _, fingerprint = await llm.embed(_CANARY_TEXT)
    except Exception:
        logger.warning(
            "memory dream: the fingerprint canary embed failed; the run reads "
            "no partition rather than guessing one",
            exc_info=True,
        )
        return None
    if not fingerprint or fingerprint.endswith(_SENTINEL_DIMS_SUFFIX):
        logger.warning(
            "memory dream: the canary returned the zero-dimension fingerprint "
            "%r, so no real vector was measured; the run reads no partition",
            fingerprint,
        )
        return None
    return fingerprint


# The same eligibility predicate topic detection uses, so two consolidation
# passes cannot disagree about which memories exist. The cursor is the
# `(created_at, id)` tuple rather than a bare timestamp: same-batch rows share
# one server-side `created_at`, so a bare `>` would skip every row after the
# first at any given instant.
_NEXT_SEEDS = text(
    """
    SELECT CAST(m.id AS text) AS memory_id,
           m.project,
           m.created_at,
           m.content,
           m.summary,
           m.metadata,
           COALESCE(
               ARRAY(
                   SELECT t.name FROM memory_tags mt
                   JOIN tags t ON t.id = mt.tag_id
                   WHERE mt.memory_id = m.id
                   ORDER BY t.name
               ),
               CAST(ARRAY[] AS text[])
           ) AS tag_names
    FROM memories m
    WHERE m.status = 'active'
      AND m.is_archived = false
      AND (m.expires_at IS NULL OR m.expires_at > now())
      AND (
            CAST(:after_created_at AS timestamptz) IS NULL
            OR (m.created_at, m.id)
                 > (CAST(:after_created_at AS timestamptz), CAST(:after_id AS uuid))
          )
    ORDER BY m.created_at, m.id
    LIMIT CAST(:batch_size AS int)
    """
)

_READ_MEMORIES = text(
    """
    SELECT CAST(m.id AS text) AS memory_id,
           m.project,
           m.created_at,
           m.content,
           m.summary,
           m.metadata,
           COALESCE(
               ARRAY(
                   SELECT t.name FROM memory_tags mt
                   JOIN tags t ON t.id = mt.tag_id
                   WHERE mt.memory_id = m.id
                   ORDER BY t.name
               ),
               CAST(ARRAY[] AS text[])
           ) AS tag_names
    FROM memories m
    WHERE m.id = ANY(CAST(:ids AS uuid[]))
    """
)


def _row_to_memory(row) -> MemoryRow:
    metadata = row["metadata"]
    return MemoryRow(
        memory_id=row["memory_id"],
        project=row["project"],
        created_at=row["created_at"],
        content=row["content"],
        summary=row["summary"],
        metadata=metadata if isinstance(metadata, dict) else {},
        tags=tuple(row["tag_names"] or ()),
    )


async def next_seeds(
    session: AsyncSession,
    *,
    state: _State,
    batch_size: int,
) -> tuple[list[MemoryRow], bool]:
    """One rotating slice of eligible memories, and whether the cursor wrapped.

    A slice that comes back empty with a cursor set means the cursor has run off
    the end, so it restarts from the beginning in the same call — otherwise the
    job would visit nothing for as long as no memory newer than the cursor
    exists.
    """

    async def fetch(after: _State) -> list[MemoryRow]:
        result = await session.execute(
            _NEXT_SEEDS,
            {
                "after_created_at": after.seed_created_at,
                "after_id": after.seed_id,
                "batch_size": batch_size,
            },
        )
        return [_row_to_memory(row) for row in result.mappings()]

    rows = await fetch(state)
    if rows or state.seed_created_at is None:
        return rows, False
    return await fetch(_State()), True


async def read_memories(
    session: AsyncSession, memory_ids: list[str]
) -> dict[str, MemoryRow]:
    if not memory_ids:
        return {}
    result = await session.execute(_READ_MEMORIES, {"ids": list(memory_ids)})
    return {row["memory_id"]: _row_to_memory(row) for row in result.mappings()}


async def seed_vectors(
    session: AsyncSession, *, fingerprint: str, memory_ids: list[str]
) -> dict[str, list[float]]:
    """Every seed's vector from the active partition, in one read.

    Never falls back to another fingerprint: a cross-fingerprint cosine has no
    defined meaning (invariant 3), so a seed with no row here is skipped rather
    than probed somewhere else.
    """
    if not memory_ids:
        return {}
    table = child_table("memory_embeddings", fingerprint)
    result = await session.execute(
        text(
            f"SELECT CAST(memory_id AS text) AS memory_id, "
            f"       embedding::text AS embedding_text "
            f"FROM {table} WHERE memory_id = ANY(CAST(:ids AS uuid[]))"
        ),
        {"ids": list(memory_ids)},
    )
    return {
        row["memory_id"]: PostgresVectorRepository._parse_vector(row["embedding_text"])
        for row in result.mappings()
    }


def order_pair(left: MemoryRow, right: MemoryRow) -> tuple[MemoryRow, MemoryRow]:
    """``(older, newer)`` under the primitive's own ordering predicate.

    Delegated rather than re-spelled: `successor_is_newer` normalises both ids
    through ``UUID(str(...))``, so a re-spelled comparison would order
    same-`created_at` pairs by text and disagree with the writer on exactly the
    rows the tie-break exists for.
    """
    if successor_is_newer(
        candidate_created_at=left.created_at,
        candidate_id=left.memory_id,
        successor_created_at=right.created_at,
        successor_id=right.memory_id,
    ):
        return left, right
    return right, left


async def generate_pairs(
    session: AsyncSession,
    *,
    seeds: list[MemoryRow],
    fingerprint: str,
    pair_candidates: int,
    near_duplicate_threshold_pct: int,
    judge_fanout: int,
    outcome: DreamOutcome,
) -> list[PairCandidate]:
    """One ANN probe per seed, project-scoped and fingerprint-pinned.

    The ``MemoryFilter`` is enforcement, not decoration: without it the probe
    crosses projects, and the primitive would refuse every such pair with
    ``cross_project`` — turning a design error into a silent refusal count.
    """
    if not seeds or judge_fanout <= 0:
        return []

    vectors = await seed_vectors(
        session, fingerprint=fingerprint, memory_ids=[s.memory_id for s in seeds]
    )
    threshold = near_duplicate_threshold_pct / 100
    repository = PostgresVectorRepository(session)

    scored: dict[frozenset[str], tuple[float, str, str]] = {}
    for seed in seeds:
        vector = vectors.get(seed.memory_id)
        if vector is None:
            outcome.pairs_skipped_no_vector += 1
            continue
        rows = await repository.search(
            vector,
            fingerprint,
            limit=pair_candidates + 1,
            filters=MemoryFilter(project=seed.project, statuses=("active",)),
        )
        for row in rows:
            other = str(row["memory_id"])
            if other == seed.memory_id:
                continue
            if float(row["score"]) < threshold:
                continue
            # One unordered pair, judged once: A's probe finding B and B's probe
            # finding A are the same pair, and judging it twice would double the
            # cost and could produce two contradictory verdicts in one cycle.
            key = frozenset({seed.memory_id, other})
            previous = scored.get(key)
            if previous is None or float(row["score"]) > previous[0]:
                scored[key] = (float(row["score"]), seed.memory_id, other)

    if not scored:
        return []

    known = {seed.memory_id: seed for seed in seeds}
    missing = [
        identifier
        for _, left, right in scored.values()
        for identifier in (left, right)
        if identifier not in known
    ]
    known.update(await read_memories(session, sorted(set(missing))))

    pairs: list[PairCandidate] = []
    for score, left, right in sorted(
        scored.values(), key=lambda item: (-item[0], item[1], item[2])
    ):
        first, second = known.get(left), known.get(right)
        if first is None or second is None:
            continue
        older, newer = order_pair(first, second)
        pairs.append(PairCandidate(older=older, newer=newer, score=score))

    outcome.pairs_considered = len(pairs)
    return pairs[:judge_fanout]


# ── Phase C: the judge ───────────────────────────────────────────────────

# The `reasoning` purpose, and nothing else. Doc 11 §6 puts dream-refine's
# merge/rewrite judgments there explicitly, at "the lowest stakes (its actions
# are undoable, doc 08)", which is why these calls carry no qualification gate.
JUDGE_PURPOSE = "reasoning"

PAIR_VERDICTS = frozenset({"subsumes", "duplicate", "distinct"})

PAIR_SYSTEM_PROMPT = """\
You compare two stored memories from one project. The pair is already ordered
for you: OLDER was captured first, NEWER second. Never reorder them and never
suggest the older one replaces the newer.

Return exactly one verdict:

- "subsumes": NEWER states everything OLDER does and corrects or completes it,
  so keeping OLDER active would leave a stale claim in the store.
- "duplicate": the two say substantially the same thing, but NEWER does not
  correct OLDER — neither should retire the other.
- "distinct": they are about different things, or each carries something the
  other does not.

Answer with a JSON object: {"verdict": "...", "reason": "<one short sentence>"}
"""

REFINE_SYSTEM_PROMPT = """\
You improve the derived enrichment of one stored memory. You may propose a
rewritten one-sentence summary and a cleaned tag list.

You may not rewrite, extend, correct or restate the memory's content — the
content is the record and is never edited. Return only the derived fields.

Answer with a JSON object: {"summary": "<one sentence>", "tags": ["...", ...]}
Use null for a field you do not want changed.
"""


class JudgeError(RuntimeError):
    """The model's answer could not be used.

    One error for every unusable shape — unparseable, truncated, missing key,
    unknown verdict — because the arm's response to all of them is identical:
    count it, take no action for that item, and never fall back to a default
    verdict. A default would let a broken model quietly drive real writes.
    """


@dataclass(frozen=True)
class PairVerdict:
    verdict: str
    reason: str


@dataclass(frozen=True)
class RefineVerdict:
    """A closed shape with no field that could carry content.

    The allowlist below refuses a content write on its own; this dataclass is
    the second, independent layer. Neither is redundant: dropping either one
    leaves a path by which a model's `content` key could reach a column.
    """

    summary: str | None
    tags: tuple[str, ...] | None


def build_pair_messages(older: MemoryRow, newer: MemoryRow) -> list[dict]:
    return [
        {"role": "system", "content": PAIR_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"OLDER:\n{older.content}\n\nNEWER:\n{newer.content}",
        },
    ]


def build_refine_messages(memory: MemoryRow) -> list[dict]:
    current = memory.summary or "(none)"
    tags = ", ".join(memory.tags) or "(none)"
    return [
        {"role": "system", "content": REFINE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"CONTENT:\n{memory.content}\n\n"
                f"CURRENT SUMMARY:\n{current}\n\n"
                f"CURRENT TAGS:\n{tags}"
            ),
        },
    ]


def pair_seed(older: MemoryRow, newer: MemoryRow) -> int:
    """Reproducibility (CLAUDE.md): the same pair replays to the same JSON.

    Seeded on both contents in their fixed order, so the seed is a property of
    the ordered pair rather than of whichever half the probe happened to start
    from."""
    return _content_seed(f"{older.content}\n{newer.content}")


def refine_seed(memory: MemoryRow) -> int:
    return _content_seed(memory.content)


def parse_pair_verdict(raw: str) -> PairVerdict:
    try:
        body = _loads_extraction(raw)
    except Exception as exc:
        raise JudgeError(f"pair verdict was not JSON: {raw[:120]!r}") from exc
    if not isinstance(body, dict):
        raise JudgeError("pair verdict was not a JSON object")
    verdict = body.get("verdict")
    if verdict not in PAIR_VERDICTS:
        raise JudgeError(f"pair verdict {verdict!r} is outside the closed set")
    reason = body.get("reason")
    return PairVerdict(
        verdict=verdict, reason=str(reason) if reason is not None else ""
    )


def parse_refine(raw: str) -> RefineVerdict:
    """Every key outside the closed shape is discarded here, before the
    allowlist ever sees it."""
    try:
        body = _loads_extraction(raw)
    except Exception as exc:
        raise JudgeError(f"refine answer was not JSON: {raw[:120]!r}") from exc
    if not isinstance(body, dict):
        raise JudgeError("refine answer was not a JSON object")

    summary = body.get("summary")
    if summary is not None and not isinstance(summary, str):
        raise JudgeError("refine summary was not a string")
    if isinstance(summary, str):
        summary = summary.strip() or None

    raw_tags = body.get("tags")
    tags: tuple[str, ...] | None = None
    if raw_tags is not None:
        if not isinstance(raw_tags, list):
            raise JudgeError("refine tags were not a list")
        cleaned = [str(tag).strip() for tag in raw_tags if str(tag).strip()]
        tags = tuple(dict.fromkeys(cleaned))

    if summary is None and tags is None:
        raise JudgeError("refine answer proposed no derived field")
    return RefineVerdict(summary=summary, tags=tags)


async def judge_pair(llm, older: MemoryRow, newer: MemoryRow) -> PairVerdict:
    raw = await llm.chat_completion(
        JUDGE_PURPOSE,
        build_pair_messages(older, newer),
        response_format={"type": "json_object"},
        seed=pair_seed(older, newer),
    )
    return parse_pair_verdict(raw)


async def judge_refine(llm, memory: MemoryRow) -> RefineVerdict:
    raw = await llm.chat_completion(
        JUDGE_PURPOSE,
        build_refine_messages(memory),
        response_format={"type": "json_object"},
        seed=refine_seed(memory),
    )
    return parse_refine(raw)


# ── Phase W: apply, one savepoint per action ─────────────────────────────

EVENT_TYPE = "consolidated"
OBJECT_TYPE = "memory"
DETECTOR = "dedup"

ACTION_SUBSUME = "subsume"
ACTION_ASSOCIATE = "associate"
ACTION_REFINE = "refine"

# Scoped inside each action's SAVEPOINT via `SET LOCAL`, so a wedged row lock
# becomes an ordinary per-action failure instead of consuming the whole tick's
# `max_run_seconds` and voiding every action the tick had already taken. A
# literal rather than a bind parameter: `SET` takes no placeholder, and the
# value is a fixed internal constant.
_LOCK_TIMEOUT_MS = 5000

_LOCK_MEMORY = text("""
    SELECT status::text AS status,
           content,
           project,
           summary,
           metadata,
           CAST(superseded_by AS text) AS superseded_by
    FROM memories
    WHERE id = CAST(:memory_id AS uuid)
    FOR UPDATE
""")

# Every refusal is reported, never swallowed and never worked around.
_REFUSAL_COUNTERS = {
    "already_superseded": "refused_already_superseded",
    "terminal": "refused_terminal",
    "successor_not_newer": "refused_not_newer",
    "cross_project": "refused_cross_project",
    "self_reference": "refused_self_reference",
    "not_found": "refused_not_found",
}

# Refusals that mean something upstream is wrong rather than that the store
# moved: my ordering disagreed with the primitive's, the project filter was
# dropped, or pair dedup failed.
_ALARMING_REFUSALS = frozenset(
    {"successor_not_newer", "cross_project", "self_reference"}
)


@dataclass(frozen=True)
class SubsumeAction:
    pair: PairCandidate
    verdict: PairVerdict

    @property
    def memory_id(self) -> str:
        return self.pair.older.memory_id


@dataclass(frozen=True)
class AssociateAction:
    pair: PairCandidate
    verdict: PairVerdict

    @property
    def memory_id(self) -> str:
        return self.pair.newer.memory_id


async def _set_local_lock_timeout(session: AsyncSession) -> None:
    await session.execute(text(f"SET LOCAL lock_timeout = '{_LOCK_TIMEOUT_MS}ms'"))


async def _locked(session: AsyncSession, memory_id: str) -> dict | None:
    result = await session.execute(_LOCK_MEMORY, {"memory_id": memory_id})
    row = result.mappings().first()
    return dict(row) if row is not None else None


async def _journal(
    session: AsyncSession,
    *,
    memory_id: str,
    project: str,
    payload: dict,
) -> None:
    """One row per real transition, never one per no-op.

    ``events`` is append-only, so a phantom transition row can never be removed
    once written. Skips, refusals and unchanged edges are counted in the run
    outcome and logged; they journal nothing.
    """
    await record_event(
        session,
        event_type=EVENT_TYPE,
        object_type=OBJECT_TYPE,
        object_id=UUID(memory_id),
        project=project,
        payload=payload,
    )


async def apply_subsume(
    session: AsyncSession,
    action: SubsumeAction,
    *,
    cycle_id: str,
    outcome: DreamOutcome,
) -> bool:
    """Flip the older half of one judged pair, inside the caller's savepoint.

    Phase C computed on a snapshot; between the read and here a delete could
    have removed either half, or a re-extraction could have changed its content
    out from under the verdict. A mismatch is a skip, never a write.

    **The candidate's status is deliberately not re-checked here.** The
    primitive re-reads it under its own ``FOR UPDATE`` and names the refusal
    precisely — ``already_superseded`` when an earlier action this same cycle
    already retired the row, ``terminal`` when it is deprecated. Pre-empting it
    with a local status check would collapse both into one anonymous skip and
    leave the refusal table with no reachable path.
    """
    await _set_local_lock_timeout(session)
    older, newer = action.pair.older, action.pair.newer

    locked = await _locked(session, older.memory_id)
    successor = await _locked(session, newer.memory_id)
    if locked is None or successor is None:
        outcome.stale_skipped += 1
        return False
    if content_sha(locked["content"]) != older.content_sha:
        outcome.stale_skipped += 1
        return False
    if content_sha(successor["content"]) != newer.content_sha:
        outcome.stale_skipped += 1
        return False

    before = {
        "status": locked["status"],
        "superseded_by": locked["superseded_by"],
    }
    result = await supersede(
        session,
        memory_id=older.memory_id,
        superseded_by=newer.memory_id,
    )
    if not result.applied:
        counter = _REFUSAL_COUNTERS.get(result.reason)
        if counter is not None:
            setattr(outcome, counter, getattr(outcome, counter) + 1)
        if result.reason in _ALARMING_REFUSALS:
            # Never retried with the endpoints swapped: a retry in the other
            # direction supersedes a newer memory with an older one, which the
            # promotion blocker cannot see.
            logger.warning(
                "memory dream: supersede refused %s -> %s with %s",
                older.memory_id, newer.memory_id, result.reason,
            )
        return False

    await _journal(
        session,
        memory_id=older.memory_id,
        project=older.project,
        payload={
            "action": ACTION_SUBSUME,
            "before": before,
            "after": {
                "status": result.status,
                "superseded_by": result.superseded_by,
            },
            "pair": {"older": older.memory_id, "newer": newer.memory_id},
            "detector": DETECTOR,
            "verdict": action.verdict.verdict,
            "score": action.pair.score,
            "cycle_id": cycle_id,
        },
    )
    outcome.subsumed += 1
    return True


# A score bucket rather than the raw float: two cycles that scored the same pair
# 0.9412 and 0.9413 have not learned anything a hygiene queue can act on, and
# treating that as a change would re-journal the pair every night forever.
_SCORE_BUCKET = 100


def _score_bucket(score: float) -> int:
    return int(round(score * _SCORE_BUCKET))


def near_duplicate_block(
    *, score: float, verdict: str, existing: dict | None, detected_at: str
) -> dict:
    """This pass's block, composed from the edge as it was read.

    ``hygiene_state`` is carried forward verbatim whenever the block already
    exists and only defaulted to ``open`` when it does not: it belongs to the
    triage queue, and re-deriving a still-similar pair must never roll a
    human's confirm or dismiss back to the derived default.
    """
    state = (existing or {}).get("hygiene_state") or HYGIENE_STATE_OPEN
    return {
        "kind": "duplicate_candidate",
        "hygiene_state": state,
        "score": score,
        "verdict": verdict,
        "detected_at": detected_at,
    }


def _edge_is_unchanged(existing: dict | None, block: dict) -> bool:
    if not existing:
        return False
    return (
        existing.get("kind") == block["kind"]
        and existing.get("verdict") == block["verdict"]
        and _score_bucket(float(existing.get("score") or 0.0))
        == _score_bucket(float(block["score"]))
    )


async def apply_associate(
    session: AsyncSession,
    action: AssociateAction,
    *,
    cycle_id: str,
    outcome: DreamOutcome,
) -> bool:
    """Mark a near-duplicate pair with one associative edge.

    Writes nothing and journals nothing when its own block is already there
    unchanged. Without that skip a stable pair would accrete one `associate`
    event per cycle, forever, into an append-only journal, for a row that never
    moved.
    """
    await _set_local_lock_timeout(session)
    older, newer = action.pair.older, action.pair.newer

    locked = await _locked(session, older.memory_id)
    successor = await _locked(session, newer.memory_id)
    if locked is None or successor is None:
        outcome.stale_skipped += 1
        return False
    if content_sha(locked["content"]) != older.content_sha:
        outcome.stale_skipped += 1
        return False
    if content_sha(successor["content"]) != newer.content_sha:
        outcome.stale_skipped += 1
        return False

    rel_type = "ELABORATES" if action.verdict.verdict == "subsumes" else "RELATES_TO"
    existing_edge = await get_edge(
        session,
        source_memory_id=newer.memory_id,
        target_memory_id=older.memory_id,
        rel_type=rel_type,
    )
    existing_block = pass_block_of(existing_edge, NEAR_DUPLICATE_PASS)
    block = near_duplicate_block(
        score=action.pair.score,
        verdict=action.verdict.verdict,
        existing=existing_block,
        detected_at=datetime.now(timezone.utc).isoformat(),
    )
    if _edge_is_unchanged(existing_block, block):
        outcome.associate_unchanged += 1
        return False

    write = await upsert_edge(
        session,
        source_memory_id=newer.memory_id,
        target_memory_id=older.memory_id,
        rel_type=rel_type,
        project=newer.project,
        pass_key=NEAR_DUPLICATE_PASS,
        block=block,
    )
    await _journal(
        session,
        memory_id=newer.memory_id,
        project=newer.project,
        payload={
            "action": ACTION_ASSOCIATE,
            "before": {"edge": existing_block},
            "after": {
                "edge": {
                    "source": newer.memory_id,
                    "target": older.memory_id,
                    "rel_type": rel_type,
                    "properties": {NEAR_DUPLICATE_PASS: block},
                }
            },
            "created": write.created,
            "pair": {"older": older.memory_id, "newer": newer.memory_id},
            "detector": DETECTOR,
            "verdict": action.verdict.verdict,
            "score": action.pair.score,
            "cycle_id": cycle_id,
        },
    )
    outcome.associated += 1
    return True



# The whole set of columns refine may move, and the `UPDATE` below is *built*
# from it rather than hand-written. A model that answers `{"content": "..."}`
# therefore cannot reach a column even if the parser were sloppy — and the
# parser discards unknown keys too, so it is refused twice, independently.
_REFINABLE_COLUMNS: tuple[str, ...] = ("summary",)

# The marker records the content revision this pass has already acted on —
# suppression bookkeeping, not a provenance claim that the summary now in place
# was derived from it. After an undo the two legitimately disagree.
REFINE_MARKER_PATH = ("dream", "refine")


class RefinableColumnError(ValueError):
    """A caller asked to write a column outside the allowlist."""


@dataclass(frozen=True)
class RefineAction:
    memory: MemoryRow
    verdict: RefineVerdict

    @property
    def memory_id(self) -> str:
        return self.memory.memory_id


def refine_marker_of(metadata: dict | None) -> dict | None:
    node = metadata if isinstance(metadata, dict) else {}
    for key in REFINE_MARKER_PATH:
        node = node.get(key) if isinstance(node, dict) else None
        if node is None:
            return None
    return node if isinstance(node, dict) else None


def needs_refine(memory: MemoryRow) -> bool:
    """Keyed on ``content_sha`` alone, and deliberately not also on the summary.

    If T2.13's undo restores the prior summary, a summary-keyed rule would see a
    mismatch and re-apply the refine on the next cycle — silently undoing the
    undo. Keying on the input alone means an undone refine stays undone until
    the memory's content genuinely changes.
    """
    marker = refine_marker_of(memory.metadata)
    return not marker or marker.get("content_sha") != memory.content_sha


def build_refine_update(fields: dict) -> tuple[str, tuple[str, ...]]:
    """The `UPDATE memories SET ...` fragment, assembled from the allowlist.

    Raises rather than filtering, because a key outside the allowlist means the
    caller believed it could write something it cannot, and silently dropping it
    would make that belief invisible.
    """
    unknown = [key for key in fields if key not in _REFINABLE_COLUMNS]
    if unknown:
        raise RefinableColumnError(
            f"refine may only write {list(_REFINABLE_COLUMNS)}; refused "
            f"{sorted(unknown)}"
        )
    ordered = tuple(column for column in _REFINABLE_COLUMNS if column in fields)
    assignments = ", ".join(f"{column} = :{column}" for column in ordered)
    return assignments, ordered


async def apply_refine(
    session: AsyncSession,
    action: RefineAction,
    *,
    cycle_id: str,
    outcome: DreamOutcome,
) -> bool:
    """Rewrite one memory's derived enrichment, and nothing else.

    The suppression marker rides the *same* statement as the summary, so a
    marker can never record a refine that did not land.
    """
    await _set_local_lock_timeout(session)
    memory = action.memory

    locked = await _locked(session, memory.memory_id)
    if locked is None or locked["status"] != "active":
        outcome.stale_skipped += 1
        return False
    if content_sha(locked["content"]) != memory.content_sha:
        outcome.stale_skipped += 1
        return False

    before_marker = refine_marker_of(locked["metadata"])
    if before_marker and before_marker.get("content_sha") == memory.content_sha:
        outcome.stale_skipped += 1
        return False

    proposed: dict = {}
    if action.verdict.summary is not None:
        proposed["summary"] = action.verdict.summary
    assignments, ordered = build_refine_update(proposed)

    marker = {
        "content_sha": memory.content_sha,
        "at": datetime.now(timezone.utc).isoformat(),
        "summary_sha": (
            content_sha(action.verdict.summary)
            if action.verdict.summary is not None
            else None
        ),
    }
    params: dict = {"memory_id": memory.memory_id, "marker": json.dumps(marker)}
    params.update({column: proposed[column] for column in ordered})
    set_clause = f"{assignments}, " if assignments else ""
    await session.execute(
        text(
            f"UPDATE memories SET {set_clause}"
            "    metadata = jsonb_set("
            "        jsonb_set("
            "            COALESCE(metadata, CAST('{}' AS jsonb)),"
            "            '{dream}',"
            "            COALESCE(metadata -> 'dream', CAST('{}' AS jsonb)),"
            "            true"
            "        ),"
            "        '{dream,refine}',"
            "        CAST(:marker AS jsonb),"
            "        true"
            "    ) "
            "WHERE id = CAST(:memory_id AS uuid)"
        ),
        params,
    )

    changed = list(ordered)
    if action.verdict.tags is not None:
        await PostgresMemoryRepository(session).set_tags(
            UUID(memory.memory_id), list(action.verdict.tags)
        )
        changed.append("tags")

    await _journal(
        session,
        memory_id=memory.memory_id,
        project=memory.project,
        payload={
            "action": ACTION_REFINE,
            "before": {
                "summary": locked["summary"],
                "tags": list(memory.tags),
                "metadata_dream_refine": before_marker,
            },
            "after": {
                "summary": proposed.get("summary", locked["summary"]),
                "tags": (
                    list(action.verdict.tags)
                    if action.verdict.tags is not None
                    else list(memory.tags)
                ),
                "metadata_dream_refine": marker,
            },
            "fields": changed,
            "detector": DETECTOR,
            "cycle_id": cycle_id,
        },
    )
    outcome.refined += 1
    return True



# ── the run ──────────────────────────────────────────────────────────────


async def _judge_pairs(
    llm,
    pairs: list[PairCandidate],
    *,
    llm_concurrency: int,
    outcome: DreamOutcome,
) -> list[SubsumeAction]:
    """Phase C for the pair arm: no transaction is open across any of this."""
    if not pairs:
        return []

    semaphore = asyncio.Semaphore(max(1, llm_concurrency))

    async def judge(pair: PairCandidate):
        async with semaphore:
            try:
                return pair, await judge_pair(llm, pair.older, pair.newer)
            except Exception:
                logger.warning(
                    "memory dream: the pair judge failed for %s / %s",
                    pair.older.memory_id, pair.newer.memory_id,
                    exc_info=True,
                )
                return pair, None

    results = await asyncio.gather(*[judge(pair) for pair in pairs])

    actions: list[SubsumeAction] = []
    for pair, verdict in results:
        if verdict is None:
            outcome.judge_failed += 1
            continue
        outcome.judged += 1
        if verdict.verdict == "subsumes":
            actions.append(SubsumeAction(pair=pair, verdict=verdict))
        elif verdict.verdict == "duplicate":
            actions.append(AssociateAction(pair=pair, verdict=verdict))
    return actions


async def _judge_refines(
    llm,
    targets: list[MemoryRow],
    *,
    llm_concurrency: int,
    outcome: DreamOutcome,
) -> list[RefineAction]:
    if not targets:
        return []

    semaphore = asyncio.Semaphore(max(1, llm_concurrency))

    async def judge(memory: MemoryRow):
        async with semaphore:
            try:
                return memory, await judge_refine(llm, memory)
            except Exception:
                logger.warning(
                    "memory dream: the refine judge failed for %s",
                    memory.memory_id, exc_info=True,
                )
                return memory, None

    results = await asyncio.gather(*[judge(memory) for memory in targets])

    actions: list[RefineAction] = []
    for memory, proposal in results:
        if proposal is None:
            outcome.refine_failed += 1
            continue
        actions.append(RefineAction(memory=memory, verdict=proposal))
    return actions


async def _apply(
    session: AsyncSession, action, *, cycle_id: str, outcome: DreamOutcome
) -> None:
    """One action in one savepoint, so a poisonous item settles alone."""
    try:
        async with session.begin_nested():
            if isinstance(action, SubsumeAction):
                await apply_subsume(
                    session, action, cycle_id=cycle_id, outcome=outcome
                )
            elif isinstance(action, AssociateAction):
                await apply_associate(
                    session, action, cycle_id=cycle_id, outcome=outcome
                )
            elif isinstance(action, RefineAction):
                await apply_refine(
                    session, action, cycle_id=cycle_id, outcome=outcome
                )
    except Exception:
        logger.warning(
            "memory dream: an action failed and was rolled back", exc_info=True
        )
        outcome.failed += 1


async def run_memory_dream(
    session_factory,
    llm_provider,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    pair_candidates: int = DEFAULT_PAIR_CANDIDATES,
    near_duplicate_threshold_pct: int = DEFAULT_NEAR_DUPLICATE_THRESHOLD_PCT,
    judge_fanout: int = DEFAULT_JUDGE_FANOUT,
    refine_batch: int = DEFAULT_REFINE_BATCH,
    write_batch: int = DEFAULT_WRITE_BATCH,
    llm_concurrency: int = DEFAULT_LLM_CONCURRENCY,
) -> DreamOutcome:
    """One dreaming cycle: read, judge, apply.

    Writes nothing and deletes nothing when it computed nothing — a missing
    provider and an unresolvable fingerprint both stop the run before Phase W,
    the same discipline topic detection applies to a missing clustering
    library, and for the same reason.
    """
    outcome = DreamOutcome(cycle_id=str(new_id()))

    llm = llm_provider() if callable(llm_provider) else llm_provider
    if llm is None:
        outcome.skipped_reason = SKIPPED_LLM_UNAVAILABLE
        logger.warning("memory dream: no LLM provider; the cycle does nothing")
        return outcome

    fingerprint = await resolve_fingerprint(llm)
    if fingerprint is None:
        outcome.skipped_reason = SKIPPED_FINGERPRINT_UNRESOLVED
        return outcome

    # Phase R. Read-only, and committed before the LLM fan-out so a pooled
    # connection does not sit `idle in transaction` for minutes.
    async with session_factory() as session:
        state = await _load_state(session)
        seeds, outcome.wrapped = await next_seeds(
            session, state=state, batch_size=batch_size
        )
        outcome.seeds_visited = len(seeds)
        pairs = await generate_pairs(
            session,
            seeds=seeds,
            fingerprint=fingerprint,
            pair_candidates=pair_candidates,
            near_duplicate_threshold_pct=near_duplicate_threshold_pct,
            judge_fanout=judge_fanout,
            outcome=outcome,
        )
        refine_targets = [
            seed for seed in seeds if needs_refine(seed)
        ][:max(0, refine_batch)]
        await session.commit()

    if seeds and outcome.pairs_skipped_no_vector == len(seeds):
        # The per-seed counter is the honest unit for one memory never
        # re-embedded after a rotation; it is the wrong unit for "the partition
        # this job reads is empty", and only the run-level check tells them
        # apart.
        outcome.skipped_reason = SKIPPED_NO_SEED_VECTORS
        logger.warning(
            "memory dream: no seed in a slice of %d had a vector under %s",
            len(seeds), fingerprint,
        )

    # Phase C — no transaction is open across any of this.
    actions: list = await _judge_pairs(
        llm, pairs, llm_concurrency=llm_concurrency, outcome=outcome
    )
    actions += await _judge_refines(
        llm, refine_targets, llm_concurrency=llm_concurrency, outcome=outcome
    )

    # Phase W.
    advanced = seeds[-1] if seeds else None
    batches = [
        actions[index:index + write_batch]
        for index in range(0, len(actions), max(1, write_batch))
    ] or [[]]
    for index, batch in enumerate(batches):
        async with session_factory() as session:
            for action in batch:
                await _apply(
                    session, action, cycle_id=outcome.cycle_id, outcome=outcome
                )
            if index == len(batches) - 1 and advanced is not None:
                # The cursor advances in the last batch's commit, not per
                # batch: one seed's actions can straddle two batches, so no
                # batch boundary corresponds to a seed the cursor could
                # honestly point past. A crash re-does at most one slice, and
                # every action is idempotent on replay.
                await _save_state(
                    session,
                    _State(
                        seed_created_at=advanced.created_at,
                        seed_id=advanced.memory_id,
                    ),
                )
                outcome.cursor_created_at = advanced.created_at
                outcome.cursor_id = advanced.memory_id
            await session.commit()

    logger.info(
        "memory dream cycle %s visited %d seed(s): %d pair(s) judged, "
        "%d subsumed, %d associated (%d unchanged), %d refined, "
        "%d stale-skipped, %d failed%s",
        outcome.cycle_id, outcome.seeds_visited, outcome.judged,
        outcome.subsumed, outcome.associated, outcome.associate_unchanged,
        outcome.refined, outcome.stale_skipped, outcome.failed,
        f" (skipped: {outcome.skipped_reason})" if outcome.skipped_reason else "",
    )
    return outcome
