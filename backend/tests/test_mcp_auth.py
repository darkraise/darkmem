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
    ADMIN_TOOLS,
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
async def door(mcp_streamable_app, session, monkeypatch):
    """A client on the mounted door with no credential of its own.

    The session factory is patched exactly as ``mcp_http_client`` patches it:
    MCP tools open their own sessions through the module-level factory rather
    than through the FastAPI dependency, so a tool whose body actually runs
    here would commit rows outside the test transaction. Most tests in this
    module are refused before any body executes, but the admin-scope test
    reaches ``code_reindex``'s body and journals from it.
    """
    from contextlib import asynccontextmanager

    import app.api.mcp.server as mcp_module

    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_module, "async_session_factory", lambda: _fake_ctx())
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


async def test_an_admin_only_key_reaches_only_admin_tools(door, mint_key):
    """``admin`` is a real scope and deliberately implies nothing: it reaches
    ``code_reindex``, ``document_delete_subtree`` and ``worklog_purge``, and nothing in
    ``CAPTURE_TOOLS`` or ``READ_TOOLS``."""
    _row_id, credential = await mint_key(scopes=["admin"])

    for tool in ("memory_stats", "memory_add"):
        response = await _post(door, tool, credential=credential)
        assert _rpc_error(response)["code"] == SCOPE_DENIED, tool

    # `code_reindex` takes arguments `_post` has no way to carry; post the
    # call directly, the same shape `_post` builds internally.
    response = await door.post(
        "/",
        json=_call("code_reindex", repo_name="no-such-repo"),
        headers={"Authorization": f"Bearer {credential}"},
    )
    assert "error" not in response.json(), response.json()


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

    ``TOOL_SCOPES`` names all 46 rather than deriving "not a writer means a
    reader". A derived partition is total by construction and therefore blind:
    it would resolve a new *capture* tool nobody classified to ``read`` and
    ship it, with this test still green. Naming all three sets makes an
    unclassified tool visible here, and — because ``require_scope_for_tool`` refuses an
    unlisted name — unreachable rather than readable in the meantime.
    """
    from tests.test_mcp import _declared_tool_names

    declared = _declared_tool_names()
    unknown = CAPTURE_TOOLS - declared
    assert not unknown, f"CAPTURE_TOOLS names tools that do not exist: {sorted(unknown)}"
    stale = READ_TOOLS - declared
    assert not stale, f"READ_TOOLS names tools that do not exist: {sorted(stale)}"
    orphaned = ADMIN_TOOLS - declared
    assert not orphaned, f"ADMIN_TOOLS names tools that do not exist: {sorted(orphaned)}"

    unclassified = declared - set(TOOL_SCOPES)
    assert not unclassified, (
        "these tools are declared but classified in neither partition, so they "
        f"are unreachable: {sorted(unclassified)}"
    )
    assert set(TOOL_SCOPES) == declared
    assert not (CAPTURE_TOOLS & READ_TOOLS)
    assert not (CAPTURE_TOOLS & ADMIN_TOOLS)
    assert not (READ_TOOLS & ADMIN_TOOLS)
    assert len(CAPTURE_TOOLS) + len(READ_TOOLS) + len(ADMIN_TOOLS) == len(declared)
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


# --- Task 8: a keyed call is attributed in the journal ---------------------
#
# REST's counterpart is `test_a_keyed_capture_stamps_its_key_on_the_journal`
# (tests/test_api_keys.py): a keyed door that still journals `api_key_id=None`
# passes every other test in this file, because nothing else asserts what doc
# 18 §5 convention 8 is actually about. These drive an in-process tool call
# rather than the mounted `door` above, so the write lands in this test's own
# `session` and can be read straight back.

import contextlib

from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from sqlalchemy import text as sql_text

from app.api.mcp.server import memory_add
import app.api.mcp.server as mcp_server_module


@contextlib.asynccontextmanager
async def authenticated_as(credential: str):
    """Run a tool call as the holder of `credential`.

    In-process calls bypass the transport, so without this the auth context is
    empty and `require_scope_for_tool`/`current_api_key_id` see no token —
    which is correct behaviour for an unauthenticated call, not a reason to
    weaken it here.

    `auth_context_var` holds an `AuthenticatedUser` (`get_access_token` reads
    `.access_token` off it), not the bare `AccessToken` the verifier returns —
    the SDK's real transport wraps it the same way in
    `AuthContextMiddleware.__call__`; skipping that wrapping here would make
    `get_access_token()` raise `AttributeError` instead of returning the token.
    """
    token = await ApiKeyTokenVerifier().verify_token(credential)
    assert token is not None, "the fixture minted a credential the verifier rejects"
    reset = auth_context_var.set(AuthenticatedUser(token))
    try:
        yield token
    finally:
        auth_context_var.reset(reset)


@pytest_asyncio.fixture
async def keyed_capture(session, monkeypatch):
    """Both the verifier (auth.py) and the tool body (server.py) open their own
    session through a module-level `async_session_factory`; each is a separate
    import binding, so both must be patched to this test's `session` for the
    key to authenticate and the write to land somewhere this test can read
    back — the same pattern the `verifier` fixture above uses for auth.py
    alone.

    `_pipeline` is process-global state (`app.api.mcp.server.set_pipeline`),
    set by whichever test ran last; pinning it to None here (restored after)
    is what `tests/test_mcp_batch.py` does for the same reason — an in-process
    tool call must not depend on, or make, a real embedder/LLM call.
    """

    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_auth_module, "async_session_factory", lambda: _fake_ctx())
    monkeypatch.setattr(mcp_server_module, "async_session_factory", lambda: _fake_ctx())

    previous_pipeline = mcp_server_module._pipeline
    mcp_server_module.set_pipeline(None)
    try:
        yield session
    finally:
        mcp_server_module.set_pipeline(previous_pipeline)


async def test_a_keyed_capture_stamps_its_key_and_actor(keyed_capture):
    """`api_key_id` must be the row id, never `client_id` (the public
    `key_id`) — the two are not interchangeable, and writing the wrong one
    produces a value that joins to nothing (doc 18 §5). `actor` is the key's
    name, matching what `events.actor` already means on REST's keyed capture
    door: the credential's identity, not the client tool — `resolved_source`
    still rides `data.source`, on the memory row and in this event's own
    payload, so nothing about which tool called is lost.
    """
    session = keyed_capture
    row, credential = await issue_key(session, name="writer-bot", scopes=["capture"])
    await session.commit()

    async with authenticated_as(credential):
        await memory_add(content="a keyed capture", project="default")

    stamped = (await session.execute(
        sql_text(
            "SELECT actor, api_key_id FROM events "
            "WHERE api_key_id = CAST(:kid AS uuid) ORDER BY created_at DESC"
        ),
        {"kid": str(row.id)},
    )).mappings().all()

    assert stamped, "the keyed capture journalled no row naming its key"
    assert all(r["actor"] == "writer-bot" for r in stamped)
    assert all(r["api_key_id"] == row.id for r in stamped)

    # api_key_id must be the row UUID, not the public key_id — the two are
    # different strings and a mismatch here would mean the wrong one was
    # written even though the assertions above happen to pass.
    assert str(row.id) != row.key_id


async def test_a_keyed_capture_never_stamps_a_different_keys_id(keyed_capture):
    """The negative case doc 18 §5 needs proven, not just the positive one:
    authenticating as key A must not attribute the write to key B, even when
    both are live and both are capture-scoped."""
    session = keyed_capture
    row_a, credential_a = await issue_key(session, name="key-a", scopes=["capture"])
    row_b, _credential_b = await issue_key(session, name="key-b", scopes=["capture"])
    await session.commit()

    async with authenticated_as(credential_a):
        await memory_add(content="attributed to key a", project="default")

    on_b = (await session.execute(
        sql_text("SELECT count(*) FROM events WHERE api_key_id = CAST(:kid AS uuid)"),
        {"kid": str(row_b.id)},
    )).scalar_one()
    assert on_b == 0, "a call authenticated as key A must not stamp key B's id"

    on_a = (await session.execute(
        sql_text("SELECT count(*) FROM events WHERE api_key_id = CAST(:kid AS uuid)"),
        {"kid": str(row_a.id)},
    )).scalar_one()
    assert on_a > 0


async def test_the_stamped_id_is_joinable_back_to_the_keys_name(keyed_capture):
    """`api_key_id` exists so a key's activity is traceable months later. Prove
    the row is actually joinable, not merely non-null: a stray UUID (e.g.
    `client_id`, the public `key_id`, parsed as if it were a UUID and coerced)
    would still satisfy `IS NOT NULL` while joining to nothing.
    """
    session = keyed_capture
    row, credential = await issue_key(session, name="joinable-key", scopes=["capture"])
    await session.commit()

    async with authenticated_as(credential):
        await memory_add(content="joinable capture", project="default")

    names = (await session.execute(
        sql_text(
            "SELECT ak.name FROM events e "
            "JOIN api_keys ak ON e.api_key_id = ak.id "
            "WHERE e.api_key_id = CAST(:kid AS uuid)"
        ),
        {"kid": str(row.id)},
    )).scalars().all()

    assert names, "the stamped api_key_id does not join to any api_keys row"
    assert all(name == "joinable-key" for name in names)


async def test_a_keyed_update_and_delete_also_stamp_the_key(keyed_capture):
    """The brief names four call sites, not one; memory_update and
    memory_delete must stamp the same way memory_add does.

    The target memory is inserted directly (the shape
    `tests/test_empty_content_update.py` uses) rather than produced through
    `memory_add`, which only buffers by default and needs a real pipeline run
    to materialize a row `memory_update`/`memory_delete` can find.
    """
    import uuid as _uuid

    from app.api.mcp.server import memory_delete, memory_update
    from app.models.memory import Memory

    session = keyed_capture
    row, credential = await issue_key(session, name="writer-bot-2", scopes=["capture"])
    await session.commit()

    memory_id = _uuid.uuid4()
    session.add(Memory(
        id=memory_id, content="will be updated then deleted", source="mcp",
        importance=0.5, metadata_={},
    ))
    await session.flush()
    await session.commit()

    async with authenticated_as(credential):
        await memory_update(memory_id=str(memory_id), content="updated content")
        await memory_delete(memory_id=str(memory_id))

    rows = (await session.execute(
        sql_text(
            "SELECT event_type, actor, api_key_id FROM events "
            "WHERE api_key_id = CAST(:kid AS uuid) ORDER BY created_at"
        ),
        {"kid": str(row.id)},
    )).mappings().all()

    event_types = [r["event_type"] for r in rows]
    assert "update" in event_types, event_types
    assert "delete" in event_types, event_types
    assert all(r["actor"] == "writer-bot-2" for r in rows)
    assert all(r["api_key_id"] == row.id for r in rows)
