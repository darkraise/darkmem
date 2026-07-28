"""Regression tests for recently landed auth/setup security fixes.

Covers three fixes that were previously no-ops or silently rolled back:

1. /setup trust-on-first-use — with no setup secret, the finalize endpoint is
   open (gated only by ``require_uninitialized``) and the first caller claims
   admin, even in production.
2. Failed-login audit persistence — a failed login records an
   ``auth_login_failed`` row that survives the 401 (it is written through a
   fresh, independently committed session, not the request session that the
   401 rolls back).
3. Password-change session revocation — changing the password stamps
   ``admin_password_changed_at``; any token issued before that instant is
   rejected by ``require_auth`` while a freshly issued token still works.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from app.api import auth as auth_module
from app.api.auth import hash_password
from app.config import settings
from app.models.config import Config


# ── setup is open trust-on-first-use (no SETUP_SECRET) ────────────────


@pytest.mark.asyncio
async def test_setup_succeeds_without_secret_in_production(client, session, monkeypatch):
    """/setup is gated only by ``require_uninitialized``: the first caller claims
    admin, no secret required even in production (LAN trust-on-first-use)."""
    monkeypatch.setattr(settings, "environment", "production")

    response = await client.post(
        "/api/v1/setup",
        json={"password": "test-pw-12345"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["password"]["ok"] is True

    config = (await session.execute(
        select(Config).where(Config.key == "admin_password_hash")
    )).scalar_one_or_none()
    assert config is not None


# ── failed-login audit persistence ────────────────────────────────────


@pytest.mark.asyncio
async def test_failed_login_persists_audit_row(client, session, monkeypatch):
    """A failed login records an auth_login_failed audit row despite the 401.

    The handler writes the audit row through ``async_session_factory`` — a
    fresh, independently committed session — precisely so the 401's rollback
    of the request session does not discard it. We point that factory at the
    test engine for the duration of the call, then read the row back through
    yet another session to prove it was committed (not merely flushed).
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.api.routes import auth as auth_routes
    from tests.conftest import test_engine

    test_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(auth_routes, "async_session_factory", test_factory)

    session.add(Config(
        key="admin_password_hash",
        value={"hash": hash_password("correct-password")},
    ))
    await session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={"password": "wrong-password"},
    )
    assert response.status_code == 401

    # Read through a brand-new session so we see only rows the handler
    # actually committed via async_session_factory.
    async with AsyncSession(test_engine) as verify_session:
        rows = (await verify_session.execute(
            text("SELECT id FROM events WHERE event_type = 'auth_login_failed'")
        )).all()
        assert len(rows) >= 1

    # The committed row outlives the fixture's rollback boundary and cannot be
    # cleaned up: `events` is append-only (T1.06), so a DELETE here would be
    # refused by the forbid-trigger. Assertions elsewhere must therefore be
    # written to tolerate rows this test leaves behind — which is the right
    # shape anyway, since production rows accumulate the same way.


# ── password-change session revocation ────────────────────────────────


@pytest.mark.asyncio
async def test_old_token_rejected_after_password_change(client, session):
    """A token issued before a password change is rejected; a new one works.

    ``require_auth`` rejects any token whose ``iat`` predates the stored
    ``admin_password_changed_at`` timestamp. Both tokens carry explicit
    ``iat`` values so the assertion does not depend on wall-clock timing.
    """
    session.add(Config(
        key="admin_password_hash",
        value={"hash": hash_password("old-password")},
    ))
    await session.flush()

    now = datetime.now(timezone.utc)
    # Stamp the change instant 30s in the past so a token issued earlier than
    # that is revoked while one issued at "now" survives. Both token iats stay
    # at-or-before now so PyJWT does not reject them as future-dated.
    change_ts = int((now - timedelta(seconds=30)).timestamp())

    session.add(Config(
        key="admin_password_changed_at",
        value={"ts": change_ts},
    ))
    await session.flush()

    # iat strictly before the change stamp -> rejected.
    old_token = _token_with_iat("admin", now - timedelta(seconds=60))
    rejected = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {old_token}"},
    )
    assert rejected.status_code == 401
    assert "revoked" in rejected.json()["detail"].lower()

    # iat after the change stamp -> accepted.
    fresh_token = _token_with_iat("admin", now)
    accepted = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {fresh_token}"},
    )
    assert accepted.status_code == 200
    assert accepted.json()["authenticated"] is True


@pytest.mark.asyncio
async def test_change_password_endpoint_revokes_old_sessions(client, session):
    """End-to-end: POST /change-password stamps the change so the caller's
    pre-change token is rejected on its next request, while the reissued
    cookie/token keeps the caller logged in."""
    session.add(Config(
        key="admin_password_hash",
        value={"hash": hash_password("old-password")},
    ))
    await session.flush()

    # Mint a token in the past so its iat is strictly below the change stamp
    # that change-password is about to write (which uses now()).
    past = datetime.now(timezone.utc) - timedelta(seconds=60)
    old_payload_token = _token_with_iat("admin", past)

    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "old-password", "new_password": "brand-new-pw-1"},
        headers={"Authorization": f"Bearer {old_payload_token}"},
    )
    assert response.status_code == 200

    # The reissued token from the Set-Cookie header keeps the caller logged in.
    set_cookie = response.headers.get("set-cookie", "")
    assert "darkmem_session=" in set_cookie

    # The change stamp now exists and the old token's iat predates it.
    stamp = (await session.execute(
        select(Config).where(Config.key == "admin_password_changed_at")
    )).scalar_one_or_none()
    assert stamp is not None

    # Drop the freshly issued session cookie so the next request authenticates
    # purely with the pre-change Authorization header — _extract_token prefers
    # the cookie, and the AsyncClient would otherwise replay the reissued one.
    client.cookies.clear()

    rejected = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {old_payload_token}"},
    )
    assert rejected.status_code == 401


def _token_with_iat(sub: str, issued_at: datetime) -> str:
    """Build a valid token with an explicit ``iat`` in the past.

    Mirrors ``create_access_token`` but lets the test pin ``iat`` so it lands
    strictly before the password-change stamp written with ``now()``.
    """
    import jwt
    from uuid import uuid4

    payload = {
        "sub": sub,
        "iat": issued_at,
        "exp": issued_at + timedelta(hours=auth_module.ACCESS_TOKEN_EXPIRE_HOURS),
        "jti": uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=auth_module.ALGORITHM)
