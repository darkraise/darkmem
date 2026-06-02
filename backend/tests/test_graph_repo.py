"""PostgresGraphRepository: shared-entity property merge and idempotent delete.

Two invariants the entity graph relies on (CLAUDE.md):
* Re-asserting a shared entity from another memory must not erase the
  properties (e.g. ``display_name``) a prior memory set.
* ``delete_by_memory_id`` removes only the contributions of one memory;
  entities AND relations that other memories still assert must survive.
"""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import text

from app.repositories.graph import PostgresGraphRepository


async def test_create_entity_merges_properties_across_memories(session):
    repo = PostgresGraphRepository(session)
    m1, m2 = uuid4(), uuid4()

    await repo.create_entity(
        name="darkmem", entity_type="project",
        properties={"display_name": "Darkmem", "a": 1}, memory_id=m1,
    )
    # A second memory re-asserts the same (name, type) with different props and
    # no display_name. It must NOT wipe the display_name memory 1 set.
    merged = await repo.create_entity(
        name="darkmem", entity_type="project",
        properties={"b": 2}, memory_id=m2,
    )

    assert merged["properties"].get("display_name") == "Darkmem"
    assert merged["properties"].get("b") == 2
    assert merged["properties"].get("a") == 1
    assert set(merged["memory_ids"]) == {str(m1), str(m2)}


async def test_delete_by_memory_id_preserves_relations_other_memories_assert(session):
    repo = PostgresGraphRepository(session)
    m1, m2 = uuid4(), uuid4()

    # Entity e is asserted only by m1; entity f and the relation e->f are
    # asserted by both. (create_relationship appends to the relation's
    # memory_ids without touching the endpoint entities, so this state is
    # reachable in the real pipeline via the rescue layer.)
    await repo.create_entity(name="e", entity_type="concept", properties={}, memory_id=m1)
    await repo.create_entity(name="f", entity_type="concept", properties={}, memory_id=m1)
    await repo.create_relationship(
        source_name="e", target_name="f", rel_type="RELATED_TO",
        properties={}, weight=0.5, memory_id=m1,
        source_type="concept", target_type="concept",
    )
    await repo.create_entity(name="f", entity_type="concept", properties={}, memory_id=m2)
    await repo.create_relationship(
        source_name="e", target_name="f", rel_type="RELATED_TO",
        properties={}, weight=0.5, memory_id=m2,
        source_type="concept", target_type="concept",
    )

    await repo.delete_by_memory_id(m1)

    # The relation e->f is still asserted by m2 and must survive, which in turn
    # requires entity e (now orphaned) to be kept so the FK does not cascade.
    rels = await repo.get_relations_between(["e", "f"])
    assert len(rels) == 1
    surviving = (
        await session.execute(
            text("SELECT memory_ids FROM entity_relations LIMIT 1")
        )
    ).scalar_one()
    assert [str(x) for x in surviving] == [str(m2)]
