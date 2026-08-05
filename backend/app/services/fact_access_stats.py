"""The ``fact_access_stats`` feeder — the fact-keyed retrieval-heat counter
T2.65 designed and T2.84 builds (doc 08 §6).

Mirrors ``access_stats.py`` deliberately: same table shape (a 1:1 side table
rather than columns on the fact row, for the identical reason —
``knowledge_triples`` is a comparatively hot read path for every retrieval
channel, and a per-read bump there would rewrite that row's MVCC history on
every serve), same coalescing-buffer idiom, same off-hot-path guarantee. The
two modules are kept separate rather than merged behind a table-name
parameter: they key on different columns, join against different parent
tables, and — most importantly — sharing one module-global buffer between
them would mean a burst of fact traffic and a burst of memory traffic
compete for the same single in-flight flush task, coupling two channels'
latency for no reason. `review_ranking.py` reads this table directly, the
way it already reads `memory_access_stats`; this module is the only writer.

**Same off-hot-path shape, same reasoning.** ``spawn_record_access`` never
awaits its own write: it buffers synchronously (a dict update, which cannot
fail or contend with anything) and schedules a background flush on its own
session, never the caller's request session. A counting failure — a DB
error inside the flush, a dropped connection, anything — is logged and
swallowed; it never propagates to the search that triggered the count. See
``access_stats.py``'s module docstring for the full argument, including why
a naive one-task-per-search design was tried and measured to slow
concurrent foreground reads even though nothing awaits it: this module
carries the identical debounce-then-drain shape for the same reason.
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

# Same debounce window as access_stats.py, and the same reason: let a burst
# of concurrent facts-channel searches land in the same buffer before the
# flush drains it. Read live from the module namespace at flush time, never
# captured by value, so tests can monkeypatch it down without changing
# behaviour, only latency.
_FLUSH_DELAY_SECONDS = 0.25

# module-global, single-threaded-event-loop state: safe without a lock
# because every mutation below happens with no `await` between the read and
# the write that follows it. Deliberately a separate dict/task pair from
# access_stats.py's — see the module docstring for why sharing one buffer
# between the two channels would be wrong.
_pending_counts: dict[str, int] = {}
_flush_task: asyncio.Task | None = None

# FK-tolerant JOIN, not a bare CAST-and-insert: a fact deleted between a
# search and this flush (facts are invalidate-not-delete in the product, but
# this module does not assume that — a foreign row deleted from under it
# degrades that one id out of the batch rather than voiding every other id's
# bump in the same statement. ``unnest`` needs the explicit CAST or asyncpg
# cannot infer the array's element type (CLAUDE.md: asyncpg needs CAST on
# raw-SQL params).
_COUNTS_UPSERT_SQL = text(
    """
    INSERT INTO fact_access_stats (fact_id, access_count, last_accessed)
    SELECT k.id, t.cnt, NOW()
    FROM unnest(CAST(:ids AS uuid[]), CAST(:counts AS integer[])) AS t(id, cnt)
    JOIN knowledge_triples k ON k.id = t.id
    ON CONFLICT (fact_id) DO UPDATE
    SET access_count = fact_access_stats.access_count + EXCLUDED.access_count,
        last_accessed = EXCLUDED.last_accessed
    """
)


def _build_counts(fact_ids: Iterable[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for fid in fact_ids:
        if not fid:
            continue
        key = str(fid)
        counts[key] = counts.get(key, 0) + 1
    return counts


async def _flush_counts(session: AsyncSession, counts: dict[str, int]) -> int:
    if not counts:
        return 0
    ids = list(counts.keys())
    amounts = [counts[i] for i in ids]
    result = await session.execute(_COUNTS_UPSERT_SQL, {"ids": ids, "counts": amounts})
    await session.commit()
    # Not len(ids): the JOIN against knowledge_triples means an id whose row
    # is gone by flush time silently degrades out of the row count instead
    # of voiding the whole statement.
    return result.rowcount


async def record_access(session: AsyncSession, fact_ids: Iterable[object]) -> int:
    """Bump the access counters for ``fact_ids`` in one statement.

    Each occurrence of an id in the input adds to its count. Returns the
    number of distinct ids written (0 for an empty/all-None input, which is
    a no-op — no statement is issued).
    """
    return await _flush_counts(session, _build_counts(fact_ids))


def spawn_record_access(
    fact_ids: Iterable[object],
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> asyncio.Task | None:
    """Fire-and-forget: buffer the access and ensure a flush is scheduled,
    without the caller awaiting anything.

    Buffering is synchronous and cannot drop an access: every id lands in
    ``_pending_counts`` before this function returns. At most one flush task
    is ever alive; a call that arrives while one is already scheduled just
    adds to the same buffer that task will drain.

    Returns the active/scheduled ``asyncio.Task`` (ignored by production
    callers; useful for tests that want to await it deterministically
    instead of sleeping), or ``None`` when there is nothing to write.
    """
    global _flush_task
    ids = [str(fid) for fid in fact_ids if fid]
    if not ids:
        return None

    for fid in ids:
        _pending_counts[fid] = _pending_counts.get(fid, 0) + 1

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
                        "fact_access_stats bump failed for %d id(s)", len(batch)
                    )
        finally:
            _flush_task = None

    _flush_task = spawn(_run(), name="fact-access-stats-bump")
    return _flush_task
