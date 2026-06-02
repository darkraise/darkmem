"""GET /api/v1/auth/audit surfaces the security audit trail to operators.

The system writes auth_*/setup_* audit rows (failed logins, password changes,
setup completion) but nothing read them back, so brute-force attempts and
surprise password changes were invisible. This admin-gated endpoint returns
those rows, newest first, with pagination and an optional action filter.
"""
from __future__ import annotations

import pytest

from app.models.audit import AuditLog


@pytest.mark.asyncio
async def test_audit_requires_auth(client):
    r = await client.get("/api/v1/auth/audit")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_audit_returns_only_security_rows_newest_first(client, session, auth_headers):
    session.add_all([
        AuditLog(action="auth_login_failed", details={"ip": "1.1.1.1"}),
        AuditLog(action="auth_login_success", details={"ip": "2.2.2.2"}),
        AuditLog(action="setup_complete", details={}),
        AuditLog(action="pipeline", details={}),          # excluded
        AuditLog(action="create", details={}),            # excluded
    ])
    await session.flush()

    r = await client.get("/api/v1/auth/audit", headers=auth_headers)
    assert r.status_code == 200
    actions = [row["action"] for row in r.json()["items"]]
    assert set(actions) == {"auth_login_failed", "auth_login_success", "setup_complete"}
    # Newest first: the last-inserted security row leads.
    assert actions[0] == "setup_complete"


@pytest.mark.asyncio
async def test_audit_filters_by_action(client, session, auth_headers):
    session.add_all([
        AuditLog(action="auth_login_failed", details={"ip": "1.1.1.1"}),
        AuditLog(action="auth_login_success", details={"ip": "2.2.2.2"}),
    ])
    await session.flush()

    r = await client.get(
        "/api/v1/auth/audit", headers=auth_headers, params={"action": "auth_login_failed"},
    )
    assert r.status_code == 200
    actions = [row["action"] for row in r.json()["items"]]
    assert actions == ["auth_login_failed"]
