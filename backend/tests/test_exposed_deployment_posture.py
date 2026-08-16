"""T4.03 — the exposed-deployment posture, end to end through the route.

`test_client_ip_attribution.py` pins `_client_ip` as a unit. This file pins the
two things that unit test cannot see: that the *limiter* really buckets on the
address the function returns, and that the `cookie_secure` tri-state collapses
to enforced once a trusted proxy is declared (doc 18 §4, §9).

The attack these tests exist for is bucket rotation. A limiter keyed on
anything the client can name is not a limiter: the attacker sends a fresh value
per guess, every guess lands in an empty bucket, and the lockout never fires.
So each lockout test asserts the 429 *arrives* while the attacker is rotating
the header they control — a test that only checked the un-rotated case would
pass against a limiter keyed on the leftmost `X-Forwarded-For`.
"""
from __future__ import annotations

import logging

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.responses import JSONResponse

from app.api.auth import hash_password, set_auth_cookie
from app.api.routes import auth as auth_routes
from app.config import Settings, settings
from app.models.config import Config
from app.services.login_rate_limit import LoginRateLimiter

# Four distinct addresses so a wrong answer is never mistaken for a right one.
PROXY_SAW_A = "192.0.2.7"
PROXY_SAW_B = "192.0.2.8"
APPENDED_HOP = "198.51.100.4"

_PROD = {"jwt_secret": "x" * 40, "db_password": "pw"}


def _spoofed(nth: int) -> str:
    """A fresh client-supplied leftmost hop for every attempt."""
    return f"203.0.113.{nth}"


async def _seed_admin(session) -> None:
    session.add(Config(key="admin_password_hash", value={"hash": hash_password("correct")}))
    await session.commit()


def _install_limiter(monkeypatch, max_failures: int = 3) -> None:
    from tests.conftest import test_engine

    monkeypatch.setattr(
        auth_routes,
        "async_session_factory",
        async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False),
    )
    monkeypatch.setattr(
        auth_routes,
        "login_rate_limiter",
        LoginRateLimiter(max_failures=max_failures, lockout_seconds=300),
    )


# ── the limiter buckets on the proxy's view, and rotation cannot evade it ──


@pytest.mark.asyncio
async def test_lockout_fires_on_the_proxied_ip_while_the_client_rotates_xff(
    client, session, monkeypatch
):
    """Exposed posture: three failures from one proxy-observed IP lock it out,
    even though every request carried a different leftmost `X-Forwarded-For`."""
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    _install_limiter(monkeypatch, max_failures=3)
    await _seed_admin(session)

    for attempt in range(3):
        response = await client.post(
            "/api/v1/auth/login",
            json={"password": "wrong"},
            headers={
                "x-real-ip": PROXY_SAW_A,
                "x-forwarded-for": f"{_spoofed(attempt)}, {APPENDED_HOP}",
            },
        )
        assert response.status_code == 401, response.text

    locked = await client.post(
        "/api/v1/auth/login",
        json={"password": "wrong"},
        headers={
            "x-real-ip": PROXY_SAW_A,
            "x-forwarded-for": f"{_spoofed(99)}, {APPENDED_HOP}",
        },
    )
    assert locked.status_code == 429
    assert locked.headers.get("Retry-After")


@pytest.mark.asyncio
async def test_the_lockout_is_per_proxied_ip_not_one_bucket_for_the_whole_proxy(
    client, session, monkeypatch
):
    """The counterpart assertion: a *different* proxy-observed IP is a different
    bucket. Without it the test above would also pass against a limiter that
    lumped every proxied request into one bucket — which locks the whole
    internet out after one attacker, an availability failure rather than a
    security one."""
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    _install_limiter(monkeypatch, max_failures=3)
    await _seed_admin(session)

    for _ in range(4):
        await client.post(
            "/api/v1/auth/login",
            json={"password": "wrong"},
            headers={"x-real-ip": PROXY_SAW_A},
        )

    assert (
        await client.post(
            "/api/v1/auth/login",
            json={"password": "wrong"},
            headers={"x-real-ip": PROXY_SAW_A},
        )
    ).status_code == 429

    other = await client.post(
        "/api/v1/auth/login",
        json={"password": "wrong"},
        headers={"x-real-ip": PROXY_SAW_B},
    )
    assert other.status_code == 401, "a second proxied IP must not inherit A's lockout"


@pytest.mark.asyncio
async def test_the_rightmost_xff_fallback_buckets_through_the_limiter_too(
    client, session, monkeypatch
):
    """E4 review M3: both lockout tests above always send `X-Real-IP`, so the
    fallback arm was pinned as a unit in `test_client_ip_attribution.py` and
    never driven through the limiter. A proxy that appends to
    `X-Forwarded-For` without setting `X-Real-IP` is an ordinary
    configuration, and its composition with the bucket was unproven."""
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    _install_limiter(monkeypatch, max_failures=3)
    await _seed_admin(session)

    for attempt in range(3):
        response = await client.post(
            "/api/v1/auth/login",
            json={"password": "wrong"},
            headers={"x-forwarded-for": f"{_spoofed(attempt)}, {APPENDED_HOP}"},
        )
        assert response.status_code == 401, response.text

    locked = await client.post(
        "/api/v1/auth/login",
        json={"password": "wrong"},
        headers={"x-forwarded-for": f"{_spoofed(99)}, {APPENDED_HOP}"},
    )
    assert locked.status_code == 429, "the appended hop must be the bucket"

    other_proxy = await client.post(
        "/api/v1/auth/login",
        json={"password": "wrong"},
        headers={"x-forwarded-for": f"{_spoofed(7)}, {PROXY_SAW_B}"},
    )
    assert other_proxy.status_code == 401, "a different appended hop is a different bucket"


@pytest.mark.asyncio
async def test_lan_posture_ignores_a_spoofed_header_and_still_locks_out(
    client, session, monkeypatch
):
    """LAN posture is unchanged and is the one that must not regress: with
    `trust_proxy_headers` off, an attacker sending a fresh `X-Real-IP` per
    request is still bucketed on the transport peer and still locked out."""
    monkeypatch.setattr(settings, "trust_proxy_headers", False)
    _install_limiter(monkeypatch, max_failures=3)
    await _seed_admin(session)

    for attempt in range(3):
        response = await client.post(
            "/api/v1/auth/login",
            json={"password": "wrong"},
            headers={"x-real-ip": _spoofed(attempt)},
        )
        assert response.status_code == 401, response.text

    locked = await client.post(
        "/api/v1/auth/login",
        json={"password": "wrong"},
        headers={"x-real-ip": _spoofed(99)},
    )
    assert locked.status_code == 429


# ── the tri-state collapses to enforced under a trusted proxy ─────────


def test_the_exposed_posture_enforces_secure_over_an_explicit_false():
    exposed = Settings(
        _env_file=None, environment="production", trust_proxy_headers=True,
        cookie_secure=False, **_PROD,
    )
    assert exposed.session_cookie_secure is True
    assert exposed.session_cookie_secure_clamped is True


def test_the_lan_tri_state_is_unchanged():
    lan_explicit_false = Settings(
        _env_file=None, environment="production", trust_proxy_headers=False,
        cookie_secure=False, **_PROD,
    )
    assert lan_explicit_false.session_cookie_secure is False
    assert lan_explicit_false.session_cookie_secure_clamped is False

    lan_unset_dev = Settings(_env_file=None, environment="development")
    assert lan_unset_dev.session_cookie_secure is False

    lan_unset_prod = Settings(_env_file=None, environment="production", **_PROD)
    assert lan_unset_prod.session_cookie_secure is True


def test_an_enforced_secure_that_overrode_nothing_is_not_reported_as_clamped():
    """`clamped` must mean "your explicit false was overridden", not merely
    "Secure is on" — otherwise the field the operator reads to detect a
    silent override is true in the ordinary case and tells them nothing."""
    exposed_unset = Settings(
        _env_file=None, environment="production", trust_proxy_headers=True, **_PROD
    )
    assert exposed_unset.session_cookie_secure is True
    assert exposed_unset.session_cookie_secure_clamped is False


def test_the_clamp_warns_at_construction(caplog):
    with caplog.at_level(logging.WARNING, logger="app.config"):
        Settings(
            _env_file=None, environment="production", trust_proxy_headers=True,
            cookie_secure=False, **_PROD,
        )
    assert any("clamped" in record.message for record in caplog.records)


def test_the_issued_cookie_carries_secure_in_the_exposed_posture(monkeypatch):
    """The property that actually protects a session: the resolved flag reaches
    the Set-Cookie header, not just the settings object."""
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "cookie_secure", False)
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    response = set_auth_cookie(JSONResponse(content={}), "tok")
    assert "secure" in response.headers["set-cookie"].lower()


# ── the operator can see the clamp happened ───────────────────────────


@pytest.mark.asyncio
async def test_security_posture_reports_the_clamp(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    monkeypatch.setattr(settings, "cookie_secure", False)

    body = (
        await client.get("/api/v1/auth/security-posture", headers=auth_headers)
    ).json()
    assert body["cookie_secure"] is True
    assert body["cookie_secure_explicit"] is True
    assert body["cookie_secure_clamped"] is True
