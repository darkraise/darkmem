# MCP: migrate to SDK v2, then require bearer auth

**Status:** proposed, 2026-08-26. Three owner rulings recorded: auth required
by default with no opt-out flag (§5), per-tool scope gating (§5), and both parts
in a single deploy (§8). Two open questions remain, both answerable only against
the real server (§9).
**Supersedes nothing. Amends:** doc 12 (API and MCP contract), doc 18 §5
(records the second activation), CLAUDE.md's MCP section, and
`ProxiedMcpGuardMiddleware`'s docstring premise (§4).

Two changes, deliberately sequenced. Migrating the MCP server to protocol
revision `2026-07-28` comes first because it changes how the authentication
should be built; landing auth on the current SDK would mean hand-rolling
machinery the new SDK supplies and then discarding it.

## 1. Why now

`/mcp` is unauthenticated. That is a designed position — the local-network
trust model of doc 18 §2 — and its only network defence is the Host allowlist.
Doc 18 §5 designed the bearer-required option and left it unshipped, gated on
"the first exposed deployment, or any remote client that must reach darkmem
across an untrusted network."

The owner has asked for it now, at required-by-default, and separately asked
that the server adopt the `2026-07-28` protocol revision. The two requests
interact, which is the whole reason this document exists.

## 2. What the revision changes

Protocol `2026-07-28` is an architectural change, not a point release:

- **Stateless.** The `initialize`/`initialized` handshake and `Mcp-Session-Id`
  are retired. Each request carries its protocol version, client identity and
  capabilities in `_meta`.
- **Required routing headers.** `MCP-Protocol-Version` and `Mcp-Method` are
  REQUIRED on every POST; `Mcp-Name` is REQUIRED only for `tools/call`,
  `resources/read` and `prompts/get`, carrying `params.name` or `params.uri`.
  They exist so intermediaries can route and authorize without parsing bodies.
- **MRTR** replaces server-initiated streams for elicitation, sampling, roots.
- **Deprecated:** Roots, Sampling, Logging (twelve-month window) and the legacy
  HTTP+SSE transport.
- **Authorization:** RFC 9207 `iss` validation and CIMD replacing Dynamic
  Client Registration. **Neither applies here** — both are OAuth-flow concerns,
  and doc 18 §5 rejected OAuth for this audience in favour of bearer keys.
- **Caching:** `ttlMs` / `cacheScope` on list responses.

### 2.1 The header rule, and why it does not simplify authorization

`Mcp-Name` carries the tool name, which looks like it would let a middleware
authorize per tool without reading the body. It does not, and the specification
says why:

> The body remains the source of truth; bindings that mirror metadata define
> how mismatches are rejected.

A middleware authorizing on `Mcp-Name` while the server executes the body would
be exploitable by a non-conforming client sending `Mcp-Name: memory_search` with
a body calling `memory_add`. The specification anticipates exactly this — "a
load balancer routing on the header value while the MCP server executes based
on the body value" — and requires servers to reject mismatches with HTTP `400`
and JSON-RPC `-32020` (`HeaderMismatch`).

**Therefore: scope is enforced from the body, never from the header.** The
header stays routing metadata for intermediaries and is never load-bearing for
an authorization decision. This is a correction to the first design sketched in
conversation, which proposed header-based scoping.

## 3. Spike findings (2026-08-26)

Measured against `mcp==2.1.1` in a throwaway venv, and against throwaway
servers over real HTTP. Recorded because the estimate rests on them.

**The tree's entire SDK surface is two import lines:**

```
from mcp.server.fastmcp import Context, FastMCP
from mcp.server.transport_security import TransportSecuritySettings
```

| Symbol | v2 status |
|---|---|
| `TransportSecuritySettings` | **Unchanged** — same module, same three fields |
| `FastMCP` | Renamed `MCPServer` (`mcp.server.mcpserver`) |
| `Context` | Same module as `MCPServer`; `request_context` intact |
| `@mcp.tool()` | Same signature |
| `streamable_http_app()` | Present |

**Dual-era support is real.** A v2 server answered a legacy `2025-11-25`
`initialize` handshake (negotiating `2025-11-25`) *and* executed a modern
stateless `tools/call`. Existing clients therefore do not break on migration —
the single largest risk, removed.

**The mismatch guard is in the SDK, not ours to build.** A request with
`Mcp-Name: something_else` against a body calling `ping` was rejected with
`-32020` / HTTP 400 and the message *"mcp-name header does not match the
request body's 'name' parameter"*.

**The identity ladder survives.** A v2 server reproducing
`_request_from_ctx` verbatim returned `client=codex ua=probe/9.9 auth=yes` over
real HTTP, so `ctx.request_context.request` still yields a live Starlette
request. `resolve_client_source` keeps working unchanged, and `Authorization`
is readable from the same place.

**The SDK supplies the auth primitives:**

```python
class TokenVerifier(Protocol):
    async def verify_token(self, token: str) -> AccessToken | None
```

`AccessToken` carries `client_id`, `scopes: list[str]`, `expires_at`,
`subject` — a near 1:1 map onto an `api_keys` row. Alongside it:
`RequireAuthMiddleware(app, required_scopes=[...])` and `get_access_token()`, a
context accessor readable from inside a tool.

**Limit of the spike:** every probe ran against a toy server holding one tool.
The real server has 33 tools, the Host-allowlist settings, the proxied-MCP
guard, and `set_pipeline` / `refresh_mcp_instructions` wiring, none of which
were exercised.

## 4. Part one — the migration

**Change.** Bump `mcp` to 2.x in `backend/requirements.lock` (regenerated with
`uv pip compile --universal`, never by hand). Swap the two imports. Rename the
server object `FastMCP(...)` → `MCPServer(...)`. Everything else — 33 tool
bodies, the Host allowlist, the proxied guard, the mount at `/mcp` — is
expected to stand unchanged.

**Conformance work the revision requires**, each verified against the real
server rather than assumed:

- GET or DELETE on `/mcp` answers `405`.
- `Mcp-Session-Id` and `Last-Event-ID` are ignored, never minted or echoed.
- An `Origin` that is **present and invalid** answers `403`. An absent
  `Origin` is not an error — most MCP agents are not browsers and send none,
  so rejecting its absence would break every non-browser client. Note this
  sits *beside* the Host
  allowlist's `421`, which is unchanged: `421` answers "is this a Host I
  serve", `403` answers "is this Origin allowed". Conflating them would break
  invariant 20's standing advice ("extend the allowlist, never disable it").

**`ProxiedMcpGuardMiddleware` stays, and its comment must change.** T4.17
refuses `/mcp` arriving through the proxy, and its docstring justifies itself on
`/mcp` being "unauthenticated by design" with the bearer option "designed but
unshipped". Auth landing makes that rationale stale while the guard itself is
still wanted — it answers "did this arrive from outside", which a valid key does
not answer. Keep the guard, rewrite the premise. Leaving a stale justification
in place invites a later reader to delete the guard as obsolete.

**Explicitly out of scope:** MRTR, `subscriptions/listen`, and `ttlMs` /
`cacheScope`. darkmem's tools are request/response and use no elicitation,
sampling or roots, so adopting MRTR would be building an unused path — the
scaffolding-as-substrate move invariant 23 forbids. The deprecations cost us
nothing for the same reason.

## 5. Part two — authentication

**Posture: required, always, with no opt-out flag** (owner's choice,
2026-08-26). Same discipline as `schema_guard`: it fails closed and offers no
override, because a switch that can be turned off is a switch that can be left
off. The escape hatch is minting a key, never disabling auth.

**The Host allowlist stays on**, exactly as doc 18 §5 requires — defence in
depth, and the `421` rule is untouched.

**Both protocol eras are authenticated.** §3 establishes that a v2 server still
answers a legacy `initialize` handshake; that path is not an auth exemption. A
legacy client presents the same bearer or is refused, or the migration would
hand every unmigrated client a way around the requirement.

**Verification.** One `TokenVerifier` implementation over the existing
`api_keys` table, reusing `authenticate()` so REST and MCP cannot drift into
two credential readers:

| `AccessToken` field | Source |
|---|---|
| `client_id` | `api_keys.key_id` (the public 32-char identifier inside `dmk_<key_id>_<secret>`, not the row's UUID) |
| `scopes` | `read_scopes(api_keys.scopes)` |
| `expires_at` | `api_keys.expires_at` |
| `subject` | `api_keys.name` |

`api_keys` carries **both** `id` (UUID primary key) and `key_id` (the public
identifier). They are not interchangeable: `client_id` above is `key_id`, while
`events.api_key_id` stores the row `id`. Conflating them writes an unjoinable
value into the journal.

**Scope per tool.** `capture` for the eight writers — `memory_add`,
`memory_batch_add`, `memory_update`, `memory_delete`, `document_put`,
`document_delete`, `checkpoint_save`, `research_run` — and `read` for the other
twenty-five. A tool reads its principal via `get_access_token()`, which is
body-side and therefore immune to the header question of §2.1.

`ratify` remains impossible: it is in `FORBIDDEN_SCOPES`, `parse_scopes`
refuses it at issue time, `has_scope` refuses to even test for it, and an
import-time assertion fails the process if it ever enters the vocabulary. This
migration adds no path around any of that.

**Attribution.** The four hardcoded `api_key_id=None` call sites take the real
key id, and `events.actor` becomes the key name. The `source` ladder (explicit
arg → `X-Darkmem-Client` → User-Agent → `mcp`) is untouched: `source` says
*which client tool*, `actor` says *which credential*. Conflating them would
lose the client attribution the header ladder exists to produce.

## 6. Invariants this must not disturb

- **Invariant 15.** No dream-job family member becomes reachable from a tool.
  The existing source scan stands.
- **Invariant 20.** A LAN `421` is still fixed by extending the allowlist,
  never by disabling the check — including once bearer auth is required.
- **Invariant 23.** No unused path ships. MRTR and the caching fields are left
  out on exactly this ground.
- **Doc 18 §5.** `ratify` is not a scope and does not become one.
- **The `research_run` exemption.** Its sanctioned invariant-15 crossing is
  scoped to nodes inside the tool's own body; adding a scope check must not
  widen that exemption.

## 7. Testing

Migration:

- Every tool still registers. **The existing `test_mcp_tools_registered` is not
  sufficient for this and must be replaced**: it hand-lists ten names and
  asserts `len(tool_names) >= 10` against a roster of 33, so a rename losing
  twenty tools passes it. Derive the expected roster from the module's own AST,
  as `test_code_deriver.py` already does for the job roster, so a tool lost in
  the migration fails the build.
- A legacy `initialize` client and a modern stateless call both succeed against
  the real server.
- `Mcp-Name`/body mismatch is rejected `-32020`.
- GET and DELETE answer `405`; an invalid `Origin` answers `403`; a foreign
  `Host` still answers `421`.
- The identity ladder resolves `X-Darkmem-Client`, User-Agent and the `mcp`
  fallback unchanged.

Auth:

- No key → refused. Invalid key → refused. Expired key → refused. **Revoked
  key → refused** (`api_keys.revoked_at`, which `authenticate()` already
  checks — omitting it would leave the revocation surface unproven on this
  door).
- Valid key lacking the scope → refused; holding it → succeeds.
- A successful keyed call stamps `events.api_key_id` and `events.actor`.
- The Host allowlist still refuses a foreign Host *with* a valid key — both
  guards, not either.
- An AST scan failing the build if any `@mcp.tool` lacks a scope declaration.
  Without it the failure mode is a new tool silently reachable unscoped.

## 8. Rollout, and the lockout it can cause

Order is load-bearing. Deploying before a key exists breaks every agent talking
to `/mcp`.

**Both parts land in a single deploy** (owner ruling, 2026-08-26). The reason
is the one §9 named: two deploys leave a window in which the server is migrated
and still unauthenticated, and that window is the exact condition this work
exists to remove. The accepted cost is that a failure is harder to attribute
between the migration and the auth, which the gate's separate test groups
mitigate but do not erase.

Rollback is therefore one step, not two: redeploy the previous image tag. That
is only true while the migration carries no schema change — it does not, and if
one appears the rollback story must be rewritten before this ships.

1. Mint a key in the UI with both scopes.
2. Update every MCP client config to send `Authorization: Bearer dmk_…`.
3. Gate, build, deploy.
4. Verify a keyed call succeeds and an unkeyed one is refused.

Minting requires an authenticated cookie session, so recovery from a lockout is
the admin password — not a flag, because there is no flag. That is the intended
cost of the chosen posture and is stated here so it is not discovered later.

## 9. Open questions

- Does the real server's `refresh_mcp_instructions` / `set_pipeline` wiring
  survive the rename? Untested.
- Do the deployed MCP clients negotiate a revision the v2 server serves? Dual-era
  support was proven for `2025-11-25`; the clients' actual negotiated version
  has not been observed.

The one-deploy question is settled; see §8.
