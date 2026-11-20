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


@pytest.mark.asyncio
async def test_flags_answer_carries_no_flag_measurements(client, auth_headers, session):
    from app.models.config import Config

    session.add(Config(key="flag_measurements", value={"measured": ["reranker_enabled"]}))
    await session.flush()

    body = (await client.get("/api/v1/config/feature-flags", headers=auth_headers)).json()

    assert {"flag_measurements", "measured_flags", "measurable_flags"}.isdisjoint(body)


async def test_the_response_serves_the_ranges_the_put_enforces(client, auth_headers):
    """The Flags dialog shows and enforces these, so they are the PUT's own
    bounds rather than a copy the form could drift from."""
    body = (await client.get("/api/v1/config/feature-flags", headers=auth_headers)).json()
    bounds = body["numeric_bounds"]
    for key in ("confidence_rank_gamma", "w_importance", "w_heat", "w_recency",
                "w_context_boost", "w_ppr", "w_dual"):
        assert bounds[key] == {"min": 0, "max": 5}, key
    assert bounds["pipeline_concurrency"] == {"min": 1, "max": 20}

    over = await client.put(
        "/api/v1/config/feature-flags",
        json={"confidence_rank_gamma": bounds["confidence_rank_gamma"]["max"] + 1},
        headers=auth_headers,
    )
    assert over.status_code == 422
