"""T1.66: `memories.superseded_by` gets an index, and the reverse-lineage
query (`PostgresMemoryRepository.get_predecessors`, T1.47) actually uses it.

T1.27's precedent (`tests/test_technologies_denorm.py`) is the model:
presence in `pg_indexes` proves nothing about the planner's choice, so this
EXPLAINs the *executed* statement — `predecessors_stmt`, the same builder
`get_predecessors` calls — against a table large enough and ANALYZEd, with
no planner hints. On a handful of rows Postgres reasonably prefers a
sequential scan regardless of the index, so the table is seeded past that
point rather than the plan being forced.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from app.repositories.relational import predecessors_stmt

pytestmark = pytest.mark.asyncio

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)


async def test_ix_memories_superseded_by_is_used_by_the_reverse_lineage_query(session):
    indexdef = (await session.execute(
        text("SELECT indexdef FROM pg_indexes "
             "WHERE tablename = 'memories' AND indexname = :n"),
        {"n": "ix_memories_superseded_by"},
    )).scalar_one()
    assert "superseded_by" in indexdef

    successor_id = uuid.uuid4()
    await session.execute(text("""
        INSERT INTO memories (id, content, source, project, status, created_at)
        VALUES (:id, 'the successor', 'test', 'default', 'active', :created_at)
    """), {"id": str(successor_id), "created_at": NOW})

    await session.execute(text("""
        INSERT INTO memories (id, content, source, project, status,
                               superseded_by, created_at)
        SELECT gen_random_uuid(), 'predecessor ' || g, 'test', 'default',
               CASE WHEN g % 500 = 0 THEN 'superseded' ELSE 'active' END::memory_status,
               CASE WHEN g % 500 = 0 THEN CAST(:successor_id AS uuid) ELSE NULL END,
               CAST(:now AS timestamptz) - (g || ' minutes')::interval
        FROM generate_series(1, 8000) g
    """), {"successor_id": str(successor_id), "now": NOW})
    await session.execute(text("ANALYZE memories"))

    stmt = predecessors_stmt(successor_id)
    sql = str(stmt.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    ))
    plan = "\n".join(
        (await session.execute(text("EXPLAIN " + sql))).scalars().all()
    )
    assert "ix_memories_superseded_by" in plan, plan
    assert "Seq Scan on memories" not in plan, plan


async def test_dropping_the_index_makes_the_planner_seq_scan(session):
    """The guard this test exists to prove: without the index the same
    statement, at the same scale, falls back to a sequential scan — so the
    assertion above is actually exercising the index rather than something
    the planner would have chosen anyway."""
    await session.execute(text("DROP INDEX ix_memories_superseded_by"))

    successor_id = uuid.uuid4()
    await session.execute(text("""
        INSERT INTO memories (id, content, source, project, status, created_at)
        VALUES (:id, 'the successor', 'test', 'default', 'active', :created_at)
    """), {"id": str(successor_id), "created_at": NOW})

    await session.execute(text("""
        INSERT INTO memories (id, content, source, project, status,
                               superseded_by, created_at)
        SELECT gen_random_uuid(), 'predecessor ' || g, 'test', 'default',
               CASE WHEN g % 500 = 0 THEN 'superseded' ELSE 'active' END::memory_status,
               CASE WHEN g % 500 = 0 THEN CAST(:successor_id AS uuid) ELSE NULL END,
               CAST(:now AS timestamptz) - (g || ' minutes')::interval
        FROM generate_series(1, 8000) g
    """), {"successor_id": str(successor_id), "now": NOW})
    await session.execute(text("ANALYZE memories"))

    stmt = predecessors_stmt(successor_id)
    sql = str(stmt.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    ))
    plan = "\n".join(
        (await session.execute(text("EXPLAIN " + sql))).scalars().all()
    )
    assert "ix_memories_superseded_by" not in plan, plan
    assert "Seq Scan on memories" in plan, plan
