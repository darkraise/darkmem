"""Doc 06 §6, §9 (inv. 6) — the ``memories.technologies`` denorm.

The column is a projection of the entity graph onto the memory row, and all
three of its properties are load-bearing for a *different* reason:

* **lowercase** — ``detect_supersessions`` lowercases its REPLACES targets to
  match this column. One upper-case entry and the overlap test misses, so the
  supersession simply never fires: no error, no log line, the old memory stays
  ``active`` forever. ``test_a_denorm_that_kept_original_casing_stops_supersession``
  is that failure mode written down.
* **denormalised** — the detector and the retrieval filter both read the column
  instead of joining ``entities``.
* **GIN-indexed** — the detector's ``&&`` overlap guard is the index's only
  reason to exist, so this module EXPLAINs the *executed* statement rather than
  asserting the index merely exists. A purpose-built index that appears in no
  plan is a cost with no benefit.

The recompute is a whole-column replace inside savepoint B, taken from the graph
as it stands after that savepoint's strip and write. An append-only
implementation passes every "a technology was added" test and fails only on
removal, so removal is tested in both of its shapes: one of two technologies
dropped, and every technology dropped.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from app.models.memory import Memory
from app.repositories.graph import PostgresGraphRepository
from app.services.extraction_clean import clean_extraction
from app.services.relations import TECH_TYPES
from app.services.supersession import candidate_stmt, detect_supersessions
from tests.test_pipeline_savepoints import VECTOR, savepoint_bed

TWO_TECHNOLOGIES = {
    "entities": [
        {"name": "Pgvector", "type": "tool"},
        {"name": "FAISS", "type": "tool"},
    ],
    "relationships": [],
    "memory_type": "fact",
}

ONE_TECHNOLOGY = {
    "entities": [{"name": "Pgvector", "type": "tool"}],
    "relationships": [],
    "memory_type": "fact",
}

NO_TECHNOLOGIES = {
    "entities": [{"name": "latency budget", "type": "concept"}],
    "relationships": [],
    "memory_type": "fact",
}

ALL_TECH_TYPED = {
    "entities": [
        {"name": "ripgrep", "type": "tool"},
        {"name": "Grafana", "type": "service"},
        {"name": "Postgres", "type": "database"},
        {"name": "Python", "type": "language"},
        {"name": "HTTP", "type": "protocol"},
        {"name": "Alice", "type": "person"},
        {"name": "latency budget", "type": "concept"},
    ],
    "relationships": [],
    "memory_type": "fact",
}

CLEANUP_NAMES = (
    "pgvector", "faiss", "latency budget", "ripgrep", "grafana",
    "postgres", "python", "http", "alice", "shoutcase",
)


async def _write(bed, extraction: dict) -> None:
    bed.extraction = dict(extraction)
    status = await bed.pipe._write_memory(
        bed.entry(), VECTOR, bed.fingerprint, bed.fingerprint,
        dict(extraction), None, {}, {},
    )
    assert status["graph"] == "ok", status


@pytest.mark.asyncio
async def test_a_removed_technology_is_cleared_from_the_column(setup_database):
    """The direction an append-only recompute gets wrong.

    Re-extraction that no longer mentions FAISS must leave a column that no
    longer mentions FAISS. A union-with-previous implementation passes every
    "technology added" assertion and fails only here.
    """
    async with savepoint_bed(
        ["pgvector and faiss"], "tech-remove|4", entity_names=CLEANUP_NAMES,
    ) as bed:
        await _write(bed, TWO_TECHNOLOGIES)
        assert await bed.technologies() == ["faiss", "pgvector"]

        await _write(bed, ONE_TECHNOLOGY)
        assert await bed.technologies() == ["pgvector"]


@pytest.mark.asyncio
async def test_losing_every_technology_empties_the_column(setup_database):
    async with savepoint_bed(
        ["pgvector and faiss"], "tech-empty|4", entity_names=CLEANUP_NAMES,
    ) as bed:
        await _write(bed, TWO_TECHNOLOGIES)
        assert await bed.technologies() == ["faiss", "pgvector"]

        await _write(bed, NO_TECHNOLOGIES)
        assert await bed.technologies() == []


@pytest.mark.asyncio
async def test_re_extracting_the_same_content_leaves_the_column_unchanged(
    setup_database,
):
    async with savepoint_bed(
        ["pgvector and faiss"], "tech-idem|4", entity_names=CLEANUP_NAMES,
    ) as bed:
        await _write(bed, TWO_TECHNOLOGIES)
        first = await bed.technologies()
        await _write(bed, TWO_TECHNOLOGIES)
        assert await bed.technologies() == first == ["faiss", "pgvector"]


@pytest.mark.asyncio
async def test_the_column_is_lowercase_however_the_extractor_cased_it(
    setup_database,
):
    async with savepoint_bed(
        ["pgvector and faiss"], "tech-case|4", entity_names=CLEANUP_NAMES,
    ) as bed:
        await _write(bed, TWO_TECHNOLOGIES)
        assert await bed.technologies() == ["faiss", "pgvector"]


@pytest.mark.asyncio
async def test_only_tech_typed_entities_reach_the_column(setup_database):
    async with savepoint_bed(
        ["one of everything"], "tech-types|4", entity_names=CLEANUP_NAMES,
    ) as bed:
        await _write(bed, ALL_TECH_TYPED)
        assert await bed.technologies() == [
            "grafana", "http", "postgres", "python", "ripgrep",
        ]


@pytest.mark.asyncio
async def test_type_overrides_not_the_prompt_route_a_name_into_the_column(
    setup_database,
):
    """Doc 06 §4: the curated map, not the prompt, is what fixes typing.

    The model is free to call pgvector a ``concept`` — a type outside
    ``TECH_TYPES``, which would keep it out of the denorm and out of every
    supersession that names it. ``_TYPE_OVERRIDES`` snaps it back to ``tool``
    deterministically, so this drives the real post-processor rather than
    hand-writing the type the pipeline is supposed to derive.
    """
    raw = {
        "entities": [{"name": "pgvector", "type": "concept"}],
        "relationships": [],
        "memory_type": "fact",
    }
    content = "we index embeddings with pgvector"
    cleaned = clean_extraction(raw, content, relation_rescue=False)
    assert [(e["name"], e["type"]) for e in cleaned["entities"]] == [
        ("pgvector", "tool"),
    ]
    assert cleaned["entities"][0]["type"] in TECH_TYPES

    async with savepoint_bed(
        [content], "tech-override|4", entity_names=CLEANUP_NAMES,
    ) as bed:
        await _write(bed, cleaned)
        assert await bed.technologies() == ["pgvector"]


@pytest.mark.asyncio
async def test_the_denorm_lowercases_a_graph_row_that_is_not(session):
    """The lowercase guard lives at the denorm, not only at the write path.

    Entity names are lowercase on disk (inv. 7), so this row is drift the write
    path cannot produce today — which is the point: the column that supersession
    matches against must be lowercase whatever reached ``entities``, because a
    mismatch here is silent.
    """
    memory_id = uuid.uuid4()
    session.add(Memory(id=memory_id, content="drifted", source="test"))
    await session.flush()
    await session.execute(
        text("""
            INSERT INTO entities (id, name, entity_type, properties, memory_ids)
            VALUES (gen_random_uuid(), 'PgVector', 'tool', '{}'::jsonb,
                    ARRAY[CAST(:mid AS uuid)])
        """),
        {"mid": str(memory_id)},
    )

    repo = PostgresGraphRepository(session)
    assert await repo.technologies_for_memory(memory_id) == ["pgvector"]


@pytest.mark.asyncio
async def test_the_gin_index_is_used_by_the_supersession_query_plan(session):
    """Present is not the same as used (T1.29b found an index in no plan at all).

    EXPLAINs the statement ``detect_supersessions`` actually executes, against a
    table large enough and analysed, with no planner hints — a plan reached by
    disabling seqscan would prove only that the index is *reachable*.
    """
    indexdef = (await session.execute(
        text("SELECT indexdef FROM pg_indexes "
             "WHERE tablename = 'memories' AND indexname = :n"),
        {"n": "ix_memories_technologies"},
    )).scalar_one()
    assert "USING gin" in indexdef
    assert "technologies" in indexdef

    await session.execute(text("""
        INSERT INTO memories (id, content, source, project, status, technologies)
        SELECT gen_random_uuid(), 'seed ' || g, 'test', 'default', 'active',
               ARRAY['tech-' || (g % 500)]::text[]
        FROM generate_series(1, 5000) g
    """))
    await session.execute(text("ANALYZE memories"))

    now = datetime.now(timezone.utc)
    stmt = candidate_stmt(
        new_memory_id=uuid.uuid4(),
        new_memory_created_at=now,
        project="default",
        replaces_targets=["tech-7"],
        cutoff=now - timedelta(days=90),
    )
    sql = str(stmt.compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    ))
    plan = "\n".join(
        (await session.execute(text("EXPLAIN " + sql))).scalars().all()
    )
    assert "ix_memories_technologies" in plan, plan
    assert "Seq Scan on memories" not in plan, plan


async def _candidate(session, technologies: list[str]) -> uuid.UUID:
    old_id = uuid.uuid4()
    session.add(Memory(
        id=old_id, content="we use faiss for vector search", source="test",
        project="default", technologies=technologies,
        created_at=datetime.now(timezone.utc) - timedelta(days=1),
    ))
    await session.flush()
    return old_id


@pytest.mark.asyncio
async def test_supersession_fires_when_the_replaces_target_is_shouted(session):
    old_id = await _candidate(session, ["faiss"])
    new_id = uuid.uuid4()
    session.add(Memory(id=new_id, content="we moved from FAISS to pgvector",
                       source="test", project="default"))
    await session.flush()

    flipped = await detect_supersessions(
        session,
        new_memory_id=new_id,
        new_memory_text="we moved from FAISS to pgvector",
        new_memory_created_at=datetime.now(timezone.utc),
        project="default",
        new_relations=[
            {"source": "pgvector", "target": "FAISS", "type": "REPLACES"},
        ],
    )
    assert flipped == [old_id]


@pytest.mark.asyncio
async def test_a_denorm_that_kept_original_casing_stops_supersession(session):
    """The cost of dropping the lowercase property, stated as a test.

    Identical to the test above except the candidate's denorm kept the
    extractor's casing. Nothing raises and nothing is logged — the memory just
    never gets superseded.
    """
    await _candidate(session, ["FAISS"])
    new_id = uuid.uuid4()
    session.add(Memory(id=new_id, content="we moved from FAISS to pgvector",
                       source="test", project="default"))
    await session.flush()

    flipped = await detect_supersessions(
        session,
        new_memory_id=new_id,
        new_memory_text="we moved from FAISS to pgvector",
        new_memory_created_at=datetime.now(timezone.utc),
        project="default",
        new_relations=[
            {"source": "pgvector", "target": "FAISS", "type": "REPLACES"},
        ],
    )
    assert flipped == []
