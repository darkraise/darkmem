"""Bearer verification on the MCP door, over the same api_keys rows REST uses."""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

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


# --- The door: bearer required, scope per tool -----------------------------
#
# The tests above prove the verifier in isolation. These drive the mounted
# streamable app, because "the door refuses" is a property of the transport,
# the middleware chain and the registry together, and each of those is a place
# the guard could be wired wrongly while the verifier stays correct.

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.mcp.scopes import (
    CAPTURE_TOOLS,
    READ_TOOLS,
    SCOPE_DENIED,
    TOOL_SCOPES,
    ScopeDenied,
    ToolScopeMiddleware,
    require_scope_for_tool,
    require_tool_scope,
)
from app.api.mcp.server import mcp
from app.models.api_key import ApiKey
from tests.conftest import test_engine


def _call(name: str, **args) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": name,
            "arguments": args,
            "_meta": {
                "io.modelcontextprotocol/protocolVersion": "2026-07-28",
                "io.modelcontextprotocol/clientInfo": {"name": "test", "version": "1"},
                "io.modelcontextprotocol/clientCapabilities": {},
            },
        },
    }


@pytest_asyncio.fixture
async def mint_key():
    """Issue committed keys the token verifier can actually see.

    The verifier opens its own session on the application engine, so a key
    written through the rollback-isolated ``session`` fixture is invisible to
    it. These rows are committed and deleted at teardown.
    """
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    minted: list = []

    async def _mint(*, scopes, name="probe", expires_at=None):
        async with factory() as s:
            row, credential = await issue_key(
                s, name=name, scopes=scopes, expires_at=expires_at
            )
            row_id = row.id
            await s.commit()
        minted.append(row_id)
        return row_id, credential

    yield _mint

    async with factory() as s:
        for row_id in minted:
            await s.execute(sa_delete(ApiKey).where(ApiKey.id == row_id))
        await s.commit()


@pytest_asyncio.fixture
async def door(mcp_streamable_app):
    """A client on the mounted door with no credential of its own."""
    async with AsyncClient(
        transport=ASGITransport(app=mcp_streamable_app),
        base_url="http://localhost:8000",
        headers={"Accept": "application/json"},
    ) as c:
        yield c


async def _post(client, name, credential=None, **extra_headers):
    headers = dict(extra_headers)
    if credential is not None:
        headers["Authorization"] = f"Bearer {credential}"
    return await client.post("/", json=_call(name), headers=headers)


def _rpc_error(response) -> dict:
    return response.json()["error"]


# --- Property 1: no Authorization header is refused ------------------------


async def test_an_unauthenticated_call_is_refused(door):
    response = await _post(door, "memory_stats")

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_token"


async def test_an_unauthenticated_capture_is_refused(door):
    response = await _post(door, "memory_add")

    assert response.status_code == 401


async def test_even_listing_the_tools_needs_a_key(door):
    """The refusal is the transport's, so it covers every method, not only
    tools/call. A door that served ``tools/list`` unauthenticated would hand an
    anonymous caller the whole surface to probe."""
    response = await door.post(
        "/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )

    assert response.status_code == 401


async def test_a_non_bearer_authorization_header_is_refused(door):
    response = await door.post(
        "/", json=_call("memory_stats"), headers={"Authorization": "Basic abc"}
    )

    assert response.status_code == 401


# --- Property 2: invalid, revoked or expired keys are refused --------------


async def test_a_garbage_key_is_refused_at_the_door(door):
    response = await _post(door, "memory_stats", credential="dmk_nope.nothing")

    assert response.status_code == 401


async def test_a_revoked_key_is_refused_at_the_door(door, mint_key):
    row_id, credential = await mint_key(scopes=["read"])
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as s:
        await revoke_key(s, row_id)
        await s.commit()

    response = await _post(door, "memory_stats", credential=credential)

    assert response.status_code == 401


async def test_an_expired_key_is_refused_at_the_door(door, mint_key):
    past = datetime.now(timezone.utc) - timedelta(days=1)
    _row_id, credential = await mint_key(scopes=["read"], expires_at=past)

    response = await _post(door, "memory_stats", credential=credential)

    assert response.status_code == 401


# --- Properties 3 and 4: the scope decides, and it is not the 401 ----------


async def test_a_read_key_cannot_reach_a_capture_tool(door, mint_key):
    _row_id, credential = await mint_key(scopes=["read"])

    response = await _post(door, "memory_add", credential=credential)

    assert response.status_code == 200, "the key authenticated; this is not a 401"
    error = _rpc_error(response)
    assert error["code"] == SCOPE_DENIED
    assert error["data"] == "memory_add"
    assert "capture" in error["message"]


async def test_a_capture_key_cannot_reach_a_read_tool(door, mint_key):
    """The partition is not a ladder: capture does not imply read."""
    _row_id, credential = await mint_key(scopes=["capture"])

    response = await _post(door, "memory_stats", credential=credential)

    error = _rpc_error(response)
    assert error["code"] == SCOPE_DENIED


async def test_a_scope_refusal_is_distinguishable_from_no_key(door, mint_key):
    _row_id, credential = await mint_key(scopes=["read"])

    anonymous = await _post(door, "memory_add")
    scoped = await _post(door, "memory_add", credential=credential)

    assert anonymous.status_code == 401
    assert scoped.status_code == 200
    assert _rpc_error(scoped)["code"] == SCOPE_DENIED


async def test_a_key_holding_the_scope_succeeds(door, mint_key):
    _row_id, credential = await mint_key(scopes=["read"])

    response = await _post(door, "memory_stats", credential=credential)

    assert response.status_code == 200
    body = response.json()
    assert "error" not in body, body
    assert body["result"]["isError"] is False


async def test_an_admin_only_key_reaches_neither_partition(door, mint_key):
    """``admin`` is a real scope and deliberately implies nothing."""
    _row_id, credential = await mint_key(scopes=["admin"])

    for tool in ("memory_stats", "memory_add"):
        response = await _post(door, tool, credential=credential)
        assert _rpc_error(response)["code"] == SCOPE_DENIED, tool


async def test_a_passing_scope_check_marks_the_key_used(door, mint_key, monkeypatch):
    """After the gate, never before: REST's ``require_scope`` marks a key used
    only once the scope passed, and a call that authenticated and then failed
    the gate did not use the key for anything."""
    import app.api.mcp.scopes as scopes_module

    marked: list = []

    async def _record(api_key_id, **_kwargs):
        marked.append(api_key_id)

    monkeypatch.setattr(scopes_module, "mark_key_used", _record)

    read_id, read_credential = await mint_key(scopes=["read"])
    await _post(door, "memory_stats", credential=read_credential)
    assert marked == [read_id]

    marked.clear()
    _denied_id, denied_credential = await mint_key(scopes=["capture"])
    await _post(door, "memory_stats", credential=denied_credential)
    assert marked == [], "a call that failed the scope gate did not use the key"

    assert scopes_module.ToolScopeMiddleware is ToolScopeMiddleware


# --- Property 5: the Host allowlist is not replaced by the key -------------


async def test_a_foreign_host_is_refused_even_with_a_valid_key(door, mint_key):
    """Both guards, not either. A key is not a licence to reach the door from
    a rebound name."""
    _row_id, credential = await mint_key(scopes=["read"])

    response = await _post(
        door, "memory_stats", credential=credential, Host="attacker.example"
    )

    assert response.status_code == 421


async def test_the_same_host_passes_without_the_foreign_name(door, mint_key):
    """The pair that makes the test above mean something: the only difference
    between a 421 and a 200 here is the Host header."""
    _row_id, credential = await mint_key(scopes=["read"])

    response = await _post(door, "memory_stats", credential=credential)

    assert response.status_code == 200


# --- The registry: total, disjoint, and fail-closed ------------------------


def test_every_tool_declares_a_scope():
    """A tool added without a scope must fail the build, not ship unscoped.

    The roster is derived from source (see tests/test_mcp.py), so this cannot
    go stale the way a hand-listed set would.

    ``TOOL_SCOPES`` names all 33 rather than deriving "not a writer means a
    reader". A derived partition is total by construction and therefore blind:
    it would resolve a new *capture* tool nobody classified to ``read`` and
    ship it, with this test still green. Naming both halves makes an
    unclassified tool visible here, and — because ``require_scope_for_tool`` refuses an
    unlisted name — unreachable rather than readable in the meantime.
    """
    from tests.test_mcp import _declared_tool_names

    declared = _declared_tool_names()
    unknown = CAPTURE_TOOLS - declared
    assert not unknown, f"CAPTURE_TOOLS names tools that do not exist: {sorted(unknown)}"
    stale = READ_TOOLS - declared
    assert not stale, f"READ_TOOLS names tools that do not exist: {sorted(stale)}"

    unclassified = declared - set(TOOL_SCOPES)
    assert not unclassified, (
        "these tools are declared but classified in neither partition, so they "
        f"are unreachable: {sorted(unclassified)}"
    )
    assert set(TOOL_SCOPES) == declared
    assert not (CAPTURE_TOOLS & READ_TOOLS)
    assert len(CAPTURE_TOOLS) + len(READ_TOOLS) == len(declared)
    assert READ_TOOLS, "no read tools found; the partition is broken"


def test_the_scope_gate_is_wired_into_the_server():
    """The guard is one middleware, so removing it is one deletion. This is the
    line that makes that deletion loud rather than silent."""
    assert any(isinstance(m, ToolScopeMiddleware) for m in mcp.middleware)


def test_an_unlisted_tool_name_is_refused_rather_than_defaulted():
    with pytest.raises(ScopeDenied):
        require_scope_for_tool("a_tool_nobody_classified")


# --- Property 6: ratify is not a scope ------------------------------------


def test_ratify_is_not_reachable_as_a_tool_scope():
    from app.services.api_key_scopes import FORBIDDEN_SCOPES

    assert "ratify" in FORBIDDEN_SCOPES
    assert "ratify" not in CAPTURE_TOOLS
    assert "ratify" not in READ_TOOLS
    assert "ratify" not in set(TOOL_SCOPES.values())


def test_require_tool_scope_refuses_ratify_outright():
    """Not merely absent from the registry: asked for directly, it is refused
    before any membership test, so a key hand-edited to carry the string still
    reaches nothing."""
    with pytest.raises(ScopeDenied):
        require_tool_scope("ratify")


def test_every_declared_scope_is_in_the_closed_set():
    from app.services.api_key_scopes import API_KEY_SCOPES

    assert set(TOOL_SCOPES.values()) <= set(API_KEY_SCOPES)
