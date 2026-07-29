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
event loop and the same Postgres backend, so an *unbounded* one-task-per-
search design measurably slows concurrent foreground searches even though no
caller ever awaits it directly (measured — see the T2.29 completion report).
``_MAX_IN_FLIGHT`` bounds how many access-stats writes may be outstanding at
once; once saturated, a new access is dropped rather than queued. Dropping
is deliberate, not a bug to fix later: these are raw, approximate counters
feeding a future heat/recency signal (never an audit trail), so losing a
count under a burst is cheap, while queuing it would trade the same
contention problem for unbounded memory growth instead of fixing it.
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

# A plain constant, not a `config` row: this bounds background-connection
# concurrency for operational safety, not a ranking/tuning parameter, so it
# is out of scope for the harness-measured tuning convention (CLAUDE.md
# convention 9) that governs the rank_fusion `w_*` weights.
_MAX_IN_FLIGHT = 4
_in_flight = 0

# One statement over the whole id set — never one round trip per memory.
# ``unnest`` needs the explicit CAST or asyncpg cannot infer the array's
# element type (CLAUDE.md: asyncpg needs CAST on raw-SQL params).
_UPSERT_SQL = text(
    """
    INSERT INTO memory_access_stats (memory_id, access_count, last_accessed)
    SELECT id, 1, NOW()
    FROM unnest(CAST(:ids AS uuid[])) AS id
    ON CONFLICT (memory_id) DO UPDATE
    SET access_count = memory_access_stats.access_count + 1,
        last_accessed = EXCLUDED.last_accessed
    """
)


def _normalize_ids(memory_ids: Iterable[object]) -> list[str]:
    # Dedup: a single INSERT..ON CONFLICT cannot affect the same row twice,
    # so a memory appearing on both the semantic and keyword side of one
    # fused result set must collapse to one id here.
    return sorted({str(mid) for mid in memory_ids if mid})


async def record_access(session: AsyncSession, memory_ids: Iterable[object]) -> int:
    """Bump the access counters for ``memory_ids`` in one statement.

    Returns the number of distinct ids written (0 for an empty/all-None
    input, which is a no-op — no statement is issued).
    """
    ids = _normalize_ids(memory_ids)
    if not ids:
        return 0
    await session.execute(_UPSERT_SQL, {"ids": ids})
    await session.commit()
    return len(ids)


def spawn_record_access(
    memory_ids: Iterable[object],
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> asyncio.Task | None:
    """Fire-and-forget: schedule the counter bump without the caller
    awaiting it, on a session independent of the caller's own.

    Bounded by ``_MAX_IN_FLIGHT``: when that many writes are already
    outstanding, this access is dropped (logged at debug level) instead of
    queued, so a concurrent burst of searches can never accumulate an
    unbounded number of background connections competing with the
    foreground request path.

    Returns the scheduled ``asyncio.Task`` (ignored by production callers;
    useful for tests that want to await it deterministically instead of
    sleeping), or ``None`` when there is nothing to write or the in-flight
    cap is already reached.
    """
    global _in_flight
    ids = _normalize_ids(memory_ids)
    if not ids:
        return None

    if _in_flight >= _MAX_IN_FLIGHT:
        logger.debug(
            "memory_access_stats bump dropped for %d id(s): %d writes already in flight",
            len(ids), _in_flight,
        )
        return None

    factory = session_factory or async_session_factory
    _in_flight += 1

    async def _run() -> None:
        global _in_flight
        try:
            async with factory() as session:
                await record_access(session, ids)
        except Exception:
            logger.exception(
                "memory_access_stats bump failed for %d id(s)", len(ids)
            )
        finally:
            _in_flight -= 1

    return spawn(_run(), name="access-stats-bump")
