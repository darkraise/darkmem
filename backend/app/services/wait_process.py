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
import logging
import time
import uuid
from typing import Awaitable, Callable

from sqlalchemy import select

from app.models.memory import MemoryBuffer
from app.services.buffer_flush import (
    BUFFER_FLUSH_DEADLINE_SECONDS,
    ClaimedFlushResult,
    flush_claimed,
    release_interrupted_claims,
    worker_identity,
)
from app.services.llm import spawn_with_llm

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL_SECONDS = 0.05
SHUTDOWN_GRACE_SECONDS = 5.0
# Each wait_process flush in flight, inside its request's window or past it,
# holds a connection and an LLM lease; past this many a capture answers the
# plain ack and leaves its row to the scheduled flush.
MAX_CONTINUING_FLUSHES = 8

_SETTLED_BUFFER_STATUSES = ("done", "error")

# Every wait_process flush in flight, from its spawn to its end: "continuing"
# here means still running, inside its request's window or past it. In-process
# tracking is enough because the app runs one worker (invariant 13).
_continuing: set[asyncio.Task] = set()


def continuing_flushes() -> frozenset[asyncio.Task]:
    return frozenset(_continuing)


async def drain_continuing_flushes(grace_seconds: float = SHUTDOWN_GRACE_SECONDS) -> None:
    """Shutdown: let continuing flushes finish within the grace, cancel the rest.

    A cancelled flush returns the rows it still holds to `pending` before it
    ends, so awaiting it here is what makes that release land.
    """
    tasks = list(_continuing)
    if not tasks:
        return
    _finished, unfinished = await asyncio.wait(tasks, timeout=grace_seconds)
    for task in unfinished:
        task.cancel()
    await asyncio.gather(*unfinished, return_exceptions=True)


async def _flush_on_own_session(
    session_factory, pipeline, *, buffer_ids: list[uuid.UUID], worker: str, max_attempts: int,
) -> ClaimedFlushResult:
    # The scheduled flush's own deadline: a run that outlived the claim
    # visibility window would have its rows reclaimed and replayed twice.
    try:
        async with asyncio.timeout(BUFFER_FLUSH_DEADLINE_SECONDS):
            async with session_factory() as session:
                return await flush_claimed(
                    session, pipeline, buffer_ids=buffer_ids, worker=worker,
                    max_attempts=max_attempts,
                )
    except TimeoutError:
        # As the scheduled flush settles a deadline cut: a lone row that cannot
        # finish inside the whole deadline pays its attempt, a batch is refunded.
        await _release(
            session_factory, buffer_ids, worker, "inline flush passed its deadline",
            max_attempts=max_attempts if len(buffer_ids) == 1 else None,
        )
        raise
    except asyncio.CancelledError:
        await _release(session_factory, buffer_ids, worker, "flush interrupted by shutdown")
        raise


async def _release(
    session_factory, buffer_ids, worker: str, message: str, *, max_attempts: int | None = None,
) -> None:
    async with session_factory() as session:
        await release_interrupted_claims(
            session, buffer_ids, worker=worker, message=message, max_attempts=max_attempts,
        )
        await session.commit()


def _forget(task: asyncio.Task) -> None:
    _continuing.discard(task)
    if not task.cancelled() and task.exception() is not None:
        logger.error("wait_process flush failed", exc_info=task.exception())


async def drive(
    session_factory,
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

    Returns the subset whose replay finished `done` before the deadline. A row
    whose replay hard-failed and went back to `pending`, or landed in
    `error`, is not in it, and neither is anything still in flight: the
    caller answers the plain 202 ack for those (Ruling 2: never hang, never
    claim loss of a capture that is merely still processing).

    Two phases, both bounded by the same deadline:

    1. Our own claim attempt (`flush_claimed`, over `buffer_ids`), run as a
       tracked task on a session of its own from `session_factory`, holding
       the pipeline's LLM lease. If it is still running at the deadline it is
       left to finish, never cancelled: cancelling would strand its claim
       until the stale sweep and throw away the model spend already made.
    2. A read-only poll for whatever we did NOT claim ourselves — raced away
       by a concurrent claimer (most likely the scheduled job, Ruling 3) —
       to catch it settling before the same deadline without this call ever
       running the pipeline on it a second time.

    `clock`/`sleep` are injectable so the timeout path is testable without a
    real wall-clock wait (Ruling 2).
    """
    if not buffer_ids or len(_continuing) >= MAX_CONTINUING_FLUSHES:
        return frozenset()

    deadline = clock() + timeout_seconds
    worker = worker or f"{worker_identity()}:wait:{uuid.uuid4().hex[:8]}"
    task = spawn_with_llm(
        getattr(pipeline, "llm", None),
        _flush_on_own_session(
            session_factory, pipeline, buffer_ids=buffer_ids, worker=worker,
            max_attempts=max_attempts,
        ),
    )
    _continuing.add(task)
    task.add_done_callback(_forget)

    while not task.done() and clock() < deadline:
        await sleep(poll_interval_seconds)
    if not task.done():
        return frozenset()

    try:
        result = task.result()
    except Exception:
        # `_forget` reports it; the capture is buffered, so the caller gets the ack.
        return frozenset()
    done = set(result.done)
    pending = set(buffer_ids) - result.settled
    if not pending:
        return frozenset(done)

    async with session_factory() as session:
        while pending and clock() < deadline:
            await sleep(poll_interval_seconds)
            rows = (await session.execute(
                select(MemoryBuffer.id, MemoryBuffer.status).where(MemoryBuffer.id.in_(pending))
            )).all()
            for buffer_id, status in rows:
                if status in _SETTLED_BUFFER_STATUSES:
                    pending.discard(buffer_id)
                    if status == "done":
                        done.add(buffer_id)
    return frozenset(done)
