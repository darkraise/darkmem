"""Tier-B flush: claim buffered captures and replay them through the pipeline.

Doc 05 §3. Capture (Tier A) commits a `memory_buffer` row and acks; this module
is the other half — a `JobRegistry` job that claims a batch of those rows with
`SELECT … FOR UPDATE SKIP LOCKED`, materialises each into its pre-minted
`memories` row, and hands the batch to `ProcessingPipeline.process_batch`.

Three properties carry the tier, and every one of them fails silently:

**A row is never processed twice.** The claim is one `UPDATE … FROM c`
statement over a `WITH c AS MATERIALIZED (SELECT … FOR UPDATE SKIP LOCKED)` row
set. The locking clause is what makes it safe: Postgres re-evaluates the row
set's `status='pending'` qual against the freshly-committed row after the lock
is released (EvalPlanQual), so a claimer that raced another one comes away with
nothing rather than with a row the other claimer already holds. Drop the
locking clause and the outer `b.id = c.id` has no status qual to recheck — both
claimers "win" the same row. `MATERIALIZED` is what bounds the claim; see
`_CLAIM_SQL`.

**A row is never stranded.** The claim transaction commits immediately, before
any pipeline session opens (invariant 11), so the row lock lives for exactly one
statement rather than for the length of an LLM round trip. That leaves a window
where a claimer can die with rows marked `claimed` and nobody holding them,
which `reclaim_stale` closes: rows claimed longer ago than
`buffer_claim_visibility_seconds` return to `pending`. Their `attempts` was
already incremented at claim time, so a capture that kills its worker every time
still walks into `buffer_max_attempts` instead of looping forever.

**Nothing captured is dropped.** Every field in
`memory_buffer.REPLAYED_METADATA_FIELDS` has to land somewhere on the `memories`
row; `_assert_replay_coverage` turns a field added to that tuple without a
replay into an import-time error rather than into data loss that reads as a
successful capture.

**A row fails alone.** Claiming is a batch operation but settling is per row.
Whatever a claimed row shares a batch with, only failures that are genuinely
batch-wide — a dead embedder, an exhausted deadline — may settle more than the
row that caused them. Everything that can fail on one row's own data settles
that row and lets its neighbours through; the batch is a throughput device, not
a fate the rows share. Without this, one 202-accepted capture carrying data the
schema cannot hold walks up to `buffer_claim_batch - 1` innocent, already
acknowledged captures into `error` beside it (Fable review of T1.13, I-1).
"""
from __future__ import annotations

import asyncio
import logging
import os
import socket
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.config import Config
from app.models.memory import Memory, MemoryBuffer
from app.repositories.relational import PostgresMemoryRepository
from app.services.job_registry import FieldDescriptor
from app.services.memory_buffer import REPLAYED_METADATA_FIELDS, buffered_memory_id
from app.services.pipeline_failures import derive_memory_failed_step

logger = logging.getLogger(__name__)

BUFFER_FLUSH_JOB_KEY = "buffer_flush"

# Doc 05 §3 / §3.1. `buffer_claim_batch` sizes ONE flush's claim and is tuned
# against the embed chunk so Phase-1 chunking stays efficient. It is deliberately
# not the capture door's 1-100 batch cap: that one bounds how much a single
# API/MCP call may submit, this one bounds internal throughput, and coupling them
# would stop either from moving on its own evidence.
BUFFER_FLUSH_DEFAULTS: dict[str, int] = {
    "buffer_claim_batch": 32,
    "buffer_max_attempts": 5,
    "buffer_claim_visibility_seconds": 300,
    "buffer_done_retention_hours": 24,
}

# Six-field, seconds first (Quartz-style): every five seconds. Tier B is not the
# p95-sensitive surface — a caller that cannot wait uses `wait_process` — so the
# worst-case queueing latency this buys is acceptable.
BUFFER_FLUSH_CRON = "*/5 * * * * *"
BUFFER_FLUSH_MIN_INTERVAL_SECONDS = 1
# The registry cancels a run at this ceiling, leaving its rows `claimed` for the
# next tick's stale sweep to recover. It must therefore not outlast
# `buffer_claim_visibility_seconds`, or a still-live run could have its own rows
# reclaimed underneath it.
BUFFER_FLUSH_MAX_RUN_SECONDS = 300
# What the flush leaves itself to settle its own rows before the registry's
# ceiling cancels it. A cancelled run never reaches a settle, so its rows sit
# `claimed` for a whole visibility window and burn the attempt they took at
# claim time with nothing recorded about why.
BUFFER_FLUSH_SETTLE_MARGIN_SECONDS = 10
BUFFER_FLUSH_DEADLINE_SECONDS = (
    BUFFER_FLUSH_MAX_RUN_SECONDS - BUFFER_FLUSH_SETTLE_MARGIN_SECONDS
)

BUFFER_FLUSH_CONFIG_SCHEMA: list[FieldDescriptor] = [
    FieldDescriptor(
        key="buffer_claim_batch", label="Claim Batch",
        default=BUFFER_FLUSH_DEFAULTS["buffer_claim_batch"], min=1, max=1000,
        help=(
            "Buffered captures claimed per flush. Sized near the embed chunk; "
            "unrelated to the capture endpoint's 1-100 submission cap."
        ),
    ),
    FieldDescriptor(
        key="buffer_max_attempts", label="Max Attempts",
        default=BUFFER_FLUSH_DEFAULTS["buffer_max_attempts"], min=1, max=100,
        help="Flush attempts before a row moves to error for triage.",
    ),
    FieldDescriptor(
        key="buffer_claim_visibility_seconds", label="Claim Visibility (s)",
        default=BUFFER_FLUSH_DEFAULTS["buffer_claim_visibility_seconds"],
        # Floored at BUFFER_FLUSH_MAX_RUN_SECONDS, not a smaller round number:
        # the registry cancels a run at that ceiling and leaves its rows
        # `claimed` for the next stale sweep, so a visibility window shorter
        # than the ceiling would let that sweep reclaim a run that is still
        # legitimately in flight — and, since T1.14, let a concurrent
        # wait_process claim the same row a second time before the original
        # runner's own claim even expires (Fable review of T1.13, finding I-2).
        min=BUFFER_FLUSH_MAX_RUN_SECONDS, max=86400,
        help="A claim older than this is treated as abandoned and retried.",
    ),
    FieldDescriptor(
        key="buffer_done_retention_hours", label="Done Retention (h)",
        default=BUFFER_FLUSH_DEFAULTS["buffer_done_retention_hours"],
        min=1, max=8760,
        help="How long flushed rows are kept before the sweep deletes them.",
    ),
]

# Where each replayed capture field lands on the `memories` row.
_REPLAY_TO_MEMORY_COLUMN: dict[str, str] = {
    "memory_type": "memory_type",
    "importance": "importance",
    "expires_at": "expires_at",
    "source_agent": "source_agent",
    "origin_key": "origin_key",
    "metadata": "metadata_",
}
# Fields that replay through something other than a plain column assignment.
_REPLAY_VIA_ASSOCIATION: frozenset[str] = frozenset({"tags"})

# The buffer's own bookkeeping, not caller data: the pre-minted memory id is the
# row's identity rather than one of its fields, and `flush_timeouts` is the
# deadline ladder's counter.
FLUSH_TIMEOUTS_KEY = "flush_timeouts"
_BUFFER_BOOKKEEPING_KEYS: frozenset[str] = frozenset({"memory_id", FLUSH_TIMEOUTS_KEY})

# Only the four hard steps return the row. A deterministic extraction failure
# (an unparseable or truncated reply to a seeded request) is not one: the
# vector and the content are written, and a retry would only repeat the reply,
# so the row settles and the memory's failure row carries it to triage.
_HARD_FAILURE_STEPS: frozenset[str] = frozenset(
    {"content_embedding", "extraction", "vector_write", "graph_write"}
)


def _returns_the_row(status: dict) -> bool:
    step = derive_memory_failed_step(status)
    if step == "extraction" and status.get("extract_failure") == "deterministic":
        return False
    return step in _HARD_FAILURE_STEPS


def _assert_replay_coverage(fields: tuple[str, ...] = REPLAYED_METADATA_FIELDS) -> None:
    unreplayed = (
        set(fields) - set(_REPLAY_TO_MEMORY_COLUMN) - _REPLAY_VIA_ASSOCIATION
    )
    if unreplayed:
        raise RuntimeError(
            "buffer flush would silently drop captured field(s) "
            f"{sorted(unreplayed)}: they are in REPLAYED_METADATA_FIELDS but "
            "have no replay in app.services.buffer_flush"
        )


_assert_replay_coverage()


@dataclass(frozen=True)
class ClaimedCapture:
    """One claimed buffer row, detached from the claim session.

    `buffer_id` is the buffer's own tracking handle and `memory_id` the
    pre-minted `memories` id the 202 already handed the caller (doc 05 §2.2).
    They are different values and neither substitutes for the other: the claim
    bookkeeping keys off `buffer_id`, the replay keys off `memory_id`.
    """

    buffer_id: uuid.UUID
    memory_id: uuid.UUID
    content: str
    project: str
    source: str
    replay: dict[str, Any]


def worker_identity() -> str:
    """Who holds a claim, recorded in `claimed_by` so a stale claim names the
    process that abandoned it."""
    return f"{socket.gethostname()}:{os.getpid()}"


class _ReuseSessionFactory:
    """Adapts one already-open `AsyncSession` to the zero-arg,
    async-context-manager-returning shape `session_factory()` calls expect.

    Doc 05 §2.2's `wait_process` bypass has only the caller's request-scoped
    session, not a session_factory — but the claim and replay code below is
    written once, against that call shape, and shared verbatim with the
    scheduled `buffer_flush` job (Ruling 3: a second claim implementation is
    exactly how a concurrent scheduled flush ends up double-processing a row).
    This wrapper closes that gap without forking the code: it never closes or
    commits the wrapped session on its own, since it is still the caller's.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    def __call__(self) -> "_ReuseSessionFactory":
        return self

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


def as_session_factory(session: AsyncSession) -> _ReuseSessionFactory:
    """Public constructor for `_ReuseSessionFactory` — the seam `wait_process`
    (and anything else driving the flush over one caller session) is meant to
    use rather than reaching for the private class directly."""
    return _ReuseSessionFactory(session)


async def buffer_settings(session_factory: async_sessionmaker[AsyncSession]) -> dict[str, int]:
    """The four buffer thresholds, DB values merged over the defaults.

    They live in the `config` row the JobRegistry already keeps for this job
    (`job:buffer_flush`, under its `config` key), so the existing
    `PUT /api/v1/jobs/{key}/config` validation and UI apply unchanged.
    """
    async with session_factory() as session:
        row = (await session.execute(
            select(Config).where(Config.key == f"job:{BUFFER_FLUSH_JOB_KEY}")
        )).scalar_one_or_none()
    merged = dict(BUFFER_FLUSH_DEFAULTS)
    stored = (row.value or {}).get("config") if row and isinstance(row.value, dict) else None
    if isinstance(stored, dict):
        for key in BUFFER_FLUSH_DEFAULTS:
            value = stored.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                merged[key] = value
    return merged


# MATERIALIZED is load-bearing, not a hint. As a plain sub-select the planner
# is free to put the row set on the inner side of a nested loop and re-execute
# it per outer row; each re-execution steps past the rows this same command
# already claimed and yields the next pending one, so LIMIT bounds nothing and
# the claim takes the whole backlog. A drained buffer that autovacuum has just
# analysed — the queue's normal steady state — is enough to reach that plan.
_CLAIM_SQL = text(
    """
    WITH c AS MATERIALIZED (
        SELECT id
        FROM memory_buffer
        WHERE status = 'pending'
        ORDER BY created_at, id
        LIMIT CAST(:limit AS int)
        FOR UPDATE SKIP LOCKED
    )
    UPDATE memory_buffer AS b
    SET status = 'claimed',
        attempts = b.attempts + 1,
        claimed_at = NOW(),
        claimed_by = CAST(:worker AS text)
    FROM c
    WHERE b.id = c.id
    RETURNING b.id
    """
)

_RECLAIM_SQL = text(
    """
    UPDATE memory_buffer AS b
    SET status = CASE
            WHEN b.attempts >= CAST(:max_attempts AS int) THEN 'error'
            ELSE 'pending'
        END,
        last_error = CAST(:reason AS text),
        claimed_at = NULL,
        claimed_by = NULL
    FROM (
        SELECT id
        FROM memory_buffer
        WHERE status = 'claimed'
          AND claimed_at IS NOT NULL
          AND claimed_at < NOW() - CAST(:seconds AS int) * INTERVAL '1 second'
        ORDER BY claimed_at
        FOR UPDATE SKIP LOCKED
    ) AS c
    WHERE b.id = c.id
    RETURNING b.id
    """
)

_SWEEP_DONE_SQL = text(
    """
    DELETE FROM memory_buffer
    WHERE status = 'done'
      AND COALESCE(claimed_at, created_at)
          < NOW() - CAST(:hours AS int) * INTERVAL '1 hour'
    RETURNING id
    """
)

# Doc 05 §2.2's `wait_process` bypass claims a caller-known row set instead of
# the oldest-N scan `_CLAIM_SQL` runs, but the predicate that matters — SKIP
# LOCKED against status='pending' — is identical. A concurrent scheduled flush
# racing this one is decided by the same lease, never a second claim path.
#
# `id = ANY(:ids)` is a fixed set no rescan can grow, so this one cannot
# overrun a bound the way an unmaterialized `_CLAIM_SQL` does; MATERIALIZED is
# here so the lock decisions are taken once rather than once per outer row,
# which on a caller's full id set is quadratic re-locking of rows SKIP LOCKED
# has already declined.
_CLAIM_IDS_SQL = text(
    """
    WITH c AS MATERIALIZED (
        SELECT id
        FROM memory_buffer
        WHERE status = 'pending'
          AND id = ANY(CAST(:ids AS uuid[]))
        FOR UPDATE SKIP LOCKED
    )
    UPDATE memory_buffer AS b
    SET status = 'claimed',
        attempts = b.attempts + 1,
        claimed_at = NOW(),
        claimed_by = CAST(:worker AS text)
    FROM c
    WHERE b.id = c.id
    RETURNING b.id
    """
)


_HEAD_TIMEOUTS_SQL = text(
    f"""
    SELECT COALESCE(CAST(metadata ->> '{FLUSH_TIMEOUTS_KEY}' AS int), 0)
    FROM memory_buffer
    WHERE status = 'pending'
    ORDER BY created_at, id
    LIMIT 1
    """
)

# A batch that cannot finish inside the deadline is halved on the next tick, so
# the shift is bounded by the widest configurable batch rather than growing
# without limit; ten halvings already take 1000 rows to one.
_MAX_CLAIM_HALVINGS = 10

_TIMED_OUT_SQL = text(
    f"""
    UPDATE memory_buffer
    SET status = 'pending',
        attempts = GREATEST(attempts - 1, 0),
        last_error = CAST(:message AS text),
        claimed_at = NULL,
        claimed_by = NULL,
        metadata = jsonb_set(
            COALESCE(metadata, '{{}}'::jsonb),
            '{{{FLUSH_TIMEOUTS_KEY}}}',
            to_jsonb(
                COALESCE(CAST(metadata ->> '{FLUSH_TIMEOUTS_KEY}' AS int), 0) + 1
            )
        )
    WHERE id = ANY(CAST(:ids AS uuid[]))
    """
)


async def claim_limit(session: AsyncSession, *, configured: int) -> int:
    """How many rows this tick may claim: the configured batch, halved once per
    deadline the row at the head of the queue has already caused.

    This is what stops a batch too slow for the ceiling from marching a healthy
    backlog into `error` (Fable review of T1.13, I-3). Raising the ceiling would
    only move that cliff; shrinking the batch removes it, because the flush
    converges on a size the ceiling can carry instead of failing every tick. The
    counter lives on the row rather than in job state so the shrink follows the
    slow work as it drains, and the claim's oldest-first order is what makes the
    head row representative of what the tick is about to attempt.
    """
    head = (await session.execute(_HEAD_TIMEOUTS_SQL)).scalar()
    if not head:
        return configured
    return max(1, configured >> min(int(head), _MAX_CLAIM_HALVINGS))


async def claim_batch(
    session: AsyncSession, *, limit: int, worker: str,
) -> list[MemoryBuffer]:
    """Claim up to `limit` pending rows for `worker`. Does not commit.

    The caller owns the transaction boundary and must commit promptly: the row
    locks this statement takes are released by that commit, and holding them
    across `process_batch` would serialise every claimer behind one LLM call and
    break invariant 11's session-lifetime rule at the same time.
    """
    if limit <= 0:
        return []
    claimed_ids = list((await session.execute(
        _CLAIM_SQL, {"limit": limit, "worker": worker}
    )).scalars())
    if not claimed_ids:
        return []
    rows = (await session.execute(
        select(MemoryBuffer)
        .where(MemoryBuffer.id.in_(claimed_ids))
        .order_by(MemoryBuffer.created_at, MemoryBuffer.id)
    )).scalars().all()
    return list(rows)


async def claim_specific(
    session: AsyncSession, *, buffer_ids: list[uuid.UUID], worker: str,
) -> list[MemoryBuffer]:
    """Claim whichever of ``buffer_ids`` are still `pending`. Does not commit.

    The interactive counterpart to `claim_batch`: same locking clause, same
    status qual, scoped to a known id set instead of an oldest-N scan. An id
    absent from the result was raced away by another claimer (most likely the
    scheduled `buffer_flush` tick) rather than rejected — the caller decides
    what to do about that (doc 05 §2.2 polls rather than reprocessing).
    """
    if not buffer_ids:
        return []
    claimed_ids = list((await session.execute(
        _CLAIM_IDS_SQL, {"ids": [str(i) for i in buffer_ids], "worker": worker}
    )).scalars())
    if not claimed_ids:
        return []
    rows = (await session.execute(
        select(MemoryBuffer)
        .where(MemoryBuffer.id.in_(claimed_ids))
        .order_by(MemoryBuffer.created_at, MemoryBuffer.id)
    )).scalars().all()
    return list(rows)


async def reclaim_stale(
    session: AsyncSession, *, visibility_seconds: int, max_attempts: int,
) -> list[uuid.UUID]:
    """Return claims older than the visibility window to `pending`. No commit.

    Safe against stealing a live claim under invariant 13's single worker: this
    runs at the top of a flush, which holds the job's `asyncio.Lock`, so no other
    flush in this process can be mid-run. Anything still `claimed` past the
    window therefore belongs to a dead process or to a run the registry already
    cancelled at `max_run_seconds`. `SKIP LOCKED` is the second line: a row a
    concurrent claim transaction still holds is skipped rather than stolen.
    """
    reason = f"stale claim reclaimed after {visibility_seconds}s"
    return list((await session.execute(
        _RECLAIM_SQL,
        {"seconds": visibility_seconds, "max_attempts": max_attempts, "reason": reason},
    )).scalars())


async def sweep_done(session: AsyncSession, *, retention_hours: int) -> int:
    """Delete `done` rows past the retention window. No commit.

    Success does not delete a buffer row — doc 05 §3.1 keeps it for replay and
    triage history and only this sweep, a window later, reclaims the space.
    `error` rows are never swept: they are the triage queue.
    """
    return len(list((await session.execute(
        _SWEEP_DONE_SQL, {"hours": retention_hours}
    )).scalars()))


# The one definition of "stale", as a composable SQL fragment over
# `memory_buffer` bound to `:seconds`. The monitor's read surface (T1.13b)
# selects and filters on this same constant rather than restating it: a second
# definition would be the one operators read off the screen, and it would drift
# from the lease the reclaim arm actually enforces.
STALE_CLAIM_PREDICATE = (
    "status = 'claimed' AND claimed_at IS NOT NULL "
    "AND claimed_at < NOW() - CAST(:seconds AS int) * INTERVAL '1 second'"
)

_PROJECT_PREDICATE = (
    "(CAST(:project AS text) IS NULL OR project = CAST(:project AS text))"
)

_STALE_CLAIMS_SQL = text(
    f"SELECT * FROM memory_buffer "
    f"WHERE {STALE_CLAIM_PREDICATE} AND {_PROJECT_PREDICATE} "
    "ORDER BY claimed_at, id "
    "LIMIT CAST(:limit AS int) OFFSET CAST(:offset AS int)"
)

_STALE_CLAIM_COUNT_SQL = text(
    f"SELECT COUNT(*) FROM memory_buffer "
    f"WHERE {STALE_CLAIM_PREDICATE} AND {_PROJECT_PREDICATE}"
)


async def stale_claims(
    session: AsyncSession,
    *,
    visibility_seconds: int,
    project: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[MemoryBuffer]:
    """Rows still `claimed` past the visibility window — the buffer monitor's
    poison/stall surface (doc 13 §6.1).

    `project` rides the WHERE clause rather than a post-fetch filter: this is a
    read surface over caller data, and a project predicate applied in Python is
    a leak the moment a caller reads `total` or a page boundary.
    """
    return list((await session.execute(
        select(MemoryBuffer).from_statement(_STALE_CLAIMS_SQL),
        {
            "seconds": visibility_seconds,
            "project": project,
            "limit": limit,
            "offset": offset,
        },
    )).scalars())


async def count_stale_claims(
    session: AsyncSession, *, visibility_seconds: int, project: str | None = None,
) -> int:
    return int((await session.execute(
        _STALE_CLAIM_COUNT_SQL,
        {"seconds": visibility_seconds, "project": project},
    )).scalar_one())


def detach(rows: list[MemoryBuffer]) -> tuple[list[ClaimedCapture], list[tuple[uuid.UUID, str]]]:
    """Split claimed rows into replayable captures and unreplayable ones.

    A row written by some path other than `enqueue` carries no pre-minted memory
    id, so it can never be replayed; it is separated here and goes straight to
    `error` for triage instead of failing the batch it happens to share.
    """
    captures: list[ClaimedCapture] = []
    rejected: list[tuple[uuid.UUID, str]] = []
    for row in rows:
        try:
            memory_id = buffered_memory_id(row)
        except ValueError as exc:
            rejected.append((row.id, str(exc)))
            continue
        metadata = dict(row.metadata_ or {})
        captures.append(ClaimedCapture(
            buffer_id=row.id,
            memory_id=memory_id,
            content=row.content,
            project=row.project,
            source=row.source or "api",
            replay={k: v for k, v in metadata.items() if k not in _BUFFER_BOOKKEEPING_KEYS},
        ))
    return captures, rejected


def _memory_kwargs(capture: ClaimedCapture) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "id": capture.memory_id,
        "content": capture.content,
        "project": capture.project,
        "source": capture.source,
    }
    for field, column in _REPLAY_TO_MEMORY_COLUMN.items():
        if field not in capture.replay:
            continue
        value = capture.replay[field]
        if field == "expires_at" and isinstance(value, str):
            value = datetime.fromisoformat(value)
        kwargs[column] = value
    return kwargs


async def materialize(
    session: AsyncSession, captures: list[ClaimedCapture],
) -> list[dict[str, Any]]:
    """Create each capture's `memories` row and return the `process_batch`
    entries. Does not commit.

    Re-claiming a row after a failed flush must not duplicate the memory, and it
    cannot: the id was minted at accept, so an existing row means this capture
    already materialised and the replay is an update of the same id rather than
    a second memory.
    """
    if not captures:
        return []
    ids = [c.memory_id for c in captures]
    existing = set((await session.execute(
        select(Memory.id).where(Memory.id.in_(ids))
    )).scalars())

    memory_repo = PostgresMemoryRepository(session)
    for capture in captures:
        if capture.memory_id not in existing:
            session.add(Memory(**_memory_kwargs(capture)))
    await session.flush()
    for capture in captures:
        tags = capture.replay.get("tags")
        if tags:
            await memory_repo.set_tags(capture.memory_id, list(tags))
    await session.flush()

    created_at = dict((await session.execute(
        select(Memory.id, Memory.created_at).where(Memory.id.in_(ids))
    )).all())
    return [
        {
            "memory_id": c.memory_id,
            "content": c.content,
            "source": c.source,
            # Carried so Phase 2 can attribute this memory's spend to the
            # project that paid for it. Without it every ingest usage row
            # reports project NULL and the cost view's project filter answers
            # zero for a corpus that is entirely one project's.
            "project": c.project,
            "tags": list(c.replay.get("tags") or []),
            "memory_type": c.replay.get("memory_type"),
            "created_at": (
                created_at[c.memory_id].isoformat() if created_at.get(c.memory_id) else ""
            ),
        }
        for c in captures
    ]


async def _mark_done(session: AsyncSession, buffer_ids: list[uuid.UUID]) -> None:
    if not buffer_ids:
        return
    await session.execute(
        text(
            "UPDATE memory_buffer SET status = 'done', last_error = NULL "
            "WHERE id = ANY(CAST(:ids AS uuid[]))"
        ),
        {"ids": [str(i) for i in buffer_ids]},
    )


async def _release(
    session: AsyncSession,
    failures: list[tuple[uuid.UUID, str]],
    *,
    max_attempts: int,
) -> None:
    """Return failed rows to `pending`, or to `error` once attempts are spent.

    An exhausted row is kept, never deleted: doc 05 §3.1 sends it to triage, and
    a row that vanishes here is a capture the caller was told had been accepted.
    """
    for buffer_id, message in failures:
        await session.execute(
            text(
                "UPDATE memory_buffer SET "
                "status = CASE WHEN attempts >= CAST(:max_attempts AS int) "
                "THEN 'error' ELSE 'pending' END, "
                "last_error = CAST(:message AS text), "
                "claimed_at = NULL, claimed_by = NULL "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(buffer_id), "message": message[:2000], "max_attempts": max_attempts},
        )


async def _requeue_timed_out(
    session: AsyncSession, buffer_ids: list[uuid.UUID], *, message: str,
) -> None:
    """Return a batch the deadline cut short to `pending`, refunding the attempt.

    A deadline says nothing about any individual row — nobody reached a settle,
    and the rows that finished are indistinguishable from the ones that did not
    — so charging every row an attempt for it walks a merely slow backlog into
    `error` without a single row being poisonous. The refund is safe against the
    livelock the claim-time increment exists to prevent because `claim_limit`
    halves the next claim off the same event: the batch converges towards one
    row, and a lone row that still cannot finish inside the whole deadline is
    genuinely poisonous and settles through `_release` on the ordinary ladder.
    """
    if not buffer_ids:
        return
    await session.execute(
        _TIMED_OUT_SQL,
        {"ids": [str(i) for i in buffer_ids], "message": message[:2000]},
    )


async def release_interrupted_claims(
    session: AsyncSession, buffer_ids: list[uuid.UUID], *, worker: str, message: str,
) -> None:
    """Return the rows ``worker`` still holds to `pending`, refunding the attempt.

    An interrupted flush (the process shutting down under it) says nothing
    about the rows it held, so it must not walk them towards `error`.
    """
    if not buffer_ids:
        return
    await session.execute(
        text(
            "UPDATE memory_buffer SET status = 'pending', "
            "attempts = GREATEST(attempts - 1, 0), "
            "last_error = CAST(:message AS text), "
            "claimed_at = NULL, claimed_by = NULL "
            "WHERE id = ANY(CAST(:ids AS uuid[])) "
            "AND status = 'claimed' AND claimed_by = CAST(:worker AS text)"
        ),
        {"ids": [str(i) for i in buffer_ids], "worker": worker, "message": message[:2000]},
    )


async def _fail_permanently(
    session: AsyncSession, rejected: list[tuple[uuid.UUID, str]],
) -> None:
    for buffer_id, message in rejected:
        await session.execute(
            text(
                "UPDATE memory_buffer SET status = 'error', "
                "last_error = CAST(:message AS text), "
                "claimed_at = NULL, claimed_by = NULL "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(buffer_id), "message": message[:2000]},
        )


async def _claim_and_prepare(
    open_session,
    *,
    worker: str,
    limit: int | None = None,
    buffer_ids: list[uuid.UUID] | None = None,
) -> tuple[list[MemoryBuffer], list[ClaimedCapture], list[tuple[uuid.UUID, str]]]:
    """Claim (batch-scan or id-scoped) then split into replayable/rejected.

    Shared by the scheduled flush and `wait_process` so both run through the
    identical claim SQL and rejection handling — `open_session` is either a
    real `session_factory` or `as_session_factory`'s single-session adapter.
    """
    async with open_session() as session:
        if buffer_ids is not None:
            rows = await claim_specific(session, buffer_ids=buffer_ids, worker=worker)
        else:
            rows = await claim_batch(
                session,
                limit=await claim_limit(session, configured=limit or 0),
                worker=worker,
            )
        captures, rejected = detach(rows)
        await _fail_permanently(session, rejected)
        # Commit the claim before anything opens a pipeline session (invariant
        # 11): the locks taken above are released here, and the claim is durable
        # so a crash from this point on leaves a reclaimable row rather than a
        # lost one.
        await session.commit()
    return rows, captures, rejected


async def _materialize_batch(
    open_session, captures: list[ClaimedCapture],
) -> list[dict[str, Any]]:
    """One `materialize` call inside its own transaction, rolled back on failure.

    The rollback is explicit because `open_session` may be
    `as_session_factory`'s adapter over a caller's session, which deliberately
    neither commits nor rolls back on exit — leaving that session poisoned for
    every statement after this one.
    """
    async with open_session() as session:
        try:
            entries = await materialize(session, captures)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return entries


async def _materialize_isolated(
    open_session, captures: list[ClaimedCapture],
) -> tuple[list[ClaimedCapture], list[dict[str, Any]], list[tuple[uuid.UUID, str]]]:
    """Materialize the batch, falling back to one row at a time if it raises.

    `materialize` is where a capture's own data first meets the schema, so it is
    where a single bad row can raise for the batch — an over-length tag against
    `tags.name`'s `String(255)` is the proven case. The batch attempt stays for
    throughput; the fallback is what stops the raiser from settling anybody
    else, and it also produces a `last_error` that names the actual failure
    instead of the batch's shared, untriageable one.
    """
    if not captures:
        return [], [], []
    if len(captures) > 1:
        try:
            return list(captures), await _materialize_batch(open_session, captures), []
        except Exception:
            logger.warning(
                "buffer flush: batch materialize of %d captures failed, "
                "retrying row by row to isolate the offender",
                len(captures),
                exc_info=True,
            )

    survivors: list[ClaimedCapture] = []
    entries: list[dict[str, Any]] = []
    failures: list[tuple[uuid.UUID, str]] = []
    for capture in captures:
        try:
            entries.extend(await _materialize_batch(open_session, [capture]))
        except Exception as exc:
            failures.append((capture.buffer_id, f"{type(exc).__name__}: {exc}"))
            continue
        survivors.append(capture)
    return survivors, entries, failures


async def _replay(
    open_session,
    pipeline,
    captures: list[ClaimedCapture],
    *,
    max_attempts: int,
    deadline_seconds: float | None = None,
) -> tuple[list[uuid.UUID], list[uuid.UUID], list[uuid.UUID]]:
    """Materialize + run the pipeline (or skip it, pipeline-less) + settle.

    Returns `(done, failed, timed_out)` buffer ids. Every capture passed in
    resolves into exactly one of the three — the caller-visible "did this row's
    flush finish" signal is `done | failed`, regardless of which one, since the
    `memories` row is written by `materialize` before the pipeline ever runs.

    `deadline_seconds` bounds the pipeline call so the flush settles its own
    rows rather than being cancelled mid-call with them left `claimed`; the
    scheduled job passes it and the interactive `wait_process` bypass does not,
    since that caller carries its own bound.
    """
    if not captures:
        return [], [], []

    captures, entries, unmaterializable = await _materialize_isolated(
        open_session, captures
    )
    if unmaterializable:
        async with open_session() as session:
            await _release(session, unmaterializable, max_attempts=max_attempts)
            await session.commit()
    failed = [buffer_id for buffer_id, _ in unmaterializable]
    if not captures:
        return [], failed, []

    try:
        if pipeline is None:
            # No pipeline configured (e.g. a Postgres-only boot, or a test
            # harness that never wires one): the memory row still
            # materializes above, just unenriched — mirrors the pre-buffer
            # `if self.pipeline:` gate MemoryService always had.
            statuses = [{} for _ in entries]
        elif deadline_seconds is None:
            statuses = await pipeline.process_batch(entries)
        else:
            statuses = await asyncio.wait_for(
                pipeline.process_batch(entries), timeout=deadline_seconds
            )
    except asyncio.TimeoutError:
        message = (
            f"flush deadline of {deadline_seconds:g}s exceeded with "
            f"{len(captures)} row(s) in flight"
        )
        logger.warning("buffer flush: %s", message)
        timed_out = [c.buffer_id for c in captures]
        async with open_session() as session:
            if len(captures) > 1:
                await _requeue_timed_out(session, timed_out, message=message)
            else:
                # A lone row that cannot finish inside the whole deadline is the
                # row's own problem, so it pays an attempt and reaches triage.
                await _release(
                    session,
                    [(c.buffer_id, message) for c in captures],
                    max_attempts=max_attempts,
                )
                await session.commit()
                return [], failed + timed_out, []
            await session.commit()
        return [], failed, timed_out
    except Exception as exc:
        # Everything left is batch-wide by construction: `process_batch` swallows
        # per-memory failures into `statuses`, so an exception escaping it is the
        # embedder or the session, not one capture's data.
        logger.exception("buffer flush batch failed for %d captures", len(captures))
        async with open_session() as session:
            await _release(
                session,
                [(c.buffer_id, f"{type(exc).__name__}: {exc}") for c in captures],
                max_attempts=max_attempts,
            )
            await session.commit()
        return [], failed + [c.buffer_id for c in captures], []

    done: list[uuid.UUID] = []
    failures: list[tuple[uuid.UUID, str]] = []
    for capture, status in zip(captures, statuses):
        status = status if isinstance(status, dict) else {}
        if _returns_the_row(status):
            step = derive_memory_failed_step(status)
            message = status.get("error") or f"pipeline failed at {step}"
            failures.append((capture.buffer_id, str(message)))
        else:
            done.append(capture.buffer_id)

    async with open_session() as session:
        await _mark_done(session, done)
        await _release(session, failures, max_attempts=max_attempts)
        await session.commit()
    return done, failed + [buffer_id for buffer_id, _ in failures], []


async def flush_once(
    session_factory: async_sessionmaker[AsyncSession],
    pipeline,
    *,
    worker: str | None = None,
    deadline_seconds: float = BUFFER_FLUSH_DEADLINE_SECONDS,
) -> dict[str, int]:
    """One flush tick: recover, sweep, claim, replay, settle."""
    settings = await buffer_settings(session_factory)
    worker = worker or worker_identity()
    stats = {
        "reclaimed": 0, "swept": 0, "claimed": 0,
        "done": 0, "failed": 0, "rejected": 0, "timed_out": 0,
    }

    async with session_factory() as session:
        reclaimed = await reclaim_stale(
            session,
            visibility_seconds=settings["buffer_claim_visibility_seconds"],
            max_attempts=settings["buffer_max_attempts"],
        )
        stats["swept"] = await sweep_done(
            session, retention_hours=settings["buffer_done_retention_hours"]
        )
        await session.commit()
    stats["reclaimed"] = len(reclaimed)

    rows, captures, rejected = await _claim_and_prepare(
        session_factory, worker=worker, limit=settings["buffer_claim_batch"]
    )
    stats["claimed"] = len(rows)
    stats["rejected"] = len(rejected)

    done, failed, timed_out = await _replay(
        session_factory,
        pipeline,
        captures,
        max_attempts=settings["buffer_max_attempts"],
        deadline_seconds=deadline_seconds,
    )
    stats["done"] = len(done)
    stats["failed"] = len(failed)
    stats["timed_out"] = len(timed_out)
    return stats


@dataclass(frozen=True)
class ClaimedFlushResult:
    """The outcome of driving one caller-known buffer-id set through the claim
    and replay `wait_process` shares with the scheduled flush.

    `claimed` is every id this call actually claimed (regardless of whether its
    replay then succeeded or hard-failed) — an id can only be missing from it
    by losing the `FOR UPDATE SKIP LOCKED` race to a concurrent claimer, most
    likely the scheduled `buffer_flush` tick. `settled` is the set whose
    `memories` row is guaranteed to exist and whose replay (if any) has
    finished — `wait_process` only needs to poll for ids outside it.
    """

    claimed: frozenset[uuid.UUID]
    rejected: frozenset[uuid.UUID]
    done: frozenset[uuid.UUID]
    failed: frozenset[uuid.UUID]

    @property
    def settled(self) -> frozenset[uuid.UUID]:
        return self.claimed | self.rejected


async def flush_claimed(
    session: AsyncSession,
    pipeline,
    *,
    buffer_ids: list[uuid.UUID],
    worker: str | None = None,
    max_attempts: int,
) -> ClaimedFlushResult:
    """Interactive counterpart to `flush_once`, scoped to a known row set and
    driven over the caller's own session (doc 05 §2.2's `wait_process`).

    Runs through the identical `_claim_and_prepare` / `_replay` the scheduled
    job uses, parameterised over `as_session_factory(session)` instead of a
    real factory — never a second claim or replay implementation (Ruling 3).
    """
    worker = worker or worker_identity()
    open_session = as_session_factory(session)
    rows, captures, rejected = await _claim_and_prepare(
        open_session, worker=worker, buffer_ids=buffer_ids
    )
    done, failed, _ = await _replay(
        open_session, pipeline, captures, max_attempts=max_attempts
    )
    return ClaimedFlushResult(
        claimed=frozenset(r.id for r in rows),
        rejected=frozenset(buffer_id for buffer_id, _ in rejected),
        done=frozenset(done),
        failed=frozenset(failed),
    )
