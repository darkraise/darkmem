"""T3.19 — the Distribution surface's live half (doc 13 §6.5).

The tab's own rendering is `frontend`'s to test. What only the server can
answer is that the screen shows the system rather than itself: the targets come
from T3.11's registry, and the curb is enforced where the client cannot ignore
it.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import text

from app.models.config import Config
from app.api.routes.distribution import DISTRIBUTION_CONFIG_KEY
from app.services import inject_adapters as ia

pytestmark = pytest.mark.asyncio


async def _adapters_config(session, value: dict) -> None:
    await session.execute(
        text(
            "INSERT INTO config (key, value) VALUES (CAST(:k AS text), CAST(:v AS jsonb)) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ),
        {"k": ia.INJECT_ADAPTERS_CONFIG_KEY, "v": json.dumps(value)},
    )
    await session.commit()


class TestTheTargetsShownAreTheTargetsUsed:
    async def test_every_registry_target_is_listed_with_its_block_path(
        self, client, auth_headers
    ):
        response = await client.get("/api/v1/distribution", headers=auth_headers)

        assert response.status_code == 200
        targets = {t["tool"]: t for t in response.json()["targets"]}
        assert targets["claude-code"]["context_file"] == "CLAUDE.md"
        assert targets["cursor"]["context_file"] == ".cursor/rules/darkmem.mdc"

    async def test_a_config_row_moves_what_the_screen_shows(
        self, client, auth_headers, session
    ):
        """The screen reads T3.11's registry rather than a list of its own. A
        second list would be a surface that agrees with itself and not with
        the inject writer — the human would configure one and the blocks would
        land by the other."""
        await _adapters_config(session, {"cursor": {"context_file": ".cursorrules"}})

        response = await client.get("/api/v1/distribution", headers=auth_headers)

        targets = {t["tool"]: t for t in response.json()["targets"]}
        assert targets["cursor"]["context_file"] == ".cursorrules"


class TestThePolicyAndTheCurb:
    async def test_the_defaults_apply_before_anything_is_written(
        self, client, auth_headers
    ):
        policy = (await client.get(
            "/api/v1/distribution", headers=auth_headers
        )).json()["policy"]

        assert policy["curbed"] is False
        assert policy["token_budget"] == 2000

    async def test_the_curb_is_one_control_and_it_persists(
        self, client, auth_headers
    ):
        """"A single control stops all injection immediately" — so it is one
        flag, not a per-target sweep the caller has to complete."""
        written = await client.put(
            "/api/v1/distribution/policy",
            json={"token_budget": 2000, "curbed": True},
            headers=auth_headers,
        )
        assert written.status_code == 200
        assert written.json()["curbed"] is True

        after = (await client.get(
            "/api/v1/distribution", headers=auth_headers
        )).json()["policy"]
        assert after["curbed"] is True

    async def test_the_curb_lives_server_side_not_in_the_client(
        self, client, auth_headers, session
    ):
        """A curb honoured only by the client would be a setting that appears
        to work and does not — the client is the thing being curbed."""
        await client.put(
            "/api/v1/distribution/policy",
            json={"token_budget": 500, "curbed": True},
            headers=auth_headers,
        )

        stored = (await session.execute(
            text("SELECT value FROM config WHERE key = CAST(:k AS text)"),
            {"k": DISTRIBUTION_CONFIG_KEY},
        )).scalar_one()
        assert stored["curbed"] is True
        assert stored["token_budget"] == 500

    async def test_the_write_answers_with_the_state_now_in_force(
        self, client, auth_headers
    ):
        """200 with the value rather than 204: a human turning push off needs
        to see what is in force, and an empty response leaves the screen
        asserting what it hopes."""
        response = await client.put(
            "/api/v1/distribution/policy",
            json={"token_budget": 1234, "curbed": False},
            headers=auth_headers,
        )
        assert response.json() == {"token_budget": 1234, "curbed": False}

    async def test_an_out_of_range_budget_is_refused(self, client, auth_headers):
        response = await client.put(
            "/api/v1/distribution/policy",
            json={"token_budget": -1, "curbed": False},
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_both_doors_require_auth(self, client):
        assert (await client.get("/api/v1/distribution")).status_code in (401, 403)
        assert (await client.put(
            "/api/v1/distribution/policy", json={"token_budget": 1, "curbed": True}
        )).status_code in (401, 403)


class TestTheCurbIsJournalled:
    """Doc 15 §7: "the **curb** … journals the curb as an ``inject_curbed``
    ``events`` row", and its mermaid draws the edge.

    ``record_inject_curbed`` shipped with the event type already in the closed
    vocabulary and **no caller anywhere in the tree**, so the one curb act the
    system can observe today — a human flipping the flag — left no trace. Found
    by the Fable review of 2026-08-10 (I-9); the writer was there, the edge had
    no producer.
    """

    async def _curbed_rows(self, session):
        return (await session.execute(text(
            "SELECT payload FROM events WHERE event_type = 'inject_curbed'"
        ))).scalars().all()

    async def test_turning_the_curb_on_journals_it(
        self, client, auth_headers, session
    ):
        await client.put(
            "/api/v1/distribution/policy",
            json={"token_budget": 2000, "curbed": True},
            headers=auth_headers,
        )

        rows = await self._curbed_rows(session)
        assert len(rows) == 1
        # One row for a global control. Per-target rows would describe
        # per-target curbs, which do not exist.
        assert rows[0]["tool"] == "*"
        assert "human" in rows[0]["reason"]

    async def test_leaving_the_curb_on_journals_nothing_further(
        self, client, auth_headers, session
    ):
        """The transition is the event, not the state. A screen that re-saves
        an unchanged policy would otherwise manufacture a curb history nobody
        performed."""
        for _ in range(3):
            await client.put(
                "/api/v1/distribution/policy",
                json={"token_budget": 2000, "curbed": True},
                headers=auth_headers,
            )

        assert len(await self._curbed_rows(session)) == 1

    async def test_releasing_the_curb_journals_nothing(
        self, client, auth_headers, session
    ):
        """Deliberate asymmetry, pinned so it reads as a decision rather than
        an omission: ``EVENT_TYPES`` is closed and holds no release event, and
        inventing one at a call site is exactly what the taxonomy-first rule
        forbids. Closing it means editing doc 04 §8.1 first."""
        await client.put(
            "/api/v1/distribution/policy",
            json={"token_budget": 2000, "curbed": True},
            headers=auth_headers,
        )
        await client.put(
            "/api/v1/distribution/policy",
            json={"token_budget": 2000, "curbed": False},
            headers=auth_headers,
        )

        assert len(await self._curbed_rows(session)) == 1

    async def test_a_budget_edit_alone_is_not_a_curb(
        self, client, auth_headers, session
    ):
        await client.put(
            "/api/v1/distribution/policy",
            json={"token_budget": 500, "curbed": False},
            headers=auth_headers,
        )

        assert await self._curbed_rows(session) == []


class TestARefusedTargetIsNamedOnTheWire:
    """A registry that drops a configured row silently is the same defect as a
    retrieval that drops a match silently (invariant 14). The reason reached
    the server log only, so an operator editing ``inject_adapters`` watched
    their row vanish from the screen with no explanation — found by the Fable
    review of 2026-08-10 (M-11)."""

    async def test_an_absolute_path_is_served_as_refused_not_dropped(
        self, client, auth_headers, session
    ):
        session.add(Config(
            key=ia.INJECT_ADAPTERS_CONFIG_KEY,
            value={"rogue": {"context_file": "/etc/passwd"}},
        ))
        await session.flush()

        state = (await client.get(
            "/api/v1/distribution", headers=auth_headers
        )).json()

        assert "rogue" not in [t["tool"] for t in state["targets"]]
        assert [r["tool"] for r in state["rejected"]] == ["rogue"]
        assert "project-relative" in state["rejected"][0]["reason"]

    async def test_a_healthy_registry_refuses_nothing(self, client, auth_headers):
        state = (await client.get(
            "/api/v1/distribution", headers=auth_headers
        )).json()

        assert state["rejected"] == []
        assert state["targets"]

    async def test_the_reason_comes_from_the_registry_not_a_second_copy(self):
        """One predicate, two readers. A second copy of these rules is what
        would let the screen say a row was kept while the writer dropped it."""
        assert ia.reject_reason("CLAUDE.md") is None
        assert "project-relative" in (ia.reject_reason("/etc/passwd") or "")
        assert "project-relative" in (ia.reject_reason("~/notes.md") or "")
        assert "project-relative" in (ia.reject_reason("../escape.md") or "")
        assert "no context_file" in (ia.reject_reason("") or "")

    async def test_a_non_object_entry_is_named_too(self, client, auth_headers, session):
        """N-5: `reject_reason` covers the `context_file` shapes, but an entry
        that is not a mapping at all was still dropped log-only — the same
        operator, the same vanished row, the same reason on the server."""
        session.add(Config(
            key=ia.INJECT_ADAPTERS_CONFIG_KEY, value={"stringly": "nope"},
        ))
        await session.flush()

        state = (await client.get(
            "/api/v1/distribution", headers=auth_headers
        )).json()

        assert [r["tool"] for r in state["rejected"]] == ["stringly"]
        assert "not an object" in state["rejected"][0]["reason"]

    async def test_the_registry_is_merged_once_per_request(
        self, client, auth_headers, monkeypatch
    ):
        """N-6: the one caller that needs both halves used to pay two SELECTs
        of the same config row and two merges."""
        calls = 0
        original = ia._resolve

        async def counting(session):
            nonlocal calls
            calls += 1
            return await original(session)

        monkeypatch.setattr(ia, "_resolve", counting)

        await client.get("/api/v1/distribution", headers=auth_headers)

        assert calls == 1
