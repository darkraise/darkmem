from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.repositories.graph import PostgresGraphRepository
from app.services.fact_lift import (
    DEFAULT_LIFT_BATCH,
    _lift_one,
    _pending_candidates,
    reconcile_code_sources,
    run_lift,
)
from app.services.fact_provenance import withdraw_memory_sources
from tests.conftest import test_engine
from tests.test_fact_lift import assert_relation, facts, seed_memory, sources


@pytest.mark.parametrize("source_kind", ["memory", "code"])
async def test_withdrawal_waits_for_lift_before_counting_surviving_sources(setup_database, source_kind):
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    project = f"withdraw-race-{uuid4()}"
    async with factory() as seed:
        original = await seed_memory(seed, project=project, origin_key="original")
        await assert_relation(seed, memory_id=original, subject=project, rel_type="USES", obj="postgres")
        await run_lift(seed)
        fact_id = (await facts(seed, project))[0]["id"]
        if source_kind == "code":
            await seed.execute(text("UPDATE fact_sources SET source_kind = 'code' WHERE fact_id = :id"), {"id": fact_id})
            await PostgresGraphRepository(seed).delete_by_memory_id(original)
        witness = await seed_memory(seed, project=project, origin_key="new-witness")
        await assert_relation(seed, memory_id=witness, subject=project, rel_type="USES", obj="postgres")
        await seed.commit()

    async with factory() as lifting, factory() as withdrawing, factory() as observer:
        withdrawal = None
        try:
            # One candidate held uncommitted inside its batch: the lift keeps
            # the fact's lock until that batch commits.
            (candidate,) = [
                c for c in await _pending_candidates(
                    lifting, batch_size=DEFAULT_LIFT_BATCH, min_asserting_memories=1,
                )
                if c.project == project
            ]
            async with lifting.begin_nested():
                lifted = await _lift_one(lifting, candidate)
            assert lifted.sources_added == 1
            withdrawing_pid = (await withdrawing.execute(text("SELECT pg_backend_pid()"))).scalar_one()
            withdrawal = asyncio.create_task(
                withdraw_memory_sources(withdrawing, memory_id=original)
                if source_kind == "memory" else reconcile_code_sources(withdrawing)
            )
            async with asyncio.timeout(5):
                while True:
                    blockers = (await observer.execute(
                        text("SELECT cardinality(pg_blocking_pids(:pid))"),
                        {"pid": withdrawing_pid},
                    )).scalar_one()
                    if blockers:
                        break
                    await asyncio.sleep(0.01)
            await lifting.commit()
            await asyncio.wait_for(withdrawal, 5)
            await withdrawing.commit()
            remaining = await sources(observer, fact_id)
            assert [source["source_ref"] for source in remaining] == [witness]
            stored = await facts(observer, project)
            assert len(stored) == 1
            assert stored[0]["id"] == fact_id
            assert stored[0]["expired_at"] is None
            assert stored[0]["invalid_at"] is None
        finally:
            if withdrawal is not None and not withdrawal.done():
                withdrawal.cancel()
                await asyncio.gather(withdrawal, return_exceptions=True)
            await lifting.rollback()
            await withdrawing.rollback()
            await observer.rollback()
            async with factory() as cleanup:
                graph = PostgresGraphRepository(cleanup)
                await graph.delete_by_memory_id(original)
                await graph.delete_by_memory_id(witness)
                await cleanup.execute(text("DELETE FROM knowledge_triples WHERE project = :project"), {"project": project})
                await cleanup.execute(text("DELETE FROM memories WHERE project = :project"), {"project": project})
                await cleanup.commit()
