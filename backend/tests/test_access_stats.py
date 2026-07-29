"""Tests for the ``memory_access_stats`` feeder (doc 07 §3, T2.29).

Two layers, matching the two things the brief calls load-bearing:

* ``record_access`` is exercised against a *real, committing* session bound
  to ``test_engine`` (not the conftest ``session`` fixture — that fixture's
  writes live inside a SAVEPOINT on one connection and are never visible to
  a genuinely separate connection, which is exactly the shape the
  background writer uses in production). These tests prove the SQL itself:
  first access, the ON CONFLICT increment path, one statement for K ids,
  ``memories.updated_at`` untouched, and the FK cascade on delete.
* ``HybridSearchService.search`` / ``search_with_trace`` are exercised with
  ``access_stats.record_access`` and ``access_stats.async_session_factory``
  monkeypatched, so the real ``app.utils.background.spawn`` machinery still
  runs — proving *structurally*, via asyncio's own scheduling guarantee
  that a freshly created task never runs before the current coroutine
  yields, that the write is scheduled rather than awaited, and that a write
  failure never reaches the caller.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.memory import Memory
from app.services import access_stats
from app.services.embedder_registry import child_table
from app.services.hybrid_search import HybridSearchService
from app.utils import background
from tests.conftest import test_engine


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


# ── record_access: the raw SQL, against a real committing session ─────


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
        class _SpySession:
            def __init__(self, inner):
                self._inner = inner
                self.execute_calls = 0

            async def execute(self, *a, **kw):
                self.execute_calls += 1
                return await self._inner.execute(*a, **kw)

            async def commit(self):
                await self._inner.commit()

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
    async with factory() as s:
        n = await access_stats.record_access(s, [])
    assert n == 0
    async with factory() as s:
        n = await access_stats.record_access(s, [None, ""])
    assert n == 0


@pytest.mark.asyncio
async def test_spawn_record_access_drops_when_saturated(monkeypatch):
    """``_MAX_IN_FLIGHT`` bounds background-connection concurrency: once that
    many writes are outstanding, a new access is dropped rather than queued
    (module docstring). Forcing the counter to the cap directly makes this
    deterministic, independent of any other test's in-flight writes."""
    monkeypatch.setattr(access_stats, "_in_flight", access_stats._MAX_IN_FLIGHT)

    before = len(background._background_tasks)
    task = access_stats.spawn_record_access([str(uuid.uuid4())])

    assert task is None, "a write must be dropped, not queued, once saturated"
    assert len(background._background_tasks) == before, "a dropped write must not spawn a task"


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

    async def fake_record_access(_session, ids):
        calls.append(sorted(str(i) for i in ids))

    monkeypatch.setattr(access_stats, "record_access", fake_record_access)
    monkeypatch.setattr(access_stats, "async_session_factory", lambda: _FakeAsyncCtx())

    svc = HybridSearchService(_FakeLLM(vector, fingerprint), session)
    results = await svc.search("off-hot-path scheduling proof", limit=10)
    assert results

    # The write is scheduled, not awaited: asyncio never runs a task created
    # via create_task before the creating coroutine yields, and search()
    # returns with no further await after scheduling it. So immediately
    # after `await svc.search(...)` returns, the fake write has not run yet
    # — this is a scheduling guarantee, not a timing race.
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

    async def fake_record_access(_session, ids):
        calls.append(sorted(str(i) for i in ids))

    monkeypatch.setattr(access_stats, "record_access", fake_record_access)
    monkeypatch.setattr(access_stats, "async_session_factory", lambda: _FakeAsyncCtx())

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

    async def boom(_session, _ids):
        raise RuntimeError("simulated counter-write failure")

    monkeypatch.setattr(access_stats, "record_access", boom)
    monkeypatch.setattr(access_stats, "async_session_factory", lambda: _FakeAsyncCtx())

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

    async def fake_record_access(_session, _ids):
        pytest.fail("record_access must not be reached when there is nothing to write")

    monkeypatch.setattr(access_stats, "record_access", fake_record_access)

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
