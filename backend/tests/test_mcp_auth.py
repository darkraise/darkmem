"""Bearer verification on the MCP door, over the same api_keys rows REST uses."""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest

import app.api.mcp.auth as mcp_auth_module
from app.api.mcp.auth import ApiKeyTokenVerifier
from app.services.api_keys import issue_key, revoke_key


@pytest.fixture
def verifier(session, monkeypatch):
    """A verifier wired to the test's own session/connection.

    `ApiKeyTokenVerifier.verify_token` opens its own session per call through
    the module-level `async_session_factory`, exactly like the rest of the
    MCP door (`app/api/mcp/server.py`) — see the module docstring for why a
    fresh session per call is the right shape in production. In this test
    process that factory is bound to `app.database.engine`'s own connection
    pool, a different physical connection than the `session` fixture's
    dedicated, rollback-isolated one; a row inserted and "committed" through
    `session` only releases a SAVEPOINT; it is invisible to any other
    connection until the fixture's outer transaction is rolled back at
    teardown, which is never as a commit. So the factory binding is patched
    here the same way `tests/conftest.py`'s `mcp_http_client` patches it for
    `app.api.mcp.server`, to see the fixture's own uncommitted work.
    """

    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_auth_module, "async_session_factory", lambda: _fake_ctx())
    return ApiKeyTokenVerifier()


async def test_valid_key_verifies_with_its_scopes(session, verifier):
    row, credential = await issue_key(session, name="agent", scopes=["read"])
    await session.commit()

    token = await verifier.verify_token(credential)

    assert token is not None
    assert token.scopes == ["read"]
    # client_id is the public key_id, never the row UUID: events.api_key_id
    # stores the row id, and conflating them writes an unjoinable value.
    assert token.client_id == row.key_id
    assert token.subject == "agent"
    # The row UUID rides in claims so a later caller can write
    # events.api_key_id from the token alone, with no second SELECT.
    assert token.claims == {"api_key_id": str(row.id)}


async def test_garbage_is_refused(verifier):
    assert await verifier.verify_token("not-a-key") is None
    assert await verifier.verify_token("") is None


async def test_revoked_key_is_refused(session, verifier):
    row, credential = await issue_key(session, name="gone", scopes=["read"])
    await revoke_key(session, row.id)
    await session.commit()

    assert await verifier.verify_token(credential) is None


async def test_expired_key_is_refused(session, verifier):
    past = datetime.now(timezone.utc) - timedelta(days=1)
    _row, credential = await issue_key(
        session, name="stale", scopes=["read"], expires_at=past
    )
    await session.commit()

    assert await verifier.verify_token(credential) is None


async def test_database_failure_refuses_rather_than_raises(session, verifier, monkeypatch):
    """An unreachable database must fail closed: refuse, never authenticate,
    never raise past this layer (a raise here is not a 401)."""
    _row, credential = await issue_key(session, name="agent", scopes=["read"])
    await session.commit()

    async def _boom(*_args, **_kwargs):
        raise RuntimeError("database unreachable")

    monkeypatch.setattr(mcp_auth_module, "authenticate", _boom)

    assert await verifier.verify_token(credential) is None
