"""T3.16 — the session-checkpoint store, on both doors (spec §Feature-2).

Three done-whens, and the interesting ones are not the happy path:

1. **Both doors expose it** (invariant 17). Asserted as *behavioural* parity —
   the same save through either door produces the same row and the same
   journal — not as "two functions exist with similar names".
2. **Latest-per-origin is one indexed query.** Asserted twice: that the answer
   is right when two checkpoints share a transaction's ``now()`` (which is the
   case an unindexed sort gets wrong silently), and that the plan actually
   uses the index rather than sorting the run's history.
3. **Payload size is bounded**, at both layers — the schema for the 422 and
   the CHECK constraint for the guarantee, with the constraint proven by
   writing round the schema.

Plus the rule this table exists under: a checkpoint is operational, not vault
knowledge, so it carries no verification column and no route into the vault.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.services import checkpoints as cp

pytestmark = pytest.mark.asyncio

ORIGIN = "cli:session-abc"
PROJECT = "t3-16"


# ─────────────── the store ───────────────


class TestSaveAndFetch:
    async def test_a_saved_checkpoint_comes_back_whole(self, session):
        await cp.save_checkpoint(
            session, origin_key=ORIGIN, summary="did the thing",
            next_steps=["ship it", "tell someone"], project=PROJECT,
        )
        await session.flush()

        latest = await cp.latest_checkpoint(session, origin_key=ORIGIN, project=PROJECT)

        assert latest is not None
        assert latest.summary == "did the thing"
        assert latest.next_steps == ["ship it", "tell someone"]

    async def test_an_origin_with_no_checkpoint_is_none_not_an_error(self, session):
        assert await cp.latest_checkpoint(
            session, origin_key="never-saved", project=PROJECT
        ) is None

    async def test_saving_twice_keeps_both_and_returns_the_newer(self, session):
        """Append-only: overwriting in place would make a wrong resume
        unexplainable afterwards.

        The origin is unique per run rather than the shared module constant.
        An earlier version counted rows for `ORIGIN` across the whole table
        and passed in isolation while failing in the full suite: the door
        tests below *commit*, so their rows outlive their own transaction and
        joined this count. A test whose result depends on what ran before it
        is not measuring what it claims to.
        """
        origin = f"twice:{uuid4()}"
        first = await cp.save_checkpoint(
            session, origin_key=origin, summary="first", project=PROJECT
        )
        second = await cp.save_checkpoint(
            session, origin_key=origin, summary="second", project=PROJECT
        )
        await session.flush()
        # `created_at` defaults to `now()`, the *transaction* start time, so
        # both rows are equal on it here and "latest" would fall to the id
        # tie-break -- deterministic, but not insertion order, since ids are
        # random. Two saves from one run are two requests in real use, so
        # ageing the first is what reproduces that shape. An earlier version
        # asserted `second` won on the tie-break and passed only by luck.
        await session.execute(
            text("UPDATE session_checkpoints SET created_at = now() - interval '1 hour' "
                 "WHERE id = CAST(:id AS uuid)"),
            {"id": str(first.id)},
        )
        await session.flush()

        latest = await cp.latest_checkpoint(session, origin_key=origin, project=PROJECT)
        assert latest is not None and latest.id == second.id

        kept = (await session.execute(
            text("SELECT COUNT(*) FROM session_checkpoints WHERE origin_key = :o"),
            {"o": origin},
        )).scalar_one()
        assert kept == 2
        assert first.id != second.id

    async def test_latest_is_right_when_both_rows_share_one_timestamp(self, session):
        """The case the `id DESC` tie-break exists for, and the reason it is
        not decoration: `created_at` defaults to `now()`, which is the
        *transaction's* start time, so two checkpoints saved in one
        transaction are exactly equal on it. Without the tie-break "latest"
        would be whichever row the planner happened to return first.
        """
        rows = [
            await cp.save_checkpoint(
                session, origin_key=ORIGIN, summary=f"n{index}", project=PROJECT
            )
            for index in range(5)
        ]
        await session.flush()

        stamps = (await session.execute(
            text("SELECT COUNT(DISTINCT created_at) FROM session_checkpoints "
                 "WHERE origin_key = :o"),
            {"o": ORIGIN},
        )).scalar_one()
        assert stamps == 1, "premise: all five share the transaction timestamp"

        latest = await cp.latest_checkpoint(session, origin_key=ORIGIN, project=PROJECT)
        assert latest is not None
        assert latest.id == max(row.id for row in rows)

    async def test_another_project_s_checkpoint_is_not_this_one_s(self, session):
        await cp.save_checkpoint(
            session, origin_key=ORIGIN, summary="theirs", project="somewhere-else"
        )
        await session.flush()

        assert await cp.latest_checkpoint(
            session, origin_key=ORIGIN, project=PROJECT
        ) is None


class TestTheLatestReadUsesItsIndex:
    async def test_the_plan_is_an_index_scan_not_a_sort(self, session):
        """The done-when says *one indexed query*, so the plan is the
        assertion. A correct answer reached by sorting a run's whole history
        satisfies every other test in this file and degrades with use — which
        is the shape that only ever shows up in production.
        """
        for index in range(20):
            await cp.save_checkpoint(
                session, origin_key=ORIGIN, summary=f"n{index}", project=PROJECT
            )
        await session.flush()
        await session.execute(text("ANALYZE session_checkpoints"))

        plan = "\n".join(row[0] for row in (await session.execute(text(
            "EXPLAIN SELECT id FROM session_checkpoints "
            "WHERE project = :p AND origin_key = :o "
            "ORDER BY created_at DESC, id DESC LIMIT 1"
        ), {"p": PROJECT, "o": ORIGIN})).all())

        assert "ix_session_checkpoints_latest" in plan, plan
        assert "Sort" not in plan, plan


# ─────────────── the bound, at both layers ───────────────


class TestThePayloadIsBounded:
    async def test_the_schema_refuses_an_oversized_summary(self):
        from pydantic import ValidationError

        from app.schemas.checkpoint import CheckpointCreate

        with pytest.raises(ValidationError):
            CheckpointCreate(
                origin_key=ORIGIN, summary="x" * (cp.MAX_SUMMARY_LENGTH + 1)
            )

    async def test_the_schema_refuses_too_many_steps(self):
        from pydantic import ValidationError

        from app.schemas.checkpoint import CheckpointCreate

        with pytest.raises(ValidationError):
            CheckpointCreate(
                origin_key=ORIGIN, summary="ok",
                next_steps=["s"] * (cp.MAX_NEXT_STEPS + 1),
            )

    async def test_the_schema_refuses_one_enormous_step(self):
        """A list bound alone is not a payload bound: fifty steps of ten
        thousand characters each satisfies `max_length`."""
        from app.schemas.checkpoint import CheckpointCreate

        body = CheckpointCreate(
            origin_key=ORIGIN, summary="ok",
            next_steps=["x" * (cp.MAX_STEP_LENGTH + 1)],
        )
        with pytest.raises(ValueError):
            body.bounded_steps()

    async def test_the_database_refuses_it_too_when_the_schema_is_bypassed(
        self, session
    ):
        """The constraint is the guarantee; the schema is only the good error
        message. Written round the schema on purpose — a bound that lives only
        in the API layer is a bound the next writer does not have."""
        with pytest.raises((IntegrityError, DBAPIError)):
            await session.execute(
                text(
                    "INSERT INTO session_checkpoints (id, origin_key, summary) "
                    "VALUES (gen_random_uuid(), :o, :s)"
                ),
                {"o": ORIGIN, "s": "x" * (cp.MAX_SUMMARY_LENGTH + 1)},
            )


# ─────────────── operational, not vault knowledge ───────────────


class TestCheckpointsAreNotVaultKnowledge:
    async def test_the_table_carries_no_verification_column(self, session):
        """T3.18's rule, asserted where it can regress: a rung here would be
        an unearned badge on prose no ladder judged."""
        columns = {
            row[0] for row in (await session.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'session_checkpoints'"
            ))).all()
        }
        assert not {"verification_status", "review_state", "confidence"} & columns

    async def test_saving_a_checkpoint_writes_no_memory_and_no_fact(self, session):
        before = (await session.execute(
            text("SELECT (SELECT COUNT(*) FROM memories), "
                 "(SELECT COUNT(*) FROM knowledge_triples)")
        )).first()

        await cp.save_checkpoint(
            session, origin_key=ORIGIN, summary="not a memory", project=PROJECT
        )
        await session.flush()

        after = (await session.execute(
            text("SELECT (SELECT COUNT(*) FROM memories), "
                 "(SELECT COUNT(*) FROM knowledge_triples)")
        )).first()
        assert before == after

    async def test_the_journal_row_does_not_copy_the_summary(self, session):
        """Write-time minimization: an event payload outlives deletion of what
        it describes, so it copies content only when a feature needs it."""
        await cp.save_checkpoint(
            session, origin_key=ORIGIN, summary="secret-token-xyz", project=PROJECT
        )
        await session.flush()

        payload = (await session.execute(
            text("SELECT payload FROM events WHERE event_type = 'checkpoint_saved' "
                 "ORDER BY created_at DESC, id DESC LIMIT 1")
        )).scalar_one()
        assert "secret-token-xyz" not in json.dumps(payload)
        assert payload["origin_key"] == ORIGIN

    async def test_the_event_vocabulary_carries_the_type(self):
        """Taxonomy-first: the value lands in the closed vocabulary before its
        emitter ships, and `record_event` only warns on an unknown type — so
        without this assertion nothing would fail if it were removed."""
        from app.services.events import EVENT_TYPES, OBJECT_TYPES

        assert cp.CHECKPOINT_SAVED_EVENT in EVENT_TYPES
        assert cp.OBJECT_TYPE in OBJECT_TYPES


# ─────────────── invariant 17: both doors, one behaviour ───────────────


class TestBothDoors:
    async def test_the_rest_door_saves_and_reads_back(self, client, auth_headers):
        origin = f"rest:{uuid4()}"
        created = await client.post(
            "/api/v1/checkpoints",
            json={"origin_key": origin, "summary": "via rest",
                  "next_steps": ["one"], "project": PROJECT},
            headers=auth_headers,
        )
        assert created.status_code == 201, created.text

        fetched = await client.get(
            "/api/v1/checkpoints/latest",
            params={"origin_key": origin, "project": PROJECT},
            headers=auth_headers,
        )
        assert fetched.status_code == 200
        assert fetched.json()["summary"] == "via rest"

    async def test_a_missing_checkpoint_is_404_not_an_empty_200(
        self, client, auth_headers
    ):
        """"This run saved nothing" and "this run's note is empty" are
        different answers, and T3.17's resume branches on exactly that."""
        response = await client.get(
            "/api/v1/checkpoints/latest",
            params={"origin_key": f"absent:{uuid4()}", "project": PROJECT},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_the_rest_door_refuses_an_oversized_payload_with_422(
        self, client, auth_headers
    ):
        response = await client.post(
            "/api/v1/checkpoints",
            json={"origin_key": ORIGIN, "summary": "x" * (cp.MAX_SUMMARY_LENGTH + 1)},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_the_two_doors_produce_the_same_row_and_the_same_journal(
        self, client, auth_headers, session
    ):
        """Invariant 17 as behaviour, not as naming. The MCP tool and the REST
        route are driven with the same input and the stored rows are compared
        field by field — a door that grew its own default, its own trimming or
        its own project fallback fails here.
        """
        from app.api.mcp import server as mcp_server

        rest_origin = f"parity-rest:{uuid4()}"
        mcp_origin = f"parity-mcp:{uuid4()}"
        body = {"summary": "same input", "next_steps": ["a", "b"], "project": PROJECT}

        rest = await client.post(
            "/api/v1/checkpoints",
            json={"origin_key": rest_origin, **body},
            headers=auth_headers,
        )
        assert rest.status_code == 201
        await mcp_server.checkpoint_save(origin_key=mcp_origin, **body)

        rows = {}
        for origin in (rest_origin, mcp_origin):
            row = (await session.execute(
                text("SELECT summary, next_steps, project FROM session_checkpoints "
                     "WHERE origin_key = :o"),
                {"o": origin},
            )).mappings().one()
            rows[origin] = dict(row)
        assert rows[rest_origin] == rows[mcp_origin]

        journalled = (await session.execute(
            text("SELECT COUNT(*) FROM events WHERE event_type = 'checkpoint_saved' "
                 "AND payload->>'origin_key' = ANY(:origins)"),
            {"origins": [rest_origin, mcp_origin]},
        )).scalar_one()
        assert journalled == 2

    async def test_the_mcp_door_answers_null_for_a_run_with_no_checkpoint(self):
        from app.api.mcp import server as mcp_server

        answer = await mcp_server.checkpoint_latest(
            origin_key=f"absent:{uuid4()}", project=PROJECT
        )
        assert json.loads(answer) is None

    async def test_the_mcp_door_refuses_an_oversized_payload(self):
        """The bound is a property of a checkpoint, not of a transport — so
        the door that has no HTTP layer to validate for it still refuses."""
        from pydantic import ValidationError

        from app.api.mcp import server as mcp_server

        with pytest.raises((ValidationError, ValueError)):
            await mcp_server.checkpoint_save(
                origin_key=ORIGIN, summary="x" * (cp.MAX_SUMMARY_LENGTH + 1)
            )
