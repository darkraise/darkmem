"""Tests for the ``fact_access_stats`` feeder (doc 08 §6, T2.84).

Mirrors ``test_access_stats.py``'s structure and its stated reason for the
shape: ``record_access`` / ``_flush_counts`` are exercised against a real,
committing session bound to ``test_engine`` (not the conftest ``session``
fixture, whose writes live inside a SAVEPOINT on one connection and are
never visible to a genuinely separate connection — exactly the shape the
background writer uses in production). The scheduling and off-hot-path
proofs against ``FactsChannel`` itself live in ``test_facts_channel.py``,
next to the channel they exercise; this file proves the SQL substrate the
same way T2.29's tests prove ``memory_access_stats``'s.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import fact_access_stats
from app.services.triple_key import compute_triple_key
from app.utils import background
from tests.conftest import test_engine

NOW = datetime(2026, 8, 5, 12, 0, 0, tzinfo=timezone.utc)
PROJECT = "t284-fact-access-stats"


def _factory() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(test_engine, expire_on_commit=False)


async def _seed_fact(factory, *, subject: str | None = None) -> str:
    subject = subject or f"subject-{uuid.uuid4()}"
    async with factory() as s:
        repo = KnowledgeTripleRepository(s)
        row = await repo.insert_open(
            triple_key=compute_triple_key(PROJECT, subject, "USES", "postgres"),
            subject_name=subject,
            object_name="postgres",
            rel_type="USES",
            fact=f"{subject} USES postgres",
            reference_time=NOW,
            project=PROJECT,
        )
        await s.commit()
        return row["id"]


async def _cleanup_facts(factory, fact_ids) -> None:
    if not fact_ids:
        return
    async with factory() as s:
        await s.execute(
            text("DELETE FROM knowledge_triples WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(f) for f in fact_ids]},
        )
        await s.commit()


async def _stats_row(factory, fact_id):
    async with factory() as s:
        return (await s.execute(
            text(
                "SELECT access_count, last_accessed FROM fact_access_stats "
                "WHERE fact_id = CAST(:id AS uuid)"
            ),
            {"id": str(fact_id)},
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
    fact_id = await _seed_fact(factory)
    try:
        async with factory() as s:
            n = await fact_access_stats.record_access(s, [fact_id])
        assert n == 1

        row = await _stats_row(factory, fact_id)
        assert row is not None
        assert row.access_count == 1
        assert row.last_accessed is not None
    finally:
        await _cleanup_facts(factory, [fact_id])


@pytest.mark.asyncio
async def test_record_access_second_access_increments_not_duplicates():
    factory = _factory()
    fact_id = await _seed_fact(factory)
    try:
        async with factory() as s:
            await fact_access_stats.record_access(s, [fact_id])
        first = await _stats_row(factory, fact_id)

        async with factory() as s:
            await fact_access_stats.record_access(s, [fact_id])
        second = await _stats_row(factory, fact_id)

        assert second.access_count == first.access_count + 1 == 2
        assert second.last_accessed > first.last_accessed, (
            "last_accessed must advance on every access, not freeze after the first"
        )

        async with factory() as s:
            count = (await s.execute(
                text("SELECT COUNT(*) FROM fact_access_stats WHERE fact_id = CAST(:id AS uuid)"),
                {"id": str(fact_id)},
            )).scalar_one()
        assert count == 1
    finally:
        await _cleanup_facts(factory, [fact_id])


@pytest.mark.asyncio
async def test_record_access_writes_k_ids_in_one_statement():
    factory = _factory()
    ids = [await _seed_fact(factory) for _ in range(4)]
    try:
        async with factory() as real:
            spy = _SpySession(real)
            n = await fact_access_stats.record_access(spy, ids)

        assert n == len(ids)
        assert spy.execute_calls == 1, "K ids must update in one statement, not N round trips"

        for fact_id in ids:
            row = await _stats_row(factory, fact_id)
            assert row is not None
            assert row.access_count == 1
    finally:
        await _cleanup_facts(factory, ids)


@pytest.mark.asyncio
async def test_record_access_empty_input_is_a_noop():
    factory = _factory()
    async with factory() as real:
        spy = _SpySession(real)
        n = await fact_access_stats.record_access(spy, [])
    assert n == 0
    assert spy.execute_calls == 0, "an empty id set must issue no statement at all"

    async with factory() as real:
        spy = _SpySession(real)
        n = await fact_access_stats.record_access(spy, [None, ""])
    assert n == 0
    assert spy.execute_calls == 0


@pytest.mark.asyncio
async def test_record_access_survives_one_deleted_fact_in_batch():
    """The FK-tolerant JOIN (against ``knowledge_triples``, mirroring
    ``access_stats``'s JOIN against ``memories``): a ghost id degrades that
    one row, not the whole batch."""
    factory = _factory()
    survivor = await _seed_fact(factory)
    ghost = await _seed_fact(factory)
    try:
        await _cleanup_facts(factory, [ghost])  # delete the ghost only

        async with factory() as s:
            n = await fact_access_stats.record_access(s, [survivor, ghost])

        assert n == 1, "only the surviving id should be reported as written"
        row = await _stats_row(factory, survivor)
        assert row is not None
        assert row.access_count == 1
    finally:
        await _cleanup_facts(factory, [survivor])


@pytest.mark.asyncio
async def test_deleting_fact_cascades_stats_row():
    factory = _factory()
    fact_id = await _seed_fact(factory)
    try:
        async with factory() as s:
            await fact_access_stats.record_access(s, [fact_id])
        assert (await _stats_row(factory, fact_id)) is not None

        await _cleanup_facts(factory, [fact_id])

        assert (await _stats_row(factory, fact_id)) is None
    finally:
        await _cleanup_facts(factory, [fact_id])


# ── spawn_record_access: the coalescing buffer itself ──────────────────


class _FakeAsyncCtx:
    """A no-op ``async with ... as session`` stand-in. Mirrors
    ``test_access_stats.py``'s helper of the same name/shape."""

    async def __aenter__(self):
        return None

    async def __aexit__(self, *exc):
        return False


@pytest.mark.asyncio
async def test_spawn_record_access_coalesces_without_loss(monkeypatch):
    """The T2.29-review shape, replayed for this module's own buffer: calling
    ``spawn_record_access`` many times back-to-back, faster than any single
    flush could run, must not drop a single count."""
    monkeypatch.setattr(fact_access_stats, "_FLUSH_DELAY_SECONDS", 0.01)
    flushed: dict[str, int] = {}

    async def fake_flush_counts(_session, counts):
        for k, v in counts.items():
            flushed[k] = flushed.get(k, 0) + v

    monkeypatch.setattr(fact_access_stats, "_flush_counts", fake_flush_counts)
    monkeypatch.setattr(fact_access_stats, "async_session_factory", lambda: _FakeAsyncCtx())

    ids = [str(uuid.uuid4()) for _ in range(5)]
    calls = 200
    for i in range(calls):
        fact_access_stats.spawn_record_access([ids[i % len(ids)]])

    pending = [
        t for t in background._background_tasks if t.get_name() == "fact-access-stats-bump"
    ]
    while pending:
        await asyncio.gather(*pending)
        pending = [
            t for t in background._background_tasks if t.get_name() == "fact-access-stats-bump"
        ]

    assert sum(flushed.values()) == calls, "every scheduled access must be recorded, none dropped"
    for fid in ids:
        assert flushed.get(fid) == calls // len(ids)


@pytest.mark.asyncio
async def test_spawn_record_access_recovers_after_flush_completes(monkeypatch):
    """After one flush cycle fully completes, a later access must still
    schedule and successfully run a fresh one — the buffer must not wedge
    shut."""
    monkeypatch.setattr(fact_access_stats, "_FLUSH_DELAY_SECONDS", 0.01)
    flushed: list[dict[str, int]] = []

    async def fake_flush_counts(_session, counts):
        flushed.append(dict(counts))

    monkeypatch.setattr(fact_access_stats, "_flush_counts", fake_flush_counts)
    monkeypatch.setattr(fact_access_stats, "async_session_factory", lambda: _FakeAsyncCtx())

    first_id = str(uuid.uuid4())
    task1 = fact_access_stats.spawn_record_access([first_id])
    assert task1 is not None
    await task1
    assert flushed == [{first_id: 1}]
    assert fact_access_stats._flush_task is None, "a completed flush must release its task slot"

    second_id = str(uuid.uuid4())
    task2 = fact_access_stats.spawn_record_access([second_id])
    assert task2 is not None, "a later access must still be able to schedule a new flush"
    assert task2 is not task1
    await task2
    assert flushed == [{first_id: 1}, {second_id: 1}], (
        "the second flush must actually run, not be silently absorbed by a wedged buffer"
    )
