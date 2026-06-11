# Memory source attribution — design

Date: 2026-06-11
Status: approved

## Problem

Every memory written through the MCP endpoint lands with `source="mcp"`.
The user wants to know which tool actually wrote it — Claude Code, Codex,
Kiro, Cursor, etc. The `memories.source` column, the UI filters, the
dashboard pie chart, and `SOURCE_COLORS` already exist; only the value is
uninformative.

## Constraints (verified 2026-06-11)

- The MCP server runs `stateless_http=True` (mcp SDK 1.26.0). The MCP
  handshake's `clientInfo.name` — which IS distinctive for nearly every
  client — is only set on the session that saw `initialize`; stateless
  mode creates a fresh `ServerSession` per request, so `clientInfo` is
  **not available during tool calls**. Going stateful would break raw
  JSON-RPC scripts (seed/eval harnesses) and add session management;
  rejected.
- The raw starlette `Request` IS reachable inside every tool call, even
  stateless: a parameter annotated `ctx: Context` is injected by FastMCP
  (excluded from the tool's wire schema), and
  `ctx.request_context.request.headers` works. Over stdio/tests the
  request is `None`.
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
`resolve_client_source(explicit_source, request) -> str` and
`default_source_agent(request) -> str | None`, consumed by `memory_add`
and `memory_batch_add` in `backend/app/api/mcp/server.py`.

Priority order:

1. **Explicit `source` argument.** The tool param default changes from
   `"mcp"` to `None`. A deliberately passed value wins, except the
   literal generic `"mcp"`, which is treated as unspecified (agents
   copying the old default must not mask detection).
2. **`X-Darkmem-Client` header.** Sanitized: lowercase, trimmed,
   restricted to `[a-z0-9._-]` (other chars dropped), capped at 100
   chars (the `memories.source` column width). Empty after sanitizing →
   skip to next tier.
3. **User-Agent product token.** Parse the first `name/version` token.
   A small known-map normalizes (`claude-code` → `claude-code`). Generic
   runtime tokens are rejected via denylist (`node`, `bun`, `mozilla`,
   `python-httpx`, `python-requests`, `python-urllib`, `aiohttp`,
   `curl`, `undici`, `axios`, `go-http-client`, `okhttp`, `java`).
   Unknown but distinctive tokens pass through slugged (same sanitizer
   as tier 2), so future clients with distinctive UAs are detected
   without code changes.
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
`memory_add`'s `"mcp"`. After this change, entries without `source` get
the resolved source, and entries without `source_agent` get the UA
default. Explicit per-entry values still win (same tier-1 rule).

### 3. Tool docstrings

`memory_add` / `memory_batch_add` `source` docs change to: "Origin tool.
Auto-detected for known clients; pass a value only to override."
`memory_search`'s `source` filter doc lists realistic values
(`claude-code`, `codex`, `dashboard`, `api`, `mcp`).

### 4. UI create path

`create-memory-dialog.tsx` sends `source: "dashboard"` so manual UI
creates stop masquerading as REST `"api"` writes. (A `dashboard` color
already exists in `SOURCE_COLORS`.) REST default stays `"api"`.

### 5. Frontend colors

The two byte-identical `SOURCE_COLORS` maps
(`routes/_authenticated/memories.tsx:62`, `routes/_authenticated/index.tsx:35`)
move to one shared module (`src/lib/source-colors.ts`) exporting the map
plus the existing `sourceColor()` rotation fallback, extended with
entries for `mcp`, `codex`, `kiro`, `cursor`, `windsurf`, `gemini-cli`,
`cline`, `opencode`. Today the most common real value (`mcp`) has no
color and renders gray.

### 6. CLAUDE.md

One line in the "MCP endpoint" section: source is resolved per call as
explicit arg > `X-Darkmem-Client` header > User-Agent map > `"mcp"`,
and `memory_batch_add` entries inherit the same resolution.

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

- `ctx.request_context.request` is `None` outside HTTP (stdio, direct
  test invocation): resolver returns the explicit arg or `"mcp"`.
- Header/UA parsing wrapped so no exception propagates; fallback `"mcp"`.
- Sanitizer guarantees values fit the column widths (100 / 255).

## Testing

- Unit tests for `resolve_client_source` / `default_source_agent`: each
  tier, tier precedence, `"mcp"`-as-unspecified, sanitization, generic-UA
  denylist, unknown-distinctive-UA passthrough, length caps, `None`
  request.
- `test_mcp.py` integration: tool call through the stateless streamable
  app with (a) an `X-Darkmem-Client` header, (b) a `claude-code/x.y`
  User-Agent, (c) neither — asserting the persisted `source` and the
  batch-entry default fix.
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
