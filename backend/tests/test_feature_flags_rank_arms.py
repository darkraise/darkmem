"""T1.57 Ruling 1 — the feature-flags REST surface exposes the w_* rank
arms and their activation task ids.

T1.31 wired ``w_importance``/``w_heat``/``w_recency`` into
``FEATURE_FLAGS_DEFAULTS`` and ``RANK_ARMS`` (each carrying its own
``activation`` task id), but the REST response never declared the fields —
Pydantic's default ``extra="ignore"`` behaviour silently dropped them, so a
client reading ``/config/feature-flags`` could not tell an arm at weight 0
from an arm that does not exist. ``rank_arms`` is read straight from
``RANK_ARMS`` so the UI's "inactive, activated by T2.30" label and the
backend's own bookkeeping can never drift apart.
"""
from __future__ import annotations

import pytest

from app.config import FEATURE_FLAGS_DEFAULTS
from app.services.feature_flags import MEASURABLE_FLAGS
from app.services.rank_fusion import RANK_ARMS


@pytest.mark.asyncio
async def test_feature_flags_exposes_the_three_future_arms(client, auth_headers):
    resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    for flag in ("w_importance", "w_heat", "w_recency", "w_context_boost"):
        assert flag in body, f"feature-flags missing {flag!r}: {body}"
        assert body[flag] == FEATURE_FLAGS_DEFAULTS[flag]


@pytest.mark.asyncio
async def test_rank_arms_carry_their_activation_task_id_from_the_backend(
    client, auth_headers
):
    resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    assert resp.status_code == 200
    by_flag = {arm["flag"]: arm for arm in resp.json()["rank_arms"]}

    assert by_flag["w_importance"]["activation"] == "T2.30"
    assert by_flag["w_heat"]["activation"] == "T2.31"
    assert by_flag["w_recency"]["activation"] == "T2.31"
    # The already-live arm carries no activation id — an id here would claim
    # a shipped arm is still dormant.
    assert by_flag["confidence_rank_gamma"]["activation"] is None


@pytest.mark.asyncio
async def test_rank_arms_response_has_one_entry_per_backend_arm(client, auth_headers):
    # Proves the wire list is read from RANK_ARMS rather than hand-copied:
    # adding or removing a RankArm changes this response with no route edit.
    resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    flags_on_wire = {arm["flag"] for arm in resp.json()["rank_arms"]}
    assert flags_on_wire == {arm.flag for arm in RANK_ARMS}


@pytest.mark.asyncio
async def test_put_roundtrips_the_three_future_arms(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"w_importance": 0.4, "w_heat": 0.2, "w_recency": 0.1},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["w_importance"] == 0.4
    assert body["w_heat"] == 0.2
    assert body["w_recency"] == 0.1

    by_flag = {arm["flag"]: arm for arm in body["rank_arms"]}
    assert by_flag["w_importance"]["value"] == 0.4

    get_resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    assert get_resp.json()["w_importance"] == 0.4


@pytest.mark.asyncio
async def test_put_rejects_out_of_range_future_arm(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/feature-flags",
        headers=auth_headers,
        json={"w_importance": -1.0},
    )
    assert resp.status_code == 422


# ── Ruling 3 — "visibly unmeasured" reads from a durable config row ────


@pytest.mark.asyncio
async def test_measurable_flags_are_advertised_and_none_are_measured_yet(
    client, auth_headers
):
    # docs/planning/gate-ledger.md's "Arm activation log" has never recorded
    # an entry, so a fresh deploy must report every measurable flag as
    # unmeasured — never a hardcoded frontend guess.
    resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    body = resp.json()
    assert set(body["measurable_flags"]) == set(MEASURABLE_FLAGS)
    assert body["measured_flags"] == []


@pytest.mark.asyncio
async def test_measured_flags_come_from_the_config_row_not_a_guess(
    client, auth_headers, session
):
    from sqlalchemy import select

    from app.models.config import Config
    from app.services.feature_flags import FLAG_MEASUREMENTS_KEY

    session.add(
        Config(key=FLAG_MEASUREMENTS_KEY, value={"measured": ["reranker_enabled"]})
    )
    await session.commit()

    resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    assert resp.json()["measured_flags"] == ["reranker_enabled"]

    # A name outside MEASURABLE_FLAGS in the row is filtered, not trusted
    # verbatim — the row is a marker, not a free-form claim surface.
    result = await session.execute(
        select(Config).where(Config.key == FLAG_MEASUREMENTS_KEY)
    )
    row = result.scalar_one()
    row.value = {"measured": ["reranker_enabled", "not_a_real_flag"]}
    await session.commit()

    resp = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    assert resp.json()["measured_flags"] == ["reranker_enabled"]
