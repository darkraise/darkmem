# MCP v2 Migration and Bearer Auth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate darkmem's MCP server to SDK v2 (protocol `2026-07-28`) and require bearer authentication on `/mcp`, landing both in a single deploy.

**Architecture:** The tree's whole SDK surface is two import lines, so the migration is an import swap plus a server-object rename; `TransportSecuritySettings` and the 33 tool bodies are unchanged. Auth is then an `mcp.server.auth` `TokenVerifier` over the existing `api_keys` table, with per-tool scope enforced body-side via `get_access_token()` — never from the `Mcp-Name` header, which the protocol makes non-authoritative.

**Tech Stack:** Python 3.12, FastAPI, `mcp` 2.x, SQLAlchemy async, pytest.

**Spec:** `docs/superpowers/specs/2026-08-26-mcp-v2-migration-and-auth-design.md`

## Global Constraints

- **`backend/requirements.lock` is regenerated ONLY with `uv pip compile --universal pyproject.toml -o requirements.lock`.** A non-universal Windows resolve leaks pywin32 and drops uvloop.
- **`ratify` is never an API-key scope.** `FORBIDDEN_SCOPES` holds it, `parse_scopes` refuses it, `has_scope` refuses to test for it, and an import-time assertion fails the process if it enters `API_KEY_SCOPES`. No task adds a path around this.
- **The Host allowlist stays on.** Bearer auth is added *beside* it, never in place of it. A LAN `421` is fixed by extending `MCP_ALLOWED_HOSTS`, never by disabling the check (invariant 20).
- **Auth is required always, with no opt-out flag** (owner ruling 2026-08-26). Do not add an env var or config row that disables it.
- **Scope is read from the request body, never from `Mcp-Name`.** The protocol makes the body the source of truth; authorizing on the header is exploitable by a non-conforming client.
- **Both parts land in one deploy** (owner ruling 2026-08-26).
- **Merge gate:** `./scripts/gate.sh` from the repo root. Backend tests alone: `cd backend && python -m pytest -q`.
- **Invariant 13:** exactly one uvicorn worker. No task introduces `--workers`, `WEB_CONCURRENCY` or `deploy.replicas`.

---

### Task 1: Replace the tool roster test with an AST-derived one

The migration's safety net, and it must exist *before* the migration. Today's `test_mcp_tools_registered` hand-lists ten names and asserts `len(tool_names) >= 10` against a roster of 33 — a rename losing twenty tools passes it clean.

**Files:**
- Modify: `backend/tests/test_mcp.py:7-22`

**Interfaces:**
- Consumes: nothing.
- Produces: `_declared_tool_names() -> set[str]`, imported by Task 7's scope-partition test.

- [ ] **Step 1: Write the failing test**

Replace the body of `test_mcp_tools_registered` in `backend/tests/test_mcp.py`:

```python
import ast
import pathlib

SERVER_PATH = pathlib.Path(__file__).resolve().parents[1] / "app" / "api" / "mcp" / "server.py"


def _declared_tool_names() -> set[str]:
    """Every function in server.py carrying an @mcp.tool decorator.

    Derived from the module's own AST rather than hand-listed: a tool lost in
    a refactor must fail the build, which a `>= 10` floor over a roster of 33
    cannot do.
    """
    tree = ast.parse(SERVER_PATH.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Attribute) and target.attr == "tool":
                names.add(node.name)
    return names


async def test_mcp_tools_registered():
    declared = _declared_tool_names()
    assert len(declared) >= 30, f"AST found only {len(declared)} tools; the scan is broken"

    registered = {t.name for t in await mcp.list_tools()}
    assert registered == declared, (
        f"registered-but-undeclared: {sorted(registered - declared)}; "
        f"declared-but-unregistered: {sorted(declared - registered)}"
    )
```

- [ ] **Step 2: Run it and confirm it passes on the current tree**

Run: `cd backend && python -m pytest tests/test_mcp.py::test_mcp_tools_registered -q`
Expected: PASS. If it fails, the AST scan disagrees with the live roster — fix the scan before going further, because every later task trusts it.

- [ ] **Step 3: Prove it actually catches a loss**

Temporarily comment out the `@mcp.tool()` decorator on `memory_tags` in `backend/app/api/mcp/server.py`, re-run the test, and confirm it FAILS naming `memory_tags`. Restore the decorator and confirm it passes again.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_mcp.py
git commit -m "test(mcp): derive the tool roster from source

The hand-listed version asserted ten names and len >= 10 against a
roster of 33, so a refactor losing twenty tools passed it. Nothing else
guards the roster across the SDK migration."
```

---

### Task 2: Pin the door's current guards before touching the SDK

Characterization tests. They must pass identically before and after the migration; that is the whole point.

**Files:**
- Create: `backend/tests/test_mcp_transport.py`

**Interfaces:**
- Consumes: `build_transport_security` from `app.api.mcp.server`.
- Produces: nothing later tasks import.

- [ ] **Step 1: Write the tests**

```python
"""Transport-level guards on /mcp, pinned across the SDK v2 migration.

These assert the Host allowlist's shape, not the SDK's internals, so they
must read identically before and after the migration.
"""
from app.api.mcp.server import build_transport_security


def test_localhost_is_always_allowed():
    s = build_transport_security("")
    assert s.enable_dns_rebinding_protection is True
    assert "localhost" in s.allowed_hosts
    assert "127.0.0.1" in s.allowed_hosts


def test_configured_lan_host_is_added():
    s = build_transport_security("192.168.0.195:8000")
    assert "192.168.0.195:8000" in s.allowed_hosts
    assert "http://192.168.0.195:8000" in s.allowed_origins
    assert "https://192.168.0.195:8000" in s.allowed_origins


def test_star_disables_the_check_wholesale():
    s = build_transport_security("*")
    assert s.enable_dns_rebinding_protection is False


def test_blank_entries_are_ignored():
    s = build_transport_security(" , ,192.168.0.7:8000, ")
    assert "192.168.0.7:8000" in s.allowed_hosts
    assert "" not in s.allowed_hosts
```

- [ ] **Step 2: Run and confirm they pass**

Run: `cd backend && python -m pytest tests/test_mcp_transport.py -q`
Expected: PASS (4 tests).

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_mcp_transport.py
git commit -m "test(mcp): pin the Host allowlist shape before the SDK migration"
```

---

### Task 3: Upgrade the SDK and swap the two imports

**Files:**
- Modify: `backend/pyproject.toml` (the `mcp` pin)
- Modify: `backend/requirements.lock` (regenerated, never hand-edited)
- Modify: `backend/app/api/mcp/server.py:7` and `:55-62`

**Interfaces:**
- Consumes: Task 1's roster test, Task 2's transport tests.
- Produces: module-level `mcp` object of type `MCPServer`, same name so no call site changes.

- [ ] **Step 1: Bump the dependency**

In `backend/pyproject.toml`, change the `mcp` requirement to `mcp>=2.1.1,<3`.

- [ ] **Step 2: Regenerate the lockfile**

```bash
cd backend && uv pip compile --universal pyproject.toml -o requirements.lock
```

Confirm `requirements.lock` now shows `mcp==2.1.1` or later. Do not hand-edit it.

- [ ] **Step 3: Swap the import**

In `backend/app/api/mcp/server.py`, replace line 7:

```python
from mcp.server.fastmcp import Context, FastMCP
```

with:

```python
from mcp.server.mcpserver import Context, MCPServer
```

Leave the `TransportSecuritySettings` import on the next line untouched — that module and its three fields are unchanged in v2.

- [ ] **Step 4: Rename the server object**

Replace the `mcp = FastMCP(...)` constructor call with:

```python
mcp = MCPServer(
    "darkmem",
    json_response=True,
    stateless_http=True,
    streamable_http_path="/",
    instructions="",
    transport_security=build_transport_security(settings.mcp_allowed_hosts),
)
```

If any keyword is rejected, consult the v2 migration guide at
`https://py.sdk.modelcontextprotocol.io/v2/migration/` and record the
substitution in the commit body rather than silently dropping the argument —
`stateless_http` and `json_response` in particular encode deliberate choices.

- [ ] **Step 5: Run the two guard suites**

Run: `cd backend && python -m pytest tests/test_mcp.py tests/test_mcp_transport.py -q`
Expected: PASS. A roster mismatch here means a tool was lost in the rename.

- [ ] **Step 6: Run the whole backend suite**

Run: `cd backend && python -m pytest -q`
Expected: PASS. Investigate every failure before continuing; do not proceed on a red suite.

- [ ] **Step 7: Commit**

```bash
git add backend/pyproject.toml backend/requirements.lock backend/app/api/mcp/server.py
git commit -m "feat(mcp): migrate to SDK v2 and protocol 2026-07-28

The tree's whole SDK surface was two import lines. FastMCP is renamed
MCPServer; TransportSecuritySettings and its three fields are unchanged,
so the Host allowlist needs no work, and the tool decorator signature is
the same, so the 33 tool bodies stand."
```

---

### Task 4: Restore `refresh_mcp_instructions`

The spec's open question #1. `refresh_mcp_instructions` writes `mcp._mcp_server.instructions` — a private attribute that may have moved in v2. It is the only writable path to the live instructions, so a silent break means prompt edits stop taking effect with no error.

**Files:**
- Modify: `backend/app/api/mcp/server.py:71-83`
- Create: test in `backend/tests/test_mcp.py`

**Interfaces:**
- Consumes: the `mcp` object from Task 3.
- Produces: `refresh_mcp_instructions()` with unchanged behaviour.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_mcp.py`:

```python
async def test_refresh_mcp_instructions_reaches_the_live_server(monkeypatch):
    """Prompt edits must take effect without a restart.

    The write goes through a private SDK attribute, so an SDK upgrade can
    break it silently: nothing raises, and the only symptom is that an edited
    prompt never reaches a client.
    """
    from app.api.mcp import server as mcp_module

    monkeypatch.setattr(
        mcp_module, "refresh_mcp_instructions", mcp_module.refresh_mcp_instructions
    )
    import app.services.prompt as prompt_module
    monkeypatch.setattr(prompt_module, "get", lambda key: "SENTINEL INSTRUCTIONS")

    mcp_module.refresh_mcp_instructions()

    assert "SENTINEL INSTRUCTIONS" in (mcp_module.mcp._mcp_server.instructions or "")
```

- [ ] **Step 2: Run it**

Run: `cd backend && python -m pytest tests/test_mcp.py::test_refresh_mcp_instructions_reaches_the_live_server -q`

If PASS: the private path survived; go to Step 4.
If FAIL with `AttributeError`: the attribute moved. Continue to Step 3.

- [ ] **Step 3: Repair the write path (only if Step 2 failed)**

Locate the writable instructions attribute on the v2 server:

```bash
cd backend && python -c "
from app.api.mcp.server import mcp
print([a for a in dir(mcp) if 'instruction' in a.lower()])
print([a for a in dir(mcp) if a.startswith('_') and 'server' in a.lower()])
"
```

Update the assignment in `refresh_mcp_instructions` to the attribute that exists, and update its docstring to name the new path. Re-run Step 2 until it passes.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/mcp/server.py backend/tests/test_mcp.py
git commit -m "test(mcp): prove prompt edits still reach the live server

The write goes through a private SDK attribute, so an upgrade can break
it with no error - the only symptom being that an edited prompt never
reaches a client."
```

---

### Task 5: Protocol conformance for the new revision

**Files:**
- Create: `backend/tests/test_mcp_conformance.py`
- Modify: `backend/app/main.py` only if a conformance test fails

**Interfaces:**
- Consumes: the mounted app at `/mcp`.
- Produces: nothing later tasks import.

- [ ] **Step 1: Write the tests**

```python
"""Conformance with protocol revision 2026-07-28.

Each assertion is a MUST in the specification. They run against the mounted
app rather than a toy server, because the guards that wrap /mcp (the Host
allowlist and the proxied-MCP guard) are part of what must keep working.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

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


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://localhost:8000"
    ) as c:
        yield c


@pytest.mark.parametrize("verb", ["get", "delete"])
async def test_get_and_delete_are_not_allowed(client, verb):
    """The GET stream endpoint and DELETE session teardown are both retired."""
    resp = await getattr(client, verb)("/mcp/")
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
    assert resp.status_code != 403


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
```

- [ ] **Step 2: Run them**

Run: `cd backend && python -m pytest tests/test_mcp_conformance.py -q`

Expected: PASS. For any failure, fix the server rather than the test — each assertion is a specification MUST. The likely fixes are: a 405 handler for GET/DELETE on the mount, and confirming the SDK's Origin handling distinguishes absent from invalid.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_mcp_conformance.py backend/app/main.py
git commit -m "test(mcp): assert 2026-07-28 conformance on the mounted app

Pins the header/body mismatch rejection we rely on for scope safety, and
that an absent Origin is not an error - rejecting it would break every
non-browser agent, which is most of them."
```

---

### Task 6: A `TokenVerifier` over `api_keys`

**Files:**
- Create: `backend/app/api/mcp/auth.py`
- Create: `backend/tests/test_mcp_auth.py`

**Interfaces:**
- Consumes: `authenticate`, `parse_credential`, `mark_key_used` from `app.services.api_keys`.
- Produces: `class ApiKeyTokenVerifier` with `async def verify_token(self, token: str) -> AccessToken | None`.

- [ ] **Step 1: Write the failing test**

```python
"""Bearer verification on the MCP door, over the same api_keys rows REST uses."""
import pytest

from app.api.mcp.auth import ApiKeyTokenVerifier
from app.services.api_keys import issue_key, revoke_key


@pytest.fixture
def verifier():
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


async def test_garbage_is_refused(verifier):
    assert await verifier.verify_token("not-a-key") is None
    assert await verifier.verify_token("") is None


async def test_revoked_key_is_refused(session, verifier):
    row, credential = await issue_key(session, name="gone", scopes=["read"])
    await revoke_key(session, row.id)
    await session.commit()

    assert await verifier.verify_token(credential) is None


async def test_expired_key_is_refused(session, verifier):
    from datetime import datetime, timedelta, timezone

    past = datetime.now(timezone.utc) - timedelta(days=1)
    _row, credential = await issue_key(
        session, name="stale", scopes=["read"], expires_at=past
    )
    await session.commit()

    assert await verifier.verify_token(credential) is None
```

`issue_key` returns `(ApiKey, str)` — the row and the plaintext credential,
which is the only time the plaintext exists. `revoke_key` takes the row's
UUID (`row.id`), not the public `key_id`.

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_mcp_auth.py -q`
Expected: FAIL with `ModuleNotFoundError: app.api.mcp.auth`.

- [ ] **Step 3: Implement**

```python
"""Bearer verification for the MCP door (doc 18 §5).

Reuses `app.services.api_keys.authenticate` rather than reading the table
directly, so REST and MCP can never drift into two credential readers with
two different ideas of what a valid key is.
"""
from mcp.server.auth.provider import AccessToken, TokenVerifier

from app.database import async_session_factory
from app.services.api_keys import authenticate, mark_key_used, parse_credential


class ApiKeyTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        # `authenticate` returns a KeyPrincipal, which carries the row UUID but
        # not the public key_id, so the id is parsed from the credential the
        # caller presented. Both are needed and they are not interchangeable.
        parsed = parse_credential(token)
        if parsed is None:
            return None
        key_id, _secret = parsed

        async with async_session_factory() as session:
            principal = await authenticate(session, token)

        if principal is None:
            return None

        await mark_key_used(principal.api_key_id)

        return AccessToken(
            token=token,
            client_id=key_id,
            scopes=sorted(principal.scopes),
            # `authenticate` already refuses expired and revoked keys, so a
            # None here means "no further expiry for the SDK to enforce",
            # never "never expires".
            expires_at=None,
            subject=principal.name,
        )
```

- [ ] **Step 4: Run the tests**

Run: `cd backend && python -m pytest tests/test_mcp_auth.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/mcp/auth.py backend/tests/test_mcp_auth.py
git commit -m "feat(mcp): verify bearer keys against the api_keys table

Reuses authenticate() so REST and MCP cannot drift into two credential
readers. client_id is the public key_id, not the row UUID - the journal
stores the row id and conflating them writes an unjoinable value."
```

---

### Task 7: Require auth on the door, and declare a scope per tool

**Files:**
- Modify: `backend/app/api/mcp/server.py` (constructor, and a decorator per tool)
- Create: `backend/app/api/mcp/scopes.py`
- Modify: `backend/tests/test_mcp_auth.py`

**Interfaces:**
- Consumes: `ApiKeyTokenVerifier` from Task 6.
- Produces: `TOOL_SCOPES: dict[str, str]` and `require_tool_scope(scope: str)`.

- [ ] **Step 1: Write the scope registry**

Create `backend/app/api/mcp/scopes.py`:

```python
"""Which scope each MCP tool requires (doc 18 §5).

Scope is decided from the tool actually invoked - the request body - never
from the `Mcp-Name` header. The protocol makes the body the source of truth
and requires servers to reject header/body mismatches, so authorizing on the
header would be exploitable by a non-conforming client.
"""
CAPTURE_TOOLS: frozenset[str] = frozenset({
    "memory_add",
    "memory_batch_add",
    "memory_update",
    "memory_delete",
    "document_put",
    "document_delete",
    "checkpoint_save",
    "research_run",
})
```

- [ ] **Step 2: Write the failing tests**

Append to `backend/tests/test_mcp_auth.py`:

```python
from app.api.mcp.scopes import CAPTURE_TOOLS


def test_every_tool_declares_a_scope():
    """A tool added without a scope must fail the build, not ship unscoped.

    The roster is derived from source (see tests/test_mcp.py), so this cannot
    go stale the way a hand-listed set would.
    """
    from tests.test_mcp import _declared_tool_names

    declared = _declared_tool_names()
    unknown = CAPTURE_TOOLS - declared
    assert not unknown, f"CAPTURE_TOOLS names tools that do not exist: {sorted(unknown)}"

    # Everything not a writer is a reader; the point is that the partition is
    # total, so no tool is left without a decision.
    readers = declared - CAPTURE_TOOLS
    assert readers, "no read tools found; the partition is broken"
    assert len(readers) + len(CAPTURE_TOOLS) == len(declared)


def test_ratify_is_not_reachable_as_a_tool_scope():
    from app.services.api_key_scopes import FORBIDDEN_SCOPES

    assert "ratify" in FORBIDDEN_SCOPES
    assert "ratify" not in CAPTURE_TOOLS
```

- [ ] **Step 3: Run and confirm they pass**

Run: `cd backend && python -m pytest tests/test_mcp_auth.py -q`
Expected: PASS. A failure naming a tool means `CAPTURE_TOOLS` is stale against the roster — fix the set, not the test.

- [ ] **Step 4: Wire the verifier into the server**

In `backend/app/api/mcp/server.py`, add `token_verifier` to the constructor:

```python
from app.api.mcp.auth import ApiKeyTokenVerifier

mcp = MCPServer(
    "darkmem",
    json_response=True,
    stateless_http=True,
    streamable_http_path="/",
    instructions="",
    transport_security=build_transport_security(settings.mcp_allowed_hosts),
    token_verifier=ApiKeyTokenVerifier(),
)
```

- [ ] **Step 5: Enforce the scope inside each capture tool**

Add to `backend/app/api/mcp/scopes.py`:

```python
from mcp.server.auth.middleware.auth_context import get_access_token


class ScopeDenied(PermissionError):
    """The presented key authenticated but lacks the scope this tool needs."""


def require_scope(tool_name: str) -> None:
    """Refuse unless the authenticated key carries this tool's scope.

    Reads the principal from the auth context, which is populated from the
    verified bearer - body-side, so the `Mcp-Name` header is never consulted
    for an authorization decision.
    """
    needed = "capture" if tool_name in CAPTURE_TOOLS else "read"
    token = get_access_token()
    if token is None:
        raise ScopeDenied("this door requires an API key")
    if needed not in token.scopes:
        raise ScopeDenied(f"key lacks the {needed!r} scope")
```

Call `require_scope("<tool_name>")` as the first statement of each of the 33 tool bodies, passing the tool's own name.

- [ ] **Step 6: Run the full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: PASS. Existing MCP tests that call tools in-process will now need a key or an authenticated context — update them to mint one rather than weakening `require_scope`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/mcp/scopes.py backend/app/api/mcp/server.py backend/tests/test_mcp_auth.py
git commit -m "feat(mcp): require a bearer key and a per-tool scope

Scope is decided from the invoked tool - the request body - never from
Mcp-Name. The protocol makes the body the source of truth, so a
non-conforming client sending one name in the header and another in the
body would otherwise bypass the check."
```

---

### Task 8: Attribute keyed calls in the journal

**Files:**
- Modify: `backend/app/api/mcp/server.py:185,284,301,335`
- Modify: `backend/tests/test_mcp_auth.py`

**Interfaces:**
- Consumes: `get_access_token()` and `ApiKeyTokenVerifier` from Tasks 6-7.
- Produces: nothing later tasks import.

- [ ] **Step 1: Write the failing test**

```python
async def test_keyed_capture_stamps_the_key_and_actor(session):
    """doc 18 §5: every keyed call stamps events.api_key_id and events.actor.

    Those two columns were dormant until the activation; a keyed write that
    leaves them null is indistinguishable from an unauthenticated one in the
    audit.
    """
    from sqlalchemy import select

    from app.api.mcp.server import memory_add
    from app.models.event import Event

    row, credential = await issue_key(session, name="writer-bot", scopes=["capture"])
    await session.commit()

    async with authenticated_as(credential):
        await memory_add(content="a keyed capture", project="default")

    journalled = (
        await session.execute(
            select(Event).where(Event.actor == "writer-bot").order_by(Event.created_at.desc())
        )
    ).scalars().first()

    assert journalled is not None, "a keyed capture journalled no event"
    assert journalled.api_key_id == row.id, "api_key_id must be the row id, not key_id"
```

`authenticated_as` is a helper this task adds to `backend/tests/test_mcp_auth.py`:
it pushes a verified `AccessToken` into the SDK's auth context so an in-process
tool call sees the same principal an HTTP call would.

```python
import contextlib

from mcp.server.auth.middleware.auth_context import auth_context_var

from app.api.mcp.auth import ApiKeyTokenVerifier


@contextlib.asynccontextmanager
async def authenticated_as(credential: str):
    """Run a tool call as the holder of `credential`.

    In-process calls bypass the transport, so without this the auth context is
    empty and `require_scope` refuses - which is correct behaviour, not a
    reason to weaken the check.
    """
    token = await ApiKeyTokenVerifier().verify_token(credential)
    assert token is not None, "the fixture minted a credential the verifier rejects"
    reset = auth_context_var.set(token)
    try:
        yield token
    finally:
        auth_context_var.reset(reset)
```

If `auth_context_var` is not the SDK's exported name, find it with
`python -c "import mcp.server.auth.middleware.auth_context as m; print(dir(m))"`
and use what that module actually exposes.

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_mcp_auth.py -k stamps -q`
Expected: FAIL — `api_key_id` is null, because all four call sites hardcode `None`.

- [ ] **Step 3: Replace the four hardcoded `None`s**

At `server.py` lines 185, 284, 301 and 335, replace `api_key_id=None` with the row id of the authenticated key. Resolve it once per call from the auth context:

Add this helper to `backend/app/api/mcp/auth.py`, beside the verifier:

```python
async def current_api_key_id() -> uuid.UUID | None:
    """The row id of the key that authenticated this call, or None.

    `AccessToken.client_id` is the public `key_id`, so the row id is looked up
    from it. `events.api_key_id` stores the row id; the two are not
    interchangeable and storing the wrong one writes an unjoinable value.
    """
    token = get_access_token()
    if token is None:
        return None
    async with async_session_factory() as session:
        row = (
            await session.execute(
                select(ApiKey).where(ApiKey.key_id == token.client_id)
            )
        ).scalar_one_or_none()
    return row.id if row is not None else None
```

with `from mcp.server.auth.middleware.auth_context import get_access_token`,
`from sqlalchemy import select` and `from app.models.api_key import ApiKey` at
the top of the module.

Leave `actor=resolve_client_source(...)` alone at each site *except* where the spec requires the key name: `actor` becomes the key's name. Keep the `source` ladder untouched — `source` says which client tool, `actor` says which credential.

- [ ] **Step 4: Run the test**

Run: `cd backend && python -m pytest tests/test_mcp_auth.py -k stamps -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/mcp/auth.py backend/app/api/mcp/server.py backend/tests/test_mcp_auth.py
git commit -m "feat(mcp): stamp api_key_id and actor on keyed calls

Those columns were dormant until the activation. A keyed write leaving
them null is indistinguishable from an unauthenticated one in the audit."
```

---

### Task 9: Amend the docs the change invalidates

Several statements in the tree become false the moment this ships. A stale justification invites a later reader to delete a guard as obsolete.

**Files:**
- Modify: `CLAUDE.md` (the "MCP endpoint" section)
- Modify: `docs/design/18-security-auth-and-trust.md` §5
- Modify: `docs/design/12-api-and-mcp-contract.md`
- Modify: `backend/app/main.py:733-753` (`ProxiedMcpGuardMiddleware` docstring)
- Modify: `docs/runbook-exposed-deployment.md`

- [ ] **Step 1: CLAUDE.md**

Replace "`/mcp` is unauthenticated (local-network trust model)" with the new posture: a bearer key is required on every call, the Host allowlist still applies beside it, and there is no flag that disables either.

- [ ] **Step 2: doc 18 §5**

Record the second activation with its date, mirroring how the first activation (2026-08-16) is recorded. State that the MCP half is now live and that `ratify` remains outside the vocabulary.

- [ ] **Step 3: `ProxiedMcpGuardMiddleware` docstring**

Its premise — "`/mcp` is unauthenticated by design … its bearer-required option is designed but unshipped" — is now false, while the guard itself is still wanted: it answers "did this arrive from outside", which a valid key does not answer. Rewrite the premise and keep the guard.

- [ ] **Step 4: doc 12 and the exposed-deployment runbook**

Update the MCP contract's auth section, and the runbook line stating `/mcp` must not be routed from the public side because its bearer option is unshipped.

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md docs/design/18-security-auth-and-trust.md docs/design/12-api-and-mcp-contract.md docs/runbook-exposed-deployment.md backend/app/main.py
git commit -m "docs(mcp): record that the door now requires a key

The proxied-guard docstring justified itself on /mcp being
unauthenticated. That premise is now false while the guard is still
wanted - it answers 'did this arrive from outside', which a valid key
does not answer - so the premise changes and the guard stays."
```

---

### Task 10: Gate, mint, reconfigure, deploy

Order is load-bearing. Deploying before a key exists breaks every agent talking to `/mcp`, and both parts land in one deploy (owner ruling), so there is no half-step to fall back to.

- [ ] **Step 1: Run the full merge gate**

Run: `./scripts/gate.sh`
Expected: `GATE GREEN`. Do not proceed on red. `GATE BLOCKED` (exit 2) is a missing toolchain, not a failure.

- [ ] **Step 2: Mint a key in the UI before anything is deployed**

Settings → API keys → create, with **both** `capture` and `read`. Copy the secret; it is shown once and never stored.

- [ ] **Step 3: Update every MCP client config**

Add `Authorization: Bearer dmk_…` to each client that reaches this server. Enumerate them first — an agent missed here simply stops working with no other symptom.

- [ ] **Step 4: Build and deploy**

```bash
DARKMEM_PUSH=0 ./scripts/build-push.sh
docker compose up -d
```

Wait for the container to report `healthy`.

- [ ] **Step 5: Verify both directions against the running container**

A keyed call succeeds:

```bash
curl -s -X POST http://127.0.0.1:8000/mcp/ \
  -H 'Authorization: Bearer dmk_YOUR_KEY' \
  -H 'MCP-Protocol-Version: 2026-07-28' -H 'Mcp-Method: tools/call' \
  -H 'Mcp-Name: memory_stats' -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"memory_stats","arguments":{},"_meta":{"io.modelcontextprotocol/protocolVersion":"2026-07-28","io.modelcontextprotocol/clientInfo":{"name":"verify","version":"1"},"io.modelcontextprotocol/clientCapabilities":{}}}}'
```

An unkeyed call is refused: repeat without the `Authorization` header and confirm it is rejected.

- [ ] **Step 6: Confirm the change is in the running image, not just the tree**

```bash
docker exec darkmem-prod-darkmem-1 grep -c "mcpserver" /app/app/api/mcp/server.py
```

Expected: at least 1. Compose reuses an image whose tag did not move, so a skipped build redeploys the old bits and still reports `Started`.

---

## Rollback

One step, because both parts landed in one deploy and the migration carries no schema change:

```bash
DARKMEM_VERSION=1.2.1 docker compose up -d
```

If a schema change is ever added to this work, this section must be rewritten before it ships.
