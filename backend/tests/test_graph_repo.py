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

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository


async def _mk_memory(session, mid):
    """Insert a minimal live memory row so memory_ids referencing it resolve as
    'live' under the orphan checks (the ORM applies the python-side defaults a
    raw INSERT would miss)."""
    session.add(Memory(id=mid, content="x", source="test"))
    await session.flush()


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
    # Both are real memories: the orphan checks keep a row only while a LIVE
    # memory still asserts it, so the relation must be backed by a live m2.
    await _mk_memory(session, m1)
    await _mk_memory(session, m2)

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


async def _entity_names(session) -> set[str]:
    rows = (await session.execute(text("SELECT name FROM entities"))).scalars().all()
    return set(rows)


async def test_delete_by_memory_id_self_heals_dangling_memory_ids(session):
    """An entity kept alive only by a dangling memory_id (an id whose memory was
    deleted without graph cleanup) must be removed when delete_by_memory_id next
    touches it — otherwise it lingers as a ghost the dedup collapses onto."""
    repo = PostgresGraphRepository(session)
    live, dangling = uuid4(), uuid4()  # only `live` is a real memory
    await _mk_memory(session, live)

    await repo.create_entity(name="ghost-x", entity_type="concept", properties={}, memory_id=live)
    # Simulate prior accumulation: a dangling id (its memory already deleted)
    # got appended to this entity, so the old emptiness check never fired.
    await session.execute(
        text("UPDATE entities SET memory_ids = array_append(memory_ids, :d) WHERE name = 'ghost-x'"),
        {"d": dangling},
    )

    await repo.delete_by_memory_id(live)

    # After stripping `live`, only the dangling id remains -> no live memory ->
    # ghost removed (self-heal).
    assert "ghost-x" not in await _entity_names(session)


async def test_prune_orphan_entities_removes_ghosts_keeps_live(session):
    repo = PostgresGraphRepository(session)
    live, dead = uuid4(), uuid4()  # `dead` is never inserted as a memory
    await _mk_memory(session, live)

    await repo.create_entity(name="keep-me", entity_type="tool", properties={}, memory_id=live)
    await repo.create_entity(name="ghost-a", entity_type="tool", properties={}, memory_id=dead)
    await repo.create_entity(name="ghost-b", entity_type="tool", properties={}, memory_id=dead)
    await repo.create_relationship(
        source_name="ghost-a", target_name="ghost-b", rel_type="RELATED_TO",
        properties={}, weight=0.5, memory_id=dead,
        source_type="tool", target_type="tool",
    )

    stats = await repo.prune_orphan_entities()

    names = await _entity_names(session)
    assert "keep-me" in names
    assert "ghost-a" not in names and "ghost-b" not in names
    assert stats["entities_pruned"] == 2
    assert stats["relations_pruned"] == 1
    # The dangling relation is gone too.
    rel_count = (await session.execute(text("SELECT count(*) FROM entity_relations"))).scalar_one()
    assert rel_count == 0


async def test_prune_orphan_entities_keeps_entity_with_surviving_relation(session):
    """A relation backed by a live memory protects an otherwise-orphaned
    endpoint entity from deletion (FK is ON DELETE CASCADE)."""
    repo = PostgresGraphRepository(session)
    live = uuid4()
    await _mk_memory(session, live)

    # Endpoint `p` has no live memory_id of its own, but the live relation p->q
    # asserts it, so prune must keep p (and the relation).
    await repo.create_entity(name="p", entity_type="concept", properties={}, memory_id=uuid4())
    await repo.create_entity(name="q", entity_type="concept", properties={}, memory_id=live)
    await repo.create_relationship(
        source_name="p", target_name="q", rel_type="RELATED_TO",
        properties={}, weight=0.5, memory_id=live,
        source_type="concept", target_type="concept",
    )

    stats = await repo.prune_orphan_entities()

    names = await _entity_names(session)
    assert {"p", "q"} <= names
    assert stats["relations_pruned"] == 0
