"""T2.23 — the hygiene queue and its bulk actions (doc 08 §6).

Three Done-when clauses, each proved rather than asserted:

- **"The two queues share no rows"** is proved against a fixture where the
  *same* memory is eligible for both readings (R1): it is low-confidence
  (hygiene) and the sole ``fact_sources`` origin of a disputed fact (review).
  ``TestDisjointness`` asserts each surface returns only its own table's id,
  and — the rule, not just the assertion — that none of hygiene's four query
  builders ever names ``knowledge_triples``/``knowledge_articles``/
  ``fact_sources`` in its SQL text, which is what makes the property hold by
  construction rather than by this fixture's data happening not to collide.
- **"Bulk actions journal per-item, not per-batch"** (R2) is proved by count:
  N items produce N ``consolidated`` events under one cycle id, and no
  additional row appears for the batch as a whole.
- **"Bulk actions are undoable through the T2.13 primitive"** is proved by
  actually calling ``dream_undo.undo`` against the events a bulk action wrote
  and checking the restored row — for the three actions this task ships
  (supersede, prune, confirm-dedup). ``set/extend a TTL`` is not shipped;
  see the report for the R4 amendment.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import text

from app.repositories import memory_relations as edges
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services import dream_journal as journal
from app.services import dream_undo as undo
from app.services import hygiene_queue
from app.services import memory_dream as dream
from app.services import review_queue as review_queue_service
from app.services.events import record_event
from app.utils.ids import new_id

pytestmark = pytest.mark.asyncio

PROJECT = "t223-hygiene"

_INSERT_MEMORY = text(
    """
    INSERT INTO memories (
        id, content, source, project, status, is_archived, created_at,
        confidence, expires_at, superseded_by
    )
    VALUES (
        CAST(:id AS uuid), :content, 'api', CAST(:project AS text),
        CAST(:status AS memory_status), false, :created_at,
        :confidence, :expires_at, CAST(:superseded_by AS uuid)
    )
    """
)


async def seed_memory(
    session,
    *,
    project: str = PROJECT,
    content: str = "a memory",
    status: str = "active",
    created_at: datetime | None = None,
    confidence: float = 0.75,
    expires_at: datetime | None = None,
    superseded_by: str | None = None,
) -> str:
    identifier = new_id()
    await session.execute(
        _INSERT_MEMORY,
        {
            "id": str(identifier),
            "content": content,
            "project": project,
            "status": status,
            "created_at": created_at or datetime.now(timezone.utc),
            "confidence": confidence,
            "expires_at": expires_at,
            "superseded_by": superseded_by,
        },
    )
    return str(identifier)


def _near_duplicate_block(
    *, hygiene_state: str = "open", score: float = 0.95, verdict: str = "duplicate"
) -> dict:
    return {
        "kind": "duplicate_candidate",
        "hygiene_state": hygiene_state,
        "score": score,
        "verdict": verdict,
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }


async def seed_duplicate_edge(
    session,
    *,
    source: str,
    target: str,
    project: str = PROJECT,
    rel_type: str = "RELATES_TO",
    block: dict | None = None,
) -> str:
    write = await edges.upsert_edge(
        session,
        source_memory_id=source,
        target_memory_id=target,
        rel_type=rel_type,
        project=project,
        pass_key=journal.NEAR_DUPLICATE_PASS,
        block=block or _near_duplicate_block(),
    )
    edge = await edges.get_edge(
        session, source_memory_id=source, target_memory_id=target, rel_type=rel_type
    )
    return str(edge["id"])


async def seed_fact(
    session, *, project: str = PROJECT, review_state: str | None = "open"
) -> str:
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=f"triple-{new_id().hex[:12]}",
        subject_name="the database",
        object_name="postgres 14",
        rel_type="USES",
        fact="the database uses postgres 14",
        reference_time=datetime.now(timezone.utc),
        project=project,
        review_state=review_state,
    )
    if review_state == "open":
        await session.execute(
            text(
                "UPDATE knowledge_triples SET verification_status = 'disputed' "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(row["id"])},
        )
    return str(row["id"])


async def seed_fact_source(session, *, fact_id: str, memory_id: str) -> None:
    await session.execute(
        text(
            "INSERT INTO fact_sources (id, fact_id, source_kind, source_ref, origin_key) "
            "VALUES (CAST(:id AS uuid), CAST(:fact_id AS uuid), 'memory', "
            "        CAST(:ref AS text), 'origin-1')"
        ),
        {"id": str(new_id()), "fact_id": fact_id, "ref": memory_id},
    )


async def event_rows(session, *, cycle_id: str, event_type: str = journal.EVENT_TYPE):
    result = await session.execute(
        text(
            "SELECT id AS event_id, CAST(object_id AS text) AS object_id, payload "
            "FROM events WHERE event_type = CAST(:event_type AS text) "
            "  AND payload ->> 'cycle_id' = CAST(:cycle_id AS text) "
            "ORDER BY id"
        ),
        {"event_type": event_type, "cycle_id": cycle_id},
    )
    return [dict(row) for row in result.mappings().all()]


async def memory_status(session, memory_id: str) -> dict:
    row = (
        await session.execute(
            text(
                "SELECT status::text AS status, "
                "       CAST(superseded_by AS text) AS superseded_by "
                "FROM memories WHERE id = CAST(:id AS uuid)"
            ),
            {"id": memory_id},
        )
    ).mappings().one()
    return dict(row)


# ─────────────────────────────── read arms ───────────────────────────────


class TestDuplicatesArm:
    async def test_open_pair_with_both_endpoints_active_is_listed(self, session):
        older = await seed_memory(session, content="uses postgres 14")
        newer = await seed_memory(session, content="uses postgres 14 as well")
        edge_id = await seed_duplicate_edge(session, source=newer, target=older)

        items, total = await hygiene_queue.list_duplicates(session, project=PROJECT)

        assert total == 1
        assert items[0]["id"] == edge_id
        assert items[0]["hygiene_state"] == "open"

    async def test_confirmed_pair_drops_off_the_open_listing(self, session):
        older = await seed_memory(session)
        newer = await seed_memory(session)
        await seed_duplicate_edge(
            session, source=newer, target=older,
            block=_near_duplicate_block(hygiene_state="confirmed"),
        )

        items, total = await hygiene_queue.list_duplicates(session, project=PROJECT)
        assert total == 0
        assert items == []

    async def test_within_cycle_race_excludes_a_pair_with_a_retired_endpoint(
        self, session
    ):
        """T2.12's re-review: a duplicate pair can outrank a subsume pair in
        one cycle, leaving an edge written against a memory retired later in
        the same tick. The general fix (both endpoints must be `active`)
        closes this whether the retirement happened in the same cycle,
        a later one, or via this module's own supersede/prune actions."""
        older = await seed_memory(session)
        newer = await seed_memory(session)
        await seed_duplicate_edge(session, source=newer, target=older)

        # The older half is retired independently of the duplicate pass.
        successor = await seed_memory(session)
        await session.execute(
            text(
                "UPDATE memories SET status = 'superseded', "
                "superseded_by = CAST(:s AS uuid) WHERE id = CAST(:id AS uuid)"
            ),
            {"s": successor, "id": older},
        )

        items, total = await hygiene_queue.list_duplicates(session, project=PROJECT)
        assert total == 0
        assert items == []


class TestLowConfidenceArm:
    async def test_low_confidence_active_memory_is_listed(self, session):
        low = await seed_memory(session, confidence=0.2)
        await seed_memory(session, confidence=0.9)

        items, total = await hygiene_queue.list_low_confidence(
            session, project=PROJECT, threshold=0.5
        )
        assert total == 1
        assert items[0]["id"] == low

    async def test_superseded_memory_is_not_double_listed_here(self, session):
        successor = await seed_memory(session)
        superseded = await seed_memory(session, confidence=0.1, status="superseded",
                                        superseded_by=successor)
        items, total = await hygiene_queue.list_low_confidence(
            session, project=PROJECT, threshold=0.5
        )
        assert total == 0
        assert superseded not in [item["id"] for item in items]


class TestExpiringSoonArm:
    async def test_expiring_within_window_is_listed(self, session):
        soon = await seed_memory(
            session, expires_at=datetime.now(timezone.utc) + timedelta(days=1)
        )
        await seed_memory(
            session, expires_at=datetime.now(timezone.utc) + timedelta(days=90)
        )
        await seed_memory(session, expires_at=None)

        items, total = await hygiene_queue.list_expiring_soon(
            session, project=PROJECT, within_days=7
        )
        assert total == 1
        assert items[0]["id"] == soon


class TestSupersededArm:
    async def test_superseded_lineage_is_listed(self, session):
        successor = await seed_memory(session)
        superseded = await seed_memory(session, status="superseded", superseded_by=successor)
        await seed_memory(session, status="active")

        items, total = await hygiene_queue.list_superseded(session, project=PROJECT)
        assert total == 1
        assert items[0]["id"] == superseded
        assert items[0]["superseded_by"] == successor


class TestCounts:
    async def test_counts_reflect_all_four_arms(self, session):
        await seed_memory(session, confidence=0.1)
        successor = await seed_memory(session)
        await seed_memory(session, status="superseded", superseded_by=successor)
        older = await seed_memory(session)
        newer = await seed_memory(session)
        await seed_duplicate_edge(session, source=newer, target=older)

        result = await hygiene_queue.counts(session, project=PROJECT, low_confidence_threshold=0.5)
        assert result == {
            "duplicates": 1, "low_confidence": 1, "expiring_soon": 0, "superseded": 1,
        }


# ───────── R1: the two queues share no rows (the rule, not just the data) ──


class TestDisjointness:
    async def test_the_same_subject_resolves_to_exactly_one_surface_each(self, session):
        """The fixture: one memory M is (a) low-confidence, hence
        hygiene-eligible, and (b) the sole `fact_sources` origin of a
        disputed fact F, hence review-eligible. Both surfaces list *their
        own table's* row for the same underlying subject — that is not a
        violation, because the two surfaces answer different questions
        (housekeep the capture vs adjudicate the belief) — but neither may
        ever surface the other's id."""
        memory_id = await seed_memory(session, confidence=0.1)
        fact_id = await seed_fact(session)
        await seed_fact_source(session, fact_id=fact_id, memory_id=memory_id)

        hygiene_items, _ = await hygiene_queue.list_low_confidence(
            session, project=PROJECT, threshold=0.5
        )
        review_items, _ = await review_queue_service.list_open_facts(
            session, project=PROJECT
        )

        hygiene_ids = {item["id"] for item in hygiene_items}
        review_ids = {item["id"] for item in review_items}

        assert memory_id in hygiene_ids
        assert fact_id in review_ids
        assert hygiene_ids.isdisjoint(review_ids)
        assert memory_id not in review_ids
        assert fact_id not in hygiene_ids

    async def test_hygiene_queries_never_name_the_review_queue_tables(self):
        """The rule that decides disjointness: hygiene's SQL text is
        lexically confined to `memories`/`memory_relations`. A subject's
        fact-side disposition can never promote or suppress its memory-side
        eligibility because the query that decides eligibility cannot see it.
        """
        forbidden = ("knowledge_triples", "knowledge_articles", "fact_sources")
        builders = (
            hygiene_queue.build_duplicates_query,
            hygiene_queue.build_low_confidence_query,
            hygiene_queue.build_expiring_soon_query,
            hygiene_queue.build_superseded_query,
        )
        for builder in builders:
            items_sql, count_sql = builder(None)
            for name in forbidden:
                assert name not in items_sql, (builder.__name__, items_sql)
                assert name not in count_sql, (builder.__name__, count_sql)


# ─────────── R2: per-item journalling, proved by count ─────────────────────


class TestPerItemJournal:
    async def test_bulk_supersede_journals_exactly_one_event_per_applied_item(
        self, session
    ):
        pairs = []
        for _ in range(3):
            older = await seed_memory(session)
            newer = await seed_memory(session)
            pairs.append((older, newer))

        cycle_id, results = await hygiene_queue.bulk_supersede(
            session,
            [{"memory_id": o, "superseded_by": n} for o, n in pairs],
            actor="tester",
        )

        assert all(result.applied for result in results)
        rows = await event_rows(session, cycle_id=cycle_id)
        assert len(rows) == len(pairs) == 3
        assert {row["object_id"] for row in rows} == {o for o, _ in pairs}
        for row in rows:
            assert row["payload"]["action"] == journal.ACTION_SUBSUME

    async def test_a_refused_item_journals_nothing(self, session):
        """A memory that does not exist refuses `not_found`; no event, and it
        does not inflate the count of a batch where its siblings applied."""
        older = await seed_memory(session)
        newer = await seed_memory(session)
        missing = str(new_id())
        other_newer = await seed_memory(session)

        cycle_id, results = await hygiene_queue.bulk_supersede(
            session,
            [
                {"memory_id": older, "superseded_by": newer},
                {"memory_id": missing, "superseded_by": other_newer},
            ],
            actor="tester",
        )
        applied = [r for r in results if r.applied]
        refused = [r for r in results if not r.applied]
        assert len(applied) == 1
        assert len(refused) == 1
        assert refused[0].reason == "not_found"

        rows = await event_rows(session, cycle_id=cycle_id)
        assert len(rows) == 1

    async def test_bulk_prune_journals_exactly_one_event_per_applied_item(self, session):
        memory_ids = [await seed_memory(session) for _ in range(4)]
        cycle_id, results = await hygiene_queue.bulk_prune(
            session, memory_ids, actor="tester",
        )
        assert all(result.applied for result in results)
        rows = await event_rows(session, cycle_id=cycle_id)
        assert len(rows) == 4
        assert {row["object_id"] for row in rows} == set(memory_ids)

    async def test_bulk_confirm_dedup_journals_exactly_one_event_per_applied_item(
        self, session
    ):
        edge_ids = []
        for _ in range(3):
            older = await seed_memory(session)
            newer = await seed_memory(session)
            edge_ids.append(await seed_duplicate_edge(session, source=newer, target=older))

        cycle_id, results = await hygiene_queue.bulk_confirm_dedup(
            session, edge_ids, hygiene_state="confirmed", actor="tester",
        )
        assert all(result.applied for result in results)
        rows = await event_rows(session, cycle_id=cycle_id)
        assert len(rows) == 3
        for row in rows:
            assert row["payload"]["action"] == journal.ACTION_ASSOCIATE

    async def test_an_unchanged_confirm_journals_nothing(self, session):
        """Already-confirmed pair: no-op, no event — the same discipline
        `apply_associate` uses for a stable pair."""
        older = await seed_memory(session)
        newer = await seed_memory(session)
        edge_id = await seed_duplicate_edge(
            session, source=newer, target=older,
            block=_near_duplicate_block(hygiene_state="confirmed"),
        )
        cycle_id, results = await hygiene_queue.bulk_confirm_dedup(
            session, [edge_id], hygiene_state="confirmed", actor="tester",
        )
        assert results[0].applied is False
        assert results[0].reason == "unchanged"
        rows = await event_rows(session, cycle_id=cycle_id)
        assert rows == []


# ─────────── R3/R4: undoable through the T2.13 primitive ──────────────────


class TestUndoIntegration:
    async def test_bulk_supersede_is_undone_by_dream_undo(self, session):
        older = await seed_memory(session)
        newer = await seed_memory(session)
        cycle_id, results = await hygiene_queue.bulk_supersede(
            session, [{"memory_id": older, "superseded_by": newer}], actor="tester",
        )
        event_id = results[0].event_id
        assert event_id is not None

        after_action = await memory_status(session, older)
        assert after_action["status"] == "superseded"

        batch = await undo.undo(session, event_ids=[event_id], actor="tester")
        assert len(batch.undone) == 1
        restored = await memory_status(session, older)
        assert restored["status"] == "active"
        assert restored["superseded_by"] is None

    async def test_bulk_prune_is_undone_by_dream_undo(self, session):
        memory_id = await seed_memory(session)
        cycle_id, results = await hygiene_queue.bulk_prune(
            session, [memory_id], actor="tester",
        )
        event_id = results[0].event_id
        assert (await memory_status(session, memory_id))["status"] == "deprecated"

        batch = await undo.undo(session, event_ids=[event_id], actor="tester")
        assert len(batch.undone) == 1
        assert (await memory_status(session, memory_id))["status"] == "active"

    async def test_bulk_confirm_dedup_is_undone_by_dream_undo(self, session):
        older = await seed_memory(session)
        newer = await seed_memory(session)
        edge_id = await seed_duplicate_edge(session, source=newer, target=older)

        cycle_id, results = await hygiene_queue.bulk_confirm_dedup(
            session, [edge_id], hygiene_state="confirmed", actor="tester",
        )
        event_id = results[0].event_id
        assert event_id is not None

        edge = await edges.get_edge(
            session, source_memory_id=newer, target_memory_id=older,
            rel_type="RELATES_TO",
        )
        assert edges.pass_block_of(edge, journal.NEAR_DUPLICATE_PASS)["hygiene_state"] == "confirmed"

        batch = await undo.undo(session, event_ids=[event_id], actor="tester")
        assert len(batch.undone) == 1
        edge_after = await edges.get_edge(
            session, source_memory_id=newer, target_memory_id=older,
            rel_type="RELATES_TO",
        )
        assert edges.pass_block_of(edge_after, journal.NEAR_DUPLICATE_PASS)["hygiene_state"] == "open"

    async def test_a_human_triage_refuses_the_original_associates_undo(self, session):
        """The amendment log's own prediction (2026-08-02, T2.13/T2.08): once
        hygiene writes a confirm/dismiss, the *original* memory_dream associate
        action can no longer be undone, because the CAS compares the whole
        pass-block and the human's write is not the journalled `after`."""
        older = await seed_memory(session)
        newer = await seed_memory(session)
        # Simulate memory_dream's own associate write and journal.
        original_block = _near_duplicate_block(hygiene_state="open")
        await edges.upsert_edge(
            session, source_memory_id=newer, target_memory_id=older,
            rel_type="ELABORATES", project=PROJECT,
            pass_key=journal.NEAR_DUPLICATE_PASS, block=original_block,
        )
        await record_event(
            session, event_type=journal.EVENT_TYPE, object_type=journal.OBJECT_TYPE,
            object_id=UUID(newer), project=PROJECT, actor="dream",
            payload={
                "action": journal.ACTION_ASSOCIATE,
                "before": {"edge": None},
                "after": {
                    "edge": {
                        "source": newer, "target": older, "rel_type": "ELABORATES",
                        "properties": {journal.NEAR_DUPLICATE_PASS: original_block},
                    }
                },
                "created": True,
                "pair": {"older": older, "newer": newer},
                "detector": journal.DETECTOR,
                "verdict": "duplicate",
                "score": 0.95,
                "cycle_id": str(new_id()),
            },
        )
        original_event_id = (
            await session.execute(
                text(
                    "SELECT id FROM events WHERE event_type = 'consolidated' "
                    "AND object_id = CAST(:id AS uuid) ORDER BY id DESC LIMIT 1"
                ),
                {"id": newer},
            )
        ).scalar_one()

        edge = await edges.get_edge(
            session, source_memory_id=newer, target_memory_id=older,
            rel_type="ELABORATES",
        )
        edge_id = str(edge["id"])

        # A human confirms it through hygiene.
        await hygiene_queue.bulk_confirm_dedup(
            session, [edge_id], hygiene_state="confirmed", actor="tester",
        )

        with pytest.raises(undo.UndoRefused) as excinfo:
            await undo.undo(session, event_ids=[original_event_id], actor="tester")
        assert excinfo.value.blocked[0].reason == undo.REASON_STATE_CHANGED


# ────── T2.12 dependency: the marker must survive re-derivation ────────────


class TestMarkerSurvivesRederivation:
    async def test_a_confirmed_pair_stays_confirmed_after_memory_dream_rederives_it(
        self, session
    ):
        """Why T2.23 depends on T2.12 (amendment log, 2026-08-02): the marker
        survives re-derivation through TWO mechanisms — the pass-keyed
        `jsonb_set` and `near_duplicate_block`'s Python-side carry-forward.
        This drives the real producer's carry-forward function rather than
        hand-writing a block, so a regression in either mechanism fails here
        exactly as it would in production."""
        older = await seed_memory(session)
        newer = await seed_memory(session)
        edge_id = await seed_duplicate_edge(session, source=newer, target=older)

        await hygiene_queue.bulk_confirm_dedup(
            session, [edge_id], hygiene_state="confirmed", actor="tester",
        )

        # memory_dream re-derives the same pair on a later cycle: same
        # score/verdict, computed fresh, through the real producer function.
        existing_edge = await edges.get_edge(
            session, source_memory_id=newer, target_memory_id=older,
            rel_type="RELATES_TO",
        )
        existing_block = edges.pass_block_of(existing_edge, journal.NEAR_DUPLICATE_PASS)
        rederived_block = dream.near_duplicate_block(
            score=0.95, verdict="duplicate", existing=existing_block,
            detected_at=datetime.now(timezone.utc).isoformat(),
        )
        await edges.upsert_edge(
            session, source_memory_id=newer, target_memory_id=older,
            rel_type="RELATES_TO", project=PROJECT,
            pass_key=journal.NEAR_DUPLICATE_PASS, block=rederived_block,
        )

        items, total = await hygiene_queue.list_duplicates(session, project=PROJECT)
        assert total == 0, (
            "a triaged item re-opened after re-derivation: "
            f"{items}"
        )


# ───────── the one arm with a backing index today (EXPLAIN) ───────────────


async def _seed_memories_at_scale(session, n: int = 6000) -> None:
    placeholder = await seed_memory(session, project="explain-project", content="successor")
    await session.execute(
        text(
            """
            INSERT INTO memories (
                id, content, source, project, status, is_archived, created_at,
                superseded_by
            )
            SELECT
                gen_random_uuid(),
                'explain content ' || g,
                'api',
                'explain-project',
                CASE WHEN g % 200 = 0 THEN 'superseded' ELSE 'active' END::memory_status,
                false,
                now() - (g || ' minutes')::interval,
                CASE WHEN g % 200 = 0 THEN CAST(:placeholder AS uuid) ELSE NULL END
            FROM generate_series(1, :n) g
            """
        ),
        {"n": n, "placeholder": placeholder},
    )
    await session.execute(text("ANALYZE memories"))


class TestSupersededIndexUsage:
    async def test_uses_the_existing_status_index(self, session):
        await _seed_memories_at_scale(session)
        items_sql, _ = hygiene_queue.build_superseded_query(None)
        plan_rows = await session.execute(
            text("EXPLAIN " + items_sql), {"limit": 50, "offset": 0},
        )
        plan = "\n".join(r[0] for r in plan_rows)
        assert "ix_memories_status" in plan, plan
        assert "Seq Scan on memories" not in plan, plan

    async def test_dropping_the_status_index_forces_seq_scan(self, session):
        await session.execute(text("DROP INDEX ix_memories_status"))
        await _seed_memories_at_scale(session)
        items_sql, _ = hygiene_queue.build_superseded_query(None)
        plan_rows = await session.execute(
            text("EXPLAIN " + items_sql), {"limit": 50, "offset": 0},
        )
        plan = "\n".join(r[0] for r in plan_rows)
        assert "ix_memories_status" not in plan, plan
        assert "Seq Scan on memories" in plan, plan
