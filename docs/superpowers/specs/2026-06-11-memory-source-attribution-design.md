# Memory source attribution — design

Date: 2026-06-11
Status: approved (revised after adversarial review, same day)

## Problem

Every memory written through the MCP endpoint lands with `source="mcp"`.
The user wants to know which tool actually wrote it — Claude Code, Codex,
Kiro, Cursor, etc. The `memories.source` column, the UI filters, the
dashboard pie chart, and `SOURCE_COLORS` already exist; only the value is
uninformative.

## Constraints (verified 2026-06-11)

- The MCP server runs `stateless_http=True` (mcp SDK; dev has 1.26.0,
  requirements.lock pins 1.27.2 — the relevant internals are verified
  identical on both). The MCP handshake's `clientInfo.name` — which IS
  distinctive for nearly every client — is only set on the session that
  saw `initialize`; stateless mode creates a fresh `ServerSession` per
  request, so `clientInfo` is **not available during tool calls**. Going
  stateful would break raw JSON-RPC scripts (seed/eval harnesses) and
  add session management; rejected.
- The raw starlette `Request` IS reachable inside every tool call, even
  stateless: a parameter annotated `ctx: Context | None = None` is
  injected by FastMCP when dispatched through the server (the union
  annotation still triggers injection; the default keeps direct
  function calls working) and is excluded from the tool's wire schema.
  Caution: `ctx.request_context` does NOT return `None` outside a
  request — it raises `ValueError` (e.g. for in-process
  `mcp.call_tool`). Only stdio yields `request=None`. The unwrap must
  therefore live inside the resolver's own try/except, not in the tool
  body.
- Client identity signals over streamable HTTP:

  | Client | clientInfo.name | User-Agent on tool calls | Custom headers |
  |---|---|---|---|
  | Claude Code | `claude-code` | `claude-code/<ver> (cli)` — distinctive | yes |
  | Codex CLI | `codex-mcp-client` | absent | yes (`config.toml`) |
  | Kiro | unknown (CLI: `Kiro CLI`) | unknown | yes |
  | Cursor | `cursor-vscode` | generic `node` | yes |
  | Windsurf | `windsurf-client` | unknown | yes |
  | Gemini CLI | `gemini-cli-mcp-client` | generic `node` | yes |
  | Cline | `Cline` | generic `node` | yes |
  | opencode | `opencode` | generic `Bun/<ver>` | yes |

  Only Claude Code sends a distinctive User-Agent. Every client supports
  custom headers, so an `X-Darkmem-Client` header is the reliable
  cross-client channel.

## Design

### 1. Source resolution (backend)

New helper module `backend/app/api/mcp/client_identity.py` exposing
`resolve_client_source(explicit_source, ctx) -> str` and
`default_source_agent(ctx) -> str | None`, consumed by `memory_add`
and `memory_batch_add` in `backend/app/api/mcp/server.py`. Both helpers
take the (possibly `None`) FastMCP `Context` and unwrap
`ctx.request_context.request` inside their own guard, because that
attribute access can raise `ValueError` outside a request.

Priority order:

1. **Explicit `source` argument.** The tool param default changes from
   `"mcp"` to `None`. A deliberately passed value wins, except the
   literal generic `"mcp"`, which is treated as unspecified (agents
   copying the old default must not mask detection). Explicit values
   are lowercased (so UI color/filter lookups match the sanitized
   tier-2/3 output) and truncated to 100 chars (the `memories.source`
   column width) before constructing `MemoryCreate` — truncate, not
   reject, because attribution must never fail a write. Likewise an
   explicit `source_agent` is truncated to 255 (not lowercased — it is
   a free-form forensic field).
2. **`X-Darkmem-Client` header.** Sanitized: lowercase, trimmed,
   restricted to `[a-z0-9._-]` (other chars dropped), capped at 100
   chars. Empty after sanitizing → skip to next tier.
3. **User-Agent product token.** Parse the first `name/version` token.
   A small known-map normalizes (`claude-code` → `claude-code`). Generic
   runtime tokens are rejected via denylist (`node`, `bun`, `mozilla`,
   `python-httpx`, `python-requests`, `python-urllib`, `aiohttp`,
   `curl`, `undici`, `axios`, `go-http-client`, `okhttp`, `java`).
   Unknown but distinctive tokens pass through slugged (same sanitizer
   as tier 2), so future clients with distinctive UAs are detected
   without code changes. An empty-string User-Agent is treated the same
   as absent.
4. **Fallback `"mcp"`.** Unchanged behavior for unidentifiable callers.

Resolution never raises: any exception (no request context, malformed
header, anything) falls back to `"mcp"`. Attribution must never fail a
write.

`source_agent`: when the caller did not supply one, store the raw
User-Agent string capped at 255 chars (column width); `None` when no UA.
The column is currently write-only and almost always empty; this makes
it a forensic detail channel without changing its contract.

### 2. `memory_batch_add` default fix

Entries without an explicit `source` currently fall through
`MemoryCreate`'s default and land as `"api"` — inconsistent with
`memory_add`'s `"mcp"`. Mechanism: resolution happens **on the raw
entry dicts before `MemoryBatchCreate` validation** (absence test:
`"source" not in entry` / value `None`), because Pydantic stamps the
`"api"` default during validation and erases the absent-vs-explicit
distinction afterward. The tier-1 rule applies unchanged per entry:
literal `"mcp"` is treated as unspecified; a deliberate `"api"` (or any
other value) wins. Entries without `source_agent` get the UA default.

### 3. Tool descriptions (wire-visible)

The Args docstrings are NOT visible to clients: `Tool.from_function`
uses `description or fn.__doc__`, and every darkmem tool passes an
explicit `description=`, so docstring edits never reach the wire, and
parameter schemas carry bare titles. The guidance therefore goes where
clients actually see it:

- `memory_add`: `source` becomes
  `Annotated[str | None, Field(description="Origin tool. Auto-detected
  for known clients; pass a value only to override.")] = None`.
- `memory_search`: the `source` param gets a
  `Field(description="Filter by origin, e.g. claude-code, codex,
  dashboard, api, mcp. mcp/api also cover all writes from before
  attribution landed (2026-06).")`.
- `memory_batch_add`: has no `source` parameter (entries are raw
  dicts), so the auto-detection note is appended to its decorator
  `description=`.

Docstrings are updated too, but only as server-side documentation.

### 4. UI create path

`create-memory-dialog.tsx` sends `source: "dashboard"` so manual UI
creates stop masquerading as REST `"api"` writes. (A `dashboard` color
already exists in `SOURCE_COLORS`.) REST default stays `"api"`.

### 5. Frontend colors

The two byte-identical `SOURCE_COLORS` maps
(`routes/_authenticated/memories.tsx:62`, `routes/_authenticated/index.tsx:35`)
move to one shared module (`src/lib/source-colors.ts`), extended with
entries for `mcp`, `codex`, `kiro`, `cursor`, `windsurf`, `gemini-cli`,
`cline`, `opencode`.

Current fallback behavior, for the record: unmapped sources render gray
only on the memories page (`?? "#8b949e"` table badge at
memories.tsx:394, `?? "#c9d1d9"` detail view at :796); the dashboard pie
uses `sourceColor()` rotation (index.tsx:43-55), whose
`FALLBACK_COLORS[0]` is `#58a6ff` — identical to claude-code's blue —
and since the overview endpoint sorts sources by count descending,
`mcp` today renders exactly that blue, not gray. The shared module must
serve all three call shapes: `sourceColor(name, index)` rotation for
the pie and the two static-fallback lookups (keeping the existing gray
values). Because tier-2/tier-3 passthrough makes unmapped source values
routine, `FALLBACK_COLORS` is adjusted so no rotation color is
identical to a mapped client color.

### 6. CLAUDE.md

One line in the "MCP endpoint" section: source is resolved per call as
explicit arg > `X-Darkmem-Client` header > User-Agent map > `"mcp"`,
and `memory_batch_add` entries inherit the same resolution.

## Mixed history

Pre-change rows keep `"mcp"` / `"api"` and cannot be backfilled — the
generic defaults recorded no client identity (`source_agent` is almost
always empty), so no migration is written. Note that `"mcp"` and
`"api"` are not purely historical markers either: `"mcp"` remains the
live tier-4 fallback and `"api"` the REST default, so both are
permanently ambiguous buckets (all pre-change writes plus post-change
unidentifiable/REST callers). The `memory_search` filter description
(section 3) says so.

## Per-tool header configuration (reference)

Tools without a distinctive User-Agent need one config line:

- **Codex** (`~/.codex/config.toml`):
  `[mcp_servers.darkmem]` → `http_headers = { "X-Darkmem-Client" = "codex" }`
- **Kiro** (`.kiro/settings/mcp.json`):
  `"headers": { "X-Darkmem-Client": "kiro" }`
- **Cursor** (`.cursor/mcp.json`):
  `"headers": { "X-Darkmem-Client": "cursor" }`
- **Gemini CLI** (`~/.gemini/settings.json`, under `httpUrl` server):
  `"headers": { "X-Darkmem-Client": "gemini-cli" }`
- **Cline / Windsurf / opencode**: same `headers` map in their MCP
  config (`cline_mcp_settings.json` / `mcp_config.json` / `opencode.json`).
- **Claude Code**: nothing — auto-detected from
  `User-Agent: claude-code/<ver>`.

## Error handling

- The resolver helpers take `ctx` and unwrap the request inside their
  own try/except: over stdio the request is `None`; outside any request
  (in-process `call_tool`, direct invocation) the unwrap raises and is
  swallowed. Either way: explicit arg or `"mcp"`.
- Header/UA parsing wrapped so no exception propagates; fallback `"mcp"`.
- All persisted values fit the column widths (100 / 255): sanitizer
  caps for tiers 2-3, truncate-only caps for tier-1 explicit values and
  raw-UA `source_agent`.

## Testing

- Unit tests for `resolve_client_source` / `default_source_agent`: each
  tier, tier precedence, `"mcp"`-as-unspecified, explicit-`"api"`
  survives while omitted gets resolved (batch semantics), sanitization,
  generic-UA denylist, unknown-distinctive-UA passthrough, length caps
  including oversized tier-1 explicit values, `ctx=None`, ctx whose
  `request_context` raises.
- `test_mcp.py` integration through the stateless streamable app:
  (a) an `X-Darkmem-Client` header, (b) a `claude-code/x.y` User-Agent,
  (c) the client's default `python-httpx/<ver>` UA (assert source
  `"mcp"` AND `source_agent == "python-httpx/<ver>"` — the denylist
  entry is load-bearing for in-process tests and raw-httpx callers),
  (d) a true no-UA request (`del client.headers["user-agent"]`; httpx
  sends an empty header if merely set to `""`) asserting
  `source_agent is None`, plus the batch-entry default fix.
  Plumbing constraints (verified): FastMCP caches one
  `StreamableHTTPSessionManager` whose `run()` is once-per-instance, and
  `test_mcp_transport_security.py` already enters it once per pytest
  process — a shared fixture must reset `mcp._session_manager = None`,
  build a fresh app via `streamable_http_app()` AFTER the reset, and
  enter `app.router.lifespan_context(app)` per test;
  `test_mcp_transport_security.py` migrates to the same fixture.
  Requests must send a localhost-form `Host` (the singleton allows
  localhost only under test settings); `Accept: application/json`
  suffices given `json_response=True`. Tests monkeypatch
  `mcp_module.async_session_factory` to the conftest session (existing
  `test_mcp.py` pattern) — the MCP path does not use the FastAPI
  `get_session` dependency override, and without the patch it commits
  real rows outside the per-test transaction. `MemoryService` tolerates
  `pipeline=None`, so no pipeline stub is needed.
- Frontend: typecheck + existing tests after the SOURCE_COLORS
  consolidation; create-dialog test asserts `source: "dashboard"` in the
  mutation payload if a test exists for the payload shape.

## Out of scope

- Switching the MCP endpoint to stateful sessions (clientInfo-based
  zero-config detection for all clients) — revisit only if header
  config proves annoying.
- Header-based attribution on the REST API.
- The pre-existing quirk that the memories-page source dropdown builds
  its options from the visible page only.
- A standalone end-user docs file (declined; the reference table above
  serves that purpose).
- Backfilling historical rows (impossible — see Mixed history).
