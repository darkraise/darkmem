"""GET /api/v1/auth/security-posture — the live security posture, never a
hardcoded assumption (T1.63 ruling 3).

Every field the route returns must come from a live read of ``settings`` or
the shared ``login_rate_limiter`` instance at call time, not a coded
default echoed back. T1.62 is about to flip ``trust_proxy_headers``'s
default, and this is the surface an operator uses to see which posture is
actually in effect once that lands — a route that answered a hardcoded
value would render exactly the same before and after that flip, which is
the failure this test suite exists to catch.

Also covers: the tri-state ``cookie_secure`` resolution, and that no
credential (JWT_SECRET, DB_PASSWORD, any provider api_key) can appear on
the response.
"""
from __future__ import annotations

import pytest

from app.config import settings
from app.services.login_rate_limit import login_rate_limiter


async def test_requires_auth(client):
    response = await client.get("/api/v1/auth/security-posture")
    assert response.status_code == 401


async def test_reads_live_trust_proxy_headers_not_a_hardcoded_default(
    client, auth_headers, monkeypatch,
):
    """Mutation proof for ruling 3: flipping the live setting must flip the
    response. A route that hardcoded `true` (today's default) would pass
    the first assertion and fail the second."""
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    on = await client.get("/api/v1/auth/security-posture", headers=auth_headers)
    assert on.status_code == 200
    assert on.json()["trust_proxy_headers"] is True

    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    off = await client.get("/api/v1/auth/security-posture", headers=auth_headers)
    assert off.status_code == 200
    assert off.json()["trust_proxy_headers"] is False


@pytest.mark.parametrize(
    "cookie_secure,environment,expected_value,expected_explicit",
    [
        (None, "production", True, False),
        (None, "development", False, False),
        (False, "production", False, True),
        (True, "development", True, True),
    ],
)
async def test_cookie_secure_tri_state_resolution(
    client, auth_headers, monkeypatch,
    cookie_secure, environment, expected_value, expected_explicit,
):
    """LAN posture only — `trust_proxy_headers` is pinned off because T4.03
    collapses the tri-state to enforced when it is on, so leaving it to the
    ambient default would make these rows depend on a setting they do not name.

    Unset derives Secure-only-in-production; an explicit value always
    wins over the environment, matching `settings.session_cookie_secure`
    exactly (this route must never recompute the rule itself)."""
    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    monkeypatch.setattr(settings, "cookie_secure", cookie_secure)
    monkeypatch.setattr(settings, "environment", environment)

    response = await client.get("/api/v1/auth/security-posture", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["cookie_secure"] is expected_value
    assert body["cookie_secure_explicit"] is expected_explicit
    assert body["environment"] == environment


async def test_mcp_allowed_hosts_reflects_the_live_env_value(
    client, auth_headers, monkeypatch,
):
    monkeypatch.setattr(
        settings, "mcp_allowed_hosts", "192.168.0.195:8000, *",
    )
    response = await client.get("/api/v1/auth/security-posture", headers=auth_headers)
    assert response.json()["mcp_allowed_hosts"] == ["192.168.0.195:8000", "*"]

    monkeypatch.setattr(settings, "mcp_allowed_hosts", "")
    empty = await client.get("/api/v1/auth/security-posture", headers=auth_headers)
    assert empty.json()["mcp_allowed_hosts"] == []


async def test_rate_limit_reads_the_shared_limiter_instance(
    client, auth_headers, monkeypatch,
):
    """Mutation proof: the numbers must come from `login_rate_limiter`, the
    same instance `auth_login` checks — not a second, independently
    hand-maintained copy that could drift from the real threshold."""
    monkeypatch.setattr(login_rate_limiter, "max_failures", 9)
    monkeypatch.setattr(login_rate_limiter, "window_seconds", 111.0)
    monkeypatch.setattr(login_rate_limiter, "lockout_seconds", 222.0)

    response = await client.get("/api/v1/auth/security-posture", headers=auth_headers)
    body = response.json()
    assert body["rate_limit_max_failures"] == 9
    assert body["rate_limit_window_seconds"] == 111.0
    assert body["rate_limit_lockout_seconds"] == 222.0


async def test_never_leaks_a_credential(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "super-secret-jwt-value-xyz")
    monkeypatch.setattr(settings, "db_password", "super-secret-db-password")

    response = await client.get("/api/v1/auth/security-posture", headers=auth_headers)
    body = response.json()

    forbidden_keys = {
        "jwt_secret", "db_password", "api_key", "llm_embedding",
        "llm_extraction", "llm_classification", "llm_reasoning",
        "llm_summarization", "llm_reranker",
    }
    assert forbidden_keys.isdisjoint(body.keys())

    raw = response.text
    assert "super-secret-jwt-value-xyz" not in raw
    assert "super-secret-db-password" not in raw


# ---------------------------------------------------------------------------
# The read-only worker's posture (increment 7, spec §9.5 as redesigned after B1)
# ---------------------------------------------------------------------------


async def test_read_only_defaults_off(client, auth_headers):
    """Prod is the default posture, and it must be byte-identical to what it
    was before the flag existed."""
    body = (
        await client.get("/api/v1/auth/security-posture", headers=auth_headers)
    ).json()
    assert body["read_only"] is False
    assert body["read_only_token_rotation_disabled"] is False


async def test_read_only_reports_the_token_rotation_cost(
    client, auth_headers, monkeypatch,
):
    """The flag's cost is reported the way `cookie_secure_clamped` reports its
    clamp. Under the flag a refresh no longer blocklists the token it replaces,
    so a captured pre-refresh token stays valid until its own `exp` — an
    operator must be able to read that off the posture rather than infer it
    from a runbook."""
    monkeypatch.setattr(settings, "read_only", True)

    body = (
        await client.get("/api/v1/auth/security-posture", headers=auth_headers)
    ).json()

    assert body["read_only"] is True
    assert body["read_only_token_rotation_disabled"] is True
