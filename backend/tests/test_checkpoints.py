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

from app.api.mcp.client_identity import CLIENT_HEADER, ORIGIN_HEADER
from app.services import checkpoints as cp

pytestmark = pytest.mark.asyncio

ORIGIN = "cli:session-abc"
PROJECT = "t3-16"


def _ctx(headers: dict[str, str] | None):
    """An MCP ``Context`` as far as identity resolution is concerned.

    The MCP door reads its transport's headers through
    ``ctx.request_context.request``, exactly as ``memory_add`` does. Driving
    the tool with a real header mapping is the only way a test can see which
    source the door resolved — an in-process call with ``ctx=None`` exercises
    the fallback rung and nothing above it.
    """
    from types import SimpleNamespace

    from starlette.datastructures import Headers

    if headers is None:
        return None
    return SimpleNamespace(
        request_context=SimpleNamespace(request=SimpleNamespace(headers=Headers(headers)))
    )


@pytest.fixture
def mcp_on_the_test_session(session, monkeypatch):
    """Point the MCP tools' own session factory at the test session.

    The MCP door opens sessions from the module-level
    ``async_session_factory`` rather than the FastAPI dependency, so by
    default it commits on a second connection and cannot see a row the REST
    door wrote inside the test's uncommitted transaction. Any test that reads
    one door's write through the *other* door needs this, or it fails for a
    harness reason that looks exactly like the key-space divergence it is
    hunting.
    """
    from contextlib import asynccontextmanager

    import app.api.mcp.server as mcp_module

    @asynccontextmanager
    async def _ctx_manager():
        yield session

    monkeypatch.setattr(mcp_module, "async_session_factory", lambda: _ctx_manager())


async def mcp_checkpoint_save(**kwargs):
    from app.api.mcp import server as mcp_server

    return await mcp_server.checkpoint_save(**kwargs)


async def mcp_checkpoint_latest(**kwargs):
    from app.api.mcp import server as mcp_server

    return await mcp_server.checkpoint_latest(**kwargs)


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

    async def test_a_cjk_payload_inside_every_character_limit_is_still_refused(self):
        """Task review I-1. The schema bounded characters and the CHECK bounds
        bytes, so these two limits were **born** different rather than
        drifted: 15 steps of 500 CJK characters passes every character check
        and encodes to ~22.5 KB, violating the constraint at flush — a 500 on
        a request this validation had just called valid.
        """
        from app.schemas.checkpoint import CheckpointCreate

        body = CheckpointCreate(
            origin_key=ORIGIN, summary="ok",
            next_steps=["漢" * cp.MAX_STEP_LENGTH] * 15,
        )
        with pytest.raises(ValueError, match="bytes"):
            body.bounded_steps()

    async def test_the_schema_maximal_ascii_payload_round_trips(self, session):
        """The seam the suite was missing: the largest payload the schema
        accepts must actually reach the table. If the schema's ceiling sits
        above the constraint's, this is the test that says so."""
        from app.schemas.checkpoint import CheckpointCreate

        steps = ["x" * cp.MAX_STEP_LENGTH] * cp.MAX_NEXT_STEPS
        body = CheckpointCreate(origin_key=ORIGIN, summary="x" * cp.MAX_SUMMARY_LENGTH,
                                next_steps=steps, project=PROJECT)
        try:
            accepted = body.bounded_steps()
        except ValueError:
            # The schema refuses its own nominal maximum, which is the honest
            # outcome once the byte bound governs -- what must never happen is
            # the schema accepting something the database then refuses.
            return
        await cp.save_checkpoint(
            session, origin_key=f"maximal:{uuid4()}", summary=body.summary,
            next_steps=accepted, project=PROJECT,
        )
        await session.flush()

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

        # Looked up by the *resolved* key, not the declared one: both doors
        # now run the declared identity through doc 05 §2.1's derivation, and
        # each resolves `source` from its own transport exactly as the capture
        # doors do. Comparing raw strings would assert that the resolution
        # never happened.
        rows = {}
        for label, origin in (("rest", rest_origin), ("mcp", mcp_origin)):
            # Matched on the sanitised tail rather than a source this test
            # hard-codes: `resolve_client_source` reads the transport's own
            # headers, so pinning REST's source here would pin the test
            # client's User-Agent instead of the behaviour under test.
            row = (await session.execute(
                text("SELECT summary, next_steps, project, origin_key "
                     "FROM session_checkpoints WHERE origin_key LIKE :pattern"),
                {"pattern": f"%{origin.replace(':', '')}"},
            )).mappings().one()
            rows[label] = dict(row)

        # The resolution happened on both doors: neither stored the declared
        # string verbatim, which is the defect this replaced.
        for label, origin in (("rest", rest_origin), ("mcp", mcp_origin)):
            assert rows[label]["origin_key"] != origin
            assert rows[label]["origin_key"].endswith(origin.replace(":", ""))
        for row in rows.values():
            row.pop("origin_key")

        # Everything the doors are allowed to have in common must be identical.
        # `origin_key` is deliberately excluded: it carries the transport's own
        # resolved source, which differs by door by design and does so for
        # capture too.
        assert rows["rest"] == rows["mcp"]

        journalled = (await session.execute(
            text("SELECT COUNT(*) FROM events WHERE event_type = 'checkpoint_saved' "
                 "AND payload->>'origin_key' LIKE ANY(:patterns)"),
            {"patterns": [f"%{rest_origin.replace(':', '')}", f"%{mcp_origin.replace(':', '')}"]},
        )).scalar_one()
        assert journalled == 2

    async def test_both_doors_refuse_an_undeclared_origin(self, client, auth_headers):
        """The refusal is the door's, not the schema's, so it must hold on
        both. An undeclared checkpoint merged into the coarse bucket would let
        two runs read each other's notes — safe for counting, wrong for
        lookup."""
        from app.api.mcp import server as mcp_server

        response = await client.post(
            "/api/v1/checkpoints",
            json={"origin_key": "   ", "summary": "no run"},
            headers=auth_headers,
        )
        assert response.status_code == 422

        with pytest.raises(ValueError):
            await mcp_server.checkpoint_save(origin_key="  ", summary="no run")

    async def test_one_declared_client_lands_on_one_key_through_either_door(
        self, client, auth_headers, session
    ):
        """The correlation's own mechanism, driven through both doors.

        The test this replaced asserted ``f(x) == f(x)`` on the resolver — a
        tautology that drove neither door, passed under the pre-resolution
        implementation, and passed while the MCP door hard-coded ``source``
        into a different key space from REST's. The property that matters is
        not that the function is deterministic; it is that **both transports
        feed it the same source**, which only a test that drives both can see.
        """
        declared = f"boot-{uuid4()}"
        body = {"summary": "same run, two doors", "project": PROJECT}

        rest = await client.post(
            "/api/v1/checkpoints",
            json={"origin_key": declared, **body},
            headers={**auth_headers, CLIENT_HEADER: "codex"},
        )
        assert rest.status_code == 201, rest.text
        await mcp_checkpoint_save(
            origin_key=declared, ctx=_ctx({CLIENT_HEADER: "codex"}), **body
        )

        keys = (await session.execute(
            text("SELECT origin_key FROM session_checkpoints "
                 "WHERE project = :p AND origin_key LIKE :pattern"),
            {"p": PROJECT, "pattern": f"%{declared}"},
        )).scalars().all()

        assert len(keys) == 2
        assert set(keys) == {f"codex:{declared}"}

    async def test_the_mcp_door_reads_the_checkpoint_the_rest_door_saved(
        self, client, auth_headers, mcp_on_the_test_session
    ):
        """The failure the key space causes, stated as behaviour.

        One agent run, one declared identity, one declared client — a resume
        over MCP must find the note the run saved over REST. While MCP passed
        the ``checkpoint`` constant as ``source`` and REST resolved ``codex``
        from the header, this returned ``null``: a wrong-context resume with
        no error and no symptom, which is the failure the refusal machinery in
        this module exists to prevent.
        """
        declared = f"boot-{uuid4()}"
        saved = await client.post(
            "/api/v1/checkpoints",
            json={"origin_key": declared, "summary": "saved over rest",
                  "project": PROJECT},
            headers={**auth_headers, CLIENT_HEADER: "codex"},
        )
        assert saved.status_code == 201, saved.text

        answer = json.loads(await mcp_checkpoint_latest(
            origin_key=declared, project=PROJECT, ctx=_ctx({CLIENT_HEADER: "codex"})
        ))

        assert answer is not None, "the MCP door missed the REST door's checkpoint"
        assert answer["summary"] == "saved over rest"

    async def test_an_undeclared_client_still_lands_on_the_door_fallback(
        self, client, auth_headers, session
    ):
        """Resolution is a ladder, not a header requirement. With nothing to
        read, both doors fall back to ``DOOR_SOURCE`` — so the fix for the
        hard-coded source does not make an unannounced client's checkpoints
        unreadable."""
        declared = f"boot-{uuid4()}"
        await mcp_checkpoint_save(
            origin_key=declared, summary="no client header", project=PROJECT, ctx=None
        )

        key = (await session.execute(
            text("SELECT origin_key FROM session_checkpoints "
                 "WHERE project = :p AND origin_key LIKE :pattern"),
            {"p": PROJECT, "pattern": f"%{declared}"},
        )).scalar_one()

        assert key == f"{cp.DOOR_SOURCE}:{declared}"

    async def test_the_origin_header_alone_is_enough_on_both_doors(
        self, client, auth_headers, mcp_on_the_test_session
    ):
        """The header the refusal message names must actually work.

        ``UndeclaredOrigin`` tells the caller to "send `origin_key`, or the
        X-Darkmem-Origin header the client mints at process boot", and the
        REST route reads that header — but ``CheckpointCreate`` required
        ``origin_key``, so the header branch was unreachable on REST and the
        MCP tool required the argument outright. The documented mechanism
        worked on neither door; capture's identical ladder
        (``routes/memories.py``) worked on both.
        """
        declared = f"boot-{uuid4()}"
        headers = {**auth_headers, ORIGIN_HEADER: declared}

        saved = await client.post(
            "/api/v1/checkpoints",
            json={"summary": "identity from the header", "project": PROJECT},
            headers=headers,
        )
        assert saved.status_code == 201, saved.text

        fetched = await client.get(
            "/api/v1/checkpoints/latest",
            params={"project": PROJECT},
            headers=headers,
        )
        assert fetched.status_code == 200, fetched.text
        assert fetched.json()["summary"] == "identity from the header"

        answer = json.loads(await mcp_checkpoint_latest(
            project=PROJECT, ctx=_ctx({ORIGIN_HEADER: declared})
        ))
        assert answer is not None, "the MCP door ignored the X-Darkmem-Origin header"
        assert answer["summary"] == "identity from the header"

    @pytest.mark.parametrize("declared", [":::", "::", "​", " : ", " "])
    async def test_a_declaration_that_sanitises_to_nothing_is_refused(self, declared):
        """The undeclared refusal was reachable round the front (branch review
        M-9).

        `_sanitize_origin` strips separators and unprintables, so `":::"`, a
        lone zero-width space and friends all reduce to the empty string and
        resolved to the bare `"<source>:"` — one key shared by every such run.
        That is precisely the merge-to-one bucket `UndeclaredOrigin` exists to
        refuse: safe for counting corroboration, wrong for lookup, because two
        runs sharing it each read the other's checkpoint as their own. The
        guard was written against an *empty* declaration and a declaration
        that survives sanitisation, and these fall between the two.
        """
        with pytest.raises(cp.UndeclaredOrigin):
            cp.resolve_checkpoint_origin(declared, source="codex", project=PROJECT)

    async def test_a_declaration_that_survives_sanitising_is_still_accepted(self):
        """The refusal must key on the sanitised result being empty, not on
        the raw string containing a stripped character — `boot:1` sanitises to
        `boot1`, which is a perfectly good identity."""
        assert cp.resolve_checkpoint_origin(
            "boot:1", source="codex", project=PROJECT
        ) == "codex:boot1"

    async def test_neither_door_invents_an_identity_when_nothing_declares_one(
        self, client, auth_headers
    ):
        """Making the header live must not make the refusal optional."""
        from app.api.mcp import server as mcp_server

        response = await client.post(
            "/api/v1/checkpoints",
            json={"summary": "no run", "project": PROJECT},
            headers=auth_headers,
        )
        assert response.status_code == 422

        with pytest.raises(ValueError):
            await mcp_server.checkpoint_save(summary="no run", project=PROJECT)

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
