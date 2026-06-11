# Memory Source Attribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Memories written via MCP record which tool created them (claude-code, codex, kiro, ...) instead of a flat `"mcp"`, resolved per request from explicit args, an `X-Darkmem-Client` header, or the User-Agent.

**Architecture:** A new `client_identity.py` resolver is called by `memory_add` / `memory_batch_add` in the MCP server; it unwraps the starlette request from the FastMCP `Context` (injected via a `ctx: Context | None = None` parameter, excluded from the wire schema) and never raises. Batch entries are resolved on the raw dicts *before* Pydantic validation, because `MemoryCreate.source` defaults to `"api"` during validation and erases the absent-vs-explicit distinction. The UI create dialog gains `source: "dashboard"`, and the two duplicated `SOURCE_COLORS` maps consolidate into `src/lib/source-colors.ts`.

**Tech Stack:** FastAPI + mcp SDK (FastMCP, stateless streamable HTTP), SQLAlchemy async, pytest + httpx ASGITransport, React/TanStack + vitest.

**Spec:** `docs/superpowers/specs/2026-06-11-memory-source-attribution-design.md`. Note: the spec names a `default_source_agent(ctx)` helper; this plan implements `resolve_source_agent(explicit, ctx)` which subsumes it (explicit truncation + UA default in one function).

**Verification environment:** Backend tests need the dev-compose Postgres on 127.0.0.1:5433 with a `darkmem_test` database (see CLAUDE.md "Commands"). All backend commands run from `backend/`, frontend commands from `frontend/`.

---

### Task 1: `client_identity.py` resolver (TDD)

**Files:**
- Create: `backend/app/api/mcp/client_identity.py`
- Test: `backend/tests/test_client_identity.py`

- [ ] **Step 1: Write the failing unit tests**

Create `backend/tests/test_client_identity.py`:

```python
from types import SimpleNamespace

from starlette.datastructures import Headers

from app.api.mcp.client_identity import (
    resolve_client_source,
    resolve_source_agent,
)


class _Ctx:
    """Stand-in for FastMCP Context: request_context.request.headers."""

    def __init__(self, headers: dict[str, str] | None, request_present: bool = True):
        request = SimpleNamespace(headers=Headers(headers or {})) if request_present else None
        self._request_context = SimpleNamespace(request=request)

    @property
    def request_context(self):
        return self._request_context


class _RaisingCtx:
    """Mimics Context outside a request: the property raises ValueError."""

    @property
    def request_context(self):
        raise ValueError("Context is not available outside of a request")


def test_explicit_source_wins_over_header():
    ctx = _Ctx({"x-darkmem-client": "codex"})
    assert resolve_client_source("my-orchestrator", ctx) == "my-orchestrator"


def test_explicit_mcp_is_treated_as_unspecified():
    ctx = _Ctx({"x-darkmem-client": "codex"})
    assert resolve_client_source("mcp", ctx) == "codex"


def test_explicit_source_truncated_to_column_width():
    assert resolve_client_source("x" * 150, None) == "x" * 100


def test_header_sanitized():
    ctx = _Ctx({"x-darkmem-client": "  Kiro IDE!  "})
    assert resolve_client_source(None, ctx) == "kiroide"


def test_header_beats_user_agent():
    ctx = _Ctx({"x-darkmem-client": "kiro", "user-agent": "claude-code/2.0"})
    assert resolve_client_source(None, ctx) == "kiro"


def test_claude_code_user_agent_detected():
    ctx = _Ctx({"user-agent": "claude-code/2.1.172 (cli)"})
    assert resolve_client_source(None, ctx) == "claude-code"


def test_generic_user_agents_rejected():
    for ua in [
        "node",
        "Bun/1.3.8",
        "python-httpx/0.28.1",
        "Mozilla/5.0 (Windows NT 10.0)",
    ]:
        ctx = _Ctx({"user-agent": ua})
        assert resolve_client_source(None, ctx) == "mcp", ua


def test_unknown_distinctive_ua_passes_through_slugged():
    ctx = _Ctx({"user-agent": "FutureAgent/0.3"})
    assert resolve_client_source(None, ctx) == "futureagent"


def test_empty_user_agent_treated_as_absent():
    ctx = _Ctx({"user-agent": ""})
    assert resolve_client_source(None, ctx) == "mcp"
    assert resolve_source_agent(None, ctx) is None


def test_no_signals_falls_back():
    assert resolve_client_source(None, None) == "mcp"
    assert resolve_client_source(None, _Ctx(None, request_present=False)) == "mcp"


def test_raising_request_context_swallowed():
    assert resolve_client_source(None, _RaisingCtx()) == "mcp"
    assert resolve_source_agent(None, _RaisingCtx()) is None


def test_source_agent_defaults_to_raw_ua():
    ctx = _Ctx({"user-agent": "claude-code/2.1.172 (cli)"})
    assert resolve_source_agent(None, ctx) == "claude-code/2.1.172 (cli)"


def test_explicit_source_agent_wins_and_truncates():
    ctx = _Ctx({"user-agent": "claude-code/2.1.172 (cli)"})
    assert resolve_source_agent("eval-r3", ctx) == "eval-r3"
    assert resolve_source_agent("a" * 300, None) == "a" * 255
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_client_identity.py -q`
Expected: collection error — `ModuleNotFoundError: No module named 'app.api.mcp.client_identity'`

- [ ] **Step 3: Implement the resolver**

Create `backend/app/api/mcp/client_identity.py`:

```python
"""Resolve which client/tool issued an MCP call.

The MCP endpoint is stateless (``stateless_http=True``), so the handshake's
``clientInfo`` is never available during tool calls. Identity is resolved per
request from explicit tool arguments and HTTP headers instead; see
docs/superpowers/specs/2026-06-11-memory-source-attribution-design.md.
"""
import logging
import re

logger = logging.getLogger(__name__)

CLIENT_HEADER = "x-darkmem-client"
FALLBACK_SOURCE = "mcp"

_SOURCE_MAX_LEN = 100  # memories.source is String(100)
_AGENT_MAX_LEN = 255  # memories.source_agent is String(255)

_SLUG_RE = re.compile(r"[^a-z0-9._-]+")

# Runtime/library User-Agent product tokens that say nothing about which
# tool is calling.
GENERIC_UA_TOKENS = frozenset({
    "node", "bun", "deno", "mozilla", "python-httpx", "python-requests",
    "python-urllib", "python-aiohttp", "aiohttp", "curl", "undici", "axios",
    "go-http-client", "okhttp", "java", "libwww-perl", "wget",
})

# Distinctive User-Agent product tokens -> canonical source names.
KNOWN_UA_SOURCES = {
    "claude-code": "claude-code",
}


def _sanitize(value: str) -> str:
    return _SLUG_RE.sub("", value.strip().lower())[:_SOURCE_MAX_LEN]


def _request_from_ctx(ctx):
    # ``ctx.request_context`` raises ValueError outside a request (e.g.
    # in-process ``call_tool``); over stdio it exists with request=None.
    if ctx is None:
        return None
    try:
        return ctx.request_context.request
    except (ValueError, LookupError, AttributeError):
        return None


def _ua_product_source(user_agent: str) -> str | None:
    token = user_agent.split(None, 1)[0] if user_agent.strip() else ""
    product, sep, _version = token.partition("/")
    if not sep:
        return None
    slug = _sanitize(product)
    if not slug or slug in GENERIC_UA_TOKENS:
        return None
    return KNOWN_UA_SOURCES.get(slug, slug)


def resolve_client_source(explicit_source, ctx) -> str:
    """Resolve the source label: explicit arg > header > User-Agent > "mcp".

    The literal "mcp" counts as unspecified so agents copying the old default
    cannot mask detection. Never raises: attribution must not fail a write.
    """
    try:
        if isinstance(explicit_source, str):
            explicit = explicit_source.strip()
            if explicit and explicit != FALLBACK_SOURCE:
                return explicit[:_SOURCE_MAX_LEN]
        request = _request_from_ctx(ctx)
        if request is not None:
            header_source = _sanitize(request.headers.get(CLIENT_HEADER, ""))
            if header_source:
                return header_source
            ua_source = _ua_product_source(request.headers.get("user-agent", ""))
            if ua_source:
                return ua_source
    except Exception:
        logger.debug("client source resolution failed", exc_info=True)
    return FALLBACK_SOURCE


def resolve_source_agent(explicit_agent, ctx) -> str | None:
    """Explicit value (truncated) or the raw User-Agent; None without either."""
    try:
        if isinstance(explicit_agent, str) and explicit_agent.strip():
            return explicit_agent.strip()[:_AGENT_MAX_LEN]
        request = _request_from_ctx(ctx)
        if request is None:
            return None
        user_agent = request.headers.get("user-agent", "").strip()
        return user_agent[:_AGENT_MAX_LEN] or None
    except Exception:
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_client_identity.py -q`
Expected: `13 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/mcp/client_identity.py backend/tests/test_client_identity.py
git commit -m "feat(mcp): add client identity resolver for memory source"
```

---

### Task 2: Shared MCP-over-HTTP test fixtures + migrate the transport-security test

FastMCP caches one `StreamableHTTPSessionManager` per instance and its `run()` raises on a second entry; `test_mcp_transport_security.py` already enters it once per pytest process, so every streamable-app test must reset the cached manager first. MCP tools also commit via the module-level `async_session_factory` (NOT the FastAPI `get_session` override), so the factory is monkeypatched onto the per-test savepoint session.

**Files:**
- Modify: `backend/tests/conftest.py` (append fixtures at end of file)
- Modify: `backend/tests/test_mcp_transport_security.py:32-50`

- [ ] **Step 1: Add the fixtures to `backend/tests/conftest.py`**

Append at the end of the file:

```python
@pytest_asyncio.fixture
async def mcp_streamable_app():
    """Fresh streamable-HTTP app with its lifespan entered.

    FastMCP caches one StreamableHTTPSessionManager whose run() is
    once-per-instance, so the cached manager is dropped first; the app must
    be built AFTER the reset so its route handler and lifespan share the
    fresh manager.
    """
    from app.api.mcp.server import mcp as mcp_server

    mcp_server._session_manager = None
    mcp_app = mcp_server.streamable_http_app()
    async with mcp_app.router.lifespan_context(mcp_app):
        yield mcp_app


@pytest_asyncio.fixture
async def mcp_http_client(session, monkeypatch, mcp_streamable_app):
    """JSON-RPC client for MCP tool calls, wired to the per-test session.

    MCP tools open sessions via the module-level async_session_factory, not
    the FastAPI get_session dependency, so the factory is patched here;
    without it tool calls commit real rows outside the test transaction.
    """
    from contextlib import asynccontextmanager

    import app.api.mcp.server as mcp_module

    @asynccontextmanager
    async def _fake_ctx():
        yield session

    monkeypatch.setattr(mcp_module, "async_session_factory", lambda: _fake_ctx())
    transport = ASGITransport(app=mcp_streamable_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://localhost:8000",
        headers={"Accept": "application/json"},
    ) as c:
        yield c
```

(`pytest_asyncio`, `ASGITransport`, and `AsyncClient` are already imported at the top of conftest.py. `base_url` is localhost-form because the FastMCP singleton was built with the default empty allowlist = localhost-only Host validation; `Accept: application/json` suffices because the server runs `json_response=True`.)

- [ ] **Step 2: Migrate the existing lifespan-entering test**

In `backend/tests/test_mcp_transport_security.py`, replace the whole `test_default_mcp_rejects_foreign_host_allows_localhost` function (lines 32-50) with:

```python
@pytest.mark.asyncio
async def test_default_mcp_rejects_foreign_host_allows_localhost(mcp_streamable_app):
    """With the default (empty) allowlist, localhost is accepted and a LAN host
    is rejected with 421 — proving rebinding protection is on by default."""
    payload = {
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                   "clientInfo": {"name": "t", "version": "1"}},
    }
    transport = httpx.ASGITransport(app=mcp_streamable_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        ok = await c.post("/", json=payload, headers={
            "Accept": "application/json, text/event-stream", "Host": "localhost:8000"})
        foreign = await c.post("/", json=payload, headers={
            "Accept": "application/json, text/event-stream", "Host": "192.168.0.195:8000"})
    assert ok.status_code == 200
    assert foreign.status_code == 421
```

Also remove the now-unused import on line 7: change
`from app.api.mcp.server import build_transport_security, mcp`
to
`from app.api.mcp.server import build_transport_security`.

- [ ] **Step 3: Run the affected suites**

Run: `python -m pytest tests/test_mcp_transport_security.py tests/test_mcp.py -q`
Expected: all pass (4 + 2 tests)

- [ ] **Step 4: Commit**

```bash
git add backend/tests/conftest.py backend/tests/test_mcp_transport_security.py
git commit -m "test(mcp): shared streamable-app fixture with session-manager reset"
```

---

### Task 3: Wire `memory_add` + `memory_search` (TDD)

**Files:**
- Modify: `backend/app/api/mcp/server.py:1-16` (imports), `:107-133` (memory_add), `:136-170` (memory_search)
- Test: `backend/tests/test_mcp.py` (append)

- [ ] **Step 1: Write the failing integration tests**

Append to `backend/tests/test_mcp.py`:

```python
from sqlalchemy import select

from app.models.memory import Memory


def _tool_call(name: str, arguments: dict, request_id: int = 1) -> dict:
    return {
        "jsonrpc": "2.0", "id": request_id, "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }


async def _post_tool(client, name: str, arguments: dict, headers: dict | None = None) -> dict:
    response = await client.post("/", json=_tool_call(name, arguments), headers=headers or {})
    assert response.status_code == 200, response.text
    body = response.json()
    assert not body["result"].get("isError"), body
    return body


async def _get_memory(session, content: str) -> Memory:
    result = await session.execute(select(Memory).where(Memory.content == content))
    return result.scalar_one()


async def test_memory_add_source_from_header(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "header attribution probe"},
                     headers={"X-Darkmem-Client": "Codex!"})
    memory = await _get_memory(session, "header attribution probe")
    assert memory.source == "codex"


async def test_memory_add_source_from_claude_code_user_agent(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "ua attribution probe"},
                     headers={"User-Agent": "claude-code/2.1.172 (cli)"})
    memory = await _get_memory(session, "ua attribution probe")
    assert memory.source == "claude-code"
    assert memory.source_agent == "claude-code/2.1.172 (cli)"


async def test_memory_add_generic_ua_falls_back_to_mcp(mcp_http_client, session):
    # httpx's default python-httpx/<ver> UA must stay on the denylist: every
    # in-process test and raw-httpx harness rides on that entry.
    await _post_tool(mcp_http_client, "memory_add", {"content": "generic ua probe"})
    memory = await _get_memory(session, "generic ua probe")
    assert memory.source == "mcp"
    assert memory.source_agent.startswith("python-httpx/")


async def test_memory_add_no_ua_leaves_source_agent_null(mcp_http_client, session):
    del mcp_http_client.headers["user-agent"]
    await _post_tool(mcp_http_client, "memory_add", {"content": "no ua probe"})
    memory = await _get_memory(session, "no ua probe")
    assert memory.source == "mcp"
    assert memory.source_agent is None


async def test_memory_add_explicit_source_beats_header(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_add",
                     {"content": "explicit override probe", "source": "my-orchestrator"},
                     headers={"X-Darkmem-Client": "codex"})
    memory = await _get_memory(session, "explicit override probe")
    assert memory.source == "my-orchestrator"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_mcp.py -q`
Expected: the five new tests FAIL — `memory_add` still defaults `source` to `"mcp"` and ignores headers (assertions like `assert 'mcp' == 'codex'`). `test_mcp_tools_registered` and `test_code_search_clamps_limit` still pass.

- [ ] **Step 3: Implement the wiring**

In `backend/app/api/mcp/server.py`, extend the imports (top of file):

```python
from typing import Annotated

from mcp.server.fastmcp import Context, FastMCP
from pydantic import Field

from app.api.mcp.client_identity import resolve_client_source, resolve_source_agent
```

(The `FastMCP` import replaces the existing `from mcp.server.fastmcp import FastMCP` line; `Annotated`/`Field` are new imports.)

Replace `memory_add` (currently lines 107-133) with:

```python
@mcp.tool(
    description="Store a new memory in the knowledge system. Use this to save facts, decisions, preferences, debugging insights, infrastructure details, or any information worth remembering across sessions. The origin tool is auto-detected and recorded in 'source'."
)
async def memory_add(
    content: str,
    tags: list[str] | None = None,
    source: Annotated[str | None, Field(
        description="Origin tool. Auto-detected for known clients; pass a value only to override."
    )] = None,
    source_agent: str | None = None,
    memory_type: str | None = None,
    project: str | None = None,
    ctx: Context | None = None,
) -> str:
    """
    Args:
        content: The memory content to store. Be specific and include context.
        tags: Categorization tags using slash notation (e.g., "project/darkmem", "debug/root-cause", "infra/services").
        source: Origin tool. Auto-detected per request (X-Darkmem-Client header, then User-Agent); pass a value only to override. Falls back to "mcp".
        source_agent: Optional agent/session identifier; defaults to the caller's raw User-Agent.
        memory_type: One of fact, decision, preference, problem, architecture, reference, milestone. Aliases (e.g. "debug"→"problem") are normalized; unknown values fall back to "fact".
        project: Supersession scope (default "default"). Set this so REPLACES-based supersession can fire within the intended project; tags do NOT feed this.
    """
    async with _memory_service_context() as service:
        data = MemoryCreate(
            content=content, tags=tags or [],
            source=resolve_client_source(source, ctx),
            source_agent=resolve_source_agent(source_agent, ctx),
            memory_type=memory_type, project=project,
        )
        memory = await service.create_memory(data, api_key_id=None)
        return json.dumps(_memory_to_dict(memory))
```

In `memory_search` (currently lines 136-170), change only the `source` parameter from `source: str | None = None` to:

```python
    source: Annotated[str | None, Field(
        description='Filter by origin tool, e.g. "claude-code", "codex", "dashboard", "api", "mcp". "mcp"/"api" also cover all writes from before attribution landed (2026-06).'
    )] = None,
```

and update its Args docstring line for `source` to match:

```python
        source: Filter by origin tool (e.g., "claude-code", "codex", "dashboard", "api", "mcp"). "mcp"/"api" also cover all writes from before attribution landed (2026-06).
```

(The `ctx` parameter is annotated `Context | None` so FastMCP still injects it on server dispatch — union annotations are detected — while direct function calls and stdio get `None`. It is excluded from the tool's wire schema. The explicit `description=` on `@mcp.tool` is what clients see; the Args docstrings are server-side documentation only.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_mcp.py tests/test_client_identity.py -q`
Expected: all pass (7 + 13 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/mcp/server.py backend/tests/test_mcp.py
git commit -m "feat(mcp): resolve memory_add source from header/User-Agent"
```

---

### Task 4: `memory_batch_add` raw-dict resolution (TDD)

**Files:**
- Modify: `backend/app/api/mcp/server.py:230-248` (memory_batch_add)
- Test: `backend/tests/test_mcp.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_mcp.py`:

```python
async def test_memory_batch_add_resolves_per_entry(mcp_http_client, session):
    await _post_tool(mcp_http_client, "memory_batch_add", {"entries": [
        {"content": "batch omitted source"},
        {"content": "batch explicit api", "source": "api"},
        {"content": "batch explicit mcp", "source": "mcp"},
    ]}, headers={"X-Darkmem-Client": "codex"})
    assert (await _get_memory(session, "batch omitted source")).source == "codex"
    assert (await _get_memory(session, "batch explicit api")).source == "api"
    assert (await _get_memory(session, "batch explicit mcp")).source == "codex"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_mcp.py::test_memory_batch_add_resolves_per_entry -q`
Expected: FAIL — omitted entry persists as `"api"` (the `MemoryCreate` default), so `assert 'api' == 'codex'`.

- [ ] **Step 3: Implement batch resolution**

Replace `memory_batch_add` (currently lines 230-248) with:

```python
@mcp.tool(
    description="Create multiple memories in a single operation with parallel pipeline processing. Each entry follows the same format as memory_add; entries without 'source' get the auto-detected origin tool. Concurrency is controlled by the pipeline_concurrency setting."
)
async def memory_batch_add(entries: list[dict], ctx: Context | None = None) -> str:
    """
    Args:
        entries: List of memory objects (1-100), each with 'content' (required), and optional 'tags', 'source' (auto-detected when omitted), 'source_agent' (defaults to the caller's User-Agent), 'memory_type', 'project' (supersession scope).
    """
    # Resolve on the raw dicts: MemoryCreate stamps its "api" default during
    # validation, erasing the absent-vs-explicit distinction afterwards.
    # Non-string source/source_agent values are left untouched so validation
    # still rejects them.
    resolved = []
    for entry in entries:
        if isinstance(entry, dict):
            entry = dict(entry)
            raw_source = entry.get("source")
            if raw_source is None or isinstance(raw_source, str):
                entry["source"] = resolve_client_source(raw_source, ctx)
            raw_agent = entry.get("source_agent")
            if raw_agent is None or isinstance(raw_agent, str):
                entry["source_agent"] = resolve_source_agent(raw_agent, ctx)
        resolved.append(entry)

    # Mirror the HTTP /memories/batch cap (MemoryBatchCreate: 1-100 entries)
    # so the MCP path cannot enqueue an unbounded batch.
    validated = MemoryBatchCreate(entries=resolved)

    # Delegate to the service so creation threads every field (notably
    # ``project``, the supersession scope) and runs the phased batch pipeline
    # once. Re-implementing creation here previously dropped ``project``,
    # landing every batch-added memory in 'default'.
    async with _memory_service_context() as service:
        memories = await service.batch_create_memories(validated.entries, api_key_id=None)
        return json.dumps([_memory_to_dict(m) for m in memories])
```

- [ ] **Step 4: Run the backend suite**

Run: `python -m pytest -q`
Expected: all pass (the full suite, ~600 tests; no test asserts the old batch `"api"` default)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/mcp/server.py backend/tests/test_mcp.py
git commit -m "fix(mcp): batch entries inherit resolved source, not the api default"
```

---

### Task 5: UI creates send `source: "dashboard"`

**Files:**
- Modify: `frontend/src/features/memories/components/create-memory-dialog.tsx:55-60`

- [ ] **Step 1: Add the source field to the mutation payload**

In `create-memory-dialog.tsx`, change the `onSubmit` mutation call (lines 56-60) to:

```typescript
      await createMemory.mutateAsync({
        content: value.content,
        memory_type: value.memory_type,
        tags: value.tags.length > 0 ? value.tags : undefined,
        source: "dashboard",
      })
```

(The create request type in `frontend/src/hooks/api/use-memory-api.ts` already declares `source?: string`.)

- [ ] **Step 2: Verify**

Run: `npm run typecheck && npm test`
Expected: typecheck clean; all vitest tests pass (no existing test asserts the create payload shape, so none change).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/memories/components/create-memory-dialog.tsx
git commit -m "feat(ui): label manually created memories as dashboard source"
```

---

### Task 6: Shared `source-colors` module

**Files:**
- Create: `frontend/src/lib/source-colors.ts`
- Modify: `frontend/src/routes/_authenticated/memories.tsx:62-68` (delete local map, import shared)
- Modify: `frontend/src/routes/_authenticated/index.tsx:35-58` (delete map + fallbacks + fn, import shared)

- [ ] **Step 1: Create the shared module**

Create `frontend/src/lib/source-colors.ts`:

```typescript
export const SOURCE_COLORS: Record<string, string> = {
  "claude-code": "#58a6ff",
  codex: "#e3b341",
  kiro: "#ff7b72",
  cursor: "#39c5cf",
  windsurf: "#1f6feb",
  "gemini-cli": "#7ee787",
  cline: "#db61a2",
  opencode: "#26a641",
  mcp: "#8957e5",
  dashboard: "#f778ba",
  api: "#d2a8ff",
  "mcp-test": "#3fb950",
  "rest-test": "#ffa657",
}

// Distinct from every mapped color so an unmapped source can't render as a
// known client on the dashboard pie. Unmapped sources stay routine: the
// header/User-Agent passthrough produces arbitrary new names.
const FALLBACK_COLORS = [
  "#6e7681",
  "#bc8cff",
  "#9e6a03",
  "#0f6e6b",
  "#bf3989",
  "#57606a",
]

export function sourceColor(name: string, index: number): string {
  return (
    SOURCE_COLORS[name] ??
    FALLBACK_COLORS[index % FALLBACK_COLORS.length] ??
    "#8b949e"
  )
}
```

- [ ] **Step 2: Use it in `memories.tsx`**

Delete the local `SOURCE_COLORS` constant (lines 62-68) and add to the imports:

```typescript
import { SOURCE_COLORS } from "@/lib/source-colors"
```

The two static-fallback lookups stay as they are (`SOURCE_COLORS[row.original.source] ?? "#8b949e"` at the table cell, `SOURCE_COLORS[detailMemory.source] ?? "#c9d1d9"` in the detail panel) — they now read the shared map.

- [ ] **Step 3: Use it in `index.tsx`**

Delete the local `SOURCE_COLORS`, `FALLBACK_COLORS`, and `sourceColor` definitions (lines 35-58) and add to the imports:

```typescript
import { sourceColor } from "@/lib/source-colors"
```

(`index.tsx` references `SOURCE_COLORS` only inside the deleted `sourceColor`; every call site uses `sourceColor(name, index)`.)

- [ ] **Step 4: Verify**

Run: `npm run typecheck && npm test && npm run build`
Expected: all clean/green.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/source-colors.ts frontend/src/routes/_authenticated/memories.tsx frontend/src/routes/_authenticated/index.tsx
git commit -m "refactor(ui): consolidate SOURCE_COLORS and add per-tool colors"
```

---

### Task 7: CLAUDE.md + final gates

**Files:**
- Modify: `CLAUDE.md` ("MCP endpoint" section)

- [ ] **Step 1: Document the resolution chain**

In `CLAUDE.md`, append to the "## MCP endpoint" section (after the sentence ending "`memory_batch_add` mirrors the HTTP 1–100 batch cap."):

```markdown
Memory writes resolve `source` per call: explicit arg (the literal `mcp`
counts as unspecified) > `X-Darkmem-Client` header > User-Agent product
map > `mcp`; `memory_batch_add` resolves on the raw entry dicts before
validation, because `MemoryCreate` would stamp its `api` default and
erase the absent-vs-explicit distinction. `source_agent` defaults to the
caller's raw User-Agent.
```

- [ ] **Step 2: Run both full gates**

Run (from `backend/`): `python -m pytest -q`
Expected: all pass.
Run (from `frontend/`): `npm run typecheck && npm test && npm run build`
Expected: all clean/green.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document MCP source resolution chain"
```
