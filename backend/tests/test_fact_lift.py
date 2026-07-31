"""Fact lifting — the first and only producer the Layer-2 truth core has.

Everything below the fact layer (the ladder, origin counting, the veto, the
withdrawal hook) shipped against hand-seeded rows. These tests are the first
that drive the layer from real Layer-1 input, so they pin the four properties a
producer can get silently wrong:

1. **Idempotence, in rows *and* in events.** A second tick over unchanged
   Layer 1 must leave the same rows with the same ``created_at``s and journal
   nothing. Row equality alone would pass while the drain saw permanent churn.
2. **Every fact traces to its sources.** A fact with no ``fact_sources`` row is
   unfalsifiable, so the invariant is asserted directly over the whole table
   rather than per-case.
3. **Birth status never above ``candidate``.** ``corroborated`` is the ladder's
   to grant and ``confirmed`` is a human's; a producer that promotes its own
   output is this layer's stated failure mode.
4. **``origin_key`` propagation.** Corroboration is
   ``COUNT(DISTINCT origin_key)``; a lift that drops the key makes every fact
   one anonymous origin and no fact ever promotes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.repositories.fact_sources import FactSourceRepository
from app.repositories.graph import PostgresGraphRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.dream_jobs import FACT_LIFT_JOB_KEY, register_dream_jobs
from app.services.fact_lift import (
    DEFAULT_LIFT_BATCH,
    LIFT_CONFIG_SCHEMA,
    fact_sentence,
    run_lift,
)
from app.services.fact_provenance import MEMORY_SOURCE_KIND, memory_source_ref
from app.services.job_registry import JobRegistry
from app.services.triple_key import compute_triple_key
from app.utils.ids import new_id

PROJECT = "t210-fact-lift"
OTHER_PROJECT = "t210-fact-lift-other"
NOW = datetime(2026, 7, 31, 9, 0, tzinfo=timezone.utc)


# ─────────────────────────── Layer-1 bed ───────────────────────────


async def seed_memory(
    session,
    *,
    project: str = PROJECT,
    origin_key: str | None = "session-a",
    content: str = "a captured claim",
    created_at: datetime | None = None,
) -> str:
    memory_id = str(new_id())
    await session.execute(
        text("""
            INSERT INTO memories (id, content, source, project, origin_key, created_at)
            VALUES (
                CAST(:id AS uuid), CAST(:content AS text), 'api',
                CAST(:project AS text), CAST(:origin_key AS text),
                COALESCE(CAST(:created_at AS timestamptz), now())
            )
        """),
        {
            "id": memory_id,
            "content": content,
            "project": project,
            "origin_key": origin_key,
            "created_at": created_at,
        },
    )
    return memory_id


async def assert_relation(
    session,
    *,
    memory_id: str,
    subject: str,
    rel_type: str,
    obj: str,
    subject_type: str = "project",
    object_type: str = "tool",
) -> None:
    """Write one Layer-1 relation the way Phase 5 writes it: lowercase names,
    endpoints resolved through `entities`, the memory appended to `memory_ids`."""
    graph = PostgresGraphRepository(session)
    await graph.create_entity(subject, subject_type, {}, memory_id)
    await graph.create_entity(obj, object_type, {}, memory_id)
    await graph.create_relationship(
        subject, obj, rel_type, {}, 0.5, memory_id,
        source_type=subject_type, target_type=object_type,
    )


# ─────────────────────────── readers ───────────────────────────


async def facts(session, project: str = PROJECT) -> list[dict]:
    result = await session.execute(
        text("""
            SELECT id, triple_key, subject_name, object_name, rel_type, fact,
                   project, verification_status, confidence, valid_at,
                   invalid_at, expired_at, reference_time, subject_id, object_id,
                   review_state, learned_in, created_at
            FROM knowledge_triples
            WHERE project = CAST(:project AS text)
            ORDER BY created_at, id
        """),
        {"project": project},
    )
    return [dict(row) for row in result.mappings().all()]


async def sources(session, fact_id) -> list[dict]:
    result = await session.execute(
        text("""
            SELECT source_kind, source_ref, origin_key, created_at
            FROM fact_sources
            WHERE fact_id = CAST(:id AS uuid)
            ORDER BY source_ref
        """),
        {"id": str(fact_id)},
    )
    return [dict(row) for row in result.mappings().all()]


async def emitted(session, project: str = PROJECT) -> list[dict]:
    result = await session.execute(
        text("""
            SELECT object_id, payload
            FROM events
            WHERE event_type = 'sources_changed'
              AND object_type = 'fact'
              AND project = CAST(:project AS text)
            ORDER BY id
        """),
        {"project": project},
    )
    return [dict(row) for row in result.mappings().all()]


async def event_count(session, event_type: str, project: str = PROJECT) -> int:
    result = await session.execute(
        text("""
            SELECT COUNT(*) FROM events
            WHERE event_type = CAST(:event_type AS text)
              AND project = CAST(:project AS text)
        """),
        {"event_type": event_type, "project": project},
    )
    return int(result.scalar_one())


# ─────────── Done-when 2: every lifted fact traces to its sources ───────────


@pytest.mark.asyncio
async def test_a_lifted_fact_carries_its_relation_and_its_provenance(session):
    memory_id = await seed_memory(session, origin_key="agent-run-1")
    await assert_relation(
        session, memory_id=memory_id, subject="darkmem", rel_type="USES", obj="postgres",
    )

    outcome = await run_lift(session)

    assert outcome.facts_created == 1
    rows = await facts(session)
    assert len(rows) == 1
    fact = rows[0]
    assert fact["triple_key"] == compute_triple_key(PROJECT, "darkmem", "USES", "postgres")
    assert (fact["subject_name"], fact["rel_type"], fact["object_name"]) == (
        "darkmem", "USES", "postgres",
    )
    assert fact["fact"] == "darkmem uses postgres"
    assert fact["subject_id"] is not None and fact["object_id"] is not None

    provenance = await sources(session, fact["id"])
    assert provenance == [
        {
            "source_kind": MEMORY_SOURCE_KIND,
            "source_ref": memory_source_ref(memory_id),
            "origin_key": "agent-run-1",
            "created_at": provenance[0]["created_at"],
        }
    ]


@pytest.mark.asyncio
async def test_no_lifted_fact_is_left_without_a_source_row(session):
    """The invariant directly, over the whole table rather than per case: an
    unfalsifiable fact must be unreachable from this producer."""
    for index, (subject, rel_type, obj) in enumerate(
        [
            ("darkmem", "USES", "postgres"),
            ("darkmem", "DEPENDS_ON", "pgvector"),
            ("api", "DEPLOYED_ON", "homelab"),
        ]
    ):
        memory_id = await seed_memory(session, origin_key=f"session-{index}")
        await assert_relation(
            session, memory_id=memory_id, subject=subject, rel_type=rel_type, obj=obj,
        )

    await run_lift(session)

    rows = await facts(session)
    assert len(rows) == 3, "the check below would pass vacuously with no facts"
    orphans = await session.execute(
        text("""
            SELECT kt.id FROM knowledge_triples kt
            WHERE kt.project = CAST(:project AS text)
              AND NOT EXISTS (
                  SELECT 1 FROM fact_sources fs WHERE fs.fact_id = kt.id
              )
        """),
        {"project": PROJECT},
    )
    assert orphans.scalars().all() == []


# ────────────── Done-when 1 + 4: idempotence, rows and events ──────────────


@pytest.mark.asyncio
async def test_a_second_tick_over_unchanged_layer_one_changes_and_emits_nothing(session):
    memory_id = await seed_memory(session)
    await assert_relation(
        session, memory_id=memory_id, subject="darkmem", rel_type="USES", obj="postgres",
    )

    first = await run_lift(session)
    facts_after_first = await facts(session)
    sources_after_first = await sources(session, facts_after_first[0]["id"])
    events_after_first = await emitted(session)

    second = await run_lift(session)

    assert (second.facts_created, second.sources_added, second.events_emitted) == (0, 0, 0)
    assert second.candidates == 0, (
        "an already-lifted, fully-sourced relation must not even be loaded as "
        "outstanding work"
    )
    assert await facts(session) == facts_after_first
    assert await sources(session, facts_after_first[0]["id"]) == sources_after_first
    assert await emitted(session) == events_after_first
    assert len(events_after_first) == first.events_emitted == 1


@pytest.mark.asyncio
async def test_a_new_asserting_memory_emits_once_and_reuses_the_open_row(session):
    first_memory = await seed_memory(session, origin_key="session-a")
    await assert_relation(
        session, memory_id=first_memory, subject="darkmem", rel_type="USES", obj="postgres",
    )
    await run_lift(session)
    fact_id = (await facts(session))[0]["id"]

    second_memory = await seed_memory(session, origin_key="session-b")
    await assert_relation(
        session, memory_id=second_memory, subject="darkmem", rel_type="USES", obj="postgres",
    )
    outcome = await run_lift(session)

    rows = await facts(session)
    assert len(rows) == 1, "a re-asserted triple reuses its open row, never opens a second"
    assert rows[0]["id"] == fact_id
    assert (outcome.facts_created, outcome.sources_added) == (0, 1)

    refs = {row["source_ref"] for row in await sources(session, fact_id)}
    assert refs == {memory_source_ref(first_memory), memory_source_ref(second_memory)}

    events = await emitted(session)
    assert len(events) == 2, "one event per newly written provenance row, never a re-emit"
    assert events[-1]["payload"] == {
        "fact_id": str(fact_id),
        "memory_id": memory_source_ref(second_memory),
    }
    assert str(events[-1]["object_id"]) == str(fact_id)


# ────────── Done-when 4: origin_key propagation feeds the ladder ──────────


@pytest.mark.asyncio
async def test_distinct_origins_survive_the_lift_and_echoes_do_not(session):
    """Two witnesses count twice; one witness restating itself counts once.

    Asserted through `count_distinct_origins` rather than by reading the column,
    because that arithmetic is what the ladder consumes — a lift that wrote the
    key into the wrong place would still pass a column read.
    """
    for origin in ("session-a", "session-b"):
        memory_id = await seed_memory(session, origin_key=origin)
        await assert_relation(
            session, memory_id=memory_id, subject="darkmem", rel_type="USES", obj="postgres",
        )
    for _ in range(3):
        memory_id = await seed_memory(session, origin_key="chatty-agent")
        await assert_relation(
            session, memory_id=memory_id, subject="api", rel_type="DEPLOYED_ON", obj="homelab",
        )

    await run_lift(session)

    repo = FactSourceRepository(session)
    by_subject = {row["subject_name"]: row["id"] for row in await facts(session)}
    assert await repo.count_distinct_origins(by_subject["darkmem"]) == 2
    assert await repo.count_distinct_origins(by_subject["api"]) == 1
    assert len(await sources(session, by_subject["api"])) == 3, (
        "three memories are three provenance rows even though they are one origin"
    )


# ────────── Done-when 3: no fact is born above `candidate` ──────────


@pytest.mark.asyncio
async def test_a_fact_is_born_candidate_however_well_corroborated(session):
    """Three distinct origins clear the ladder's ungated N, and lifting still
    must not promote: counting and promoting are the recompute's, and a producer
    grading its own output is exactly the silent over-confidence this layer
    exists to avoid."""
    for origin in ("session-a", "session-b", "session-c"):
        memory_id = await seed_memory(session, origin_key=origin)
        await assert_relation(
            session, memory_id=memory_id, subject="darkmem", rel_type="USES", obj="postgres",
        )

    await run_lift(session)

    rows = await facts(session)
    assert [row["verification_status"] for row in rows] == ["candidate"]
    assert rows[0]["confidence"] is None, (
        "confidence is an aggregated estimate the recompute writes; a value here "
        "would be the single-source guess doc 08 §4.1 forbids"
    )
    assert rows[0]["review_state"] is None
    assert await FactSourceRepository(session).count_distinct_origins(rows[0]["id"]) == 3
    assert await event_count(session, "verified") == 0, (
        "lifting must journal no verification transition at all"
    )


@pytest.mark.asyncio
async def test_no_lifted_fact_in_the_table_is_above_candidate(session):
    for index in range(4):
        memory_id = await seed_memory(session, origin_key=f"session-{index}")
        await assert_relation(
            session, memory_id=memory_id, subject=f"svc{index}",
            rel_type="USES", obj="postgres",
        )

    await run_lift(session)

    rows = await facts(session)
    assert len(rows) == 4
    assert {row["verification_status"] for row in rows} == {"candidate"}


@pytest.mark.asyncio
async def test_a_schema_default_above_candidate_aborts_the_lift(session):
    """The birth status comes from the column default, so a schema edit could
    raise the whole layer's floor with nothing in this module changing. The
    check re-reads what actually landed and refuses it — a fact born
    over-confident is silent, and the savepoint rolls it back rather than
    leaving it behind."""
    await session.execute(
        text(
            "ALTER TABLE knowledge_triples "
            "ALTER COLUMN verification_status SET DEFAULT 'corroborated'"
        )
    )
    memory_id = await seed_memory(session)
    await assert_relation(
        session, memory_id=memory_id, subject="darkmem", rel_type="USES", obj="postgres",
    )

    outcome = await run_lift(session)

    assert outcome.facts_created == 0
    assert await facts(session) == []


# ────────────── project scope is part of fact identity ──────────────


@pytest.mark.asyncio
async def test_one_relation_asserted_in_two_projects_lifts_to_two_facts(session):
    """`triple_key` embeds `project`, so merging them would merge two scopes'
    corroboration into one count."""
    here = await seed_memory(session, project=PROJECT, origin_key="session-a")
    there = await seed_memory(session, project=OTHER_PROJECT, origin_key="session-b")
    for memory_id in (here, there):
        await assert_relation(
            session, memory_id=memory_id, subject="darkmem", rel_type="USES", obj="postgres",
        )

    await run_lift(session)

    mine = await facts(session, PROJECT)
    theirs = await facts(session, OTHER_PROJECT)
    assert len(mine) == len(theirs) == 1
    assert mine[0]["triple_key"] != theirs[0]["triple_key"]
    assert [row["source_ref"] for row in await sources(session, mine[0]["id"])] == [
        memory_source_ref(here)
    ]
    assert [row["source_ref"] for row in await sources(session, theirs[0]["id"])] == [
        memory_source_ref(there)
    ]


# ────────────── the temporal passes, and HAPPENED_ON's three senses ──────────────


@pytest.mark.asyncio
async def test_happened_on_never_yields_a_belief_window_whatever_its_object(session):
    """`LEGACY_RELATION_TYPE_MAP` folds `VISITED` and `LIVES_IN` into
    `HAPPENED_ON`, so one stored `rel_type` carries a point occurrence, a span
    day and a *place* with no discriminator. The lift must therefore never read
    a `HAPPENED_ON` object as a date: doing so would invent a validity window
    out of a location, and a window is what closes another fact's window.

    Both rows below stay open-ended and both stay live — the polyvalence cannot
    manufacture a succession, because lifting derives no window at all.
    """
    for obj, object_type in (("paris", "place"), ("tokyo", "place"), ("2024-01-01", "entity")):
        memory_id = await seed_memory(session, origin_key=f"session-{obj}")
        await assert_relation(
            session, memory_id=memory_id, subject="alice", rel_type="HAPPENED_ON",
            obj=obj, subject_type="person", object_type=object_type,
        )

    await run_lift(session)

    rows = await facts(session)
    assert {row["object_name"] for row in rows} == {"paris", "tokyo", "2024-01-01"}
    for row in rows:
        assert row["valid_at"] is None, "an unbounded-past belief, never a derived window"
        assert row["invalid_at"] is None, "nothing closes another sense's window"
        assert row["expired_at"] is None


@pytest.mark.asyncio
async def test_reference_time_anchors_on_the_earliest_asserting_memory(session):
    older = await seed_memory(
        session, origin_key="session-a", created_at=NOW - timedelta(days=10),
    )
    newer = await seed_memory(session, origin_key="session-b", created_at=NOW)
    for memory_id in (older, newer):
        await assert_relation(
            session, memory_id=memory_id, subject="darkmem", rel_type="USES", obj="postgres",
        )

    await run_lift(session)

    rows = await facts(session)
    assert rows[0]["reference_time"] == NOW - timedelta(days=10)


@pytest.mark.asyncio
async def test_an_expired_fact_re_lifts_as_a_new_open_belief(session):
    """Belief withdrawal is a re-save on a retained row, so a re-asserted claim
    cannot un-expire history — it opens a new belief beside it."""
    memory_id = await seed_memory(session)
    await assert_relation(
        session, memory_id=memory_id, subject="darkmem", rel_type="USES", obj="postgres",
    )
    await run_lift(session)
    first_id = (await facts(session))[0]["id"]
    await KnowledgeTripleRepository(session).expire(first_id)

    outcome = await run_lift(session)

    rows = await facts(session)
    assert outcome.facts_created == 1
    assert len(rows) == 2
    retained = next(row for row in rows if row["id"] == first_id)
    reborn = next(row for row in rows if row["id"] != first_id)
    assert retained["expired_at"] is not None
    assert reborn["expired_at"] is None and reborn["invalid_at"] is None
    assert reborn["triple_key"] == retained["triple_key"]
    assert len(await sources(session, reborn["id"])) == 1


# ────────────── the salience bar and the batch bound ──────────────


@pytest.mark.asyncio
async def test_the_salience_bar_holds_a_relation_below_the_minimum(session):
    first = await seed_memory(session, origin_key="session-a")
    await assert_relation(
        session, memory_id=first, subject="darkmem", rel_type="USES", obj="postgres",
    )

    assert (await run_lift(session, min_asserting_memories=2)).facts_created == 0
    assert await facts(session) == []

    second = await seed_memory(session, origin_key="session-b")
    await assert_relation(
        session, memory_id=second, subject="darkmem", rel_type="USES", obj="postgres",
    )
    assert (await run_lift(session, min_asserting_memories=2)).facts_created == 1
    assert len(await sources(session, (await facts(session))[0]["id"])) == 2


@pytest.mark.asyncio
async def test_successive_ticks_drain_the_backlog_rather_than_re_walking_it(session):
    for index in range(3):
        memory_id = await seed_memory(session, origin_key=f"session-{index}")
        await assert_relation(
            session, memory_id=memory_id, subject=f"svc{index}",
            rel_type="USES", obj="postgres",
        )

    seen = 0
    for _ in range(3):
        seen += (await run_lift(session, batch_size=1)).facts_created
    assert seen == 3
    assert len(await facts(session)) == 3
    assert (await run_lift(session, batch_size=1)).candidates == 0


# ────────────── the sentence, and the job wiring ──────────────


def test_the_fact_sentence_reads_as_a_clause():
    """The `fact` text is what the contradiction scan trigram-matches and what a
    Layer-3 article quotes, so it has to be prose rather than a tuple dump."""
    assert fact_sentence("darkmem", "DEPENDS_ON", "pgvector") == "darkmem depends on pgvector"
    assert fact_sentence("alice", "HAPPENED_ON", "paris") == "alice happened on paris"


@pytest.mark.asyncio
async def test_the_job_is_wired_with_a_real_runner_and_its_own_schema():
    engine = create_async_engine(settings.test_database_url)
    registry = JobRegistry(async_sessionmaker(engine, expire_on_commit=False))
    register_dream_jobs(registry)
    try:
        job = registry.get(FACT_LIFT_JOB_KEY)
        assert job.config_schema is LIFT_CONFIG_SCHEMA
        assert {fd.key for fd in job.config_schema} == {
            "batch_size", "min_asserting_memories",
        }
        assert job.default_config["batch_size"] == DEFAULT_LIFT_BATCH
        assert job.default_cron == "*/15 * * * *"
        assert job.min_interval_seconds == 60

        # The runner opens and commits its own session; a run that raised would
        # land as last_status="error" rather than propagating out of trigger().
        cfg = await registry.trigger(FACT_LIFT_JOB_KEY)
        assert cfg.last_status == "ok", cfg.last_error
    finally:
        await registry.stop_all()
        await engine.dispose()
