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
