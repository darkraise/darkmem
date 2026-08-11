"""T4.06 — watch mode: re-inject as the working context shifts (doc 15 §3.5).

Three claims, and each one is a refusal or a record rather than a feature:

- **Off by default.** Doc 15 §3.5 defers watch "behind a measured need, gated
  by a `config` flag". A cadence accepted but not gated would be the flag
  nobody turned on taking effect anyway.
- **Every re-inject journals**, carrying the trigger. Session-start pushes
  already journal; what a *watch* record has to add is *why* the context
  swapped, or the human sees a second block appear with nothing distinguishing
  it from the first.
- **The curb stops it immediately** — server-side. The client is the thing
  being curbed, so a curb it enforces itself is a setting that appears to work
  and does not.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.config import Config
from app.services import inject_watch as iw
from app.services.events import list_events
from app.services.inject_adapters import UnsupportedCadence, resolve_adapter
from app.services.layer_composition import ComposedResult

from tests.test_inject_fill import _memory, _result, _verified_fact

pytestmark = pytest.mark.asyncio

PROJECT = "t4-06-watch"
POLICY_KEY = "distribution_policy"


async def _set_policy(session, **values) -> None:
    row = (
        await session.execute(select(Config).where(Config.key == POLICY_KEY))
    ).scalar_one_or_none()
    if row is None:
        session.add(Config(key=POLICY_KEY, value=values))
    else:
        row.value = {**(row.value or {}), **values}
    await session.flush()


def _content() -> ComposedResult:
    return _result(_verified_fact("f1", "a verified claim"), _memory("m1", "a summary"))


async def _inject_rows(session):
    items, _ = await list_events(
        session, project=PROJECT, event_type="inject", limit=50
    )
    return items


# ─────────────── off by default ───────────────


class TestOffByDefault:
    async def test_a_watch_refresh_is_refused_when_nothing_enabled_it(self, session):
        with pytest.raises(iw.WatchDisabled):
            await iw.watch_refresh(
                session, tool="claude-code", trigger="project_changed",
                result=_content(), project=PROJECT,
            )

    async def test_the_refusal_writes_no_journal_row(self, session):
        """A refused watch is not a push, and a record of one would put a
        context swap in the stream that no session received."""
        with pytest.raises(iw.WatchDisabled):
            await iw.watch_refresh(
                session, tool="claude-code", trigger="project_changed",
                result=_content(), project=PROJECT,
            )

        assert await _inject_rows(session) == []

    async def test_the_adapter_door_still_refuses_the_cadence_while_off(self, session):
        """The two gates are the same flag read at two doors. If the registry
        kept refusing `watch` after the flag went on, the mode would be
        enabled and unreachable; if it accepted while off, the flag would be
        decoration."""
        with pytest.raises(UnsupportedCadence):
            await resolve_adapter(session, "claude-code", cadence=iw.REFRESH_WATCH)

    async def test_the_adapter_door_accepts_the_cadence_once_enabled(self, session):
        await _set_policy(session, watch_enabled=True)

        adapter = await resolve_adapter(
            session, "claude-code", cadence=iw.REFRESH_WATCH
        )

        assert adapter.tool == "claude-code"


# ─────────────── every re-inject journals ───────────────


class TestEveryRefreshJournals:
    async def test_a_watch_refresh_journals_one_inject_row(self, session):
        await _set_policy(session, watch_enabled=True)

        out = await iw.watch_refresh(
            session, tool="claude-code", trigger="project_changed",
            result=_content(), project=PROJECT,
        )
        await session.flush()

        rows = await _inject_rows(session)
        assert len(rows) == 1
        assert rows[0]["payload"]["tokens_used"] == out.tokens_used

    async def test_the_record_names_the_trigger_that_caused_the_swap(self, session):
        """Without it a re-inject is indistinguishable from a session start in
        the timeline, and "the human can see the swap" reduces to seeing that
        *something* was pushed twice."""
        await _set_policy(session, watch_enabled=True)

        await iw.watch_refresh(
            session, tool="claude-code", trigger="file_opened",
            result=_content(), project=PROJECT,
        )
        await session.flush()

        payload = (await _inject_rows(session))[0]["payload"]
        assert payload["trigger"] == "file_opened"
        assert payload["cadence"] == iw.REFRESH_WATCH

    async def test_a_session_start_push_records_no_trigger_rather_than_a_fake_one(
        self, session
    ):
        """`record_inject`'s other caller has no trigger to report, and a
        default of `session_start` there would invent a cause for a push that
        had none."""
        from app.services import inject_journal as ij

        await ij.record_inject(
            session, tool="claude-code", context_file="CLAUDE.md", project=PROJECT,
            budget_tokens=2000, tokens_used=10,
        )
        await session.flush()

        payload = (await _inject_rows(session))[0]["payload"]
        assert payload["trigger"] is None
        assert payload["cadence"] == iw.REFRESH_SESSION_START

    async def test_every_refresh_journals_not_only_the_first(self, session):
        """"Every re-inject journals" is a claim about the second one: a
        writer that recorded only changes would go quiet exactly when the
        context is churning."""
        await _set_policy(session, watch_enabled=True)

        for trigger in ("project_changed", "file_opened", "context_changed"):
            await iw.watch_refresh(
                session, tool="claude-code", trigger=trigger,
                result=_content(), project=PROJECT,
            )
        await session.flush()

        triggers = [row["payload"]["trigger"] for row in await _inject_rows(session)]
        assert sorted(triggers) == ["context_changed", "file_opened", "project_changed"]

    async def test_an_unknown_trigger_is_refused_rather_than_recorded(self, session):
        """The journal is the record a human reads to explain a swap. A
        free-form string there makes the set of causes unenumerable, and the
        first misspelling becomes a cause nobody can search for."""
        await _set_policy(session, watch_enabled=True)

        with pytest.raises(ValueError):
            await iw.watch_refresh(
                session, tool="claude-code", trigger="vibes",
                result=_content(), project=PROJECT,
            )
        assert await _inject_rows(session) == []


# ─────────────── the curb stops it immediately ───────────────


class TestCurb:
    async def test_a_curbed_install_refuses_the_refresh(self, session):
        await _set_policy(session, watch_enabled=True, curbed=True)

        with pytest.raises(iw.PushCurbed):
            await iw.watch_refresh(
                session, tool="claude-code", trigger="project_changed",
                result=_content(), project=PROJECT,
            )

    async def test_the_curb_wins_over_an_enabled_watch(self, session):
        """Both flags on is the state a human reaches by curbing an install
        that had watch running — the point at which the curb has to win, or it
        is not a stop control."""
        await _set_policy(session, watch_enabled=True, curbed=True)

        with pytest.raises(iw.PushCurbed):
            await iw.watch_refresh(
                session, tool="claude-code", trigger="file_opened",
                result=_content(), project=PROJECT,
            )
        assert await _inject_rows(session) == []

    async def test_the_curb_is_read_per_refresh_not_cached(self, session):
        """"Takes effect immediately" is exactly this: a curb flipped between
        two refreshes has to stop the second one."""
        await _set_policy(session, watch_enabled=True)
        await iw.watch_refresh(
            session, tool="claude-code", trigger="project_changed",
            result=_content(), project=PROJECT,
        )

        await _set_policy(session, curbed=True)

        with pytest.raises(iw.PushCurbed):
            await iw.watch_refresh(
                session, tool="claude-code", trigger="file_opened",
                result=_content(), project=PROJECT,
            )
        await session.flush()
        assert len(await _inject_rows(session)) == 1


# ─────────────── the block itself ───────────────


class TestTheBlock:
    async def test_the_refresh_spends_the_configured_budget_not_its_own(self, session):
        """Watch adds a cadence, not a second budget authority — a re-inject
        that computed its own would exceed the operator's on every swap."""
        await _set_policy(session, watch_enabled=True, token_budget=0)

        out = await iw.watch_refresh(
            session, tool="claude-code", trigger="project_changed",
            result=_content(), project=PROJECT,
        )

        assert out.items == []
        assert out.tokens_used == 0

    async def test_an_unknown_tool_is_refused_before_anything_is_journalled(
        self, session
    ):
        from app.services.inject_adapters import UnknownTool

        await _set_policy(session, watch_enabled=True)

        with pytest.raises(UnknownTool):
            await iw.watch_refresh(
                session, tool="emacs", trigger="project_changed",
                result=_content(), project=PROJECT,
            )
        assert await _inject_rows(session) == []


# ─────────────── the flag has one owner ───────────────


class TestOneFlagOneOwner:
    async def test_the_service_reads_the_row_the_door_writes(self):
        """Two spellings of the config key would make the switch on the
        distribution surface set a flag nothing reads — the quietest possible
        failure, since both halves look correct in isolation."""
        from app.api.routes.distribution import DISTRIBUTION_CONFIG_KEY

        assert iw.DISTRIBUTION_CONFIG_KEY == DISTRIBUTION_CONFIG_KEY

    async def test_the_door_serves_watch_off_for_an_install_that_never_set_it(
        self, client, auth_headers
    ):
        response = await client.get("/api/v1/distribution", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["policy"]["watch_enabled"] is False

    async def test_turning_it_on_at_the_door_is_what_the_service_reads(
        self, client, auth_headers, session
    ):
        written = await client.put(
            "/api/v1/distribution/policy",
            json={"token_budget": 2000, "curbed": False, "watch_enabled": True},
            headers=auth_headers,
        )
        assert written.status_code == 200, written.text

        assert await iw.watch_enabled(session) is True
