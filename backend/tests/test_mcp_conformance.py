"""Conformance with protocol revision 2026-07-28.

Each assertion is a MUST in the specification. They run against the mounted
app rather than a toy server, because the guards that wrap /mcp (the Host
allowlist and the proxied-MCP guard) are part of what must keep working.
"""
import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import _mcp_app, app

MODERN = {
    "MCP-Protocol-Version": "2026-07-28",
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
}


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


@pytest_asyncio.fixture(scope="session")
async def _mcp_mount_lifespan():
    """Enter the mounted /mcp sub-app's own lifespan once for the module.

    The literal fixture the task brief specifies (a bare ``ASGITransport``
    over ``app.main.app``, entered fresh per test) 500s on every /mcp
    request: the mounted streamable app's ``StreamableHTTPSessionManager``
    is only started inside its own ``lifespan=lambda app:
    session_manager.run()`` (see
    ``mcp.server.lowlevel.server.Server.streamable_http_app``), and httpx's
    ``ASGITransport`` never drives ASGI lifespan events, so an untouched
    client hits "Task group is not initialized. Make sure to use run()."
    every time. This is not the app's full FastAPI ``lifespan`` (DB warmup,
    LLM orchestrator, job registry) — conftest's own ``client`` fixture
    deliberately skips all of that too — only the /mcp sub-app's own
    lifespan needs to run for its routes to serve requests.

    It cannot be entered per test either: ``StreamableHTTPSessionManager.run()``
    is single-use by the SDK's own design ("can only be called once per
    instance"), and ``app.main``'s mounted ``_mcp_app`` is a module-level
    singleton built once at import time — precisely how production runs it,
    once for the life of the process, inside ``app.main.lifespan``. So this
    fixture is session-scoped and entered exactly once, mirroring that
    shape, with a per-test ``AsyncClient`` layered on top by the ``client``
    fixture below. The task's own pytest config pins one event loop for the
    whole session (``asyncio_default_fixture_loop_scope = session``), so a
    session-scoped async fixture shares its loop with every test safely.
    """
    started = asyncio.Event()
    stop = asyncio.Event()

    async def _run_lifespan():
        async with _mcp_app.router.lifespan_context(_mcp_app):
            started.set()
            await stop.wait()

    runner = asyncio.create_task(_run_lifespan())
    startup = asyncio.create_task(started.wait())
    done, _ = await asyncio.wait({runner, startup}, return_when=asyncio.FIRST_COMPLETED)
    if runner in done:
        startup.cancel()
        runner.result()  # surfaces the startup exception instead of hanging
    try:
        yield
    finally:
        stop.set()
        await runner


@pytest_asyncio.fixture
async def client(_mcp_mount_lifespan, mcp_credential):
    """AsyncClient against the mounted FastAPI app, carrying a valid key.

    Exercises the real mount together with every guard wrapping it
    (Host allowlist, ``ProxiedMcpGuardMiddleware``), backed by the
    session-scoped lifespan above.

    Every assertion below is a protocol MUST, and since /mcp requires a bearer
    the probes have to clear the auth gate to reach the behaviour they are
    about - otherwise each one would pass on a 401 while proving nothing. The
    key is the conftest suite key, not a disabled check.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost:8000",
        headers={"Authorization": f"Bearer {mcp_credential}"},
    ) as c:
        yield c


@pytest.mark.parametrize("verb", ["get", "delete"])
async def test_get_and_delete_are_not_allowed(client, verb):
    """The GET stream endpoint and DELETE session teardown are both retired.

    This must carry ``MCP-Protocol-Version: 2026-07-28``: without it, the
    manager cannot tell the request apart from an older client's, so it
    dispatches to the legacy stateless handler instead of the modern one —
    for GET that legacy path opens a standalone SSE stream and blocks
    forever rather than 405ing, which is correct behaviour for an old
    client's request, not a bug, but the wrong revision to probe here.
    """
    resp = await getattr(client, verb)(
        "/mcp/", headers={"MCP-Protocol-Version": "2026-07-28"}
    )
    assert resp.status_code == 405


async def test_header_body_mismatch_is_rejected(client):
    """The SDK enforces this; the test pins that we rely on it.

    Without it, a middleware authorizing on Mcp-Name while the server executes
    the body would be a scope bypass.
    """
    headers = {**MODERN, "Mcp-Method": "tools/call", "Mcp-Name": "memory_search"}
    resp = await client.post("/mcp/", headers=headers, json=_call("memory_stats"))
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == -32020


async def test_absent_origin_is_not_an_error(client):
    """Most MCP agents are not browsers and send no Origin. Rejecting its
    absence would break every one of them."""
    headers = {**MODERN, "Mcp-Method": "tools/call", "Mcp-Name": "memory_stats"}
    resp = await client.post("/mcp/", headers=headers, json=_call("memory_stats"))
    assert resp.status_code == 200


async def test_present_but_invalid_origin_is_forbidden(client):
    headers = {
        **MODERN,
        "Mcp-Method": "tools/call",
        "Mcp-Name": "memory_stats",
        "Origin": "http://attacker.example",
    }
    resp = await client.post("/mcp/", headers=headers, json=_call("memory_stats"))
    assert resp.status_code == 403


@pytest.mark.parametrize("stale", ["Mcp-Session-Id", "Last-Event-ID"])
async def test_retired_session_headers_are_ignored(client, stale):
    """Sessions and resumable streams are gone in this revision.

    The server must neither honour these nor fail on them: an older client
    that still sends one should simply be served, and no session id may be
    minted or echoed back.
    """
    headers = {
        **MODERN,
        "Mcp-Method": "tools/call",
        "Mcp-Name": "memory_stats",
        stale: "whatever",
    }
    resp = await client.post("/mcp/", headers=headers, json=_call("memory_stats"))
    assert resp.status_code != 400, f"{stale} should be ignored, not rejected"
    # Pinned to 200 rather than left at "not 400": once the door requires a
    # bearer, a refusal that never reached the transport would satisfy the
    # inequality above while proving nothing about the stale header.
    assert resp.status_code == 200
    assert "Mcp-Session-Id" not in resp.headers


async def test_foreign_host_still_gets_421(client):
    """Invariant 20: the Host allowlist is unchanged by the migration."""
    headers = {
        **MODERN,
        "Mcp-Method": "tools/call",
        "Mcp-Name": "memory_stats",
        "Host": "attacker.example",
    }
    resp = await client.post("/mcp/", headers=headers, json=_call("memory_stats"))
    assert resp.status_code == 421
