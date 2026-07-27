"""Tier-B flush: claim buffered captures and replay them through the pipeline.

Doc 05 §3. Capture (Tier A) commits a `memory_buffer` row and acks; this module
is the other half — a `JobRegistry` job that claims a batch of those rows with
`SELECT … FOR UPDATE SKIP LOCKED`, materialises each into its pre-minted
`memories` row, and hands the batch to `ProcessingPipeline.process_batch`.

Three properties carry the tier, and every one of them fails silently:

**A row is never processed twice.** The claim is one `UPDATE … FROM (SELECT …
FOR UPDATE SKIP LOCKED)` statement. The locking clause is what makes it safe:
Postgres re-evaluates the sub-select's `status='pending'` qual against the
freshly-committed row after the lock is released (EvalPlanQual), so a claimer
that raced another one comes away with nothing rather than with a row the other
claimer already holds. Drop the locking clause and the outer `b.id = c.id` has
no status qual to recheck — both claimers "win" the same row.

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
"""
from __future__ import annotations

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
        min=10, max=86400,
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
# row's identity rather than one of its fields.
_BUFFER_BOOKKEEPING_KEYS: frozenset[str] = frozenset({"memory_id"})

# A partial extraction is degraded, not failed: the vector and the content are
# written and only the graph is thin, so re-claiming the row would burn attempts
# on work that already landed. Only the four hard steps return the row.
_HARD_FAILURE_STEPS: frozenset[str] = frozenset(
    {"content_embedding", "extraction", "vector_write", "graph_write"}
)


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


_CLAIM_SQL = text(
    """
    UPDATE memory_buffer AS b
    SET status = 'claimed',
        attempts = b.attempts + 1,
        claimed_at = NOW(),
        claimed_by = CAST(:worker AS text)
    FROM (
        SELECT id
        FROM memory_buffer
        WHERE status = 'pending'
        ORDER BY created_at, id
        LIMIT CAST(:limit AS int)
        FOR UPDATE SKIP LOCKED
    ) AS c
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


_STALE_CLAIMS_SQL = text(
    """
    SELECT * FROM memory_buffer
    WHERE status = 'claimed'
      AND claimed_at IS NOT NULL
      AND claimed_at < NOW() - CAST(:seconds AS int) * INTERVAL '1 second'
    ORDER BY claimed_at
    """
)


async def stale_claims(
    session: AsyncSession, *, visibility_seconds: int,
) -> list[MemoryBuffer]:
    """Rows still `claimed` past the visibility window — the buffer monitor's
    poison/stall surface (doc 13 §6.1)."""
    return list((await session.execute(
        select(MemoryBuffer).from_statement(_STALE_CLAIMS_SQL),
        {"seconds": visibility_seconds},
    )).scalars())


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


async def flush_once(
    session_factory: async_sessionmaker[AsyncSession],
    pipeline,
    *,
    worker: str | None = None,
) -> dict[str, int]:
    """One flush tick: recover, sweep, claim, replay, settle."""
    settings = await buffer_settings(session_factory)
    worker = worker or worker_identity()
    stats = {"reclaimed": 0, "swept": 0, "claimed": 0, "done": 0, "failed": 0, "rejected": 0}

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

    async with session_factory() as session:
        rows = await claim_batch(
            session, limit=settings["buffer_claim_batch"], worker=worker
        )
        captures, rejected = detach(rows)
        await _fail_permanently(session, rejected)
        # Commit the claim before anything opens a pipeline session (invariant
        # 11): the locks taken above are released here, and the claim is durable
        # so a crash from this point on leaves a reclaimable row rather than a
        # lost one.
        await session.commit()
    stats["claimed"] = len(rows)
    stats["rejected"] = len(rejected)

    if not captures:
        return stats

    failures: list[tuple[uuid.UUID, str]] = []
    try:
        async with session_factory() as session:
            entries = await materialize(session, captures)
            await session.commit()
        statuses = await pipeline.process_batch(entries)
    except Exception as exc:
        logger.exception("buffer flush batch failed for %d captures", len(captures))
        async with session_factory() as session:
            await _release(
                session,
                [(c.buffer_id, f"{type(exc).__name__}: {exc}") for c in captures],
                max_attempts=settings["buffer_max_attempts"],
            )
            await session.commit()
        stats["failed"] = len(captures)
        return stats

    done: list[uuid.UUID] = []
    for capture, status in zip(captures, statuses):
        step = derive_memory_failed_step(status if isinstance(status, dict) else {})
        if step in _HARD_FAILURE_STEPS:
            message = (status or {}).get("error") or f"pipeline failed at {step}"
            failures.append((capture.buffer_id, str(message)))
        else:
            done.append(capture.buffer_id)

    async with session_factory() as session:
        await _mark_done(session, done)
        await _release(session, failures, max_attempts=settings["buffer_max_attempts"])
        await session.commit()
    stats["done"] = len(done)
    stats["failed"] = len(failures)
    return stats
