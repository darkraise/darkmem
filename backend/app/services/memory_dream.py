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

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.repositories.vector import MemoryFilter, PostgresVectorRepository
from app.services.embedder_registry import child_table
from app.services.extraction_clean import _content_seed, _loads_extraction
from app.services.supersede import successor_is_newer

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
    events: list[dict] = field(default_factory=list)


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
