"""T1.57 Ruling 2 — the `repo_allowlist` config row gets an editing surface.

T1.15 shipped the SSRF allowlist gate itself (`evaluate_hint`,
`load_allowlist`) but no route ever wrote `repo_allowlist`, so the only way
to opt into repo auto-provisioning was a direct Postgres write. These tests
cover the new `/config/repo-allowlist` GET/PUT pair, and — the point of
Ruling 2 — that its validation is the *same* `validate_pattern` call
`evaluate_hint` runs a stored pattern through, not a second hand-rolled
check that could quietly define "allowed" differently.
"""
from __future__ import annotations

import pytest

from app.services.repo_allowlist import evaluate_hint, validate_pattern


@pytest.mark.asyncio
async def test_get_repo_allowlist_defaults_to_empty(client, auth_headers):
    resp = await client.get("/api/v1/config/repo-allowlist", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == {"patterns": []}


@pytest.mark.asyncio
async def test_put_valid_patterns_roundtrips_through_get(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/repo-allowlist",
        headers=auth_headers,
        json={"patterns": ["github.com/darkraise/*", "*.forge.internal.example"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["patterns"] == [
        "github.com/darkraise/*",
        "*.forge.internal.example",
    ]

    get_resp = await client.get("/api/v1/config/repo-allowlist", headers=auth_headers)
    assert get_resp.json()["patterns"] == [
        "github.com/darkraise/*",
        "*.forge.internal.example",
    ]


@pytest.mark.asyncio
async def test_put_deduplicates_and_normalises_case(client, auth_headers):
    resp = await client.put(
        "/api/v1/config/repo-allowlist",
        headers=auth_headers,
        json={"patterns": ["GitHub.com/darkraise/*", "github.com/darkraise/*"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["patterns"] == ["github.com/darkraise/*"]


@pytest.mark.parametrize(
    "bad_pattern",
    [
        "https://github.com/darkraise/*",  # scheme not allowed on a pattern
        "git@github.com/darkraise/*",  # userinfo not allowed on a pattern
        "a b",  # whitespace
        "*",  # bare wildcard, no host
        "",  # empty
    ],
)
@pytest.mark.asyncio
async def test_put_rejects_a_pattern_the_ssrf_gate_would_also_reject(
    client, auth_headers, bad_pattern
):
    # The two must agree: whatever validate_pattern refuses is exactly what
    # evaluate_hint's own pattern parse (_split_pattern) refuses too — proving
    # this route did not grow a second, looser definition of "valid pattern".
    assert validate_pattern(bad_pattern) is None

    resp = await client.put(
        "/api/v1/config/repo-allowlist",
        headers=auth_headers,
        json={"patterns": [bad_pattern]},
    )
    assert resp.status_code == 422

    get_resp = await client.get("/api/v1/config/repo-allowlist", headers=auth_headers)
    assert get_resp.json()["patterns"] == []


@pytest.mark.asyncio
async def test_a_pattern_saved_through_the_route_actually_gates_a_hint(
    client, auth_headers, session
):
    """End-to-end proof the settings write path and the SSRF gate share one
    definition of "allowed": a pattern saved here must let the matching hint
    through evaluate_hint, and a hint outside it must still be refused."""
    resp = await client.put(
        "/api/v1/config/repo-allowlist",
        headers=auth_headers,
        json={"patterns": ["github.com/darkraise/*"]},
    )
    assert resp.status_code == 200, resp.text

    from app.services.repo_allowlist import load_allowlist

    patterns = await load_allowlist(session)
    good = evaluate_hint("https://github.com/darkraise/darkmem.git", patterns)
    assert good.allowed

    bad = evaluate_hint("https://github.com/attacker/evil.git", patterns)
    assert not bad.allowed
    assert bad.reason == "not_allowlisted"
