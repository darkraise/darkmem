"""The two Flags-tab surfaces that had a config row but no API field.

Both gaps rendered in the UI as "no config row exists for these yet, in either
mode", and in both cases a row had existed for months. The doc 07 §4 graph
channels have been in ``FEATURE_FLAGS_DEFAULTS`` since T2.32; the verification
ladder's thresholds have had a ``config`` row, floors, a clamp and a
measurement licence since T2.03. What was missing was the response field and
the door — a different absence, and the only one these tests can keep closed.

The ladder half also pins the property that made the door worth building: a
clamp must be *visible in the response*, not only in the log. A settings form
that echoes the operator's own number back at them has told them the ladder is
running at that number, which is precisely what a clamp means it is not doing.
"""
from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import FEATURE_FLAGS_DEFAULTS
from app.repositories.fact_sources import (
    CORROBORATION_N_DEFAULT,
    CORROBORATION_N_DIVERSE,
    CORROBORATION_TIME_GAP_DAYS,
)
from app.services.feature_flags import MEASURABLE_FLAGS
from app.services.feature_flags import FEATURE_FLAGS_KEY
from app.services.ladder_config import LADDER_CONFIG_KEY, LADDER_MEASUREMENTS_KEY
from app.services.rank_fusion import GRAPH_CHANNELS, LIST_WEIGHT_KEYS

GRAPH_FLAGS = (
    "ppr_enabled",
    "w_ppr",
    "dual_level_enabled",
    "w_dual",
    "community_injection_enabled",
)


# ── the graph channels ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_feature_flags_serves_every_graph_flag(client, auth_headers):
    resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    for flag in GRAPH_FLAGS:
        assert flag in body, f"feature-flags missing {flag!r}: {body}"
        assert body[flag] == FEATURE_FLAGS_DEFAULTS[flag]


@pytest.mark.asyncio
async def test_graph_channels_pair_each_flag_with_its_own_weight(
    client, auth_headers
):
    """The pairing comes off ``GRAPH_CHANNELS``, never off a UI-side guess.

    A settings surface that pairs `ppr_enabled` with `w_dual` renders a control
    that writes the wrong row, and nothing about the result looks wrong.
    """
    resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    by_flag = {c["flag"]: c for c in resp.json()["graph_channels"]}

    assert set(by_flag) == {c.flag for c in GRAPH_CHANNELS}
    assert by_flag["ppr_enabled"]["weight_flag"] == "w_ppr"
    assert by_flag["dual_level_enabled"]["weight_flag"] == "w_dual"
    # Context augmentation, not a ranked list: there is no weight to serve, and
    # a 0.0 here would invent a knob the fusion does not read.
    assert by_flag["community_injection_enabled"]["weight_flag"] is None
    assert by_flag["community_injection_enabled"]["weight"] is None


@pytest.mark.asyncio
async def test_graph_channel_weights_are_list_weights_not_rank_arms(
    client, auth_headers
):
    """`w_ppr`/`w_dual` weight a ranked *list*; they are not `RankArm`s.

    Serving them under `rank_arms` would tell a client they multiply rows, and
    a UI acting on that would apply them per row the graph never proposed.
    """
    resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    body = resp.json()
    arm_flags = {arm["flag"] for arm in body["rank_arms"]}
    assert "w_ppr" not in arm_flags
    assert "w_dual" not in arm_flags
    assert {"w_ppr", "w_dual"} <= LIST_WEIGHT_KEYS


@pytest.mark.asyncio
async def test_graph_channels_carry_their_activation_task_id(client, auth_headers):
    resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    for channel in resp.json()["graph_channels"]:
        assert channel["activation"] == "T2.50"


@pytest.mark.asyncio
async def test_every_graph_flag_is_measurable(client, auth_headers):
    """Doc 07 §4: all three land inert and T2.50 measures them before any moves.

    A flippable control with no `unmeasured` badge reads as proven.
    """
    resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    advertised = set(resp.json()["measurable_flags"])
    assert set(GRAPH_FLAGS) <= advertised
    assert set(GRAPH_FLAGS) <= set(MEASURABLE_FLAGS)


@pytest.mark.asyncio
async def test_put_roundtrips_the_graph_flags(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"ppr_enabled": True, "w_ppr": 0.2, "community_injection_enabled": True},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ppr_enabled"] is True
    assert body["w_ppr"] == 0.2
    assert body["community_injection_enabled"] is True
    # The PUT response is built by the same builder as the GET, so the channel
    # list reflects the write rather than the pre-write state.
    by_flag = {c["flag"]: c for c in body["graph_channels"]}
    assert by_flag["ppr_enabled"]["enabled"] is True
    assert by_flag["ppr_enabled"]["weight"] == 0.2

    again = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    assert again.json()["w_ppr"] == 0.2


@pytest.mark.asyncio
async def test_put_rejects_an_out_of_range_list_weight(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/feature-flags", headers=auth_headers, json={"w_dual": 9}
    )
    assert resp.status_code == 422


# ── the verification ladder ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_ladder_reads_the_shipped_floors_with_no_row(client, auth_headers):
    resp = await client.get(
        "/api/v1/config/verification-ladder", headers=auth_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["row_present"] is False
    assert body["measured"] == []
    assert body["measurement_task"] == "T2.40"

    by_name = {p["name"]: p for p in body["params"]}
    assert by_name["n_default"]["effective"] == CORROBORATION_N_DEFAULT
    assert by_name["n_diverse"]["effective"] == CORROBORATION_N_DIVERSE
    assert by_name["time_gap_days"]["effective"] == CORROBORATION_TIME_GAP_DAYS
    for param in body["params"]:
        # No row means nothing was committed — distinct from a row that happens
        # to hold the defaults, which is what `row_present` separates.
        assert param["committed"] is None
        assert param["state"] == "default"
        assert param["note"] is None


@pytest.mark.asyncio
async def test_tightening_is_honoured_and_says_so(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/verification-ladder",
        headers=auth_headers,
        json={"n_default": 5},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["row_present"] is True
    n_default = next(p for p in body["params"] if p["name"] == "n_default")
    assert n_default["committed"] == 5
    assert n_default["effective"] == 5
    assert n_default["state"] == "honoured"


@pytest.mark.asyncio
async def test_an_unbacked_loosening_clamps_and_the_response_shows_it(
    client, auth_headers
):
    """The whole reason this door answers with a report.

    The clamp already existed and already logged. What it did not do was reach
    the operator: a form that echoes 1 back has told them the ladder promotes
    at one origin. It promotes at three.
    """
    resp = await client.put(
        "/api/v1/config/verification-ladder",
        headers=auth_headers,
        json={"n_default": 1},
    )
    assert resp.status_code == 200
    n_default = next(
        p for p in resp.json()["params"] if p["name"] == "n_default"
    )
    assert n_default["committed"] == 1
    assert n_default["effective"] == CORROBORATION_N_DEFAULT
    assert n_default["state"] == "clamped"
    assert n_default["measured"] is False
    assert n_default["note"] and "T2.40" in n_default["note"], (
        "a clamp note must name the gate, so the operator learns what would "
        "license the value rather than only that it was refused"
    )


@pytest.mark.asyncio
async def test_a_measured_parameter_may_sit_below_its_floor(
    client, auth_headers, session
):
    from app.models.config import Config

    session.add(
        Config(key=LADDER_MEASUREMENTS_KEY, value={"measured": ["n_diverse"]})
    )
    session.add(Config(key=LADDER_CONFIG_KEY, value={"n_diverse": 1}))
    await session.commit()

    resp = await client.get(
        "/api/v1/config/verification-ladder", headers=auth_headers
    )
    body = resp.json()
    assert body["measured"] == ["n_diverse"]
    n_diverse = next(p for p in body["params"] if p["name"] == "n_diverse")
    assert n_diverse["effective"] == 1
    assert n_diverse["state"] == "honoured"
    assert n_diverse["measured"] is True


@pytest.mark.asyncio
async def test_an_explicit_null_returns_a_parameter_to_its_floor(
    client, auth_headers
):
    await client.put(
        "/api/v1/config/verification-ladder",
        headers=auth_headers,
        json={"n_default": 5},
    )
    resp = await client.put(
        "/api/v1/config/verification-ladder",
        headers=auth_headers,
        json={"n_default": None},
    )
    n_default = next(
        p for p in resp.json()["params"] if p["name"] == "n_default"
    )
    assert n_default["committed"] is None
    assert n_default["effective"] == CORROBORATION_N_DEFAULT
    assert n_default["state"] == "default"


@pytest.mark.asyncio
async def test_an_omitted_field_is_left_alone(client, auth_headers):
    await client.put(
        "/api/v1/config/verification-ladder",
        headers=auth_headers,
        json={"n_default": 5, "time_gap_days": 14},
    )
    resp = await client.put(
        "/api/v1/config/verification-ladder",
        headers=auth_headers,
        json={"time_gap_days": 21},
    )
    by_name = {p["name"]: p for p in resp.json()["params"]}
    assert by_name["time_gap_days"]["effective"] == 21
    assert by_name["n_default"]["effective"] == 5, (
        "a partial update must not reset the fields it omits"
    )


@pytest.mark.asyncio
async def test_the_door_writes_only_known_thresholds(client, auth_headers, session):
    """A hand-edited row's junk keys do not survive an edit through the door."""
    from sqlalchemy import select
    from app.models.config import Config

    session.add(Config(key=LADDER_CONFIG_KEY, value={"nonsense": 4, "n_default": 5}))
    await session.commit()

    await client.put(
        "/api/v1/config/verification-ladder",
        headers=auth_headers,
        json={"n_diverse": 3},
    )
    row = (
        await session.execute(
            select(Config).where(Config.key == LADDER_CONFIG_KEY)
        )
    ).scalar_one()
    await session.refresh(row)
    assert "nonsense" not in row.value
    assert row.value["n_default"] == 5


@pytest.mark.asyncio
async def test_the_ladder_door_requires_auth(client):
    assert (await client.get("/api/v1/config/verification-ladder")).status_code == 401


# ── concurrent writes to one config row ───────────────────────────────
#
# The `client` fixture binds ONE connection for the whole request, so two
# requests through it cannot race -- they deadlock on the shared asyncpg
# connection instead, proving nothing. These tests open independent sessions
# against the real engine, which is the only level at which this race exists.


@pytest.mark.asyncio
async def test_the_config_lock_excludes_a_second_writer_on_the_same_key():
    """Deterministic proof of the mutual exclusion, not a timing hope.

    Both config PUTs read a JSON blob, patch it in Python and write the whole
    blob back. Measured in a browser before this lock: resetting two ladder
    thresholds inside one round-trip sent both patches, each read the row
    before the other committed, and the row ended up holding only one of them.
    Both requests answered 200 and nothing anywhere reported a problem -- the
    operator just sees the control they reset sitting at its old value.
    """
    from tests.conftest import test_engine
    from app.api.routes.config import _lock_config_row

    async with AsyncSession(test_engine) as holder:
        await _lock_config_row(holder, LADDER_CONFIG_KEY)
        async with AsyncSession(test_engine) as contender:
            taken = (
                await contender.execute(
                    text("SELECT pg_try_advisory_xact_lock(hashtext(:k))"),
                    {"k": LADDER_CONFIG_KEY},
                )
            ).scalar_one()
            assert taken is False, (
                "a second writer took the same key's lock while the first held "
                "it -- the read-modify-write is not serialised"
            )

            # Per key, not global: a lock that also blocked unrelated config
            # writes would serialise the whole settings surface behind one
            # slow save.
            other = (
                await contender.execute(
                    text("SELECT pg_try_advisory_xact_lock(hashtext(:k))"),
                    {"k": FEATURE_FLAGS_KEY},
                )
            ).scalar_one()
            assert other is True
        await holder.rollback()


@pytest.mark.asyncio
async def test_two_concurrent_ladder_clears_both_survive():
    """The composed read-modify-write, run concurrently for real.

    **This one cannot prove the fix and must not be read as doing so**: with
    the lock removed it still passes, because two coroutines that each open a
    connection do not reliably interleave between their read and their write.
    A barrier would make it deterministic and would then deadlock against the
    very lock it is meant to exercise. Its sibling above is the teeth --
    verified red with the lock neutered. This one is a smoke check that the
    locked path composes and commits at all.
    """
    from tests.conftest import test_engine
    from app.api.routes.config import _lock_config_row
    from app.models.config import Config

    async with AsyncSession(test_engine) as setup:
        await setup.execute(
            text(
                "INSERT INTO config (key, value) VALUES (:k, :v) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            ),
            {"k": LADDER_CONFIG_KEY, "v": '{"n_default": 9, "n_diverse": 4}'},
        )
        await setup.commit()

    async def clear(name: str) -> None:
        """One request's worth of read-modify-write, lock included."""
        async with AsyncSession(test_engine) as s:
            await _lock_config_row(s, LADDER_CONFIG_KEY)
            row = (
                await s.execute(
                    select(Config).where(Config.key == LADDER_CONFIG_KEY)
                )
            ).scalar_one()
            current = dict(row.value)
            current.pop(name, None)
            row.value = current
            await s.commit()

    await asyncio.gather(clear("n_default"), clear("n_diverse"))

    async with AsyncSession(test_engine) as check:
        value = (
            await check.execute(
                text("SELECT value FROM config WHERE key = :k"),
                {"k": LADDER_CONFIG_KEY},
            )
        ).scalar_one()
        assert value == {}, (
            f"one clear was overwritten by the other; row holds {value}"
        )

    async with AsyncSession(test_engine) as cleanup:
        await cleanup.execute(
            text("DELETE FROM config WHERE key = :k"), {"k": LADDER_CONFIG_KEY}
        )
        await cleanup.commit()
