"""Doc 06 §6 — strip-before-rewrite, and what the strip is allowed to delete.

T1.21 fixed *where* the strip runs (inside savepoint B, so strip-and-write is one
atomic replace and a failed strip fails savepoint B). This module covers *what*
it deletes:

* a relation goes only when no LIVE memory still asserts it — which is what
  self-heals ``memory_ids`` left pointing at deleted memories;
* an entity goes only when no live memory asserts it AND no surviving relation
  references it. ``entity_relations``' FK is ON DELETE CASCADE, so deleting a
  referenced entity silently destroys an edge another memory still asserts —
  the failure mode is a second memory quietly losing a relationship, with no
  error anywhere;
* the strip is self-sufficient: it never leaves behind an entity that its own
  relation deletions orphaned. ``graph_orphan_cleanup`` is a backstop for
  ghosts arriving by other routes, not the mechanism this depends on.

The idempotency assertions compare full graph *contents* — names, types,
``memory_ids`` membership, ``display_name``, relation endpoints and rel_type —
because a row-count comparison passes over a graph with the right cardinality
and the wrong contents.
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from tests.test_pipeline_savepoints import savepoint_bed

NAMES = ("store-1", "store-2", "store-3")

FIRST_PASS = {
    "entities": [
        {"name": "Store-1", "type": "tool"},
        {"name": "store-2", "type": "tool"},
    ],
    "relationships": [
        {"source": "store-1", "target": "store-2",
         "type": "RELATED_TO", "weight": 0.6},
    ],
    "memory_type": "fact",
}


async def _mk_memory(session, mid: UUID) -> None:
    session.add(Memory(id=mid, content="x", source="test"))
    await session.flush()


def _entity_key(row) -> tuple:
    props = dict(row["properties"] or {})
    return (
        row["name"],
        row["entity_type"],
        props.get("display_name"),
        tuple(sorted(str(m) for m in (row["memory_ids"] or []))),
    )


def _relation_key(row) -> tuple:
    return (
        row["source"], row["source_type"],
        row["target"], row["target_type"],
        row["rel_type"],
        tuple(sorted(str(m) for m in (row["memory_ids"] or []))),
    )


async def _graph_snapshot(factory, names: tuple[str, ...] = NAMES) -> dict:
    """Full contents of the graph reachable from ``names``, order-normalised.

    ``memory_ids`` is compared as a set: the strip's ``array_remove`` followed by
    ``create_entity``'s ``array_append`` rotates a shared entity's array without
    changing who asserts it, and array order carries no meaning.
    """
    async with factory() as s:
        entity_rows = (await s.execute(
            text("SELECT name, entity_type, properties, memory_ids FROM entities "
                 "WHERE name = ANY(CAST(:names AS text[]))"),
            {"names": list(names)},
        )).mappings().all()
        relation_rows = (await s.execute(
            text("SELECT src.name AS source, src.entity_type AS source_type, "
                 "       tgt.name AS target, tgt.entity_type AS target_type, "
                 "       r.rel_type, r.memory_ids "
                 "FROM entity_relations r "
                 "JOIN entities src ON src.id = r.source_entity_id "
                 "JOIN entities tgt ON tgt.id = r.target_entity_id "
                 "WHERE src.name = ANY(CAST(:names AS text[])) "
                 "   OR tgt.name = ANY(CAST(:names AS text[]))"),
            {"names": list(names)},
        )).mappings().all()
    return {
        "entities": sorted(_entity_key(r) for r in entity_rows),
        "relations": sorted(_relation_key(r) for r in relation_rows),
    }


async def _entity_names(session) -> set[str]:
    return set((await session.execute(text("SELECT name FROM entities"))).scalars().all())


@pytest.mark.asyncio
async def test_reextracting_the_same_memory_yields_an_identical_graph(setup_database):
    """The whole point of the strip, asserted on contents rather than counts.

    Without it the second pass re-asserts every entity on top of the first pass's
    rows: the cardinality stays right (the ON CONFLICT clauses merge), so only a
    contents comparison notices the drift.
    """
    async with savepoint_bed(["store-1 relates to store-2"], "reextract-same|4", NAMES,
                             extraction=FIRST_PASS) as bed:
        first = (await bed.pipe.process_batch([bed.entry()]))[0]
        assert first["graph"] == "ok"
        before = await _graph_snapshot(bed.factory)

        second = (await bed.pipe.process_batch([bed.entry()]))[0]
        assert second["graph"] == "ok"
        after = await _graph_snapshot(bed.factory)

        assert before == after
        assert before["entities"] == [
            ("store-1", "tool", "Store-1", (str(bed.memory_id),)),
            ("store-2", "tool", None, (str(bed.memory_id),)),
        ]
        assert before["relations"] == [
            ("store-1", "tool", "store-2", "tool", "RELATED_TO",
             (str(bed.memory_id),)),
        ]


@pytest.mark.asyncio
async def test_reextraction_replaces_rather_than_accumulates(setup_database):
    """A changed extraction leaves exactly the new graph, not the union."""
    async with savepoint_bed(["store-1 relates to store-2"], "reextract-replace|4", NAMES,
                             extraction=FIRST_PASS) as bed:
        assert (await bed.pipe.process_batch([bed.entry()]))[0]["graph"] == "ok"

        bed.extraction = {
            "entities": [{"name": "store-3", "type": "tool"}],
            "relationships": [],
            "memory_type": "fact",
        }
        assert (await bed.pipe.process_batch([bed.entry()]))[0]["graph"] == "ok"

        assert await _graph_snapshot(bed.factory) == {
            "entities": [("store-3", "tool", None, (str(bed.memory_id),))],
            "relations": [],
        }


@pytest.mark.asyncio
async def test_entities_shared_with_other_live_memories_survive_the_strip(setup_database):
    """Stripping one memory must not disturb a co-asserted entity's other owner.

    The second memory keeps asserting ``store-1``, so the strip may only
    remove the first memory's id from the array — never the row.
    """
    async with savepoint_bed(
        ["first asserts 1 and 2", "second asserts 1 and 3"],
        "reextract-shared|4", NAMES, extraction=FIRST_PASS,
    ) as bed:
        assert (await bed.pipe.process_batch([bed.entry(0)]))[0]["graph"] == "ok"

        bed.extraction = {
            "entities": [
                {"name": "Store-1", "type": "tool"},
                {"name": "store-3", "type": "tool"},
            ],
            "relationships": [
                {"source": "store-1", "target": "store-3",
                 "type": "RELATED_TO", "weight": 0.6},
            ],
            "memory_type": "fact",
        }
        assert (await bed.pipe.process_batch([bed.entry(1)]))[0]["graph"] == "ok"

        # Re-extract the FIRST memory into something that drops store-1.
        bed.extraction = {
            "entities": [{"name": "store-2", "type": "tool"}],
            "relationships": [],
            "memory_type": "fact",
        }
        assert (await bed.pipe.process_batch([bed.entry(0)]))[0]["graph"] == "ok"

        m0, m1 = str(bed.memory_ids[0]), str(bed.memory_ids[1])
        assert await _graph_snapshot(bed.factory) == {
            "entities": [
                ("store-1", "tool", "Store-1", (m1,)),
                ("store-2", "tool", None, (m0,)),
                ("store-3", "tool", None, (m1,)),
            ],
            "relations": [
                ("store-1", "tool", "store-3", "tool", "RELATED_TO", (m1,)),
            ],
        }


@pytest.mark.asyncio
async def test_a_co_asserted_entity_with_no_relation_survives_the_strip(session):
    """Isolates the 'no live memory asserts it' guard from the relation guard.

    In the end-to-end shape above the shared entity also sits on a surviving
    relation, so the relation guard alone keeps it and the live-memory guard
    could be removed unnoticed. Here nothing references ``co-owned``, so that
    guard is the only thing between it and deletion.
    """
    repo = PostgresGraphRepository(session)
    m1, m2 = uuid4(), uuid4()
    await _mk_memory(session, m1)
    await _mk_memory(session, m2)

    await repo.create_entity(name="co-owned", entity_type="tool", properties={}, memory_id=m1)
    await repo.create_entity(name="co-owned", entity_type="tool", properties={}, memory_id=m2)

    await repo.delete_by_memory_id(m1)

    remaining = (await session.execute(
        text("SELECT memory_ids FROM entities WHERE name = 'co-owned'")
    )).scalar_one()
    assert [str(x) for x in remaining] == [str(m2)]


@pytest.mark.asyncio
async def test_an_entity_a_surviving_relation_references_is_never_deleted(session):
    """The dangerous rule: the FK cascades, so this delete would destroy an edge.

    ``shared-a`` loses its last live asserter when m1 is stripped, but the
    relation ``shared-a -> shared-b`` is still asserted by the live m2. Deleting
    the entity would cascade that relation away and m2 would silently lose a
    relationship it still asserts — no error, no failed step, nothing on the
    wire.
    """
    repo = PostgresGraphRepository(session)
    m1, m2 = uuid4(), uuid4()
    await _mk_memory(session, m1)
    await _mk_memory(session, m2)

    await repo.create_entity(name="shared-a", entity_type="tool", properties={}, memory_id=m1)
    await repo.create_entity(name="shared-b", entity_type="tool", properties={}, memory_id=m2)
    await repo.create_relationship(
        source_name="shared-a", target_name="shared-b", rel_type="RELATED_TO",
        properties={}, weight=0.5, memory_id=m2,
        source_type="tool", target_type="tool",
    )

    await repo.delete_by_memory_id(m1)

    assert {"shared-a", "shared-b"} <= await _entity_names(session)
    surviving = (await session.execute(
        text("SELECT memory_ids FROM entity_relations")
    )).scalars().all()
    assert [[str(x) for x in row] for row in surviving] == [[str(m2)]]


@pytest.mark.asyncio
async def test_dangling_memory_ids_on_a_relation_self_heal(session):
    """A relation whose remaining asserters are all dead memories is not alive.

    Testing the array for emptiness instead of for a live memory leaves the
    relation and both endpoints standing forever, and Phase-4 dedup then
    collapses fresh entities onto those ghosts.
    """
    repo = PostgresGraphRepository(session)
    live, dead = uuid4(), uuid4()
    await _mk_memory(session, live)

    await repo.create_entity(name="heal-x", entity_type="tool", properties={}, memory_id=live)
    await repo.create_entity(name="heal-y", entity_type="tool", properties={}, memory_id=live)
    await repo.create_relationship(
        source_name="heal-x", target_name="heal-y", rel_type="RELATED_TO",
        properties={}, weight=0.5, memory_id=live,
        source_type="tool", target_type="tool",
    )
    await session.execute(
        text("UPDATE entity_relations SET memory_ids = array_append(memory_ids, :d)"),
        {"d": dead},
    )

    await repo.delete_by_memory_id(live)

    assert not {"heal-x", "heal-y"} & await _entity_names(session)
    assert (await session.execute(
        text("SELECT count(*) FROM entity_relations")
    )).scalar_one() == 0


@pytest.mark.asyncio
async def test_the_strip_leaves_behind_no_entity_it_orphaned_itself(session):
    """An endpoint kept alive only by the relation the strip just deleted.

    ``ghost-endpoint`` is asserted by no live memory; the sole thing protecting
    it from the entity guard is the relation this memory asserts. Deleting that
    relation is what orphans it, so the same strip has to reconsider it — a
    candidate set scoped to the entities this memory asserted skips it entirely
    and leaves a ghost for the ANN dedup to snap onto.
    """
    repo = PostgresGraphRepository(session)
    live, dead = uuid4(), uuid4()
    await _mk_memory(session, live)

    await repo.create_entity(name="own-a", entity_type="tool", properties={}, memory_id=live)
    await repo.create_entity(name="ghost-endpoint", entity_type="tool", properties={}, memory_id=dead)
    await repo.create_relationship(
        source_name="own-a", target_name="ghost-endpoint", rel_type="RELATED_TO",
        properties={}, weight=0.5, memory_id=live,
        source_type="tool", target_type="tool",
    )

    await repo.delete_by_memory_id(live)

    assert not {"own-a", "ghost-endpoint"} & await _entity_names(session)


@pytest.mark.asyncio
async def test_an_orphaned_endpoint_is_kept_while_a_live_memory_asserts_it(session):
    """The widened candidate set must not overreach past the two guards."""
    repo = PostgresGraphRepository(session)
    live, other = uuid4(), uuid4()
    await _mk_memory(session, live)
    await _mk_memory(session, other)

    await repo.create_entity(name="own-b", entity_type="tool", properties={}, memory_id=live)
    await repo.create_entity(name="kept-endpoint", entity_type="tool", properties={}, memory_id=other)
    await repo.create_relationship(
        source_name="own-b", target_name="kept-endpoint", rel_type="RELATED_TO",
        properties={}, weight=0.5, memory_id=live,
        source_type="tool", target_type="tool",
    )

    await repo.delete_by_memory_id(live)

    names = await _entity_names(session)
    assert "kept-endpoint" in names
    assert "own-b" not in names
