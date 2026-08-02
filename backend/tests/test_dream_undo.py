"""T2.13 — the dream digest and its per-action / per-batch undo.

Doc 08 §7, doc 13 §6.3. Three Done-whens, and every one of them is a claim a
green suite can make vacuously:

- *"Undo restores exact prior state"* passes trivially if the assertions only
  check that no exception was raised. Every inverse here is asserted field by
  field, against the exclusion table in the plan's D2, and each exclusion is
  itself a first-class assertion rather than an unmentioned gap.
- *"Batch undo is atomic"* is a claim about what the code can *express*, so the
  behavioural tests are backed by an AST scan over ``dream_undo.py`` for the
  five shapes that could produce or report a partial outcome.
- *"Undo itself journals"* passes with the journal readback deleted if the test
  asserts the row is present. It is asserted the other way round instead: with
  ``record_event`` stubbed to a no-op, the *restore* must be absent.
"""
from __future__ import annotations

import ast
import json
import logging
import pathlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.repositories import memory_relations as edges
from app.repositories.relational import PostgresMemoryRepository
from app.services import dream_digest as digest
from app.services import dream_journal as journal
from app.services import dream_undo as undo
from app.services import events as events_module
from app.services import memory_dream as dream
from app.utils.ids import new_id
from tests.test_dream_jobs import dream_job_implementation_modules
from tests.test_memory_dream import StubLLM, put_vector, seed_partition

BACKEND = pathlib.Path(__file__).resolve().parent.parent


# ── Step 1: the vocabulary ───────────────────────────────────────────────


class TestVocabulary:
    def test_undone_is_in_the_closed_vocabulary(self):
        """T-VOC1."""
        assert "undone" in events_module.EVENT_TYPES

    async def test_journalling_undone_warns_about_nothing(self, session, caplog):
        """T-VOC2 — the non-vacuous half.

        T-VOC1 alone is a tautology over a list literal: it would keep passing
        if `record_event` never consulted the list. This one asserts the
        emitter's own view, through the frozenset it actually checks.
        """
        with caplog.at_level(logging.WARNING, logger=events_module.__name__):
            await events_module.record_event(
                session,
                event_type="undone",
                object_type="memory",
                payload={"probe": True},
            )
        assert not [
            record for record in caplog.records
            if "closed vocabulary" in record.getMessage()
        ]

    async def test_an_unknown_type_still_warns(self, session, caplog):
        """T-VOC2's negative control: the check the previous test relies on is
        live, so its silence means the value was admitted rather than that the
        warning was removed."""
        with caplog.at_level(logging.WARNING, logger=events_module.__name__):
            await events_module.record_event(
                session,
                event_type="undone_but_not_really",
                object_type="memory",
                payload={"probe": True},
            )
        assert [
            record for record in caplog.records
            if "closed vocabulary" in record.getMessage()
        ]


# ── Step 2: the shared vocabulary module ─────────────────────────────────

# Everything the producer used to assign and now imports. The move is a pure
# re-export, so each name must still resolve off the producer's module and be
# the *same object* — a duplicated literal would satisfy an equality check.
MOVED_NAMES = (
    "EVENT_TYPE",
    "OBJECT_TYPE",
    "DETECTOR",
    "ACTION_SUBSUME",
    "ACTION_ASSOCIATE",
    "ACTION_REFINE",
    "NEAR_DUPLICATE_PASS",
    "HYGIENE_STATE_OPEN",
    "REFINE_MARKER_PATH",
    "refine_marker_of",
    "content_sha",
)


class TestSharedVocabulary:
    @pytest.mark.parametrize("name", MOVED_NAMES)
    def test_the_producer_re_exports_the_moved_name(self, name):
        """T-VOC3. Written to hold under either of D1's two layouts: it
        compares objects across the two modules rather than asserting where
        the assignment lives."""
        assert hasattr(dream, name), (
            f"{name} no longer resolves off the producer's module, so the "
            "move stopped being a pure re-export and T2.12's suite is only "
            "passing because nothing reads it"
        )
        assert getattr(dream, name) is getattr(journal, name)

    def test_the_shared_module_is_outside_the_forbidden_set(self):
        """T-VOC5, asserted from this lane rather than trusted.

        The whole module layout rests on invariant 15's forbidden set being
        derived ONE HOP from the umbrella's imports. A rebuild that computed
        the transitive closure would pull this module in the moment the
        producer imports it, and the undo service importing it would then fail
        the build. Pinned here so that regression fails by name instead of
        surfacing as an unexplained import error somewhere else.
        """
        assert "dream_journal" not in dream_job_implementation_modules()


# ── the fixtures ─────────────────────────────────────────────────────────

# Every action under test is produced by driving the **real** producer, never
# by hand-writing a payload. The plan's §1.2 records five places where the
# shipped payload differs from the interface prose it was documented with; an
# inverse built against a hand-written payload would be built against my
# reading of the contract and would pass against itself.

NOW = datetime(2026, 8, 2, 3, 0, tzinfo=timezone.utc)

_INSERT_MEMORY = text("""
    INSERT INTO memories (
        id, content, source, project, status, is_archived, created_at,
        summary, metadata
    )
    VALUES (
        CAST(:id AS uuid), :content, 'api', CAST(:project AS text),
        CAST(:status AS memory_status), false, :created_at, :summary,
        CAST(:metadata AS jsonb)
    )
""")


@pytest.fixture
async def committing(setup_database):
    """A real session factory with real commits.

    The rollback-isolated `session` fixture cannot express what an undo does:
    the caller-rollback seam T-ATOM6 pins is only observable against a session
    that could really commit.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import settings

    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        async with factory() as cleanup:
            # `events` is append-only, so a DELETE raises. Isolation comes from
            # the per-test project scope key instead. Tags outlive their
            # memories — `memory_tags` cascades but `tags` does not — and a
            # stray committed tag is an orphan every tag-sweep assertion in the
            # suite would then count.
            for statement in (
                "DELETE FROM memory_relations WHERE project LIKE 't213-%'",
                "DELETE FROM memories WHERE project LIKE 't213-%'",
                "DELETE FROM tags WHERE name LIKE 't213-%'",
                "DELETE FROM config WHERE key = "
                f"'{undo.RETENTION_CONFIG_KEY}'",
            ):
                await cleanup.execute(text(statement))
            await cleanup.commit()
        await engine.dispose()


@pytest.fixture
def project() -> str:
    return f"t213-{new_id().hex[:12]}"


async def seed_memory(
    session,
    *,
    project: str,
    content: str = "a memory",
    status: str = "active",
    created_at: datetime | None = None,
    summary: str | None = None,
    metadata: dict | None = None,
) -> UUID:
    identifier = new_id()
    await session.execute(
        _INSERT_MEMORY,
        {
            "id": str(identifier),
            "content": content,
            "project": project,
            "status": status,
            "created_at": created_at or NOW,
            "summary": summary,
            "metadata": json.dumps(metadata or {}),
        },
    )
    return identifier


async def memory_row(factory, memory_id) -> dict:
    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT status::text AS status, content, summary, "
                "       CAST(superseded_by AS text) AS superseded_by, "
                "       metadata, updated_at, "
                "       COALESCE(ARRAY(SELECT t.name FROM memory_tags mt "
                "         JOIN tags t ON t.id = mt.tag_id "
                "         WHERE mt.memory_id = m.id ORDER BY t.name), "
                "         CAST(ARRAY[] AS text[])) AS tag_names "
                "FROM memories m WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(memory_id)},
        )
        return dict(result.mappings().one())


async def edge_row(factory, source, target, rel_type) -> dict | None:
    async with factory() as session:
        return await edges.get_edge(
            session,
            source_memory_id=source,
            target_memory_id=target,
            rel_type=rel_type,
        )


async def journal_rows(factory, project, event_type=journal.EVENT_TYPE) -> list[dict]:
    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT id AS event_id, CAST(object_id AS text) AS object_id, "
                "       actor, payload, created_at "
                "FROM events WHERE event_type = CAST(:kind AS text) "
                "  AND project = CAST(:project AS text) "
                "ORDER BY created_at, id"
            ),
            {"kind": event_type, "project": project},
        )
        return [dict(row) for row in result.mappings()]


def memory_row_of(memory_id, *, project, content, created_at=NOW, summary=None,
                  metadata=None, tags=()) -> dream.MemoryRow:
    return dream.MemoryRow(
        memory_id=str(memory_id),
        project=project,
        created_at=created_at,
        content=content,
        summary=summary,
        metadata=metadata or {},
        tags=tuple(tags),
    )


async def produce_subsume(factory, project, *, cycle_id, older_content="old truth",
                          newer_content="new truth") -> tuple[UUID, UUID, int]:
    """One real subsume action and the event id it journalled."""
    async with factory() as session:
        older = await seed_memory(
            session, project=project, content=older_content, created_at=NOW,
        )
        newer = await seed_memory(
            session, project=project, content=newer_content,
            created_at=NOW + timedelta(hours=1),
        )
        await session.commit()
    async with factory() as session:
        pair = dream.PairCandidate(
            older=memory_row_of(older, project=project, content=older_content),
            newer=memory_row_of(
                newer, project=project, content=newer_content,
                created_at=NOW + timedelta(hours=1),
            ),
            score=0.97,
        )
        applied = await dream.apply_subsume(
            session,
            dream.SubsumeAction(
                pair=pair, verdict=dream.PairVerdict(verdict="subsumes", reason="r")
            ),
            cycle_id=cycle_id,
            outcome=dream.DreamOutcome(),
        )
        assert applied
        await session.commit()
    rows = await journal_rows(factory, project)
    return older, newer, int(rows[-1]["event_id"])


async def produce_associate(factory, project, *, cycle_id, prior_block=None,
                            sibling_block=None) -> tuple[UUID, UUID, int]:
    """One real associate action, optionally over a row a sibling pass owns.

    `prior_block` seeds this pass's own block so the action overwrites it;
    `sibling_block` seeds a *different* pass's block so the row exists and
    `created` comes back False with no near-duplicate block to restore — F4's
    arm, which the documented two-way inverse has no place for.
    """
    async with factory() as session:
        older = await seed_memory(
            session, project=project, content="dup a", created_at=NOW,
        )
        newer = await seed_memory(
            session, project=project, content="dup b",
            created_at=NOW + timedelta(hours=1),
        )
        await session.commit()
    if prior_block is not None or sibling_block is not None:
        async with factory() as session:
            if prior_block is not None:
                await edges.upsert_edge(
                    session, source_memory_id=newer, target_memory_id=older,
                    rel_type="RELATES_TO", project=project,
                    pass_key=journal.NEAR_DUPLICATE_PASS, block=prior_block,
                )
            if sibling_block is not None:
                await edges.upsert_edge(
                    session, source_memory_id=newer, target_memory_id=older,
                    rel_type="RELATES_TO", project=project,
                    pass_key="proximity", block=sibling_block,
                )
            await session.commit()
    async with factory() as session:
        pair = dream.PairCandidate(
            older=memory_row_of(older, project=project, content="dup a"),
            newer=memory_row_of(
                newer, project=project, content="dup b",
                created_at=NOW + timedelta(hours=1),
            ),
            score=0.99,
        )
        applied = await dream.apply_associate(
            session,
            dream.AssociateAction(
                pair=pair, verdict=dream.PairVerdict(verdict="duplicate", reason="r")
            ),
            cycle_id=cycle_id,
            outcome=dream.DreamOutcome(),
        )
        assert applied
        await session.commit()
    rows = await journal_rows(factory, project)
    return older, newer, int(rows[-1]["event_id"])


async def produce_refine(factory, project, *, cycle_id, summary="a refined summary",
                         tags=("t213-alpha",), prior_summary="the old summary",
                         prior_tags=("t213-original",),
                         metadata=None) -> tuple[UUID, int]:
    content = "the sweeper runs hourly"
    async with factory() as session:
        memory = await seed_memory(
            session, project=project, content=content, summary=prior_summary,
            metadata=metadata,
        )
        await session.commit()
    if prior_tags:
        async with factory() as session:
            await PostgresMemoryRepository(session).set_tags(memory, list(prior_tags))
            await session.commit()
    async with factory() as session:
        applied = await dream.apply_refine(
            session,
            dream.RefineAction(
                memory=memory_row_of(
                    memory, project=project, content=content,
                    summary=prior_summary, metadata=metadata, tags=prior_tags,
                ),
                verdict=dream.RefineVerdict(
                    summary=summary, tags=tuple(tags) if tags is not None else None
                ),
            ),
            cycle_id=cycle_id,
            outcome=dream.DreamOutcome(),
        )
        assert applied
        await session.commit()
    rows = await journal_rows(factory, project)
    return memory, int(rows[-1]["event_id"])


# ── Step 3: the digest ───────────────────────────────────────────────────


class TestDigest:
    async def test_one_cycle_groups_with_its_three_counts(self, committing, project):
        """T-DIG1."""
        cycle = str(new_id())
        await produce_subsume(committing, project, cycle_id=cycle)
        await produce_associate(committing, project, cycle_id=cycle)
        await produce_refine(committing, project, cycle_id=cycle)

        async with committing() as session:
            cycles, total = await digest.list_cycles(session, project=project)

        assert total == 1
        assert len(cycles) == 1
        assert cycles[0].cycle_id == cycle
        assert cycles[0].counts == {"subsume": 1, "associate": 1, "refine": 1}
        assert cycles[0].total == 3
        assert cycles[0].projects == [project]
        assert cycles[0].undone_count == 0

    async def test_two_cycles_on_one_night_stay_separate(self, committing, project):
        """T-DIG2. The grouping key is `payload.cycle_id`, not the calendar
        day: both of these are written seconds apart on the same date."""
        first, second = str(new_id()), str(new_id())
        await produce_subsume(committing, project, cycle_id=first)
        await produce_refine(committing, project, cycle_id=second)

        async with committing() as session:
            cycles, total = await digest.list_cycles(session, project=project)

        assert total == 2
        assert {cycle.cycle_id for cycle in cycles} == {first, second}
        assert all(cycle.total == 1 for cycle in cycles)

    async def test_actions_stay_in_journal_order(self, committing, project):
        """T-DIG3 — the inherited within-cycle ordering case.

        An associate against a memory, then a subsume retiring that same
        memory. That sequence is what happened, and the digest must render it
        in application order rather than regrouping by action kind.
        """
        cycle = str(new_id())
        older, newer, _ = await produce_associate(committing, project, cycle_id=cycle)
        async with committing() as session:
            pair = dream.PairCandidate(
                older=memory_row_of(older, project=project, content="dup a"),
                newer=memory_row_of(
                    newer, project=project, content="dup b",
                    created_at=NOW + timedelta(hours=1),
                ),
                score=0.99,
            )
            assert await dream.apply_subsume(
                session,
                dream.SubsumeAction(
                    pair=pair,
                    verdict=dream.PairVerdict(verdict="subsumes", reason="r"),
                ),
                cycle_id=cycle,
                outcome=dream.DreamOutcome(),
            )
            await session.commit()

        async with committing() as session:
            actions = await digest.read_cycle_actions(session, cycle)
        grouped = digest.group_by_object(actions)

        assert [view.action for view in actions] == ["associate", "subsume"]
        # Two objects: the associate journals against `newer`, the subsume
        # against `older`. Group order follows first-action time.
        assert [group.object_id for group in grouped] == [str(newer), str(older)]

    async def test_the_primitives_own_superseded_row_is_absent(
        self, committing, project
    ):
        """T-DIG4. `supersede()` journals its own `superseded` event beside the
        pass's `consolidated` one. Without the event_type predicate each
        subsume would appear twice, the second time in a shape carrying no
        before/after and therefore no inverse."""
        cycle = str(new_id())
        await produce_subsume(committing, project, cycle_id=cycle)

        assert len(await journal_rows(committing, project, "superseded")) == 1

        async with committing() as session:
            actions = await digest.read_cycle_actions(session, cycle)
        assert [view.action for view in actions] == ["subsume"]

    async def test_a_row_outside_the_window_is_absent(self, committing, project):
        """T-DIG5. The `created_at` bound is what prunes the partitioned read,
        so it has to be provably live rather than decorative."""
        cycle = str(new_id())
        await produce_subsume(committing, project, cycle_id=cycle)

        async with committing() as session:
            inside, _ = await digest.list_cycles(session, project=project)
            outside, outside_total = await digest.list_cycles(
                session,
                project=project,
                until=datetime.now(timezone.utc) - timedelta(days=1),
            )
        assert [cycle_summary.cycle_id for cycle_summary in inside] == [cycle]
        assert outside == [] and outside_total == 0

    async def test_the_detector_filter_excludes_a_foreign_producer(
        self, committing, project
    ):
        """T-DIG5's companion. A future producer emitting `consolidated` rows
        under its own detector must not appear in this digest wearing an action
        name no inverse exists for."""
        cycle = str(new_id())
        await produce_subsume(committing, project, cycle_id=cycle)
        async with committing() as session:
            await events_module.record_event(
                session,
                event_type=journal.EVENT_TYPE,
                object_type=journal.OBJECT_TYPE,
                object_id=new_id(),
                project=project,
                payload={
                    "action": "merge",
                    "detector": "some_other_pass",
                    "cycle_id": cycle,
                },
            )
            await session.commit()

        async with committing() as session:
            actions = await digest.read_cycle_actions(session, cycle)
            cycles, _ = await digest.list_cycles(session, project=project)
        assert [view.action for view in actions] == ["subsume"]
        assert cycles[0].total == 1

    async def test_the_refine_detail_names_the_fields_that_moved(
        self, committing, project
    ):
        """What T2.38 renders as "what changed" for a refine."""
        cycle = str(new_id())
        await produce_refine(committing, project, cycle_id=cycle)
        async with committing() as session:
            actions = await digest.read_cycle_actions(session, cycle)
        assert actions[0].detail == {"fields": ["summary", "tags"]}
        assert actions[0].before["summary"] == "the old summary"
        assert actions[0].after["summary"] == "a refined summary"


# ── Step 4: the three inverses ───────────────────────────────────────────


async def undo_ids(factory, *event_ids, actor="admin", now=None):
    """One batch through the door, committed. Mirrors what the HTTP route
    does, including the commit the primitive deliberately does not do."""
    async with factory() as session:
        batch = await undo.undo(
            session, event_ids=list(event_ids), actor=actor, now=now
        )
        await session.commit()
    return batch


class TestSubsumeInverse:
    async def test_status_and_pointer_come_back(self, committing, project):
        """T-SUB1. Asserted field by field, and the successor is asserted
        byte-identical because an inverse that "helpfully" tidied the other
        half would pass any assertion phrased as "no exception"."""
        cycle = str(new_id())
        older, newer, event_id = await produce_subsume(
            committing, project, cycle_id=cycle
        )
        before_newer = await memory_row(committing, newer)
        assert (await memory_row(committing, older))["status"] == "superseded"

        batch = await undo_ids(committing, event_id)

        row = await memory_row(committing, older)
        assert row["status"] == "active"
        assert row["superseded_by"] is None
        assert row["content"] == "old truth"
        assert row["summary"] is None
        assert await memory_row(committing, newer) == before_newer
        assert batch.undone[0].restored == ("status", "superseded_by")

    async def test_the_pointer_first_split_raises(self, committing, project):
        """T-SUB2. The provocation, not an assumption.

        `chk_superseded_has_pointer` is `status != 'superseded' OR
        superseded_by IS NOT NULL`, and it is evaluated once per row per
        statement, so clearing the pointer while the status still says
        superseded has no legal intermediate. This test fails the day the
        constraint is relaxed.
        """
        cycle = str(new_id())
        older, _, _ = await produce_subsume(committing, project, cycle_id=cycle)
        with pytest.raises(IntegrityError):
            async with committing() as session:
                await session.execute(
                    text(
                        "UPDATE memories SET superseded_by = NULL "
                        "WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": str(older)},
                )
                await session.commit()

    async def test_the_status_first_split_fails_silently_instead(
        self, committing, project
    ):
        """T-SUB2's other half, and the stronger argument for one statement.

        The CHECK is one-sided, so the *other* split order does not raise: it
        leaves an `active` memory still pointing at its successor, which no
        constraint objects to and nothing downstream would notice. The forward
        flip is the mirror image — there it is the status-first order that
        raises — so carrying the forward direction's reasoning into the inverse
        gets the failure mode exactly backwards. The one-statement restore is
        required because the alternative fails **silently**, not loudly.
        """
        cycle = str(new_id())
        older, newer, _ = await produce_subsume(committing, project, cycle_id=cycle)
        async with committing() as session:
            await session.execute(
                text(
                    "UPDATE memories SET status = 'active' "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": str(older)},
            )
            await session.commit()
        row = await memory_row(committing, older)
        assert row["status"] == "active" and row["superseded_by"] == str(newer)

    async def test_updated_at_moves_and_is_declared(self, committing, project):
        """T-SUB3. E1 asserted as a real exclusion rather than left unmentioned:
        the trigger fires on the inverse's own UPDATE and no honest undo can
        claim otherwise."""
        cycle = str(new_id())
        older, _, event_id = await produce_subsume(
            committing, project, cycle_id=cycle
        )
        before = (await memory_row(committing, older))["updated_at"]

        batch = await undo_ids(committing, event_id)

        assert (await memory_row(committing, older))["updated_at"] > before
        assert "updated_at" in batch.undone[0].not_restored


class TestAssociateInverse:
    async def test_an_exclusively_mine_row_is_deleted(self, committing, project):
        """T-ASC1. `created=True` with nothing else on the row: prior state was
        "no row", so the row goes."""
        cycle = str(new_id())
        older, newer, event_id = await produce_associate(
            committing, project, cycle_id=cycle
        )
        assert await edge_row(committing, newer, older, "RELATES_TO") is not None

        await undo_ids(committing, event_id)

        assert await edge_row(committing, newer, older, "RELATES_TO") is None

    async def test_a_prior_block_is_restored_beside_its_siblings(
        self, committing, project
    ):
        """T-ASC2. The F4/§9.2-item-7 guard from the undo side: a whole-object
        `SET properties = …` would restore the block and take the sibling pass
        with it."""
        cycle = str(new_id())
        prior = {
            "kind": "duplicate_candidate",
            "hygiene_state": "open",
            "score": 0.5,
            "verdict": "duplicate",
            "detected_at": "2026-07-01T00:00:00+00:00",
        }
        older, newer, event_id = await produce_associate(
            committing, project, cycle_id=cycle,
            prior_block=prior, sibling_block={"kind": "proximity", "score": 0.3},
        )

        await undo_ids(committing, event_id)

        edge = await edge_row(committing, newer, older, "RELATES_TO")
        assert edges.pass_block_of(edge, journal.NEAR_DUPLICATE_PASS) == prior
        assert edge["properties"]["dream"]["proximity"] == {
            "kind": "proximity", "score": 0.3
        }

    async def test_a_block_a_sibling_owned_first_is_removed_not_nulled(
        self, committing, project
    ):
        """T-ASC3 — F4's missing arm.

        A sibling pass owned the row first, so `created` is False and there was
        no near-duplicate block to restore. `jsonb_set(…, 'null')` would leave
        the key present holding JSON null, which `pass_block_of` reads as absent
        while the row carries a value the prior state never had. The assertion
        is on the key's absence, so that mutation fails.
        """
        cycle = str(new_id())
        older, newer, event_id = await produce_associate(
            committing, project, cycle_id=cycle,
            sibling_block={"kind": "proximity", "score": 0.3},
        )
        async with committing() as session:
            rows = await session.execute(
                text(
                    "SELECT payload FROM events WHERE id = CAST(:id AS bigint) "
                    "  AND created_at > CAST(:floor AS timestamptz)"
                ),
                {"id": event_id, "floor": NOW},
            )
            payload = rows.mappings().one()["payload"]
        assert payload["created"] is False and payload["before"]["edge"] is None

        await undo_ids(committing, event_id)

        edge = await edge_row(committing, newer, older, "RELATES_TO")
        assert edge is not None, "the sibling's row must survive"
        assert journal.NEAR_DUPLICATE_PASS not in edge["properties"]["dream"]
        assert edges.pass_block_of(edge, journal.NEAR_DUPLICATE_PASS) is None

    async def test_a_row_a_sibling_claimed_since_survives(
        self, committing, project
    ):
        """T-ASC4 — E5. `created=True`, but a sibling pass added its own block
        afterwards. Deleting unconditionally would destroy another actor's edge:
        the same whole-object hazard, arriving through the other door."""
        cycle = str(new_id())
        older, newer, event_id = await produce_associate(
            committing, project, cycle_id=cycle
        )
        async with committing() as session:
            await edges.upsert_edge(
                session, source_memory_id=newer, target_memory_id=older,
                rel_type="RELATES_TO", project=project,
                pass_key="proximity", block={"kind": "proximity", "score": 0.3},
            )
            await session.commit()

        batch = await undo_ids(committing, event_id)

        edge = await edge_row(committing, newer, older, "RELATES_TO")
        assert edge is not None
        assert edge["properties"]["dream"] == {
            "proximity": {"kind": "proximity", "score": 0.3}
        }
        assert "memory_relations_row" in batch.undone[0].not_restored

    async def test_a_human_triage_refuses_the_undo(self, committing, project):
        """T-ASC5 — D5's load-bearing test.

        A human moved `hygiene_state` off its derived default. That write is not
        a consolidation event, so an `events` watermark over the consolidated
        stream would not see it, would report this action still undoable, and
        the `created=True` arm would delete a row carrying the triage. The
        compare-and-swap sees it, because the live block no longer equals the
        journalled `after` block.
        """
        cycle = str(new_id())
        older, newer, event_id = await produce_associate(
            committing, project, cycle_id=cycle
        )
        async with committing() as session:
            await session.execute(
                text(
                    "UPDATE memory_relations "
                    "   SET properties = jsonb_set(properties, "
                    "       '{dream,near_duplicate,hygiene_state}', "
                    "       CAST('\"dismissed\"' AS jsonb), true) "
                    " WHERE source_memory_id = CAST(:source AS uuid) "
                    "   AND target_memory_id = CAST(:target AS uuid) "
                    "   AND rel_type = 'RELATES_TO'"
                ),
                {"source": str(newer), "target": str(older)},
            )
            await session.commit()
        before = await edge_row(committing, newer, older, "RELATES_TO")

        with pytest.raises(undo.UndoRefused) as refusal:
            await undo_ids(committing, event_id)

        assert [item.reason for item in refusal.value.blocked] == ["state_changed"]
        assert await edge_row(committing, newer, older, "RELATES_TO") == before


class TestRefineInverse:
    async def test_summary_and_tags_both_come_back(self, committing, project):
        """T-REF1."""
        cycle = str(new_id())
        memory, event_id = await produce_refine(committing, project, cycle_id=cycle)
        assert (await memory_row(committing, memory))["summary"] == "a refined summary"

        batch = await undo_ids(committing, event_id)

        row = await memory_row(committing, memory)
        assert row["summary"] == "the old summary"
        assert list(row["tag_names"]) == ["t213-original"]
        assert batch.undone[0].restored == ("summary", "tags")

    async def test_the_refine_marker_is_preserved(self, committing, project):
        """T-REF2 — E2, asserted on both halves.

        Restoring the marker from `before` would clear it on a first refine, and
        `needs_refine` keys on the marker alone: the next cycle would re-apply
        the refine and silently reverse the undo. Asserting only that the
        marker's value is unchanged could be finessed; asserting `needs_refine`
        is still False pins the behaviour that matters.
        """
        cycle = str(new_id())
        memory, event_id = await produce_refine(committing, project, cycle_id=cycle)
        after_action = (await memory_row(committing, memory))["metadata"]

        await undo_ids(committing, event_id)

        row = await memory_row(committing, memory)
        assert row["metadata"] == after_action
        assert journal.refine_marker_of(row["metadata"]) is not None
        assert not dream.needs_refine(
            memory_row_of(
                memory, project=project, content=row["content"],
                summary=row["summary"], metadata=row["metadata"],
            )
        )

    async def test_a_tags_only_refine_leaves_summary_alone(
        self, committing, project
    ):
        """T-REF3. `fields` is an exact record of what moved, so an inverse that
        always wrote `summary` would write a None over a live one."""
        cycle = str(new_id())
        memory, event_id = await produce_refine(
            committing, project, cycle_id=cycle, summary=None, tags=("t213-new",),
        )
        assert (await memory_row(committing, memory))["summary"] == "the old summary"

        batch = await undo_ids(committing, event_id)

        row = await memory_row(committing, memory)
        assert batch.undone[0].restored == ("tags",)
        assert row["summary"] == "the old summary"
        assert list(row["tag_names"]) == ["t213-original"]

    async def test_a_superset_of_the_journalled_tags_refuses(
        self, committing, project
    ):
        """T-REF4. Compared exactly, not as a subset: a human's added tag would
        otherwise be silently discarded by the undo."""
        cycle = str(new_id())
        memory, event_id = await produce_refine(committing, project, cycle_id=cycle)
        async with committing() as session:
            await PostgresMemoryRepository(session).set_tags(
                memory, ["t213-alpha", "t213-added-by-a-human"]
            )
            await session.commit()

        with pytest.raises(undo.UndoRefused) as refusal:
            await undo_ids(committing, event_id)

        assert [item.reason for item in refusal.value.blocked] == ["state_changed"]
        assert sorted((await memory_row(committing, memory))["tag_names"]) == [
            "t213-added-by-a-human", "t213-alpha"
        ]


class TestExclusions:
    async def test_updated_at_is_named_on_both_actions_that_move_it(
        self, committing, project
    ):
        """T-EXC1."""
        cycle = str(new_id())
        _, _, subsume_id = await produce_subsume(committing, project, cycle_id=cycle)
        _, refine_id = await produce_refine(committing, project, cycle_id=cycle)

        for event_id in (subsume_id, refine_id):
            batch = await undo_ids(committing, event_id)
            assert "updated_at" in batch.undone[0].not_restored

    async def test_the_action_row_survives_its_own_undo(self, committing, project):
        """T-EXC2 — E3. `events` is append-only: the undo adds a row, it removes
        nothing, and the delete that would "clean up" raises."""
        cycle = str(new_id())
        _, _, event_id = await produce_subsume(committing, project, cycle_id=cycle)
        before = await journal_rows(committing, project)

        await undo_ids(committing, event_id)

        assert await journal_rows(committing, project) == before
        with pytest.raises(Exception):
            async with committing() as session:
                await session.execute(
                    text("DELETE FROM events WHERE id = CAST(:id AS bigint)"),
                    {"id": event_id},
                )
                await session.commit()

    def test_the_exclusion_table_matches_the_code(self):
        """T-EXC3. Documentation and code drift silently; this fails the build
        when they do. The plan's D2 table is the other half."""
        assert {item.key for item in undo.EXCLUSIONS} == {
            "E1", "E2", "E3", "E4", "E5", "E6",
        }
        assert len(undo.EXCLUSIONS_BY_FIELD) == len(undo.EXCLUSIONS)
        for item in undo.EXCLUSIONS:
            assert item.actions <= journal.ACTIONS
            assert item.kind in (undo.NOT_RESTORABLE, undo.BY_DESIGN)

    async def test_every_reported_exclusion_is_in_the_table(
        self, committing, project
    ):
        """T-EXC3's live half: a result may not name an exclusion the table has
        never heard of, and each one must be declared for the action reporting
        it."""
        cycle = str(new_id())
        _, _, subsume_id = await produce_subsume(committing, project, cycle_id=cycle)
        _, _, associate_id = await produce_associate(
            committing, project, cycle_id=cycle
        )
        _, refine_id = await produce_refine(committing, project, cycle_id=cycle)

        for event_id in (subsume_id, associate_id, refine_id):
            batch = await undo_ids(committing, event_id)
            action = batch.undone[0]
            for field_name in action.not_restored:
                entry = undo.EXCLUSIONS_BY_FIELD[field_name]
                assert action.action in entry.actions


# ── Step 5: atomicity, and the window ────────────────────────────────────

# Layer 2's forbidden field names: any one of these on a result type gives a
# caller somewhere to *report* a per-item outcome, which is the first move
# towards producing one.
FORBIDDEN_RESULT_FIELDS = {"applied", "skipped", "failed", "error", "status"}

# Layer 3's forbidden shapes. `try`/`except` is the obvious one; the other two
# are the shapes that swallow a failure without being a `try` statement at all,
# and a scan looking only for `ast.Try` sails straight past both.
FORBIDDEN_CALLS = {"begin_nested", "commit", "suppress"}


def _undo_tree() -> ast.Module:
    return ast.parse(
        (BACKEND / "app" / "services" / "dream_undo.py").read_text(),
        filename="app/services/dream_undo.py",
    )


def _scan_undo_module(tree: ast.Module) -> list[str]:
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Try, ast.TryStar)):
            offenders.append(
                f"line {node.lineno}: a try statement — a swallowed failure "
                "lets a batch continue past a broken action"
            )
        elif isinstance(node, ast.Call):
            name = (
                node.func.attr if isinstance(node.func, ast.Attribute)
                else node.func.id if isinstance(node.func, ast.Name)
                else None
            )
            if name in FORBIDDEN_CALLS:
                offenders.append(f"line {node.lineno}: {name}()")
            for keyword in node.keywords:
                if keyword.arg == "return_exceptions":
                    offenders.append(
                        f"line {node.lineno}: return_exceptions= turns a "
                        "failure into a value the batch can walk past"
                    )
        elif isinstance(node, ast.ClassDef) and node.name in (
            "UndoneAction", "UndoBatch"
        ):
            for statement in node.body:
                target = (
                    statement.target if isinstance(statement, ast.AnnAssign)
                    else None
                )
                if isinstance(target, ast.Name) and target.id in (
                    FORBIDDEN_RESULT_FIELDS
                ):
                    offenders.append(
                        f"line {statement.lineno}: {node.name}.{target.id} "
                        "can carry a per-item outcome"
                    )
    return offenders


class TestAtomicity:
    def test_the_module_cannot_express_a_partial_undo(self):
        """T-ATOM1.

        *Not representable* is stronger than *not produced*, so the argument
        has to be about what the code can express. The five shapes scanned for
        are the five ways a partial outcome gets produced or reported: a
        savepoint or a commit that lets half a batch survive, a `try` that
        swallows the failure, `contextlib.suppress` and
        `gather(return_exceptions=True)` which swallow one without being a
        `try` at all, and a result field with somewhere to put the news.
        """
        assert _scan_undo_module(_undo_tree()) == []

    def test_the_scan_catches_each_shape(self):
        """T-ATOM1's negative control. A scan that flags nothing on a module
        deliberately full of offences is a scan that has stopped working — five
        decorative guards in this epic read exactly like the one above."""
        offending = ast.parse(
            "from dataclasses import dataclass\n"
            "import asyncio, contextlib\n"
            "@dataclass\n"
            "class UndoneAction:\n"
            "    applied: bool\n"
            "async def go(session, inverses):\n"
            "    for item in inverses:\n"
            "        try:\n"
            "            async with session.begin_nested():\n"
            "                await item()\n"
            "        except Exception:\n"
            "            continue\n"
            "    with contextlib.suppress(Exception):\n"
            "        await session.commit()\n"
            "    await asyncio.gather(*inverses, return_exceptions=True)\n"
        )
        offenders = _scan_undo_module(offending)
        assert len(offenders) >= 6, offenders
        joined = "\n".join(offenders)
        for fragment in (
            "try statement", "begin_nested", "commit", "suppress",
            "return_exceptions", "UndoneAction.applied",
        ):
            assert fragment in joined

    def test_there_is_no_second_entry_point(self):
        """T-ATOM4's structural half. A per-action undo is a batch of one
        through the same function; a sibling single-action coroutine is exactly
        how the two paths start to diverge."""
        appliers = {
            node.name
            for node in ast.walk(_undo_tree())
            if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
            and any(
                isinstance(inner, ast.Subscript)
                and isinstance(inner.value, ast.Name)
                and inner.value.id == "_INVERSES"
                for inner in ast.walk(node)
            )
        }
        assert appliers == {"undo"}, appliers

    async def test_a_middle_failure_leaves_nothing_behind(
        self, committing, project, monkeypatch
    ):
        """T-ATOM2. Asserted field by field after the caller rolls back, not by
        the absence of an exception."""
        cycle = str(new_id())
        older, _, subsume_id = await produce_subsume(
            committing, project, cycle_id=cycle
        )
        src, tgt, associate_id = await produce_associate(
            committing, project, cycle_id=cycle
        )
        memory, refine_id = await produce_refine(
            committing, project, cycle_id=cycle
        )
        before = {
            "subsume": await memory_row(committing, older),
            "edge": await edge_row(committing, tgt, src, "RELATES_TO"),
            "refine": await memory_row(committing, memory),
        }

        async def explode(*_args, **_kwargs):
            raise RuntimeError("the second inverse failed")

        monkeypatch.setitem(undo._INVERSES, journal.ACTION_ASSOCIATE, explode)

        with pytest.raises(RuntimeError):
            async with committing() as session:
                await undo.undo(
                    session,
                    event_ids=[subsume_id, associate_id, refine_id],
                    actor="admin",
                )
                await session.commit()

        assert await memory_row(committing, older) == before["subsume"]
        assert await edge_row(committing, tgt, src, "RELATES_TO") == before["edge"]
        assert await memory_row(committing, memory) == before["refine"]

    async def test_the_caller_rollback_seam_is_real(
        self, committing, project, monkeypatch
    ):
        """T-ATOM6 — the sharp edge D6 hands T2.23, documented rather than
        hidden.

        Between the raise and the rollback the session really does hold the
        first inverse's restore. This module owns no savepoint by construction
        — the scan above forbids it — so it cannot self-heal, and "partial undo
        is not representable" holds *under caller rollback*. A consumer that
        catches broadly and carries on with the same session commits half an
        undo. Deleting this assertion turns that contract into folklore.
        """
        cycle = str(new_id())
        older, _, subsume_id = await produce_subsume(
            committing, project, cycle_id=cycle
        )
        memory, refine_id = await produce_refine(
            committing, project, cycle_id=cycle
        )

        async def explode(*_args, **_kwargs):
            raise RuntimeError("the second inverse failed")

        monkeypatch.setitem(undo._INVERSES, journal.ACTION_SUBSUME, explode)

        async with committing() as session:
            with pytest.raises(RuntimeError):
                # LIFO: the refine is applied first, then the subsume raises.
                await undo.undo(
                    session, event_ids=[subsume_id, refine_id], actor="admin"
                )
            held = (
                await session.execute(
                    text(
                        "SELECT summary FROM memories WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": str(memory)},
                )
            ).scalar_one()
            assert held == "the old summary", (
                "the restore is in the session before the rollback; if this "
                "ever stops holding, the caller obligation D6 states has "
                "quietly stopped being load-bearing"
            )
            await session.rollback()

        assert (await memory_row(committing, memory))["summary"] == "a refined summary"
        assert (await memory_row(committing, older))["status"] == "superseded"

    async def test_a_refusal_leaves_the_session_clean(self, committing, project):
        """T-ATOM7. The property that makes `UndoRefused` the one raise a caller
        may swallow: validation completed before any write, so no rollback is
        needed and the session is still usable."""
        cycle = str(new_id())
        older, _, subsume_id = await produce_subsume(
            committing, project, cycle_id=cycle
        )
        memory, refine_id = await produce_refine(
            committing, project, cycle_id=cycle
        )
        async with committing() as session:
            await PostgresMemoryRepository(session).set_tags(
                memory, ["t213-alpha", "t213-added-by-a-human"]
            )
            await session.commit()

        async with committing() as session:
            with pytest.raises(undo.UndoRefused) as refusal:
                await undo.undo(
                    session, event_ids=[subsume_id, refine_id], actor="admin"
                )
            # No rollback, and the session still works.
            still_usable = (
                await session.execute(text("SELECT 1"))
            ).scalar_one()
            assert still_usable == 1
            await session.commit()

        assert [item.event_id for item in refusal.value.blocked] == [refine_id]
        assert (await memory_row(committing, older))["status"] == "superseded"

    async def test_one_blocked_action_writes_nothing(self, committing, project):
        """T-ATOM3. Proved by asserting the *unblocked* action is untouched:
        validation inside the apply loop would land it before the second was
        refused."""
        cycle = str(new_id())
        older, _, subsume_id = await produce_subsume(
            committing, project, cycle_id=cycle
        )
        memory, refine_id = await produce_refine(
            committing, project, cycle_id=cycle
        )
        async with committing() as session:
            await session.execute(
                text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"),
                {"id": str(memory)},
            )
            await session.commit()

        with pytest.raises(undo.UndoRefused):
            await undo_ids(committing, subsume_id, refine_id)

        assert (await memory_row(committing, older))["status"] == "superseded"

    async def test_a_short_result_is_unreturnable(
        self, committing, project, monkeypatch
    ):
        """T-ATOM8. A tuple shorter than the request carries no forbidden field
        and is invisible to the scan, so the representational claim needs this
        one line of code and this one test to close."""
        cycle = str(new_id())
        _, _, subsume_id = await produce_subsume(committing, project, cycle_id=cycle)

        async def restores_nothing(*_args, **_kwargs):
            return None

        monkeypatch.setitem(undo._INVERSES, journal.ACTION_SUBSUME, restores_nothing)
        with pytest.raises(undo.UndoIncomplete):
            await undo_ids(committing, subsume_id)

    async def test_a_batch_returns_one_entry_per_named_action(
        self, committing, project
    ):
        """T-ATOM4/T-ATOM8's positive half, and the batch-of-one equivalence:
        the same action produces the same `UndoneAction` alone or in company,
        because there is only one code path that could produce it."""
        cycle = str(new_id())
        _, _, subsume_id = await produce_subsume(committing, project, cycle_id=cycle)
        _, refine_id = await produce_refine(committing, project, cycle_id=cycle)

        batch = await undo_ids(committing, subsume_id, refine_id)
        assert len(batch.undone) == 2
        assert [item.event_id for item in batch.undone] == [subsume_id, refine_id]

        other = str(new_id())
        _, _, lone_id = await produce_subsume(committing, project, cycle_id=other)
        lone = await undo_ids(committing, lone_id)
        assert lone.undone[0].restored == batch.undone[0].restored
        assert lone.undone[0].not_restored == batch.undone[0].not_restored
        assert lone.undone[0].action == batch.undone[0].action

    def test_the_lock_order_is_deterministic(self):
        """T-ATOM5. Asserted on the recorded order rather than on the absence of
        a deadlock, which is untestable."""
        ids = [str(new_id()) for _ in range(4)]
        triples = [("b", "a", "RELATES_TO"), ("a", "b", "ELABORATES")]

        def actions(order):
            built = []
            for index in order:
                if index < len(ids):
                    built.append(
                        undo.ResolvedAction(
                            event_id=index, created_at=NOW,
                            object_id=ids[index], project="p",
                            payload={"action": "subsume"},
                        )
                    )
                else:
                    source, target, rel_type = triples[index - len(ids)]
                    built.append(
                        undo.ResolvedAction(
                            event_id=index, created_at=NOW,
                            object_id=source, project="p",
                            payload={
                                "action": "associate",
                                "after": {"edge": {
                                    "source": source, "target": target,
                                    "rel_type": rel_type,
                                }},
                            },
                        )
                    )
            return built

        forward = undo.lock_plan(actions(range(6)))
        shuffled = undo.lock_plan(actions([4, 1, 5, 0, 3, 2]))
        assert forward == shuffled
        assert [kind for kind, _ in forward] == ["memory"] * 4 + ["edge"] * 2
        assert [key[0] for kind, key in forward if kind == "memory"] == sorted(ids)


class TestUndoWindow:
    async def test_an_action_past_its_retention_refuses(self, committing, project):
        """T-UND2."""
        cycle = str(new_id())
        older, _, event_id = await produce_subsume(
            committing, project, cycle_id=cycle
        )
        later = datetime.now(timezone.utc) + timedelta(
            days=undo.DEFAULT_RETENTION_DAYS + 1
        )

        with pytest.raises(undo.UndoRefused) as refusal:
            await undo_ids(committing, event_id, now=later)

        assert [item.reason for item in refusal.value.blocked] == [
            "retention_elapsed"
        ]
        assert (await memory_row(committing, older))["status"] == "superseded"

    async def test_a_deleted_memory_reports_object_missing(
        self, committing, project
    ):
        """T-UND3. Collapsing this into `state_changed` tells an operator
        investigating a vanished row that the state moved."""
        cycle = str(new_id())
        memory, event_id = await produce_refine(committing, project, cycle_id=cycle)
        async with committing() as session:
            await session.execute(
                text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"),
                {"id": str(memory)},
            )
            await session.commit()

        with pytest.raises(undo.UndoRefused) as refusal:
            await undo_ids(committing, event_id)

        assert [item.reason for item in refusal.value.blocked] == ["object_missing"]

    async def test_a_demoted_dependent_reports_state_changed(
        self, committing, project
    ):
        """T-UND4. Deleting the successor demotes the older row to
        `deprecated`/NULL — the FK is ON DELETE SET NULL, so the demotion is
        mandatory — and the compare-and-swap must see it. Comparing only
        `status` would pass a `superseded_by` drift unseen, which is why both
        halves are in the predicate.
        """
        from app.services.supersession import demote_dependents

        cycle = str(new_id())
        older, newer, event_id = await produce_subsume(
            committing, project, cycle_id=cycle
        )
        async with committing() as session:
            await demote_dependents(session, [newer])
            await session.execute(
                text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"),
                {"id": str(newer)},
            )
            await session.commit()
        row = await memory_row(committing, older)
        assert row["status"] == "deprecated" and row["superseded_by"] is None

        with pytest.raises(undo.UndoRefused) as refusal:
            await undo_ids(committing, event_id)

        assert [item.reason for item in refusal.value.blocked] == ["state_changed"]

    def test_the_reasons_have_a_fixed_precedence(self):
        """T-UND5, on the pure predicate. An action that is both already undone
        and out of window reports `already_undone`, because that is the fact an
        operator needs first."""
        action = undo.ResolvedAction(
            event_id=1,
            created_at=datetime.now(timezone.utc) - timedelta(days=400),
            object_id=str(new_id()),
            project="p",
            payload={"action": "subsume", "after": {"status": "superseded"}},
        )
        common = {
            "now": datetime.now(timezone.utc),
            "retention": timedelta(days=undo.DEFAULT_RETENTION_DAYS),
        }
        gone = undo.LiveState(exists=False)
        assert undo.blocking_reason(
            action, live=gone, already_undone=True, **common
        ) == "already_undone"
        assert undo.blocking_reason(
            action, live=gone, already_undone=False, **common
        ) == "retention_elapsed"
        assert undo.blocking_reason(
            action, live=gone, already_undone=False,
            now=common["now"], retention=timedelta(days=500),
        ) == "object_missing"
        assert undo.blocking_reason(
            action,
            live=undo.LiveState(exists=True, memory={"status": "active"}),
            already_undone=False,
            now=common["now"], retention=timedelta(days=500),
        ) == "state_changed"
        assert undo.BLOCKING_REASONS == (
            "already_undone", "retention_elapsed", "object_missing",
            "state_changed",
        )

    async def test_an_unknown_event_id_is_refused_not_invented(
        self, committing, project
    ):
        """An id naming no dream action refuses before any write, carrying
        exactly `UndoRefused`'s guarantee — which is why it is a subclass."""
        with pytest.raises(undo.UndoActionNotFound) as refusal:
            await undo_ids(committing, 2 ** 40)
        assert isinstance(refusal.value, undo.UndoRefused)
        assert refusal.value.missing_event_ids == (2 ** 40,)

    async def test_the_digest_and_the_door_share_one_predicate(
        self, committing, project, monkeypatch
    ):
        """T-UND6, proved behaviourally rather than by reading two call sites:
        replacing the door's predicate changes the digest's answer, so a
        duplicated copy would fail this test."""
        cycle = str(new_id())
        await produce_subsume(committing, project, cycle_id=cycle)

        async with committing() as session:
            actions = await digest.read_cycle_actions(session, cycle)
            honest = await digest.annotate_undoability(session, actions)
        assert [view.undoable for view in honest] == [True]

        monkeypatch.setattr(
            undo, "blocking_reason", lambda *a, **k: "a_sentinel_reason"
        )
        async with committing() as session:
            actions = await digest.read_cycle_actions(session, cycle)
            annotated = await digest.annotate_undoability(session, actions)
        assert [view.undo_blocked_reason for view in annotated] == [
            "a_sentinel_reason"
        ]

    async def test_a_malformed_retention_row_degrades_to_the_default(
        self, committing
    ):
        """T-API6's service half. Unreadable bookkeeping must not take the door
        down; the tolerant-read discipline `index_debt.normalize` established."""
        async with committing() as session:
            await session.execute(
                text(
                    "INSERT INTO config (key, value) VALUES "
                    "(CAST(:key AS text), CAST(:value AS jsonb)) "
                    "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
                ),
                {"key": undo.RETENTION_CONFIG_KEY, "value": json.dumps("nonsense")},
            )
            await session.commit()
        async with committing() as session:
            assert await undo.read_retention(session) == timedelta(
                days=undo.DEFAULT_RETENTION_DAYS
            )
        async with committing() as session:
            await session.execute(
                text(
                    "UPDATE config SET value = CAST(:value AS jsonb) "
                    "WHERE key = CAST(:key AS text)"
                ),
                {"key": undo.RETENTION_CONFIG_KEY, "value": json.dumps({"days": 3})},
            )
            await session.commit()
        async with committing() as session:
            assert await undo.read_retention(session) == timedelta(days=3)


# ── Step 6: the suppression tombstone ────────────────────────────────────


async def run_one_cycle(factory, *, verdict="subsumes"):
    stub = StubLLM(
        pair_verdict=json.dumps({"verdict": verdict, "reason": "r"}), refine=None
    )
    return await dream.run_memory_dream(factory, lambda: stub, refine_batch=0)


async def build_dreamable_pair(factory, project):
    """Two near-identical memories with vectors, so a real cycle nominates
    them. The whole ruling is about what the *next cycle* does, so the test
    that pins it has to run one."""
    async with factory() as session:
        await seed_partition(session)
        older = await seed_memory(
            session, project=project, content="the api listens on port 8000",
            created_at=NOW,
        )
        newer = await seed_memory(
            session, project=project,
            content="the api listens on port 8000 with keepalive",
            created_at=NOW + timedelta(hours=1),
        )
        await put_vector(session, older, [1.0, 0.0, 0.0, 0.0])
        await put_vector(session, newer, [1.0, 0.0, 0.0, 0.0])
        await session.commit()
    return older, newer


class TestSubsumeTombstone:
    async def test_an_undone_subsumption_is_not_re_applied(
        self, committing, project
    ):
        """T-TOMB1 — the ruling's own test.

        Restoring the older memory to `active` puts the pair back exactly as
        the detector found it, and the judge is seeded on both contents in
        fixed order: re-application is not merely likely, it is deterministic.
        Without the read in `generate_pairs` the second cycle subsumes again
        and the human's undo is silently reversed, every night, forever.
        """
        older, newer = await build_dreamable_pair(committing, project)
        first = await run_one_cycle(committing)
        assert first.subsumed == 1

        rows = await journal_rows(committing, project)
        event_id = int(
            [row for row in rows if row["payload"].get("action") == "subsume"][-1][
                "event_id"
            ]
        )
        await undo_ids(committing, event_id)
        assert (await memory_row(committing, older))["status"] == "active"

        async with committing() as session:
            await session.execute(
                text("DELETE FROM config WHERE key = 'memory_dream_state'")
            )
            await session.commit()
        second = await run_one_cycle(committing)

        assert second.pairs_suppressed_by_undo == 1
        assert second.subsumed == 0
        assert (await memory_row(committing, older))["status"] == "active"

    @pytest.mark.parametrize(
        "metadata",
        [None, {}, {"x": 1}, {"dream": {"refine": {"content_sha": "abc"}}}],
        ids=["null", "empty", "other-key", "dream-key-present"],
    )
    async def test_the_tombstone_lands_in_every_metadata_shape(
        self, committing, project, metadata
    ):
        """T-TOMB2. Four shapes, because the trap is shape-dependent.

        `create_if_missing` creates only the *final* path element, so a
        two-level `jsonb_set` on a three-element path drops the write. The
        fourth case is the one a reader gets wrong: it fails **even on a row
        that already carries a `dream` key**, because `undone_subsume` beneath
        it does not exist — so a test written only against a previously-refined
        memory would not catch the collapse either.
        """
        cycle = str(new_id())
        async with committing() as session:
            older = await seed_memory(
                session, project=project, content="old truth",
                created_at=NOW, metadata=metadata,
            )
            newer = await seed_memory(
                session, project=project, content="new truth",
                created_at=NOW + timedelta(hours=1),
            )
            await session.commit()
        async with committing() as session:
            assert await dream.apply_subsume(
                session,
                dream.SubsumeAction(
                    pair=dream.PairCandidate(
                        older=memory_row_of(
                            older, project=project, content="old truth",
                            metadata=metadata,
                        ),
                        newer=memory_row_of(
                            newer, project=project, content="new truth",
                            created_at=NOW + timedelta(hours=1),
                        ),
                        score=0.97,
                    ),
                    verdict=dream.PairVerdict(verdict="subsumes", reason="r"),
                ),
                cycle_id=cycle,
                outcome=dream.DreamOutcome(),
            )
            await session.commit()
        event_id = int((await journal_rows(committing, project))[-1]["event_id"])

        await undo_ids(committing, event_id)

        row = await memory_row(committing, older)
        tombstone = journal.subsume_tombstone_of(row["metadata"], str(newer))
        assert tombstone is not None, (
            f"the tombstone was dropped for metadata={metadata!r}"
        )
        assert tombstone["content_sha"] == journal.content_sha("old truth")
        assert tombstone["counterpart_content_sha"] == journal.content_sha(
            "new truth"
        )
        # The pre-existing metadata survives beside it.
        if metadata:
            for key, value in metadata.items():
                if key != "dream":
                    assert row["metadata"][key] == value
        if metadata and "dream" in metadata:
            assert row["metadata"]["dream"]["refine"] == metadata["dream"]["refine"]

    async def test_the_counterpart_sha_is_the_newer_memorys(
        self, committing, project
    ):
        """T-TOMB6. Writing the older's sha into both fields would make T-TOMB4
        pass for the older-side edit and silently stop the newer-side edit from
        ever lapsing the tombstone, so the two tests together pin both the
        field's source and its purpose."""
        cycle = str(new_id())
        older, newer, event_id = await produce_subsume(
            committing, project, cycle_id=cycle,
        )
        await undo_ids(committing, event_id)
        tombstone = journal.subsume_tombstone_of(
            (await memory_row(committing, older))["metadata"], str(newer)
        )
        assert tombstone["content_sha"] != tombstone["counterpart_content_sha"]
        assert tombstone["counterpart_content_sha"] == journal.content_sha(
            "new truth"
        )

    async def test_a_failed_restore_leaves_no_tombstone(self, committing, project):
        """T-TOMB3. The tombstone rides the same statement as the status
        restore, so it can never record an undo that did not land. Provoked by
        making that one statement fail on the FK."""
        cycle = str(new_id())
        older, newer, event_id = await produce_subsume(
            committing, project, cycle_id=cycle,
        )
        async with committing() as session:
            action = await undo.resolve(
                session, [event_id],
                now=datetime.now(timezone.utc),
                retention=timedelta(days=undo.DEFAULT_RETENTION_DAYS),
            )
            # A superseded_by pointing at a memory that does not exist: the FK
            # rejects the one statement, so neither half of it lands.
            action[0].payload["before"]["superseded_by"] = str(new_id())
            live = await undo._read_live(
                session, undo.lock_plan(action), lock=True
            )
            with pytest.raises(IntegrityError):
                await undo._invert_subsume(
                    session, action[0], live[undo.live_key(action[0])],
                    undo_batch_id=str(new_id()),
                )
            await session.rollback()

        row = await memory_row(committing, older)
        assert row["status"] == "superseded"
        assert journal.subsume_tombstone_of(row["metadata"], str(newer)) is None

    async def test_editing_either_content_lapses_the_tombstone(
        self, committing, project
    ):
        """T-TOMB4. The human's judgement was about these two texts; once
        either moves the judgement is stale and dreaming may re-ask. Keying on
        the older's sha alone would leave a newer-side edit suppressed forever.
        """
        older, newer = await build_dreamable_pair(committing, project)
        await run_one_cycle(committing)
        rows = await journal_rows(committing, project)
        event_id = int(
            [row for row in rows if row["payload"].get("action") == "subsume"][-1][
                "event_id"
            ]
        )
        await undo_ids(committing, event_id)

        async with committing() as session:
            await session.execute(
                text(
                    "UPDATE memories SET content = :content "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": str(newer), "content": "the api now listens on port 9000"},
            )
            await session.execute(
                text("DELETE FROM config WHERE key = 'memory_dream_state'")
            )
            await session.commit()

        second = await run_one_cycle(committing)
        assert second.pairs_suppressed_by_undo == 0
        assert second.subsumed == 1

    async def test_the_tombstone_never_reaches_the_lifecycle(
        self, committing, project
    ):
        """T-TOMB5 — the Tier-2/Tier-3 line, asserted rather than argued.

        A nomination filter changes which pairs the nightly pass proposes. A
        lifecycle mechanism would change what makes a supersession fire. Wiring
        the read into `supersede()` crosses that line, and this test is what
        makes the crossing audible.
        """
        from app.services.supersede import supersede

        cycle = str(new_id())
        older, newer, event_id = await produce_subsume(
            committing, project, cycle_id=cycle,
        )
        await undo_ids(committing, event_id)
        assert journal.subsume_tombstone_of(
            (await memory_row(committing, older))["metadata"], str(newer)
        ) is not None

        async with committing() as session:
            result = await supersede(
                session, memory_id=str(older), superseded_by=str(newer),
                reason="a_direct_caller",
            )
            await session.commit()

        assert result.applied, (
            "the primitive consulted the tombstone; that is a lifecycle "
            "change, which is Tier 3 and not this task's to make"
        )
        assert (await memory_row(committing, older))["status"] == "superseded"

    async def test_a_metadata_patch_clears_both_dream_markers(
        self, committing, project, client, auth_headers, session
    ):
        """T-TOMB7 — the blunter lapse path, **recorded rather than defended
        against**.

        `MemoryUpdate.metadata` is wire-editable (the door is a PUT, not the
        PATCH the plan named) and the repository replaces
        `metadata_` wholesale rather than merging, so one PATCH clears every
        subsystem's marker beneath `dream` at once. Both current cases fail
        open — a cleared tombstone re-proposes the pair, a cleared refine
        marker re-refines — so this is a bound to know, not a bug to route
        around from this lane. Asserting the loss is what makes the seam a test
        the third marker's author meets rather than a surprise.
        """
        memory_id = new_id()
        await session.execute(
            _INSERT_MEMORY,
            {
                "id": str(memory_id),
                "content": "a memory carrying two dream markers",
                "project": project,
                "status": "active",
                "created_at": NOW,
                "summary": None,
                "metadata": json.dumps(
                    {
                        "dream": {
                            "refine": {"content_sha": "abc"},
                            "undone_subsume": {"some-counterpart": {"at": "now"}},
                        },
                        "kept": 1,
                    }
                ),
            },
        )
        await session.flush()

        response = await client.put(
            f"/api/v1/memories/{memory_id}",
            json={"metadata": {"kept": 2}},
            headers=auth_headers,
        )
        assert response.status_code == 200

        stored = (
            await session.execute(
                text(
                    "SELECT metadata FROM memories WHERE id = CAST(:id AS uuid)"
                ),
                {"id": str(memory_id)},
            )
        ).scalar_one()
        assert stored == {"kept": 2}
        assert journal.refine_marker_of(stored) is None
        assert journal.subsume_tombstone_of(stored, "some-counterpart") is None


# ── Step 7: the journal ──────────────────────────────────────────────────


class TestUndoJournal:
    async def test_one_row_per_undone_action(self, committing, project):
        """T-JRN1. Per item, never per batch — matching the producer's own rule
        and T2.23's Done-when. The batch stays visible as one act through
        `undo_batch_id`."""
        cycle = str(new_id())
        older, _, subsume_id = await produce_subsume(
            committing, project, cycle_id=cycle
        )
        memory, refine_id = await produce_refine(
            committing, project, cycle_id=cycle
        )

        batch = await undo_ids(committing, subsume_id, refine_id, actor="curator")

        rows = await journal_rows(committing, project, journal.UNDONE_EVENT_TYPE)
        assert len(rows) == 2
        assert {row["object_id"] for row in rows} == {str(older), str(memory)}
        assert {row["actor"] for row in rows} == {"curator"}
        assert {row["payload"]["undoes_event_id"] for row in rows} == {
            subsume_id, refine_id
        }
        assert {row["payload"]["undo_batch_id"] for row in rows} == {
            batch.undo_batch_id
        }
        assert {row["payload"]["cycle_id"] for row in rows} == {cycle}

    async def test_the_payload_is_in_the_undos_own_frame(self, committing, project):
        """T-JRN2. Written the other way round the journal reads plausibly and
        is exactly backwards — the sort of thing only ever noticed years
        later."""
        cycle = str(new_id())
        older, newer, event_id = await produce_subsume(
            committing, project, cycle_id=cycle
        )
        action = [
            row for row in await journal_rows(committing, project)
            if row["payload"].get("action") == "subsume"
        ][-1]["payload"]

        batch = await undo_ids(committing, event_id)

        undone = (
            await journal_rows(committing, project, journal.UNDONE_EVENT_TYPE)
        )[0]["payload"]
        assert undone["before"] == action["after"]
        assert undone["after"] == action["before"]
        assert undone["before"]["status"] == "superseded"
        assert undone["after"]["status"] == "active"
        assert undone["restored"] == list(batch.undone[0].restored)
        assert undone["not_restored"] == list(batch.undone[0].not_restored)

    async def test_an_unjournallable_undo_does_not_land(
        self, committing, project, monkeypatch
    ):
        """T-JRN3 — clause 3, proved non-vacuously.

        Asserted on the **restored state being absent**, not on the row being
        absent: the latter passes with the readback deleted. `record_event`
        degrades loudly and never raises, so without the readback an undo whose
        journal silently failed would commit — which is precisely the erasure
        the clause forbids.
        """
        cycle = str(new_id())
        older, _, event_id = await produce_subsume(
            committing, project, cycle_id=cycle
        )

        async def swallow(*_args, **_kwargs):
            return None

        monkeypatch.setattr(undo, "record_event", swallow)

        with pytest.raises(undo.UndoNotJournalled):
            async with committing() as session:
                await undo.undo(session, event_ids=[event_id], actor="admin")
                await session.commit()

        assert (await memory_row(committing, older))["status"] == "superseded"
        assert await journal_rows(
            committing, project, journal.UNDONE_EVENT_TYPE
        ) == []

    async def test_the_batch_id_groups_one_batch_and_only_one(
        self, committing, project
    ):
        """T-JRN4."""
        cycle = str(new_id())
        _, _, first_id = await produce_subsume(committing, project, cycle_id=cycle)
        _, second_id = await produce_refine(committing, project, cycle_id=cycle)
        _, _, third_id = await produce_associate(
            committing, project, cycle_id=cycle
        )

        first = await undo_ids(committing, first_id, second_id)
        second = await undo_ids(committing, third_id)

        assert first.undo_batch_id != second.undo_batch_id
        rows = await journal_rows(committing, project, journal.UNDONE_EVENT_TYPE)
        grouped: dict[str, int] = {}
        for row in rows:
            key = row["payload"]["undo_batch_id"]
            grouped[key] = grouped.get(key, 0) + 1
        assert grouped == {first.undo_batch_id: 2, second.undo_batch_id: 1}

    async def test_a_second_undo_of_one_action_refuses(self, committing, project):
        """T-UND1. Without the check a second `undone` row is journalled for one
        transition, and the timeline claims a memory was restored twice."""
        cycle = str(new_id())
        older, _, event_id = await produce_subsume(
            committing, project, cycle_id=cycle
        )
        await undo_ids(committing, event_id)

        with pytest.raises(undo.UndoRefused) as refusal:
            await undo_ids(committing, event_id)

        assert [item.reason for item in refusal.value.blocked] == ["already_undone"]
        assert len(
            await journal_rows(committing, project, journal.UNDONE_EVENT_TYPE)
        ) == 1

    async def test_already_undone_outranks_the_elapsed_window(
        self, committing, project
    ):
        """T-UND5 end to end: an action that is both already undone and out of
        window reports `already_undone`, which is the fact an operator needs
        first."""
        cycle = str(new_id())
        _, _, event_id = await produce_subsume(committing, project, cycle_id=cycle)
        await undo_ids(committing, event_id)
        later = datetime.now(timezone.utc) + timedelta(
            days=undo.DEFAULT_RETENTION_DAYS + 1
        )

        with pytest.raises(undo.UndoRefused) as refusal:
            await undo_ids(committing, event_id, now=later)

        assert [item.reason for item in refusal.value.blocked] == ["already_undone"]

    async def test_the_digest_marks_an_undone_action(self, committing, project):
        """What T2.38 renders as "an undone action still appears, marked
        undone" — guaranteed by append-only rather than by the read surface
        remembering to include it."""
        cycle = str(new_id())
        older, _, event_id = await produce_subsume(
            committing, project, cycle_id=cycle
        )
        batch = await undo_ids(committing, event_id, actor="curator")

        async with committing() as session:
            actions = await digest.read_cycle_actions(session, cycle)
            actions = await digest.annotate_undoability(session, actions)
            cycles, _ = await digest.list_cycles(session, project=project)

        assert actions[0].undone is True
        assert actions[0].undone_by == "curator"
        assert actions[0].undo_batch_id == batch.undo_batch_id
        assert actions[0].undoable is False
        assert actions[0].undo_blocked_reason == "already_undone"
        assert cycles[0].undone_count == 1


# ── Step 8: the doors ────────────────────────────────────────────────────


@pytest.fixture
async def api(client, session, auth_headers):
    """The HTTP door on the rollback-isolated session, so a route test cannot
    leak state into the `committing` fixtures above."""
    return client, session, auth_headers


async def seed_action_over(session, project, *, cycle_id):
    """One real subsume through the request-scoped session, so the route sees
    exactly what the pass writes."""
    older = await seed_memory(
        session, project=project, content="old truth", created_at=NOW
    )
    newer = await seed_memory(
        session, project=project, content="new truth",
        created_at=NOW + timedelta(hours=1),
    )
    await session.flush()
    assert await dream.apply_subsume(
        session,
        dream.SubsumeAction(
            pair=dream.PairCandidate(
                older=memory_row_of(older, project=project, content="old truth"),
                newer=memory_row_of(
                    newer, project=project, content="new truth",
                    created_at=NOW + timedelta(hours=1),
                ),
                score=0.97,
            ),
            verdict=dream.PairVerdict(verdict="subsumes", reason="r"),
        ),
        cycle_id=cycle_id,
        outcome=dream.DreamOutcome(),
    )
    await session.flush()
    event_id = (
        await session.execute(
            text(
                "SELECT max(id) FROM events WHERE event_type = 'consolidated' "
                "AND project = CAST(:project AS text)"
            ),
            {"project": project},
        )
    ).scalar_one()
    return older, newer, int(event_id)


class TestDoors:
    async def test_every_route_needs_auth(self, client):
        """T-API1."""
        cycle = str(new_id())
        for method, path in (
            ("get", "/api/v1/dream-digest/cycles"),
            ("get", f"/api/v1/dream-digest/cycles/{cycle}"),
            ("post", "/api/v1/dream-digest/actions/1/undo"),
            ("post", f"/api/v1/dream-digest/cycles/{cycle}/undo"),
        ):
            response = await getattr(client, method)(path)
            assert response.status_code == 401, path

    async def test_the_cycle_list_and_digest_render(self, api, project):
        client, session, headers = api
        cycle = str(new_id())
        older, _, event_id = await seed_action_over(session, project, cycle_id=cycle)

        listing = await client.get(
            "/api/v1/dream-digest/cycles", params={"project": project},
            headers=headers,
        )
        assert listing.status_code == 200
        body = listing.json()
        assert body["total"] == 1
        assert body["items"][0]["cycle_id"] == cycle
        assert body["items"][0]["counts"]["subsume"] == 1

        detail = await client.get(
            f"/api/v1/dream-digest/cycles/{cycle}", headers=headers
        )
        assert detail.status_code == 200
        digest_body = detail.json()
        assert digest_body["objects"][0]["object_id"] == str(older)
        action = digest_body["objects"][0]["actions"][0]
        assert action["event_id"] == event_id
        assert action["undoable"] is True
        assert action["undo_blocked_reason"] is None
        assert action["before"] == {"status": "active", "superseded_by": None}

    async def test_an_unknown_cycle_is_404(self, api):
        """T-API4. An empty digest would tell a client the cycle exists and did
        nothing."""
        client, _, headers = api
        response = await client.get(
            f"/api/v1/dream-digest/cycles/{new_id()}", headers=headers
        )
        assert response.status_code == 404

    async def test_the_single_action_door_undoes_and_journals(self, api, project):
        client, session, headers = api
        cycle = str(new_id())
        older, _, event_id = await seed_action_over(session, project, cycle_id=cycle)

        response = await client.post(
            f"/api/v1/dream-digest/actions/{event_id}/undo", headers=headers
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body["undone"]) == 1
        assert body["undone"][0]["restored"] == ["status", "superseded_by"]
        assert "updated_at" in body["undone"][0]["not_restored"]
        status = (
            await session.execute(
                text(
                    "SELECT status::text FROM memories WHERE id = CAST(:id AS uuid)"
                ),
                {"id": str(older)},
            )
        ).scalar_one()
        assert status == "active"
        assert (
            await session.execute(
                text(
                    "SELECT count(*) FROM events WHERE event_type = 'undone' "
                    "AND project = CAST(:project AS text)"
                ),
                {"project": project},
            )
        ).scalar_one() == 1

    async def test_a_blocked_batch_answers_409_naming_every_reason(
        self, api, project
    ):
        """T-API2. 200 with a partial result is the one answer this primitive
        refuses to represent."""
        client, session, headers = api
        cycle = str(new_id())
        older, newer, event_id = await seed_action_over(
            session, project, cycle_id=cycle
        )
        await session.execute(
            text(
                "UPDATE memories SET status = 'active', superseded_by = NULL "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(older)},
        )
        await session.flush()

        response = await client.post(
            f"/api/v1/dream-digest/actions/{event_id}/undo", headers=headers
        )

        assert response.status_code == 409
        body = response.json()
        assert body["error"]["code"] == "conflict"
        assert body["error"]["details"] == [
            {"event_id": event_id, "action": "subsume", "reason": "state_changed"}
        ]

    async def test_an_unknown_event_id_is_404(self, api):
        client, _, headers = api
        response = await client.post(
            f"/api/v1/dream-digest/actions/{2 ** 40}/undo", headers=headers
        )
        assert response.status_code == 404

    async def test_a_cycle_undo_honours_the_action_filter(self, api, project):
        """T-API3. Ignoring the filter would undo the whole cycle when the user
        asked for one kind of it."""
        client, session, headers = api
        cycle = str(new_id())
        older, _, subsume_id = await seed_action_over(
            session, project, cycle_id=cycle
        )
        memory = await seed_memory(
            session, project=project, content="the sweeper runs hourly",
            summary="the old summary",
        )
        await session.flush()
        assert await dream.apply_refine(
            session,
            dream.RefineAction(
                memory=memory_row_of(
                    memory, project=project, content="the sweeper runs hourly",
                    summary="the old summary",
                ),
                verdict=dream.RefineVerdict(summary="a refined summary", tags=None),
            ),
            cycle_id=cycle,
            outcome=dream.DreamOutcome(),
        )
        await session.flush()

        response = await client.post(
            f"/api/v1/dream-digest/cycles/{cycle}/undo",
            json={"action": "subsume"},
            headers=headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert [item["action"] for item in body["undone"]] == ["subsume"]
        summary = (
            await session.execute(
                text("SELECT summary FROM memories WHERE id = CAST(:id AS uuid)"),
                {"id": str(memory)},
            )
        ).scalar_one()
        assert summary == "a refined summary", "the refine must be untouched"

    async def test_a_whole_cycle_undo_takes_every_action(self, api, project):
        client, session, headers = api
        cycle = str(new_id())
        older, _, _ = await seed_action_over(session, project, cycle_id=cycle)
        memory = await seed_memory(
            session, project=project, content="the sweeper runs hourly",
            summary="the old summary",
        )
        await session.flush()
        assert await dream.apply_refine(
            session,
            dream.RefineAction(
                memory=memory_row_of(
                    memory, project=project, content="the sweeper runs hourly",
                    summary="the old summary",
                ),
                verdict=dream.RefineVerdict(summary="a refined summary", tags=None),
            ),
            cycle_id=cycle,
            outcome=dream.DreamOutcome(),
        )
        await session.flush()

        response = await client.post(
            f"/api/v1/dream-digest/cycles/{cycle}/undo", headers=headers
        )

        assert response.status_code == 200
        assert len(response.json()["undone"]) == 2
        rows = {
            row["id"]: row
            for row in (
                await session.execute(
                    text(
                        "SELECT CAST(id AS text) AS id, status::text AS status, "
                        "       summary FROM memories "
                        " WHERE id = ANY(CAST(:ids AS uuid[]))"
                    ),
                    {"ids": [str(older), str(memory)]},
                )
            ).mappings()
        }
        assert rows[str(older)]["status"] == "active"
        assert rows[str(memory)]["summary"] == "the old summary"

    def test_the_paths_and_response_models_match_the_conventions(self):
        """T-API5."""
        import re

        from app.api.routes import dream_digest as routes
        from app.schemas import dream_digest as schemas

        for route in routes.router.routes:
            assert re.fullmatch(
                r"/api/v1/dream-digest(/[a-z-]+|/\{[a-z_]+\})*", route.path
            ), route.path
        for name in dir(schemas):
            model = getattr(schemas, name)
            if isinstance(model, type) and issubclass(model, schemas.BaseModel):
                assert not [
                    field for field in model.model_fields if field.startswith("llm_")
                ], name

    async def test_a_missing_retention_row_does_not_500(self, api, project):
        """T-API6. The door reads the config row on every call; an absent one is
        the ordinary state, not an error."""
        client, session, headers = api
        cycle = str(new_id())
        _, _, event_id = await seed_action_over(session, project, cycle_id=cycle)
        assert (
            await session.execute(
                text("SELECT count(*) FROM config WHERE key = CAST(:key AS text)"),
                {"key": undo.RETENTION_CONFIG_KEY},
            )
        ).scalar_one() == 0

        response = await client.post(
            f"/api/v1/dream-digest/actions/{event_id}/undo", headers=headers
        )
        assert response.status_code == 200
