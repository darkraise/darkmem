"""The ``memory_access_stats`` feeder — the substrate ``w_heat`` and
``w_recency`` will read (doc 07 §3, T2.29).

The side table exists precisely so a per-read counter bump never rewrites
``memories`` — the widest, most-read row in the system — which would both
bloat that table's MVCC history and fire ``touch_updated_at``, corrupting
``updated_at``'s "content changed" meaning (baseline 0001, the comment above
the ``CREATE TABLE memory_access_stats`` DDL). This module is the only
writer: it upserts raw counters and never derives, decays, or ranks on them
— that is T2.31's job, once the arms it left at zero have a measured number
to justify moving them.

The write must stay off the caller's hot path. ``spawn_record_access`` never
awaits its own write: it schedules a background task on its own session
(never the caller's request session — CLAUDE.md's async-session-lifetime
invariant forbids a fresh session competing with a request transaction still
holding locks) and swallows any failure, because a counter miss must never
degrade or fail the search that triggered it.

Never awaiting the write is necessary but not sufficient: a background task
still competes with the foreground request for the same single-threaded
event loop and the same Postgres backend, so a naive one-task-per-search
design measurably slows concurrent foreground searches even though no caller
ever awaits it directly (measured — see the T2.29 completion report).

**This is a coalescing counter buffer, not a per-call writer, per a T2.29
review ruling.** An earlier revision capped concurrent background writes and
*dropped* an access when the cap was saturated. That was wrong: the review
measured 20-75% loss under sustained load, concentrated on exactly the
memories being accessed fastest — a load-correlated bias that poisons a heat
signal (busy-period popularity is what heat exists to capture, and dropping
proportionally more of it inverts the point). The fix is not a bigger cap;
it is to stop treating one search as one connection. `spawn_record_access`
only ever increments an in-process ``dict[memory_id, count]``, which is
synchronous and cannot fail or contend with anything. At most one background
task is ever alive at a time: it sleeps `_FLUSH_DELAY_SECONDS` to let a
burst of concurrent searches coalesce into the same buffer, then drains it
in a loop (one upsert per iteration, additively summing whatever counts
accumulated) until empty. This is bounded by the number of *distinct* memory
ids touched during the flush window, uses one connection instead of several,
issues strictly fewer statements than the per-call design under any
concurrent load, and loses nothing: every increment lands in the dict before
the flush task can be scheduled to read it (both happen synchronously, with
no ``await`` between them), and every dict entry present when a drain
iteration starts is captured and cleared atomically before that iteration's
``await`` point, so nothing referenced by a later caller can be silently
dropped by an earlier one.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database import async_session_factory
from app.utils.background import spawn

logger = logging.getLogger(__name__)

__all__ = ["record_access", "spawn_record_access"]

# Debounce window: lets a burst of concurrent searches land in the same
# buffer before the flush task drains it, so N concurrent searches touching
# the same or overlapping memories cost one statement, not N. Read live from
# the module namespace at flush time (never captured by value), so tests can
# monkeypatch it down without changing behaviour, only latency.
_FLUSH_DELAY_SECONDS = 0.25

# module-global, single-threaded-event-loop state: safe without a lock
# because every mutation below happens with no `await` between the read and
# the write that follows it.
_pending_counts: dict[str, int] = {}
_flush_task: asyncio.Task | None = None

# The FK-tolerant JOIN (not a bare CAST-and-insert) means one memory deleted
# between a search and this flush degrades that one row out of the batch
# instead of voiding every other id's bump in the same statement.
# ``unnest`` needs the explicit CAST or asyncpg cannot infer the array's
# element type (CLAUDE.md: asyncpg needs CAST on raw-SQL params).
_COUNTS_UPSERT_SQL = text(
    """
    INSERT INTO memory_access_stats (memory_id, access_count, last_accessed)
    SELECT m.id, t.cnt, NOW()
    FROM unnest(CAST(:ids AS uuid[]), CAST(:counts AS integer[])) AS t(id, cnt)
    JOIN memories m ON m.id = t.id
    ON CONFLICT (memory_id) DO UPDATE
    SET access_count = memory_access_stats.access_count + EXCLUDED.access_count,
        last_accessed = EXCLUDED.last_accessed
    """
)


def _build_counts(memory_ids: Iterable[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for mid in memory_ids:
        if not mid:
            continue
        key = str(mid)
        counts[key] = counts.get(key, 0) + 1
    return counts


async def _flush_counts(session: AsyncSession, counts: dict[str, int]) -> int:
    if not counts:
        return 0
    ids = list(counts.keys())
    amounts = [counts[i] for i in ids]
    result = await session.execute(_COUNTS_UPSERT_SQL, {"ids": ids, "counts": amounts})
    await session.commit()
    # Not len(ids): the JOIN against `memories` (F4) means an id deleted
    # between search and flush silently degrades out of the row count
    # instead of voiding the whole statement, so the true write count can be
    # smaller than the number of ids offered.
    return result.rowcount


async def record_access(session: AsyncSession, memory_ids: Iterable[object]) -> int:
    """Bump the access counters for ``memory_ids`` in one statement.

    Each occurrence of an id in the input adds to its count (an id appearing
    twice bumps its counter by 2). Returns the number of distinct ids
    written (0 for an empty/all-None input, which is a no-op — no statement
    is issued).
    """
    return await _flush_counts(session, _build_counts(memory_ids))


def spawn_record_access(
    memory_ids: Iterable[object],
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> asyncio.Task | None:
    """Fire-and-forget: buffer the access and ensure a flush is scheduled,
    without the caller awaiting anything.

    Buffering is synchronous (a plain dict update) and cannot drop an
    access: every id lands in ``_pending_counts`` before this function
    returns. At most one flush task is ever alive; a call that arrives
    while one is already scheduled just adds to the same buffer that task
    will drain.

    Returns the active/scheduled ``asyncio.Task`` (ignored by production
    callers; useful for tests that want to await it deterministically
    instead of sleeping), or ``None`` when there is nothing to write.
    """
    global _flush_task
    ids = [str(mid) for mid in memory_ids if mid]
    if not ids:
        return None

    for mid in ids:
        _pending_counts[mid] = _pending_counts.get(mid, 0) + 1

    if _flush_task is not None and not _flush_task.done():
        return _flush_task

    factory = session_factory or async_session_factory

    async def _run() -> None:
        global _flush_task
        try:
            await asyncio.sleep(_FLUSH_DELAY_SECONDS)
            while _pending_counts:
                batch = dict(_pending_counts)
                _pending_counts.clear()
                try:
                    async with factory() as session:
                        await _flush_counts(session, batch)
                except Exception:
                    logger.exception(
                        "memory_access_stats bump failed for %d id(s)", len(batch)
                    )
        finally:
            _flush_task = None

    _flush_task = spawn(_run(), name="access-stats-bump")
    return _flush_task
