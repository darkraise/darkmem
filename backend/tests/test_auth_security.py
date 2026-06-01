"""Regression tests for recently landed auth/setup security fixes.

Covers three fixes that were previously no-ops or silently rolled back:

1. ``setup_secret`` enforcement — in production the finalize endpoint must
   reject a request that does not present the configured secret, and accept
   one that does.
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
from sqlalchemy import select

from app.api import auth as auth_module
from app.api.auth import hash_password
from app.api.routes import setup as setup_routes
from app.config import settings
from app.models.audit import AuditLog
from app.models.config import Config


# ── setup_secret enforcement ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_production_setup_rejected_without_secret(client, monkeypatch):
    """In production a finalize request lacking the secret is rejected (403)."""
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "setup_secret", "the-real-secret")

    response = await client.post(
        "/api/v1/setup",
        json={"password": "test-pw-12345"},
    )
    assert response.status_code == 403
    assert "setup secret" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_production_setup_rejected_with_wrong_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "setup_secret", "the-real-secret")

    response = await client.post(
        "/api/v1/setup",
        json={"password": "test-pw-12345", "setup_secret": "wrong"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_production_setup_allowed_with_correct_secret_in_body(
    client, session, monkeypatch
):
    """With the correct secret in the body, production setup completes."""
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "setup_secret", "the-real-secret")

    response = await client.post(
        "/api/v1/setup",
        json={"password": "test-pw-12345", "setup_secret": "the-real-secret"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["password"]["ok"] is True

    config = (await session.execute(
        select(Config).where(Config.key == "admin_password_hash")
    )).scalar_one_or_none()
    assert config is not None


@pytest.mark.asyncio
async def test_production_setup_allowed_with_correct_secret_header(
    client, session, monkeypatch
):
    """The X-Setup-Secret header is an accepted way to present the secret."""
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "setup_secret", "the-real-secret")

    response = await client.post(
        "/api/v1/setup",
        json={"password": "test-pw-12345"},
        headers={"X-Setup-Secret": "the-real-secret"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["password"]["ok"] is True


@pytest.mark.asyncio
async def test_nonproduction_setup_open_without_secret(client, monkeypatch):
    """Outside production with no secret configured the endpoint stays open."""
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "setup_secret", None)
    # Guard against a stray /.dockerenv on the host flipping _is_production.
    monkeypatch.setattr(setup_routes, "_is_production", lambda: False)

    response = await client.post(
        "/api/v1/setup",
        json={"password": "test-pw-12345"},
    )
    assert response.status_code == 200, response.text


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
            select(AuditLog).where(AuditLog.action == "auth_login_failed")
        )).scalars().all()
        assert len(rows) >= 1

        # The committed row lives outside the fixture's rollback boundary;
        # delete it so it does not leak into other tests.
        for row in rows:
            await verify_session.delete(row)
        await verify_session.commit()


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
