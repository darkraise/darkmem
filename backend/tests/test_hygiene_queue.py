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
from app.repositories.relational import PostgresMemoryRepository
from app.services import dream_digest as digest
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
            session, edge_ids, actor="tester",
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
            session, [edge_id], actor="tester",
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
            session, [edge_id], actor="tester",
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
            session, [edge_id], actor="tester",
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
            session, [edge_id], actor="tester",
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


# ───────── F1 (Fable review): the digest must not misdescribe a batch ──────


class TestDigestDistinguishesOrigin:
    async def test_a_hygiene_batch_carries_origin_and_actor_not_a_false_detector(
        self, session
    ):
        older = await seed_memory(session)
        newer = await seed_memory(session)
        cycle_id, results = await hygiene_queue.bulk_supersede(
            session, [{"memory_id": older, "superseded_by": newer}], actor="alice",
        )
        assert results[0].applied

        cycles, _ = await digest.list_cycles(session, project=PROJECT)
        cycle = next(c for c in cycles if c.cycle_id == cycle_id)
        assert cycle.origin == hygiene_queue.ORIGIN_HYGIENE

        actions = await digest.read_cycle_actions(session, cycle_id)
        assert len(actions) == 1
        action = actions[0]
        assert action.origin == hygiene_queue.ORIGIN_HYGIENE
        assert action.actor == "alice"
        assert action.detector is None, (
            "a human-initiated action must never render a detector it did "
            f"not use: {action.detector!r}"
        )

    async def test_an_automated_action_still_renders_its_detector_and_no_origin(
        self, session
    ):
        """Differential control: an automated memory_dream-shaped action (no
        `origin` key at all) must still show `detector='dedup'` and no
        origin/actor, so the fix distinguishes the two rather than hiding
        both."""
        older = await seed_memory(session)
        newer = await seed_memory(session)
        cycle_id = str(new_id())
        await record_event(
            session, event_type=journal.EVENT_TYPE, object_type=journal.OBJECT_TYPE,
            object_id=UUID(older), project=PROJECT,
            payload={
                "action": journal.ACTION_SUBSUME,
                "before": {"status": "active", "superseded_by": None},
                "after": {"status": "superseded", "superseded_by": newer},
                "pair": {"older": older, "newer": newer},
                "detector": journal.DETECTOR,
                "cycle_id": cycle_id,
            },
        )

        cycles, _ = await digest.list_cycles(session, project=PROJECT)
        cycle = next(c for c in cycles if c.cycle_id == cycle_id)
        assert cycle.origin is None

        actions = await digest.read_cycle_actions(session, cycle_id)
        assert actions[0].origin is None
        assert actions[0].actor is None
        assert actions[0].detector == journal.DETECTOR


# ───────── F2 (Fable review): the readback must be scoped to the batch ─────


class TestEventReadbackIsScopedToTheBatch:
    async def test_a_degraded_journal_write_is_reported_honestly_not_as_a_stale_id(
        self, session, monkeypatch
    ):
        """R2/F2: `_last_event_id` must not return a *different* action's
        event id when this action's own journal write silently degrades
        (`record_event` never raises -- CLAUDE.md). This drives the real
        degradation path by making `record_event` itself a no-op -- the same
        technique `test_dream_undo.py` uses for the same class of claim --
        rather than mocking this module's own readback helper."""
        stale_older = await seed_memory(session)
        stale_target = await seed_memory(session)
        # A real, unrelated prior action against `stale_older`, from a
        # different cycle: exactly what an unscoped-by-object-id readback
        # would find and misreport as this test's own event.
        await record_event(
            session, event_type=journal.EVENT_TYPE, object_type=journal.OBJECT_TYPE,
            object_id=UUID(stale_older), project=PROJECT, actor="someone-else",
            payload={
                "action": journal.ACTION_SUBSUME,
                "before": {"status": "active", "superseded_by": None},
                "after": {"status": "superseded", "superseded_by": stale_target},
                "pair": {"older": stale_older, "newer": stale_target},
                "detector": journal.DETECTOR,
                "cycle_id": str(new_id()),
            },
        )

        newer = await seed_memory(session)

        async def _noop_record_event(*args, **kwargs):
            return None

        monkeypatch.setattr(hygiene_queue, "record_event", _noop_record_event)

        cycle_id, results = await hygiene_queue.bulk_supersede(
            session, [{"memory_id": stale_older, "superseded_by": newer}],
            actor="tester",
        )

        assert results[0].applied is True
        assert (await memory_status(session, stale_older))["status"] == "superseded"
        assert results[0].event_id is None, (
            "the readback returned a stale event id from an unrelated prior "
            f"action instead of reporting the degraded journal honestly: "
            f"{results[0].event_id}"
        )


# ───────── F4: never a gate on the read path (invariant 14) ────────────────


class TestNeverAGateOnTheReadPath:
    async def test_an_open_duplicate_marker_never_gates_or_reorders_list_memories(
        self, session
    ):
        """T2.22 proves its analogue against `KnowledgeTripleRepository.
        get_live`; this pins it against `PostgresMemoryRepository.
        list_memories` -- today's plain memory read path, which never joins
        `memory_relations` at all. The near_duplicate marker T2.12 introduced
        and this module reads is exactly the new signal invariant 14 is at
        risk from, so the fixture proves against it rather than against a
        column retrieval already filtered on."""
        repo = PostgresMemoryRepository(session)
        base = datetime.now(timezone.utc)
        ids = []
        for index in range(3):
            ids.append(
                await seed_memory(
                    session, content=f"read-path-{index}",
                    created_at=base + timedelta(seconds=index),
                )
            )

        async def _order():
            rows, _ = await repo.list_memories(offset=0, limit=50)
            return [str(row.id) for row in rows]

        before = await _order()
        assert set(ids) <= set(before)

        older, newer = ids[0], ids[1]
        await seed_duplicate_edge(session, source=newer, target=older)

        after_open = await _order()
        assert after_open == before, (
            "an 'open' duplicate marker changed the plain memory read "
            "path's set or order"
        )

        edge = await edges.get_edge(
            session, source_memory_id=newer, target_memory_id=older,
            rel_type="RELATES_TO",
        )
        await hygiene_queue.bulk_confirm_dedup(
            session, [str(edge["id"])], actor="tester",
        )
        after_confirm = await _order()
        assert after_confirm == before, (
            "confirming a duplicate changed the plain memory read path's "
            "set or order"
        )


# ───────── Minor: /counts must accept the same overrides its siblings do ───


class TestCountsRouteAcceptsOverrides:
    async def test_counts_route_honours_threshold_and_within_days(
        self, client, auth_headers, session
    ):
        await seed_memory(session, confidence=0.6)
        await seed_memory(
            session, confidence=0.9,
            expires_at=datetime.now(timezone.utc) + timedelta(days=20),
        )
        await session.commit()

        default_response = await client.get(
            "/api/v1/hygiene-queue/counts", params={"project": PROJECT},
            headers=auth_headers,
        )
        assert default_response.status_code == 200
        assert default_response.json() == {
            "duplicates": 0, "low_confidence": 0, "expiring_soon": 0, "superseded": 0,
        }

        widened_response = await client.get(
            "/api/v1/hygiene-queue/counts",
            params={"project": PROJECT, "threshold": 0.8, "within_days": 30},
            headers=auth_headers,
        )
        assert widened_response.status_code == 200
        assert widened_response.json() == {
            "duplicates": 0, "low_confidence": 1, "expiring_soon": 1, "superseded": 0,
        }
