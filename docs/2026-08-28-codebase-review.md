# Codebase review — 2026-08-28

Reviewed at `9af67230` (master), immediately after the `darkraise-ui`
6.4.0 → 6.6.0 upgrade. Scope was the whole tree: `backend/`, `frontend/`,
`extension/`, `sdks/`, `scripts/`.

## Method, and what it does not cover

The tree is roughly 400k lines (`backend/app` 85k, `backend/tests` 126k,
`frontend/src` 178k). Nobody read all of it for this report, and a review
claiming otherwise would be worth less than one that says so.

What was actually done: every automated signal the repo supports was run to
completion and its output triaged by hand (backend pytest, frontend
typecheck/test/build, eslint across `src/`, ruff over `backend/app`, npm audit,
a credential scan), then each surviving signal was read in context to separate
real defects from tool noise. On top of that, the invariants `CLAUDE.md`
declares were checked against the code rather than taken on trust, and the
modules those invariants live in were read directly.

So: high confidence on anything a tool can see and on the declared invariants;
lower confidence on business-logic defects in code no test exercises and no
linter flags. The `demo/` fixtures, generated files (`routeTree.gen.ts`, the
SDK clients) and the docs tree were not reviewed as code.

## Health summary

| Signal | Result |
|---|---|
| Merge gate (`./scripts/gate.sh`) | GREEN |
| Backend pytest | 6355 passed, 22 skipped |
| Frontend vitest | 1308 passed, 165 files |
| Frontend typecheck (`tsc -b`) | clean |
| Frontend build | succeeds, with a chunk-size warning |
| eslint | 41 errors, 169 warnings |
| ruff (no project config; defaults) | 730, almost entirely noise |
| npm audit | 8 advisories (7 high), build tooling only |
| Hardcoded secrets in tracked source | none |
| TODO/FIXME/HACK in shipped code | 4 |

The headline is that this codebase is in good shape. The gate is green, debt
markers are almost absent, and the invariants that `CLAUDE.md` treats as
load-bearing are genuinely enforced in code rather than merely described. The
findings below are real but none of them is an emergency.

## Findings

### 1. React hook-rule errors concentrated in the graph renderers — medium

41 eslint errors, all from `react-hooks` (the React 19 compiler rules) plus two
`no-useless-assignment`:

| Rule | Count |
|---|---|
| `react-hooks/set-state-in-effect` | 22 |
| `react-hooks/refs` | 11 |
| `react-hooks/immutability` | 5 |
| `no-useless-assignment` | 2 |
| `react-hooks/rules-of-hooks` | 1 |

They cluster: `graph-3d-renderer.tsx` (6), `graph-2d-renderer.tsx` (4),
`knowledge-graph-renderer.tsx` (3). The sharpest are in
`frontend/src/features/graph/components/graph-3d-renderer.tsx:244-282`, where
the rule reports that hook arguments are being mutated after render
("Modifying component props or hook arguments is not allowed"). Under the React
compiler that is not a style preference — memoization assumes the values it
caches are not mutated behind it, so this class of violation produces stale or
torn renders that are extremely hard to reproduce.

The `rules-of-hooks` hit at `src/routes/_authenticated/chat.tsx:21` is a
`Route.useSearch()` call inside a TanStack Router `component` function, which
the rule cannot recognise as a component. That one reads as a false positive.

`src/lib/websocket.ts:205` is worth its own look: `ws.current.onclose` schedules
`setTimeout(connect, delay)`, where `connect` is the `useCallback` currently
being defined. It works today only because `connect`'s dependency list is `[qc]`
and therefore effectively stable — the registered handler captures one specific
closure and will keep calling it across every reconnect. Add a dependency to
that callback and reconnection silently starts using a stale closure.

Recommendation: fix the `immutability` and `refs` errors in the three graph
renderers; the `set-state-in-effect` instances are mostly derived-state
anti-patterns that cost an extra render rather than correctness, and can be
scheduled. Note lint is advisory per `CLAUDE.md`, so none of this is gating.

### 2. Timezone-dependent activity bucketing — medium

`backend/app/services/analytics.py:242`:

```python
since = date.today() - timedelta(days=days - 1)
...
func.date(Memory.created_at)
```

Two separate timezone dependencies in one query. `date.today()` reads the
*process* local date, and `func.date()` on a `timestamptz` truncates in the
*database session's* `TimeZone` setting. Neither is pinned anywhere — there is
no `TimeZone` in `connect_args` and no `SET TIME ZONE` in the session setup.

In production this is currently harmless: the container runs UTC. It breaks
when the app runs on the host, which is UTC+7 — `scripts/start_dev_server.sh`
does exactly that — where the window boundary shifts by seven hours and rows
land in the wrong day bucket. This is the same hazard `CLAUDE.md` already
names for the events calendar, where the fix was to pin the bucket expression
to `ix_events_day`'s immutable UTC expression. `analytics.py` is the one place
that still buckets a `timestamptz` without that discipline, and it is the only
`func.date(` call site in `backend/app`.

Recommendation: use an explicit UTC expression on both sides.

### 3. MCP bearer verification has no rate limit — low, and already known

`backend/app/api/mcp/auth.py` verifies every presented key, and
`app/services/api_keys.py:212` burns an equivalent bcrypt verify against a
fixed sentinel on a miss so that a bad `key_id` cannot be distinguished by
timing. That constant-time property is correct and deliberate. Its cost is that
**an invented key is as expensive to reject as a real one is to accept**, and
there is no login-style lockout on this door — nothing in `auth.py` mentions
rate limiting, and the verify runs on the shared thread executor that also
serves git subprocesses, code parsing and local classification.

`CLAUDE.md` already records this. It is listed here because it is unmitigated,
not because it is undiscovered. What holds it down today is that `/mcp` is
localhost-only by default and the Host allowlist sits beside the bearer check;
the exposure is real only for a deployment that widens `MCP_ALLOWED_HOSTS`.

### 4. Dependency advisories, all in build tooling — low

`npm audit` reports 8 (7 high, 1 low): `brace-expansion`, `fast-uri`,
`js-yaml`, `nanoid`, `postcss`, `undici`, `vite`, `esbuild`. Four survive
`--omit=dev` (`vite`, `postcss`, `nanoid`, `esbuild`), but every one is build
tooling — `vite`, `typescript` and `vitest` are all in `devDependencies`, and
the shipped artifact is static JS with no Node runtime behind it. Runtime
exposure to these is therefore nil; the exposure is to the build host.

Recommendation: run `npm audit fix` opportunistically. Not urgent.

### 5. Two 1.6 MB JavaScript chunks — low

`dist` totals 5.7 MB, and the build warns. Largest chunks:

| Chunk | Size |
|---|---|
| `hooks-*.js` | 1.6 MB |
| `memory-graph-*.js` | 1.6 MB |
| `index-*.js` | 644 KB |
| `usage-*.js` | 360 KB |

For a LAN-served single-operator homelab this is close to irrelevant. It is
recorded because `hooks-*.js` at 1.6 MB suggests the hooks barrel is pulling
far more into the entry path than any one route needs, which is a
code-splitting problem rather than a size problem.

### 6. Backend has no lint configuration — informational

`backend/pyproject.toml` carries no `[tool.ruff]` section and ruff is not in the
venv, so the backend has no lint gate at all. Running ruff with stock defaults
produces 730 findings, of which the overwhelming majority are noise against
this codebase's actual conventions: 353 `B008` are FastAPI `Depends()` in
argument defaults (idiomatic and correct), 95 are import ordering nobody has
opted into, 42 are quoted annotations.

Triaging the plausible ones by hand yielded almost nothing. Eight `B033`
duplicate set members in `entity_detector.py` and `entity_registry.py` are
stopword sets where a duplicate is inert. Two `PLW1510` unchecked
`subprocess.run` calls in `repo_manager.py:113` and `:553` both check
`result.returncode` explicitly on the next line — false positives. The one
`S110` try/except/pass at `ml_runtime.py:131` is awaiting cancelled eviction
tasks during shutdown, where swallowing is the correct behaviour. The single
genuine defect the whole ruff run surfaced is finding 2 above.

That is a meaningful result in itself: a stock linter run over 85k lines of
application code found one real bug. Adopting a tuned ruff config would make
the signal usable going forward, but the absence of one is clearly not hiding a
pile of defects.

### 7. `darkraise-ui` 6.6.0 does not export `surfaceColors` — informational

Recorded because the upgrade in this same change had to work around it.
`SURFACE_COLORS` grew from `["slate", ...ACCENT_COLORS]` in 6.4.0 to twelve
neutral surfaces plus the accents in 6.6.0. The library holds scales for those
neutrals in its own internal `surfaceColors` map but exports only
`accentColors`, so a swatch preview for the eleven new neutrals has no
supported source. This crashed `minimal-theme-switcher.tsx` on
`accentColors[color][500]` returning `undefined`.

Worked around with a local `NEUTRAL_SURFACE_PREVIEW` table carrying the 500
stop for each, labelled with the gap per the `CLAUDE.md` rule that a local
component written against a library gap must record which gap. Retire it when
`surfaceColors` is exported. Worth raising upstream.

## Verified, not merely documented

These were checked in code because a review that only repeats `CLAUDE.md` back
is worthless. Each held:

- **Single worker (invariant 13).** No `--workers`, no `WEB_CONCURRENCY`, no
  compose `deploy.replicas` on any launch path.
- **`--no-proxy-headers` on all three launch paths.** Present in
  `entrypoint.sh:20`, `scripts/start_dev_server.sh:24`, and
  `docker-compose.dev.yml:23`, with a comment in the compose file explaining
  why the override must repeat it.
- **The graph strip lives inside savepoint B.** `pipeline.py:686` calls
  `delete_by_memory_id` inside `session.begin_nested()` with no `try` around
  it, so a failure rolls the strip back rather than being swallowed.
- **MCP tool scopes fail closed.** `TOOL_SCOPES` names all 33 tools
  explicitly rather than deriving readers as the complement, so an
  unclassified new tool is refused rather than silently shipping as `read`.
- **Job roster count is accurate.** 18 `Job(` registrations in `main.py` plus
  the 6 dream jobs = the 24 that `CLAUDE.md` claims, with 18 live.
- **No SQL injection through the f-string SQL.** The `text(f"...")` sites in
  `repositories/` interpolate table identifiers only. `_partition_slug`
  (`embedder_registry.py:346`) reduces a fingerprint through
  `re.sub(r"[^A-Za-z0-9]+", "_", ...)`, so no operator-supplied model name can
  reach SQL as syntax. The one dynamic `WHERE` (`graph.py:255-271`) appends
  literal condition strings and binds every value, and escapes `ILIKE`
  wildcards.
- **No hardcoded credentials.** The only matches in tracked source are
  `sk-demo-…` / `zk-demo-…` placeholders in `frontend/src/demo/`.

## Not findings, though a scan will flag them

- **115 `no-restricted-imports` warnings across 71 files.** Production code
  importing from `src/demo/`. This looks like architectural erosion and is not:
  it is a named, measured residual from T1.64/T1.67, whose count is pinned by
  `src/__tests__/no-restricted-imports-count.test.ts` and whose remaining work
  (relocating shared types out of `src/demo/types.ts`) was deliberately scoped
  out with the reasoning recorded in `eslint.config.js:60-75`. The narrower
  `src/demo/data/**` rule is already an `error`.
- **49 `react-refresh/only-export-components` warnings.** Dev-ergonomics only.

## Recommended order

1. Fix the `react-hooks/immutability` and `refs` errors in the three graph
   renderers (finding 1) — the only findings with a plausible correctness cost
   in normal operation.
2. Pin the timezone in `analytics.py` (finding 2).
3. Adopt a `[tool.ruff]` config so the backend gains a lint gate (finding 6).
4. `npm audit fix` (finding 4) and the websocket closure smell (finding 1),
   whenever those files are next touched.
