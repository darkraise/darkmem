"""GET /api/v1/auth/audit surfaces the security audit trail to operators.

The system writes auth_*/setup_* audit rows (failed logins, password changes,
setup completion) but nothing read them back, so brute-force attempts and
surprise password changes were invisible. This admin-gated endpoint returns
those rows, newest first, with pagination and an optional action filter.
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth import create_access_token
from app.api.routes import auth as auth_routes
from app.services.events import record_event
from app.services.login_rate_limit import LoginRateLimiter


@pytest.mark.asyncio
async def test_audit_requires_auth(client):
    r = await client.get("/api/v1/auth/audit")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_audit_returns_only_security_rows_newest_first(client, session, auth_headers):
    for event_type, payload in [
        ("auth_login_failed", {"ip": "1.1.1.1"}),
        ("auth_login_success", {"ip": "2.2.2.2"}),
        ("setup_complete", {}),
        ("pipeline", {}),          # excluded
        ("create", {}),            # excluded
    ]:
        await record_event(
            session, event_type=event_type, object_type="system", payload=payload
        )
    await session.flush()

    r = await client.get("/api/v1/auth/audit", headers=auth_headers)
    assert r.status_code == 200
    actions = [row["action"] for row in r.json()["items"]]
    assert set(actions) == {"auth_login_failed", "auth_login_success", "setup_complete"}
    # Newest first: the last-inserted security row leads.
    assert actions[0] == "setup_complete"


@pytest.mark.asyncio
async def test_audit_filters_by_action(client, session, auth_headers):
    for event_type, payload in [
        ("auth_login_failed", {"ip": "1.1.1.1"}),
        ("auth_login_success", {"ip": "2.2.2.2"}),
    ]:
        await record_event(
            session, event_type=event_type, object_type="system", payload=payload
        )
    await session.flush()

    r = await client.get(
        "/api/v1/auth/audit", headers=auth_headers, params={"action": "auth_login_failed"},
    )
    assert r.status_code == 200
    actions = [row["action"] for row in r.json()["items"]]
    # What the filter must guarantee is that no OTHER action comes back. An
    # exact-length assertion would instead be asserting that no earlier test
    # left an `auth_login_failed` row behind — and since `events` is append-only
    # (T1.06), rows genuinely do accumulate for the life of the database.
    assert set(actions) == {"auth_login_failed"}
    assert actions


@pytest.mark.asyncio
async def test_audit_surfaces_every_real_auth_route_at_the_door(client, session, monkeypatch):
    """T2.103's regression clause, driven for real rather than reasoned
    about: every literal the auth/setup routes actually journal —
    including the two (`auth_login_failed`, `auth_lockout`) that only
    reach `events` through `_record_audit`'s own committed session, not
    the request session `GET /auth/audit` reads through — must still come
    back from the door with its exact spelling. `GET /auth/audit` filters
    by an `auth_%`/`setup_%` LIKE prefix, so this is the test that would
    catch a renamed literal quietly falling outside that prefix or outside
    EVENT_TYPES, not an argument that the filter "shouldn't" care.
    """
    from tests.conftest import test_engine

    test_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(auth_routes, "async_session_factory", test_factory)
    monkeypatch.setattr(
        auth_routes, "login_rate_limiter",
        LoginRateLimiter(max_failures=2, lockout_seconds=300),
    )

    # 1. Setup finalize — writes auth_setup then setup_complete on the one
    # request session.
    setup_response = await client.post(
        "/api/v1/setup", json={"password": "setup-pw-12345"},
    )
    assert setup_response.status_code == 200, setup_response.text

    # 2. A real successful login — writes auth_login_success.
    login_response = await client.post(
        "/api/v1/auth/login", json={"password": "setup-pw-12345"},
    )
    assert login_response.status_code == 200, login_response.text

    # 3. Two real failed logins with a lowered threshold — the first
    # writes only auth_login_failed, the second crosses max_failures=2 and
    # also writes auth_lockout. Both go through _record_audit.
    for _ in range(2):
        failed_response = await client.post(
            "/api/v1/auth/login", json={"password": "definitely-wrong"},
        )
        assert failed_response.status_code == 401

    # 4. Real logout and change-password calls, each with its own freshly
    # minted token so neither depends on cookie-jar state or on a token
    # the lockout above or an earlier step already blocklisted.
    logout_token = create_access_token({"sub": "admin"})
    logout_response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {logout_token}"},
    )
    assert logout_response.status_code == 200, logout_response.text

    change_password_token = create_access_token({"sub": "admin"})
    change_password_response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "setup-pw-12345", "new_password": "rotated-pw-67890"},
        headers={"Authorization": f"Bearer {change_password_token}"},
    )
    assert change_password_response.status_code == 200, change_password_response.text

    # 5. Read the door with a fresh token of its own.
    audit_token = create_access_token({"sub": "admin"})
    audit_response = await client.get(
        "/api/v1/auth/audit",
        headers={"Authorization": f"Bearer {audit_token}"},
        params={"limit": 100},
    )
    assert audit_response.status_code == 200, audit_response.text
    actions = {row["action"] for row in audit_response.json()["items"]}

    expected = {
        "auth_setup",
        "setup_complete",
        "auth_login_success",
        "auth_login_failed",
        "auth_lockout",
        "auth_logout",
        "auth_password_change",
    }
    missing = expected - actions
    assert not missing, f"GET /auth/audit did not surface: {sorted(missing)}"
