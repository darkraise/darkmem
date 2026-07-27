"""The `memory_buffer` read surface and its poison-row actions (T1.13b).

Doc 13 §6.1 names the buffer monitor as *the* place a poison row appears, and
doc 05 §3.1 makes `error` the triage queue that is never swept — but nothing
read `memory_buffer` over the API, so the monitor could only bind demo data.
This module is the missing half: the state T1.13 produces, and the two actions
that make a poison row actionable rather than merely visible.

Two things it is deliberately not. It is **not** a cleanup path: `done` rows are
retained until the flush's own retention sweep and `error` rows are never swept,
and nothing here changes that — the one deletion is an explicit per-row discard
an operator asks for. And it does **not** own a definition of "stale": that is
`buffer_flush.STALE_CLAIM_PREDICATE`, the same fragment the reclaim arm enforces
and `stale_claims()` reads, composed here rather than restated, because a
monitor showing a different staleness than the lease is the one an operator
would believe.

Every predicate rides the SQL the database executes, `project` included. This is
a new read surface over caller data and the service-layer Python project filter
that used to backstop it is gone (T1.29b), so a scope applied after the fetch
would be a fresh leak with nothing behind it.
"""
from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.buffer_flush import (
    STALE_CLAIM_PREDICATE,
    as_session_factory,
    buffer_settings,
    count_stale_claims,
)
from app.services.events import record_event

BufferState = Literal["pending", "claimed", "stale", "done", "poison"]

# What each filter means in the buffer's own vocabulary. `poison` is the
# operator-facing name doc 13 §6.1 uses for `status='error'`; `stale` is not a
# status at all but a claim older than the lease, which is why it composes the
# predicate instead of comparing a column.
_STATE_PREDICATES: dict[str, str] = {
    "pending": "status = 'pending'",
    "claimed": "status = 'claimed'",
    "stale": STALE_CLAIM_PREDICATE,
    "done": "status = 'done'",
    "poison": "status = 'error'",
}

# Enough of the content to recognise the capture in a triage list without
# streaming an unbounded column into every page.
CONTENT_PREVIEW_CHARS = 500

_ROW_COLUMNS = f"""
    id,
    CAST(metadata ->> 'memory_id' AS uuid) AS memory_id,
    project,
    source,
    status,
    attempts,
    last_error,
    created_at,
    claimed_at,
    claimed_by,
    token_size,
    LEFT(content, {CONTENT_PREVIEW_CHARS}) AS content_preview,
    LENGTH(content) AS content_length,
    ({STALE_CLAIM_PREDICATE}) AS is_stale
"""

_PROJECT_PREDICATE = (
    "(CAST(:project AS text) IS NULL OR project = CAST(:project AS text))"
)


class BufferRowNotFound(LookupError):
    pass


class BufferRowNotActionable(RuntimeError):
    """The row exists but is not in `error`.

    Only a poison row is actionable. A `pending` or `done` row is not a problem
    to solve, and a `claimed` one is either in flight or already on the reclaim
    arm's path back to `pending` — requeueing it behind a live claimer would let
    two claimers hold one row, which is the failure the whole lease exists to
    prevent, and discarding it would delete the row its own flush is about to
    settle.
    """


def _where(state: str | None) -> str:
    parts = [_PROJECT_PREDICATE]
    if state is not None:
        parts.append(_STATE_PREDICATES[state])
    return " AND ".join(parts)


async def list_rows(
    session: AsyncSession,
    *,
    state: BufferState | None = None,
    project: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int, dict[str, int]]:
    """One page of buffer rows, the total, and the thresholds they read against.

    Newest first: triage reads the head of the queue, and a poison row is most
    often the one that just landed.
    """
    settings = await buffer_settings(as_session_factory(session))
    where = _where(state)
    rows = (await session.execute(
        text(
            f"SELECT {_ROW_COLUMNS} FROM memory_buffer WHERE {where} "
            "ORDER BY created_at DESC, id DESC "
            "LIMIT CAST(:limit AS int) OFFSET CAST(:offset AS int)"
        ),
        {
            "seconds": settings["buffer_claim_visibility_seconds"],
            "project": project,
            "limit": limit,
            "offset": offset,
        },
    )).mappings().all()
    total = int((await session.execute(
        text(f"SELECT COUNT(*) FROM memory_buffer WHERE {where}"),
        {
            "seconds": settings["buffer_claim_visibility_seconds"],
            "project": project,
        },
    )).scalar_one())
    max_attempts = settings["buffer_max_attempts"]
    return (
        [dict(row) | {"max_attempts": max_attempts} for row in rows],
        total,
        settings,
    )


async def stats(
    session: AsyncSession, *, project: str | None = None,
) -> dict[str, int]:
    """Per-state counts for the monitor header.

    The stale count comes from `count_stale_claims`, not from a fourth copy of
    the lease arithmetic — the same helper the reclaim arm's predicate is
    written once for.
    """
    settings = await buffer_settings(as_session_factory(session))
    row = (await session.execute(
        text(
            "SELECT "
            "COUNT(*) FILTER (WHERE status = 'pending') AS pending, "
            "COUNT(*) FILTER (WHERE status = 'claimed') AS claimed, "
            "COUNT(*) FILTER (WHERE status = 'done') AS done, "
            "COUNT(*) FILTER (WHERE status = 'error') AS poison "
            f"FROM memory_buffer WHERE {_PROJECT_PREDICATE}"
        ),
        {"project": project},
    )).mappings().one()
    return {
        **{k: int(v) for k, v in row.items()},
        "stale": await count_stale_claims(
            session,
            visibility_seconds=settings["buffer_claim_visibility_seconds"],
            project=project,
        ),
        "max_attempts": settings["buffer_max_attempts"],
        "visibility_seconds": settings["buffer_claim_visibility_seconds"],
    }


_LOAD_SQL = text(
    f"SELECT {_ROW_COLUMNS} FROM memory_buffer "
    f"WHERE id = CAST(:id AS uuid) AND {_PROJECT_PREDICATE}"
)

_REQUEUE_SQL = text(
    f"""
    UPDATE memory_buffer
    SET status = 'pending',
        attempts = 0,
        last_error = NULL,
        claimed_at = NULL,
        claimed_by = NULL,
        metadata = COALESCE(metadata, '{{}}'::jsonb) - 'flush_timeouts'
    WHERE id = CAST(:id AS uuid) AND status = 'error'
    RETURNING {_ROW_COLUMNS}
    """
)

_DISCARD_SQL = text(
    "DELETE FROM memory_buffer "
    "WHERE id = CAST(:id AS uuid) AND status = 'error' "
    "RETURNING id"
)


async def _load(
    session: AsyncSession,
    buffer_id: uuid.UUID,
    *,
    project: str | None,
    visibility_seconds: int,
) -> dict[str, Any]:
    row = (await session.execute(
        _LOAD_SQL,
        {"id": str(buffer_id), "project": project, "seconds": visibility_seconds},
    )).mappings().one_or_none()
    if row is None:
        raise BufferRowNotFound(str(buffer_id))
    return dict(row)


async def requeue(
    session: AsyncSession, buffer_id: uuid.UUID, *, project: str | None = None,
) -> dict[str, Any]:
    """Send a poison row back to `pending` with a clean slate. Does not commit.

    Attempts reset to zero, not decrement: an operator requeue follows a fix
    somewhere else — a widened column, a repaired embedder — so the row deserves
    the whole ladder again rather than the one attempt left before it errored.
    The deadline ladder's counter is cleared for the same reason.
    """
    settings = await buffer_settings(as_session_factory(session))
    visibility = settings["buffer_claim_visibility_seconds"]
    before = await _load(
        session, buffer_id, project=project, visibility_seconds=visibility,
    )
    row = (await session.execute(
        _REQUEUE_SQL, {"id": str(buffer_id), "seconds": visibility},
    )).mappings().one_or_none()
    if row is None:
        raise BufferRowNotActionable(before["status"])
    await record_event(
        session,
        event_type="buffer_requeued",
        object_type="memory",
        object_id=before["memory_id"],
        project=before["project"],
        source=before["source"],
        payload={
            "buffer_id": str(buffer_id),
            "attempts_before": before["attempts"],
            "last_error": before["last_error"],
        },
    )
    return dict(row) | {"max_attempts": settings["buffer_max_attempts"]}


async def discard(
    session: AsyncSession, buffer_id: uuid.UUID, *, project: str | None = None,
) -> None:
    """Delete a poison row the operator has decided not to keep. Does not commit.

    The one place this surface deletes anything, and it is always a row a human
    named: the retention contract is unchanged, so `done` rows still leave only
    through the flush's own sweep and `error` rows still leave only through
    here. The journal entry is what survives the row.
    """
    settings = await buffer_settings(as_session_factory(session))
    before = await _load(
        session,
        buffer_id,
        project=project,
        visibility_seconds=settings["buffer_claim_visibility_seconds"],
    )
    deleted = (await session.execute(
        _DISCARD_SQL, {"id": str(buffer_id)}
    )).scalar_one_or_none()
    if deleted is None:
        raise BufferRowNotActionable(before["status"])
    await record_event(
        session,
        event_type="buffer_discarded",
        object_type="memory",
        object_id=before["memory_id"],
        project=before["project"],
        source=before["source"],
        payload={
            "buffer_id": str(buffer_id),
            "attempts": before["attempts"],
            "last_error": before["last_error"],
            "content_preview": before["content_preview"],
        },
    )
