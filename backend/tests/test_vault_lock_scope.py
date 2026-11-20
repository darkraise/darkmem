"""How long the vault's writers hold fact locks, on real connections."""
from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.repositories.graph import PostgresGraphRepository
from app.services import fact_lift
from app.services.fact_lift import run_lift
from app.services.fact_provenance import reconcile_memory_sources
from tests.conftest import test_engine
from tests.test_fact_lift import facts, sources
from tests.test_fact_lift_interleave import _cleanup, _seed_asserting


async def _lifted(factory, project: str) -> tuple[str, str]:
    memory_id = await _seed_asserting(factory, project, "withdrawn")
    async with factory() as lifting:
        await run_lift(lifting)
        await lifting.commit()
    async with factory() as reader:
        (fact,) = await facts(reader, project)
    return memory_id, fact["id"]


async def _strip_and_reconcile(session, memory_id: str) -> None:
    async with session.begin_nested():
        await PostgresGraphRepository(session).delete_by_memory_id(UUID(memory_id))
        await reconcile_memory_sources(session, memory_id=memory_id)


async def test_lift_commits_per_candidate_batch(setup_database, monkeypatch):
    monkeypatch.setattr(fact_lift, "LIFT_COMMIT_BATCH", 1)
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    projects = [f"lift-commit-{uuid4()}" for _ in range(3)]
    memories = [await _seed_asserting(factory, project, "m") for project in projects]

    lockable_before_commit: list[int] = []
    async with factory() as lifting, factory() as probe:
        try:
            real_commit = lifting.commit

            async def spying_commit():
                rows = await probe.execute(
                    text(
                        "SELECT id FROM knowledge_triples "
                        "WHERE project = ANY(CAST(:projects AS text[])) "
                        "FOR UPDATE NOWAIT"
                    ),
                    {"projects": projects},
                )
                lockable_before_commit.append(len(rows.all()))
                await probe.rollback()
                await real_commit()

            monkeypatch.setattr(lifting, "commit", spying_commit)
            await run_lift(lifting)
            monkeypatch.setattr(lifting, "commit", real_commit)
            await lifting.commit()

            assert len(lockable_before_commit) >= 3
            assert 2 in lockable_before_commit, (
                "a fact lifted earlier in the tick stayed locked or invisible "
                f"while a later batch ran: {lockable_before_commit}"
            )
        finally:
            await lifting.rollback()
            await probe.rollback()
            await _cleanup(factory, projects, memories)


async def test_withdrawal_times_out_instead_of_waiting(setup_database):
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    project = f"withdraw-timeout-{uuid4()}"
    memory_id, fact_id = await _lifted(factory, project)

    async with factory() as holder, factory() as pipeline:
        try:
            await holder.execute(
                text("SELECT id FROM knowledge_triples WHERE id = CAST(:id AS uuid) FOR UPDATE"),
                {"id": fact_id},
            )
            loop = asyncio.get_running_loop()
            started = loop.time()
            with pytest.raises(DBAPIError) as raised:
                await asyncio.wait_for(_strip_and_reconcile(pipeline, memory_id), 8)
            assert getattr(raised.value.orig, "sqlstate", None) == "55P03"
            assert loop.time() - started < 6

            remaining = await sources(pipeline, fact_id)
            assert len(remaining) == 1, "the failed savepoint kept its withdrawal"
        finally:
            await holder.rollback()
            await pipeline.rollback()
            await _cleanup(factory, [project], [memory_id])


async def test_withdrawal_leaves_lock_timeout_as_it_found_it(setup_database):
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    projects = [f"withdraw-guc-{uuid4()}" for _ in range(2)]
    lifted = [await _lifted(factory, project) for project in projects]

    async with factory() as batch:
        try:
            before = (await batch.execute(text("SHOW lock_timeout"))).scalar_one()
            await _strip_and_reconcile(batch, lifted[0][0])
            after_first = (await batch.execute(text("SHOW lock_timeout"))).scalar_one()
            await _strip_and_reconcile(batch, lifted[1][0])

            assert after_first == before
            assert await sources(batch, lifted[0][1]) == []
        finally:
            await batch.rollback()
            await _cleanup(factory, projects, [memory for memory, _ in lifted])
