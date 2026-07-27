"""Doc 05 §2.2: `wait_process`, the interactive bypass over Tier B's buffer.

A capture always writes its `memory_buffer` row first (Tier A never skips the
buffer — that durability is what makes a later timeout safe to degrade rather
than fail). `wait_process` is the opt-in, bounded exception that then drives
that row's own flush inline, so an interactive caller gets the processed
memory back instead of just an ack.

Driving the flush inline means running through the exact same claim
(`buffer_flush.flush_claimed`, itself the same `FOR UPDATE SKIP LOCKED` lease
the scheduled job uses) rather than reimplementing it — a second claim path is
how a concurrent scheduled flush would end up processing the row twice
(Ruling 3). When this call loses that race, the row is being flushed by
someone else; this polls for it to settle rather than reprocessing it itself.
"""
from __future__ import annotations

import asyncio
import time
import uuid
from typing import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemoryBuffer
from app.services.buffer_flush import flush_claimed

DEFAULT_POLL_INTERVAL_SECONDS = 0.05

_SETTLED_BUFFER_STATUSES = ("done", "error")


async def drive(
    session: AsyncSession,
    pipeline,
    *,
    buffer_ids: list[uuid.UUID],
    timeout_seconds: float,
    max_attempts: int,
    worker: str | None = None,
    poll_interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> frozenset[uuid.UUID]:
    """Drive `buffer_ids` through their flush, bounded by `timeout_seconds`.

    Returns the subset that settled (their `memories` row exists and any
    pipeline replay has finished) before the deadline. Anything missing from
    the return value is still safely buffered — durably written, possibly
    mid-flush elsewhere — and the caller degrades to the plain 202 for it
    rather than waiting past the bound (Ruling 2: never hang, never claim loss
    of a capture that is merely still processing).

    Two phases, both bounded by the same deadline:

    1. Our own claim attempt (`flush_claimed`, over `buffer_ids`). If it is
       still running when the deadline passes, it is cancelled — the row(s)
       it claimed stay `claimed`, exactly the state a crashed worker leaves,
       so the next scheduled flush's stale-claim sweep recovers them rather
       than this call reprocessing or losing anything.
    2. A read-only poll for whatever we did NOT claim ourselves — raced away
       by a concurrent claimer (most likely the scheduled job, Ruling 3) —
       to catch it settling before the same deadline without this call ever
       running the pipeline on it a second time.

    `clock`/`sleep` are injectable so the timeout path is testable without a
    real wall-clock wait (Ruling 2): a fake pair can advance a virtual clock
    on every `sleep` call so the deadline is reached deterministically, with
    no actual waiting.
    """
    if not buffer_ids:
        return frozenset()

    deadline = clock() + timeout_seconds
    settled: set[uuid.UUID] = set()

    task = asyncio.ensure_future(
        flush_claimed(session, pipeline, buffer_ids=buffer_ids, worker=worker, max_attempts=max_attempts)
    )
    while not task.done() and clock() < deadline:
        await sleep(poll_interval_seconds)

    if task.done():
        settled |= set(task.result().settled)
    else:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    pending = set(buffer_ids) - settled
    while pending and clock() < deadline:
        await sleep(poll_interval_seconds)
        rows = (await session.execute(
            select(MemoryBuffer.id, MemoryBuffer.status).where(MemoryBuffer.id.in_(pending))
        )).all()
        for buffer_id, status in rows:
            if status in _SETTLED_BUFFER_STATUSES:
                settled.add(buffer_id)
        pending = set(buffer_ids) - settled

    return frozenset(settled)
