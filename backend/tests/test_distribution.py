"""T3.19 — the Distribution surface's live half (doc 13 §6.5).

The tab's own rendering is `frontend`'s to test. What only the server can
answer is that the screen shows the system rather than itself: the targets come
from T3.11's registry.
"""

from __future__ import annotations

import importlib.util
import json

import pytest
from sqlalchemy import text

from app.models.config import Config
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


class TestThePolicyIsGone:
    """The token budget, the watch switch and the curb steered nothing: no
    inject writer ever read them. The writer modules and the policy door
    went together, and the read keeps only the adapter targets."""

    async def test_inject_modules_and_policy_route_are_gone(self):
        from app.main import app

        for name in (
            "app.services.inject_watch",
            "app.services.inject_fill",
            "app.services.inject_block",
            "app.services.inject_journal",
        ):
            assert importlib.util.find_spec(name) is None, name

        routes = {
            (method, route.path)
            for route in app.routes
            for method in (getattr(route, "methods", None) or ())
        }
        assert ("PUT", "/api/v1/distribution/policy") not in routes
        assert ("GET", "/api/v1/distribution") in routes

    async def test_distribution_get_has_no_policy_keys(self, client, auth_headers):
        response = await client.get("/api/v1/distribution", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert "policy" not in body
        for target in body["targets"]:
            assert "watched" not in target
            assert "refresh" not in target
        assert {t["tool"] for t in body["targets"]} >= {
            "claude-code", "cursor", "codex", "cline",
        }

    async def test_the_read_requires_auth(self, client):
        assert (await client.get("/api/v1/distribution")).status_code in (401, 403)


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

    async def test_a_malformed_override_of_a_known_tool_is_not_a_refusal(
        self, client, auth_headers, session
    ):
        """NEW-2, a regression the first N-5 fix introduced: the rejection was
        written from the raw-config loop while the shipped default survived the
        merge, so `cursor` came back in **both** lists and the screen said no
        block was written for a tool that has one."""
        session.add(Config(
            key=ia.INJECT_ADAPTERS_CONFIG_KEY, value={"cursor": "nope"},
        ))
        await session.flush()

        state = (await client.get(
            "/api/v1/distribution", headers=auth_headers
        )).json()

        assert "cursor" in [t["tool"] for t in state["targets"]]
        assert [r["tool"] for r in state["rejected"]] == ["cursor"]
        assert "still in force" in state["rejected"][0]["reason"]

    async def test_an_unknown_tool_with_no_default_is_a_plain_refusal(
        self, client, auth_headers, session
    ):
        """The other half, and the one the first test happened to use — which
        is why it could not fail on the defect above."""
        session.add(Config(
            key=ia.INJECT_ADAPTERS_CONFIG_KEY, value={"stringly": "nope"},
        ))
        await session.flush()

        state = (await client.get(
            "/api/v1/distribution", headers=auth_headers
        )).json()

        assert "stringly" not in [t["tool"] for t in state["targets"]]
        assert "still in force" not in state["rejected"][0]["reason"]
