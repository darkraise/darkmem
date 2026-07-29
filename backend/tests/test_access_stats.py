"""Tests for the ``memory_access_stats`` feeder (doc 07 §3, T2.29).

Two layers, matching the two things the brief calls load-bearing:

* ``record_access`` / ``_flush_counts`` are exercised against a *real,
  committing* session bound to ``test_engine`` (not the conftest ``session``
  fixture — that fixture's writes live inside a SAVEPOINT on one connection
  and are never visible to a genuinely separate connection, which is exactly
  the shape the background writer uses in production). These tests prove
  the SQL itself: first access, the ON CONFLICT increment path (including
  that ``last_accessed`` actually moves, not just ``access_count``), one
  statement for K ids, ``memories.updated_at`` untouched, the FK cascade on
  delete, and that one deleted memory in a batch degrades only that row
  rather than voiding the whole statement.
* ``HybridSearchService.search`` / ``search_with_trace`` are exercised with
  ``access_stats._flush_counts`` and ``access_stats.async_session_factory``
  monkeypatched, so the real ``app.utils.background.spawn`` machinery still
  runs — proving *structurally*, via asyncio's own scheduling guarantee
  that a freshly created task never runs before the current coroutine
  yields, that the write is scheduled rather than awaited, and that a write
  failure never reaches the caller.

Following a T2.29 review, ``spawn_record_access`` is a coalescing buffer
(see the module docstring in ``access_stats.py`` for why the earlier
drop-when-saturated cap was wrong: it lost 20-75% of accesses under
sustained load, concentrated on the busiest memories). The tests below
cover the buffer directly: that it never loses a count under concurrent
calls, and that it recovers to schedule a fresh flush after a previous one
completes rather than wedging shut.
"""
from __future__ import annotations

import asyncio
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.memory import Memory
from app.services import access_stats
from app.services.embedder_registry import child_table
from app.services.hybrid_search import HybridSearchService
from app.utils import background
from tests.conftest import test_engine


@pytest_asyncio.fixture(autouse=True)
async def _clean_access_stats_buffer():
    """``spawn_record_access``'s buffer (``_pending_counts`` / `_flush_task``)
    is process-global and the whole suite shares one event loop
    (``asyncio_default_test_loop_scope = "session"``), so a real, unpatched
    flush left running by an unrelated hybrid-search test elsewhere in the
    suite (default debounce 0.25s) could still be mid-sleep when a test here
    starts, coalescing unrelated ids into this test's buffer. Draining any
    such leftover before each test starts keeps every test's buffer state
    genuinely its own."""
    task = access_stats._flush_task
    if task is not None and not task.done():
        await asyncio.wait_for(task, timeout=5)
    yield


def _factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(test_engine, expire_on_commit=False)


async def _seed_memory(factory, **overrides) -> uuid.UUID:
    mem_id = overrides.pop("id", uuid.uuid4())
    async with factory() as s:
        s.add(Memory(
            id=mem_id, content="access stats fixture", source="test",
            importance=0.5, metadata_={}, **overrides,
        ))
        await s.commit()
    return mem_id


async def _cleanup_memories(factory, memory_ids) -> None:
    if not memory_ids:
        return
    async with factory() as s:
        await s.execute(
            text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(m) for m in memory_ids]},
        )
        await s.commit()


async def _stats_row(factory, memory_id):
    async with factory() as s:
        return (await s.execute(
            text(
                "SELECT access_count, last_accessed FROM memory_access_stats "
                "WHERE memory_id = :id"
            ),
            {"id": str(memory_id)},
        )).first()


class _SpySession:
    """Wraps a real session, counting ``execute`` calls so a test can prove
    "one statement", not just "the right end state"."""

    def __init__(self, inner):
        self._inner = inner
        self.execute_calls = 0

    async def execute(self, *a, **kw):
        self.execute_calls += 1
        return await self._inner.execute(*a, **kw)

    async def commit(self):
        await self._inner.commit()


# ── record_access / _flush_counts: the raw SQL, real committing session ──


@pytest.mark.asyncio
async def test_record_access_first_access_creates_row():
    factory = _factory()
    mem_id = await _seed_memory(factory)
    try:
        async with factory() as s:
            n = await access_stats.record_access(s, [mem_id])
        assert n == 1

        row = await _stats_row(factory, mem_id)
        assert row is not None
        assert row.access_count == 1
        assert row.last_accessed is not None
    finally:
        await _cleanup_memories(factory, [mem_id])


@pytest.mark.asyncio
async def test_record_access_second_access_increments_not_duplicates():
    factory = _factory()
    mem_id = await _seed_memory(factory)
    try:
        async with factory() as s:
            await access_stats.record_access(s, [mem_id])
        first = await _stats_row(factory, mem_id)

        async with factory() as s:
            await access_stats.record_access(s, [mem_id])
        second = await _stats_row(factory, mem_id)

        assert second.access_count == first.access_count + 1 == 2
        # F3 guard: last_accessed must actually move on the ON CONFLICT path,
        # not just access_count -- w_recency reads this column, and a SQL
        # regression that pins it to `memory_access_stats.last_accessed`
        # (freezing at first-access forever) leaves access_count correct
        # while silently breaking the recency half of the substrate.
        assert second.last_accessed > first.last_accessed, (
            "last_accessed must advance on every access, not freeze after the first"
        )

        async with factory() as s:
            count = (await s.execute(
                text("SELECT COUNT(*) FROM memory_access_stats WHERE memory_id = :id"),
                {"id": str(mem_id)},
            )).scalar_one()
        assert count == 1
    finally:
        await _cleanup_memories(factory, [mem_id])


@pytest.mark.asyncio
async def test_record_access_writes_k_ids_in_one_statement():
    factory = _factory()
    ids = [await _seed_memory(factory) for _ in range(4)]
    try:
        async with factory() as real:
            spy = _SpySession(real)
            n = await access_stats.record_access(spy, ids)

        assert n == len(ids)
        assert spy.execute_calls == 1, "K ids must update in one statement, not N round trips"

        for mem_id in ids:
            row = await _stats_row(factory, mem_id)
            assert row is not None
            assert row.access_count == 1
    finally:
        await _cleanup_memories(factory, ids)


@pytest.mark.asyncio
async def test_record_access_leaves_memories_updated_at_untouched():
    factory = _factory()
    mem_id = await _seed_memory(factory)
    try:
        async with factory() as s:
            before = (await s.execute(
                select(Memory.updated_at).where(Memory.id == mem_id)
            )).scalar_one()

        async with factory() as s:
            await access_stats.record_access(s, [mem_id])
        async with factory() as s:
            await access_stats.record_access(s, [mem_id])  # exercise the update path too

        async with factory() as s:
            after = (await s.execute(
                select(Memory.updated_at).where(Memory.id == mem_id)
            )).scalar_one()

        assert before == after, "an access must never bump memories.updated_at"
    finally:
        await _cleanup_memories(factory, [mem_id])


@pytest.mark.asyncio
async def test_record_access_empty_input_is_a_noop():
    factory = _factory()
    async with factory() as real:
        spy = _SpySession(real)
        n = await access_stats.record_access(spy, [])
    assert n == 0
    assert spy.execute_calls == 0, "an empty id set must issue no statement at all"

    async with factory() as real:
        spy = _SpySession(real)
        n = await access_stats.record_access(spy, [None, ""])
    assert n == 0
    assert spy.execute_calls == 0


@pytest.mark.asyncio
async def test_record_access_survives_one_deleted_memory_in_batch():
    """F4: the upsert JOINs against ``memories`` so a ghost id (deleted
    between search and flush) degrades that one row, not the whole batch --
    a bare CAST-and-insert against the FK would abort the entire statement
    and lose every surviving id's bump too."""
    factory = _factory()
    survivor = await _seed_memory(factory)
    ghost = await _seed_memory(factory)
    try:
        await _cleanup_memories(factory, [ghost])  # delete the ghost only

        async with factory() as s:
            n = await access_stats.record_access(s, [survivor, ghost])

        assert n == 1, "only the surviving id should be reported as written"
        row = await _stats_row(factory, survivor)
        assert row is not None
        assert row.access_count == 1
    finally:
        await _cleanup_memories(factory, [survivor])


@pytest.mark.asyncio
async def test_deleting_memory_cascades_stats_row():
    factory = _factory()
    mem_id = await _seed_memory(factory)
    try:
        async with factory() as s:
            await access_stats.record_access(s, [mem_id])
        assert (await _stats_row(factory, mem_id)) is not None

        async with factory() as s:
            await s.execute(text("DELETE FROM memories WHERE id = :id"), {"id": str(mem_id)})
            await s.commit()

        assert (await _stats_row(factory, mem_id)) is None
    finally:
        await _cleanup_memories(factory, [mem_id])


# ── spawn_record_access: the coalescing buffer itself ──────────────────


@pytest.mark.asyncio
async def test_spawn_record_access_coalesces_without_loss(monkeypatch):
    """The load-bearing regression test for the review's F1 finding: calling
    ``spawn_record_access`` many times back-to-back, faster than any single
    flush could run, must not drop a single count -- unlike the old
    drop-when-saturated cap, which lost 20-75% under exactly this shape."""
    monkeypatch.setattr(access_stats, "_FLUSH_DELAY_SECONDS", 0.01)
    flushed: dict[str, int] = {}

    async def fake_flush_counts(_session, counts):
        for k, v in counts.items():
            flushed[k] = flushed.get(k, 0) + v

    monkeypatch.setattr(access_stats, "_flush_counts", fake_flush_counts)
    monkeypatch.setattr(access_stats, "async_session_factory", lambda: _FakeAsyncCtx())

    ids = [str(uuid.uuid4()) for _ in range(5)]
    calls = 200
    for i in range(calls):
        access_stats.spawn_record_access([ids[i % len(ids)]])

    # Drain every task the loop above may have scheduled (the buffer can
    # legitimately produce more than one flush cycle if a prior one finished
    # mid-loop), not just the last one returned.
    pending = [t for t in background._background_tasks if t.get_name() == "access-stats-bump"]
    while pending:
        await asyncio.gather(*pending)
        pending = [t for t in background._background_tasks if t.get_name() == "access-stats-bump"]

    assert sum(flushed.values()) == calls, "every scheduled access must be recorded, none dropped"
    for mid in ids:
        assert flushed.get(mid) == calls // len(ids)


@pytest.mark.asyncio
async def test_spawn_record_access_recovers_after_flush_completes(monkeypatch):
    """F2: proves the mechanism cannot wedge itself shut the way the old
    ``_in_flight`` cap could (a leaked decrement silently killed the feeder
    forever after four searches). After one flush cycle fully completes, a
    later access must still schedule and successfully run a fresh one."""
    monkeypatch.setattr(access_stats, "_FLUSH_DELAY_SECONDS", 0.01)
    flushed: list[dict[str, int]] = []

    async def fake_flush_counts(_session, counts):
        flushed.append(dict(counts))

    monkeypatch.setattr(access_stats, "_flush_counts", fake_flush_counts)
    monkeypatch.setattr(access_stats, "async_session_factory", lambda: _FakeAsyncCtx())

    first_id = str(uuid.uuid4())
    task1 = access_stats.spawn_record_access([first_id])
    assert task1 is not None
    await task1
    assert flushed == [{first_id: 1}]
    assert access_stats._flush_task is None, "a completed flush must release its task slot"

    second_id = str(uuid.uuid4())
    task2 = access_stats.spawn_record_access([second_id])
    assert task2 is not None, "a later access must still be able to schedule a new flush"
    assert task2 is not task1
    await task2
    assert flushed == [{first_id: 1}, {second_id: 1}], (
        "the second flush must actually run, not be silently absorbed by a wedged buffer"
    )


# ── HybridSearchService: off-the-hot-path proof ────────────────────────


class _FakeLLM:
    def __init__(self, vector: list[float], fingerprint: str):
        self._vector = vector
        self._fingerprint = fingerprint

    async def embed(self, query: str):
        return self._vector, self._fingerprint


async def _seed_embedding_partition(session, fingerprint: str, dims: int) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": fingerprint, "mid": "fake-embedder", "dims": dims},
    )
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({dims}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))


class _FakeAsyncCtx:
    """A no-op ``async with ... as session`` stand-in, so the real
    ``spawn_record_access`` -> ``async with factory() as session`` shape
    runs without touching the app's real database."""

    async def __aenter__(self):
        return None

    async def __aexit__(self, *exc):
        return False


async def _seed_searchable_memory(session, fingerprint: str, dims: int, vector, content: str):
    mem_id = uuid.uuid4()
    session.add(Memory(id=mem_id, content=content, source="test", project="access-stats-test"))
    await session.flush()
    await _seed_embedding_partition(session, fingerprint, dims)
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), '{}'::jsonb)"
        ),
        {"mid": mem_id, "fp": fingerprint, "vec": str(vector)},
    )
    await session.flush()
    return mem_id


@pytest.mark.asyncio
async def test_search_schedules_write_without_awaiting_it(session, monkeypatch):
    fingerprint = "access-stats-fake|4"
    dims = 4
    vector = [1.0, 0.0, 0.0, 0.0]
    mem_id = await _seed_searchable_memory(
        session, fingerprint, dims, vector, "off-hot-path scheduling proof"
    )

    calls: list[list[str]] = []

    async def fake_flush_counts(_session, counts):
        calls.append(sorted(counts.keys()))

    monkeypatch.setattr(access_stats, "_flush_counts", fake_flush_counts)
    monkeypatch.setattr(access_stats, "async_session_factory", lambda: _FakeAsyncCtx())
    monkeypatch.setattr(access_stats, "_FLUSH_DELAY_SECONDS", 0.01)

    svc = HybridSearchService(_FakeLLM(vector, fingerprint), session)
    results = await svc.search("off-hot-path scheduling proof", limit=10)
    assert results

    # The write is scheduled, not awaited: asyncio never runs a task created
    # via create_task before the creating coroutine yields, and search()
    # returns with no further await after scheduling it. So immediately
    # after `await svc.search(...)` returns, the fake write has not run yet
    # — this is a scheduling guarantee, not a timing race. It is even more
    # robustly true here since the flush task also sleeps `_FLUSH_DELAY_SECONDS`
    # before touching the buffer at all.
    pending = [t for t in background._background_tasks if t.get_name() == "access-stats-bump"]
    assert len(pending) == 1, "expected exactly one scheduled access-stats task"
    assert calls == [], "the write must not have run before search() returned"

    await pending[0]
    assert calls == [[str(mem_id)]]


@pytest.mark.asyncio
async def test_search_with_trace_also_schedules_access_write(session, monkeypatch):
    fingerprint = "access-stats-fake-trace|4"
    dims = 4
    vector = [0.0, 1.0, 0.0, 0.0]
    mem_id = await _seed_searchable_memory(
        session, fingerprint, dims, vector, "trace path scheduling proof"
    )

    calls: list[list[str]] = []

    async def fake_flush_counts(_session, counts):
        calls.append(sorted(counts.keys()))

    monkeypatch.setattr(access_stats, "_flush_counts", fake_flush_counts)
    monkeypatch.setattr(access_stats, "async_session_factory", lambda: _FakeAsyncCtx())
    monkeypatch.setattr(access_stats, "_FLUSH_DELAY_SECONDS", 0.01)

    svc = HybridSearchService(_FakeLLM(vector, fingerprint), session)
    trace = await svc.search_with_trace("trace path scheduling proof", limit=10)
    assert trace.results

    pending = [t for t in background._background_tasks if t.get_name() == "access-stats-bump"]
    assert len(pending) == 1
    assert calls == []

    await pending[0]
    assert calls == [[str(mem_id)]]


@pytest.mark.asyncio
async def test_search_survives_access_write_failure(session, monkeypatch):
    fingerprint = "access-stats-fail|4"
    dims = 4
    vector = [0.0, 0.0, 1.0, 0.0]
    await _seed_searchable_memory(
        session, fingerprint, dims, vector, "write failure must not surface"
    )

    async def boom(_session, _counts):
        raise RuntimeError("simulated counter-write failure")

    monkeypatch.setattr(access_stats, "_flush_counts", boom)
    monkeypatch.setattr(access_stats, "async_session_factory", lambda: _FakeAsyncCtx())
    monkeypatch.setattr(access_stats, "_FLUSH_DELAY_SECONDS", 0.01)

    svc = HybridSearchService(_FakeLLM(vector, fingerprint), session)
    results = await svc.search("write failure must not surface", limit=10)
    assert results, "search results must be intact even though the counter write will raise"

    pending = [t for t in background._background_tasks if t.get_name() == "access-stats-bump"]
    assert len(pending) == 1
    # Let the failing write run to completion; spawn_record_access's own
    # try/except must swallow it — a task that raised would show up as a
    # logged "Background task failed" error, never as an exception on the
    # awaited handle here.
    await pending[0]


@pytest.mark.asyncio
async def test_search_with_no_results_schedules_nothing(session, monkeypatch):
    fingerprint = "access-stats-empty|4"
    # The partition must exist (an empty table is fine) so the semantic side
    # runs cleanly to zero rows instead of erroring on a missing relation.
    await _seed_embedding_partition(session, fingerprint, 4)

    async def fake_flush_counts(_session, _counts):
        pytest.fail("_flush_counts must not be reached when there is nothing to write")

    monkeypatch.setattr(access_stats, "_flush_counts", fake_flush_counts)

    svc = HybridSearchService(_FakeLLM([1.0, 0.0, 0.0, 0.0], fingerprint), session)
    # No memory matches this project filter on either side, so both channels
    # return empty.
    from app.repositories.vector import MemoryFilter
    results = await svc.search(
        "no matching content whatsoever xyzzy", limit=10,
        filters=MemoryFilter(project="nonexistent-project-access-stats"),
    )
    assert results == []

    # spawn_record_access no-ops on an empty id list, so no task is created.
    pending = [t for t in background._background_tasks if t.get_name() == "access-stats-bump"]
    assert pending == []
