"""Integration tests for the Phase 6 / 6.5 backfill scripts.

These use the shared `session` fixture so they inherit the clean-slate savepoint
behaviour from `conftest.setup_database` and roll back on teardown.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.services.confidence import CONFIDENCE_LOW, estimate_confidence


@pytest.mark.asyncio
async def test_backfill_technologies_denormalises_entity_names(session):
    mem_a = Memory(
        id=uuid.uuid4(),
        content="pgvector powers retrieval",
        source="test",
        importance=0.5,
        metadata_={},
    )
    mem_b = Memory(
        id=uuid.uuid4(),
        content="redis cache is hot",
        source="test",
        importance=0.5,
        metadata_={},
    )
    session.add_all([mem_a, mem_b])
    await session.flush()

    await session.execute(
        text(
            """
            INSERT INTO entities (id, name, entity_type, memory_ids)
            VALUES
              (gen_random_uuid(), 'pgvector', 'tool', ARRAY[:a]::uuid[]),
              (gen_random_uuid(), 'postgres', 'database', ARRAY[:a, :b]::uuid[]),
              (gen_random_uuid(), 'Paper 2024',  'concept', ARRAY[:a]::uuid[])
            """
        ),
        {"a": mem_a.id, "b": mem_b.id},
    )

    await session.execute(
        text(
            """
            WITH exploded AS (
                SELECT e.name AS name, unnest(e.memory_ids) AS memory_id
                FROM entities e
                WHERE e.entity_type = ANY(ARRAY['tool','service','database','language','protocol'])
            ),
            tech AS (
                SELECT memory_id, array_agg(DISTINCT name ORDER BY name) AS tech_names
                FROM exploded
                GROUP BY memory_id
            )
            UPDATE memories m
            SET technologies = t.tech_names
            FROM tech t
            WHERE m.id = t.memory_id
              AND (m.technologies IS NULL OR m.technologies = '{}'::text[])
            """
        )
    )

    await session.refresh(mem_a)
    await session.refresh(mem_b)
    assert list(mem_a.technologies) == ["pgvector", "postgres"]
    assert list(mem_b.technologies) == ["postgres"]


@pytest.mark.asyncio
async def test_backfill_confidence_uses_estimator(session):
    mem = Memory(
        id=uuid.uuid4(),
        content="we might switch to valkey",
        source="test",
        memory_type="preference",
        importance=0.5,
        metadata_={},
    )
    session.add(mem)
    await session.flush()

    # Mirror the script's per-row update.
    new_conf = estimate_confidence(mem.content, mem.memory_type)
    assert new_conf == CONFIDENCE_LOW
    await session.execute(
        text("UPDATE memories SET confidence = :c WHERE id = :id"),
        {"c": new_conf, "id": mem.id},
    )

    await session.refresh(mem)
    assert mem.confidence == pytest.approx(CONFIDENCE_LOW)


@pytest.mark.asyncio
async def test_backfill_relations_remap_and_delete(session):
    # Two entities and two relations: one collapses to USES, one to None (drop).
    a = uuid.uuid4()
    b = uuid.uuid4()
    await session.execute(
        text(
            """
            INSERT INTO entities (id, name, entity_type)
            VALUES (:a, 'pgvector', 'tool'),
                   (:b, 'postgres', 'database')
            """
        ),
        {"a": a, "b": b},
    )
    await session.execute(
        text(
            """
            INSERT INTO entity_relations (id, source_entity_id, target_entity_id, rel_type)
            VALUES (gen_random_uuid(), :a, :b, 'DEPENDS_ON'),
                   (gen_random_uuid(), :a, :b, 'RELATED_TO')
            """
        ),
        {"a": a, "b": b},
    )

    from app.services.relations import REL_MAP_5

    # Remap the survivors; drop the None-mapped label.
    for old, new in REL_MAP_5.items():
        if new is None:
            await session.execute(
                text("DELETE FROM entity_relations WHERE rel_type = :old"),
                {"old": old},
            )
        elif old != new:
            # Simple UPDATE without the merge CTE is fine here: no collision set up.
            await session.execute(
                text("UPDATE entity_relations SET rel_type = :new WHERE rel_type = :old"),
                {"old": old, "new": new},
            )

    remaining = (
        await session.execute(
            text("SELECT rel_type FROM entity_relations ORDER BY rel_type")
        )
    ).scalars().all()
    assert remaining == ["USES"]
