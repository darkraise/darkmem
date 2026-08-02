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
        assert "updated_at" in batch.undone[0].excluded


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
        assert "memory_relations_row" in batch.undone[0].excluded

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
            assert "updated_at" in batch.undone[0].excluded

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
            "E1", "E2", "E3", "E4", "E5",
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
            for field_name in action.excluded:
                entry = undo.EXCLUSIONS_BY_FIELD[field_name]
                assert action.action in entry.actions
