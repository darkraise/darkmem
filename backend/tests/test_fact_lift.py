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

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

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
    _lift_one,
    _pending_candidates,
    fact_sentence,
    run_lift,
)
from app.services.fact_provenance import (
    MEMORY_SOURCE_KIND,
    memory_source_ref,
    reconcile_memory_sources,
)
from app.services.job_registry import JobRegistry
from app.services.triple_key import compute_triple_key
from app.utils.ids import new_id

PROJECT = "t210-fact-lift"
OTHER_PROJECT = "t210-fact-lift-other"
NOW = datetime(2026, 7, 31, 9, 0, tzinfo=timezone.utc)

# Separators `str.isspace()` accepts -- so `compute_triple_key` folds them --
# while this database's `\s` does not. Spelled as escapes, never as literals:
# the whole point is that they are indistinguishable from a space on screen.
NBSP = "\u00a0"
NARROW_NBSP = "\u202f"


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


# ────── the snapshot is not evidence: re-read assertion at write time ──────


@pytest.mark.asyncio
async def test_a_memory_stripped_between_scan_and_write_is_not_re_added(session):
    """Phantom corroboration, which is the failure this layer exists to prevent.

    `_pending_candidates` snapshots a whole batch; the writes follow one
    candidate at a time. If Phase 5 strips a memory's relations and the
    withdrawal sweep reconciles its provenance away in that gap, writing from
    the snapshot puts the row back on a **live** fact — and nothing withdraws it
    a second time, so a memory asserting nothing counts as a distinct origin
    forever. That is over-serving, not under-serving.
    """
    keeper = await seed_memory(session, origin_key="session-a")
    doomed = await seed_memory(session, origin_key="session-b")
    for memory_id in (keeper, doomed):
        await assert_relation(
            session, memory_id=memory_id, subject="darkmem", rel_type="USES", obj="postgres",
        )
    await run_lift(session)
    fact_id = (await facts(session))[0]["id"]
    assert len(await sources(session, fact_id)) == 2

    # A third memory makes the group outstanding again, so the scan snapshots
    # it — carrying all three, `doomed` included — exactly as it would when a
    # batch is scanned and then written one candidate at a time.
    newcomer = await seed_memory(session, origin_key="session-c")
    await assert_relation(
        session, memory_id=newcomer, subject="darkmem", rel_type="USES", obj="postgres",
    )
    stale = await _pending_candidates(
        session, batch_size=DEFAULT_LIFT_BATCH, min_asserting_memories=1,
    )
    assert len(stale) == 1
    assert memory_source_ref(doomed) in stale[0].origins

    # Now Tier B moves under the snapshot: Phase 5 strips `doomed`'s relations
    # and the withdrawal sweep reconciles its provenance away.
    await PostgresGraphRepository(session).delete_by_memory_id(UUID(doomed))
    await reconcile_memory_sources(session, memory_id=doomed)
    assert {row["source_ref"] for row in await sources(session, fact_id)} == {
        memory_source_ref(keeper)
    }

    async with session.begin_nested():
        lifted = await _lift_one(session, stale[0])

    refs = {row["source_ref"] for row in await sources(session, fact_id)}
    assert refs == {memory_source_ref(keeper), memory_source_ref(newcomer)}, (
        "a memory with zero Layer-1 assertions was re-added as a source"
    )
    assert lifted.sources_added == 1
    assert await FactSourceRepository(session).count_distinct_origins(fact_id) == 2


@pytest.mark.asyncio
async def test_a_candidate_whose_every_assertion_vanished_mints_nothing(session):
    memory_id = await seed_memory(session)
    await assert_relation(
        session, memory_id=memory_id, subject="darkmem", rel_type="USES", obj="postgres",
    )
    candidates = await _pending_candidates(
        session, batch_size=DEFAULT_LIFT_BATCH, min_asserting_memories=1,
    )
    assert len(candidates) == 1

    await PostgresGraphRepository(session).delete_by_memory_id(UUID(memory_id))

    async with session.begin_nested():
        lifted = await _lift_one(session, candidates[0])

    assert (lifted.minted, lifted.sources_added) == (False, 0)
    assert await facts(session) == [], (
        "a fact no memory stands behind must not be minted from a stale snapshot"
    )


# ────────── identity, not spelling, is what the scan groups on ──────────


async def seed_two_spellings(session) -> tuple[str, str]:
    """One canonical triple asserted under two whitespace spellings.

    `compute_triple_key` collapses interior whitespace; Phase 5 strips and
    lowers but does not collapse (`pipeline.py`), so this is reachable on disk.
    """
    first = await seed_memory(session, origin_key="session-a")
    second = await seed_memory(session, origin_key="session-b")
    await assert_relation(
        session, memory_id=first, subject="darkmem", rel_type="USES", obj="postgres db",
    )
    await assert_relation(
        session, memory_id=second, subject="darkmem", rel_type="USES", obj="postgres  db",
    )
    return first, second


@pytest.mark.asyncio
async def test_two_spellings_of_one_triple_lift_to_one_canonically_named_fact(session):
    first, second = await seed_two_spellings(session)

    outcome = await run_lift(session)

    rows = await facts(session)
    assert len(rows) == 1, "two spellings of one canonical triple are one fact"
    assert rows[0]["object_name"] == "postgres db", (
        "the denormalised name is canonical, so the trigram text the "
        "contradiction scan reads carries no double space"
    )
    assert rows[0]["fact"] == "darkmem uses postgres db"
    assert outcome.sources_added == 2
    assert {row["source_ref"] for row in await sources(session, rows[0]["id"])} == {
        memory_source_ref(first), memory_source_ref(second),
    }


@pytest.mark.asyncio
async def test_a_losing_spelling_does_not_stay_outstanding_work_forever(session):
    """The starvation consequence, asserted on its own so nothing earlier can
    mask it. Grouping on raw names leaves the spelling that lost the merge
    unmatched by the minted row, so it is reported outstanding on every tick —
    a permanent batch-slot occupant that starves later groups at the margin and
    destroys the `candidates == 0` steady state the no-op guard is recognised
    by."""
    await seed_two_spellings(session)
    await run_lift(session)

    for tick in range(3):
        outcome = await run_lift(session)
        assert outcome.candidates == 0, (
            f"tick {tick} still reports outstanding work for an already-lifted, "
            f"fully-sourced fact"
        )
        assert outcome.events_emitted == 0


async def sql_keeps_apart(session, separator: str) -> bool:
    """Does the scan's SQL canonicaliser leave ``separator`` uncollapsed?

    ``compute_triple_key`` folds every separator ``str.isspace()`` accepts,
    while the database's ``\\s`` is narrower. Which separators fall in the gap
    is a property of this database, so the tests below read it rather than
    assuming it — a run where nothing falls in the gap would exercise nothing
    and must say so instead of passing.
    """
    result = await session.execute(
        text(
            "SELECT lower(btrim(regexp_replace("
            "  CAST(:txt AS text), '\\s+', ' ', 'g'))) <> CAST(:folded AS text)"
        ),
        {"txt": f"postgres{separator}db", "folded": "postgres db"},
    )
    return bool(result.scalar_one())


@pytest.mark.asyncio
async def test_a_witness_under_a_third_spelling_is_never_silently_dropped(session):
    """Exact parity with the withdrawal half, not approximate parity via SQL.

    Matching the write-time re-read on the candidate's own spelling makes it
    *narrower* than `reconcile_memory_sources`' retention predicate: a memory
    asserting the same fact under a spelling the database canonicaliser keeps
    apart is dropped by the lift though the sweep would keep it. That silently
    and permanently loses a legitimate witness — under-serving, but real data
    loss, and it is the same defect class as the one the canonicalisation was
    added to fix.
    """
    exotic = [sep for sep in (NBSP, NARROW_NBSP) if await sql_keeps_apart(session, sep)]
    assert len(exotic) >= 2, (
        "this database collapses the separators the test needs, so the "
        "spelling-split shape is unreachable and the assertions below would "
        "pass vacuously; find separators that fall in the gap"
    )

    first = await seed_memory(session, origin_key="session-a")
    await assert_relation(
        session, memory_id=first, subject="darkmem", rel_type="USES", obj="postgres db",
    )
    await run_lift(session)

    witnesses = {first}
    for index, separator in enumerate(exotic):
        memory_id = await seed_memory(session, origin_key=f"session-{index}")
        await assert_relation(
            session, memory_id=memory_id, subject="darkmem", rel_type="USES",
            obj=f"postgres{separator}db",
        )
        witnesses.add(memory_id)

    for _ in range(4):
        await run_lift(session)

    rows = await facts(session)
    assert len(rows) == 1, "every spelling folds to one fact identity"
    refs = {row["source_ref"] for row in await sources(session, rows[0]["id"])}
    assert refs == {memory_source_ref(m) for m in witnesses}, (
        "a witness the withdrawal half would retain was dropped by the lift"
    )
    assert await FactSourceRepository(session).count_distinct_origins(rows[0]["id"]) == 3


@pytest.mark.asyncio
async def test_a_permanently_pending_group_is_reported_rather_than_silent(session, caplog):
    """The loudness guard has to cover the subset case too.

    A spelling the database keeps apart leaves its group outstanding forever
    even once every source has landed, because the minted fact carries a
    different canonical name. That residue is not fixable inside this module,
    so it must at least be visible — and an earlier spelling of the guard was
    inert in exactly this shape, which reads as coverage while providing none.
    """
    separator = NBSP
    assert await sql_keeps_apart(session, separator), (
        "this database collapses the separator, so no residue exists to report"
    )

    first = await seed_memory(session, origin_key="session-a")
    await assert_relation(
        session, memory_id=first, subject="darkmem", rel_type="USES", obj="postgres db",
    )
    second = await seed_memory(session, origin_key="session-b")
    await assert_relation(
        session, memory_id=second, subject="darkmem", rel_type="USES",
        obj=f"postgres{separator}db",
    )
    await run_lift(session)
    await run_lift(session)

    with caplog.at_level(logging.WARNING, logger="app.services.fact_lift"):
        outcome = await run_lift(session)

    assert outcome.candidates >= 1, "the residue must still be reachable here"
    assert (outcome.facts_created, outcome.sources_added) == (0, 0)
    assert any(
        record.name == "app.services.fact_lift"
        and record.levelno == logging.WARNING
        and "outstanding work" in record.getMessage()
        for record in caplog.records
    ), "a group that recurs forever while writing nothing must be logged"


@pytest.mark.asyncio
async def test_a_no_op_candidate_reports_stalled_even_when_part_of_it_vanished(session):
    """The loudness guard must not be conditioned on the whole snapshot.

    Requiring `live == origins` makes the flag inert whenever any snapshot
    memory drops out, which is precisely when a tick is most likely to write
    nothing — so the guard would read as coverage while providing none in the
    subset case. Here the surviving memory is already sourced and the other has
    been stripped, so the candidate writes nothing with `live` a strict subset.
    """
    stored_memory = await seed_memory(session, origin_key="session-a")
    await assert_relation(
        session, memory_id=stored_memory, subject="darkmem", rel_type="USES",
        obj="postgres",
    )
    await run_lift(session)

    doomed = await seed_memory(session, origin_key="session-b")
    await assert_relation(
        session, memory_id=doomed, subject="darkmem", rel_type="USES", obj="postgres",
    )
    candidates = await _pending_candidates(
        session, batch_size=DEFAULT_LIFT_BATCH, min_asserting_memories=1,
    )
    assert len(candidates) == 1
    assert set(candidates[0].origins) == {
        memory_source_ref(stored_memory), memory_source_ref(doomed),
    }

    await PostgresGraphRepository(session).delete_by_memory_id(UUID(doomed))

    async with session.begin_nested():
        lifted = await _lift_one(session, candidates[0])

    assert (lifted.minted, lifted.sources_added) == (False, 0)
    assert lifted.stalled, (
        "a candidate that wrote nothing must report stalled even when part of "
        "its snapshot stopped asserting"
    )


@pytest.mark.asyncio
async def test_the_salience_bar_counts_memories_per_fact_not_per_spelling(session):
    """Two distinct memories asserting one canonical triple under two spellings
    are two witnesses for that fact, so a bar of two must clear."""
    first = await seed_memory(session, origin_key="session-a")
    second = await seed_memory(session, origin_key="session-b")
    await assert_relation(
        session, memory_id=first, subject="darkmem", rel_type="USES", obj="postgres db",
    )
    await assert_relation(
        session, memory_id=second, subject="darkmem", rel_type="USES", obj="postgres  db",
    )

    outcome = await run_lift(session, min_asserting_memories=2)

    assert outcome.facts_created == 1
    assert len(await sources(session, (await facts(session))[0]["id"])) == 2


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
