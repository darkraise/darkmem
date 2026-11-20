"""The lift against a re-extraction of the same memory, on two connections."""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.repositories.graph import PostgresGraphRepository
from app.services import fact_lift
from app.services.fact_lift import DEFAULT_LIFT_BATCH, _lift_one, _pending_candidates, run_lift
from app.services.fact_provenance import memory_source_ref
from tests.conftest import test_engine
from tests.test_fact_lift import assert_relation, facts, seed_memory, sources


async def _seed_asserting(factory, project: str, origin_key: str) -> str:
    async with factory() as seed:
        memory_id = await seed_memory(seed, project=project, origin_key=origin_key)
        await assert_relation(
            seed, memory_id=memory_id, subject=project, rel_type="USES", obj="postgres",
        )
        await seed.commit()
    return memory_id


async def _candidate(session, project: str):
    pending = await _pending_candidates(
        session, batch_size=DEFAULT_LIFT_BATCH, min_asserting_memories=1,
    )
    (candidate,) = [c for c in pending if c.project == project]
    return candidate


async def _lift(session, candidate):
    async with session.begin_nested():
        return await _lift_one(session, candidate)


async def _hold_memory_row(session, memory_id: str) -> None:
    await session.execute(
        text("UPDATE memories SET content = content WHERE id = CAST(:id AS uuid)"),
        {"id": memory_id},
    )


async def _cleanup(factory, projects: list[str], memory_ids: list[str]) -> None:
    async with factory() as cleanup:
        graph = PostgresGraphRepository(cleanup)
        for memory_id in memory_ids:
            await graph.delete_by_memory_id(UUID(memory_id))
        for project in projects:
            await cleanup.execute(
                text("DELETE FROM knowledge_triples WHERE project = :project"), {"project": project},
            )
            await cleanup.execute(
                text("DELETE FROM memories WHERE project = :project"), {"project": project},
            )
        await cleanup.commit()


async def test_lift_waits_for_the_reextraction_and_reads_the_new_graph(setup_database):
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    project = f"lift-interleave-{uuid4()}"
    keeper = await _seed_asserting(factory, project, "keeper")
    async with factory() as seed:
        await run_lift(seed)
        await seed.commit()
    moved = await _seed_asserting(factory, project, "moved")

    task = None
    async with factory() as reextracting, factory() as lifting, factory() as observer:
        try:
            fact_id = (await facts(observer, project))[0]["id"]
            candidate = await _candidate(lifting, project)
            assert memory_source_ref(moved) in candidate.origins

            await _hold_memory_row(reextracting, moved)
            await PostgresGraphRepository(reextracting).delete_by_memory_id(UUID(moved))

            task = asyncio.create_task(_lift(lifting, candidate))
            await asyncio.sleep(0.3)
            assert not task.done(), "the lift read the memory's graph past its re-extraction"

            await reextracting.commit()
            await asyncio.wait_for(task, 5)
            await lifting.commit()

            refs = {row["source_ref"] for row in await sources(observer, fact_id)}
            assert refs == {memory_source_ref(keeper)}
        finally:
            if task is not None and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            await reextracting.rollback()
            await lifting.rollback()
            await observer.rollback()
            await _cleanup(factory, [project], [keeper, moved])


async def test_lift_of_an_unrelated_memory_is_not_blocked(setup_database):
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    busy_project = f"lift-busy-{uuid4()}"
    free_project = f"lift-free-{uuid4()}"
    busy = await _seed_asserting(factory, busy_project, "busy")
    free = await _seed_asserting(factory, free_project, "free")

    async with factory() as reextracting, factory() as lifting:
        try:
            candidate = await _candidate(lifting, free_project)
            await _hold_memory_row(reextracting, busy)

            lifted = await asyncio.wait_for(_lift(lifting, candidate), 0.3)

            assert lifted.minted
        finally:
            await reextracting.rollback()
            await lifting.rollback()
            await _cleanup(factory, [busy_project, free_project], [busy, free])


async def test_a_memory_locked_past_the_wait_defers_its_candidate(
    setup_database, monkeypatch, caplog,
):
    monkeypatch.setattr(fact_lift, "MEMORY_LOCK_WAIT_SECONDS", 0.2)
    caplog.set_level(logging.INFO, logger=fact_lift.logger.name)
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    busy_project = f"lift-deferred-{uuid4()}"
    free_project = f"lift-alongside-{uuid4()}"
    busy = await _seed_asserting(factory, busy_project, "busy")
    free = await _seed_asserting(factory, free_project, "free")

    async with factory() as reextracting, factory() as lifting, factory() as observer:
        try:
            await _hold_memory_row(reextracting, busy)

            await run_lift(lifting)
            await lifting.commit()
            assert await facts(observer, busy_project) == []
            assert len(await facts(observer, free_project)) == 1
            lift_records = [r for r in caplog.records if r.name == fact_lift.logger.name]
            assert any("fact lifting deferred" in r.getMessage() for r in lift_records)
            assert not [r for r in lift_records if r.levelno >= logging.ERROR]

            await reextracting.commit()
            await run_lift(lifting)
            await lifting.commit()
            assert len(await facts(observer, busy_project)) == 1
        finally:
            await reextracting.rollback()
            await lifting.rollback()
            await observer.rollback()
            await _cleanup(factory, [busy_project, free_project], [busy, free])


async def test_a_tick_spends_one_lock_wait_budget(setup_database, monkeypatch):
    monkeypatch.setattr(fact_lift, "MEMORY_LOCK_WAIT_SECONDS", 1.0)
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    projects = [f"lift-budget-{uuid4()}", f"lift-budget-{uuid4()}"]
    held = [await _seed_asserting(factory, project, "held") for project in projects]

    async with factory() as reextracting, factory() as lifting, factory() as observer:
        try:
            for memory_id in held:
                await _hold_memory_row(reextracting, memory_id)

            loop = asyncio.get_running_loop()
            started = loop.time()
            await run_lift(lifting)
            elapsed = loop.time() - started
            await lifting.commit()

            assert elapsed < 1.6, f"two busy candidates spent {elapsed:.2f}s"
            for project in projects:
                assert await facts(observer, project) == []
        finally:
            await reextracting.rollback()
            await lifting.rollback()
            await observer.rollback()
            await _cleanup(factory, projects, held)
