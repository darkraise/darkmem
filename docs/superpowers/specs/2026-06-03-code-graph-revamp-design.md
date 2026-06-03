# Code Graph Revamp — Design Spec

Date: 2026-06-03
Branch: `feat/code-graph-revamp`
Goal: (1) make the Code Graph page follow the darkraise-ui **theme system**
instead of its hardcoded cyberpunk styling, and (2) reach **feature parity
with GitNexus**'s graph explorer, leaning on darkmem's existing backend.

## Current state (audited)

- `routes/_authenticated/code-graph.tsx` + `features/graph/components/{code-graph-renderer,code-inspector-panel,code-analysis-panel}.tsx`: a 3-panel Sigma.js/graphology WebGL explorer (Inspector | Canvas | Analysis).
- Existing features: repo selector, symbol search, focus-depth BFS (All/1/2/3/5), per-type node/edge filters, blast-radius highlight, inspector (source/files/results tabs), analysis (symbol meta + AI summary + blast-radius + stats + filters), hover/selection focus-context.
- **Off-theme:** chrome is hardcoded (`cyan-*`/`zinc-*`/`violet-*` with opacity, `#06060a`/`#0a0a12` gradients, neon `box-shadow` glows, pervasive literal `font-mono`); node/edge colors are hardcoded hex maps **duplicated 3×** (route, renderer, legend); the renderer reads **zero CSS variables**; `globals.css` `.code-*` panels use literal `rgba(8,8,14,…)`.
- **Latent backend** (no UI today): `GET /code/symbols` paginated browser; `GET /code/files/{repo}`; wiki `?force=true`; **process** subgraph (entry_point_of + ordered step_in_process); **community** subgraph (Leiden member_of); blast-radius `risk` + per-depth buckets; heritage drill-down.

## Scope

### In scope

**A. Theme compliance (primary ask).**
**B. GitNexus parity features** that darkmem's backend already supports:
layout switcher, camera controls + play/pause, Cmd-K node search, theme-aware
legend, Processes panel + Mermaid flow modal, community cluster coloring +
navigator, symbol browser, fully-surfaced blast-radius risk/buckets.

### Out of scope (flagged, with rationale — not faked)

- **Raw Cypher query box** (GitNexus has one): darkmem's graph is Postgres
  property tables (`code_graph_nodes`/`code_edges`), not a Cypher/graph-query
  DB (GitNexus uses LadybugDB). No query engine backs it. A structured
  filter/query could be a future addition; not this revamp.
- **Full chat-over-graph AI ReAct agent** (7 graph tools, citation→graph→code
  loop): a substantial separate backend system. darkmem's `/chat` is RAG over
  *memories*, not a code-graph-grounded agent. Out of scope for the page
  revamp; can be a follow-up project.
- **In-browser embeddings / WebGPU / SSE heartbeat**: darkmem indexes
  server-side; N/A.

## A. Theming architecture

### A1. Central accent-aware color module — `features/graph/lib/code-graph-theme.ts` (new)

Single source of truth, eliminating the 3-way hardcoded duplication.

```ts
export interface GraphThemeTokens {
  background: string; foreground: string; card: string; cardForeground: string
  popover: string; popoverForeground: string; muted: string; mutedForeground: string
  border: string; primary: string; ring: string; destructive: string
  chart: string[]            // [--chart-1..--chart-5] full hsl() strings
  primaryHue: number         // parsed H from --primary "H S% L%"
  isDark: boolean
  fontMono: string
}
export function resolveGraphTokens(rootEl: HTMLElement): GraphThemeTokens
export function nodeKindColor(kind: string, t: GraphThemeTokens): string
export function edgeTypeColor(type: string, t: GraphThemeTokens): string
```

- `resolveGraphTokens` reads every token **once** via `getComputedStyle(rootEl)` (tokens are `H S% L%` triplets → wrap `hsl(var)`; `--chart-*` are full `hsl()`; parse `--primary`'s H for the hue anchor; `--font-mono`).
- `nodeKindColor`/`edgeTypeColor` are **two-tier**:
  - **Curated** (top categories) → `chart[0..4]` + `primary`: structural containers (file/module/folder/namespace)→chart-1; types (class/struct/interface/trait/enum)→chart-2; callables (function/method/constructor/impl)→chart-3; route/tool/process/entrypoint→chart-4; property/community/data→chart-5.
  - **Generated long tail** (~26 kinds, ~18 edge types > 5 slots): `hsl((primaryHue + OFFSET[kind]) % 360, S·sat, L)` where `OFFSET` is a fixed deterministic per-kind table (~30° spread) and S/L pick by `isDark` (mirrors `getChartColors` shade-400-dark/500-light). Unknown kinds → `stableHash(kind) % 360` (mirrors existing `resolveNodeColor`). Edges = endpoint-family color, darkened toward `--background` (edges read darker), preserving existing `EDGE_SIZE_MULTIPLIERS`.

### A2. Renderer (`code-graph-renderer.tsx`)
- Replace baked literals: `dimColor` fade target `{18,18,28}` → live `--background` rgb; hover pill `#12121c`/`#f5f5f7` → `--popover`/`--popover-foreground`; label color → `--foreground`; selection halo/hover ring `#6366f1` → `--primary`; blast highlight `#ef4444` → `--destructive`; Sigma `labelFont` → resolved `--font-mono`.
- `resolveGraphTokens(rootEl)` called **once per `buildGraph()`**; node/edge colors via the module.
- **Re-resolve on theme change:** consume `useTheme()` from darkraise-ui (or `MutationObserver` on the theme root) and include theme identity in the `buildGraph` graph-key so colors/dim/labels/backdrop recompute on accent/mode/surface change (today it keys only on node/edge counts).

### A3. Chrome → tokens (`code-graph.tsx`, the 3 panels, `globals.css`)
Per the audited `offThemeStyling` catalog: `bg-cyan-500/8`→`bg-primary/10`, `text-zinc-600/700`→`text-muted-foreground`, `border-cyan-900/*`→`border-border`, active states→`bg-primary/15 text-primary`, focus→`focus-visible:ring-ring`, `#06060a` gradient backdrop→`bg-background` (optionally `--sf-hue*` mesh with `--background` fallback), literal `'JetBrains Mono'`→`font-mono`, `.code-*` panel `rgba(8,8,14,…)`→`bg-card`/`text-card-foreground`. Mirror the memory toolbar idiom (`bg-card/80 backdrop-blur`, `border-border`, `ScrollArea`, `data-[pressed]:bg-primary/20`).

### A4. Legend
Centralized, theme-aware: render swatches from `nodeKindColor`/`edgeTypeColor` so renderer, page, and legend share one accent-derived source.

## B. Feature additions (data source → UI)

1. **Layout switcher** — graphology layouts: `force` (existing FA2+noverlap), `tree` (depth-banded by structural depth), `circles` (concentric by kind/depth). Toolbar `ToggleGroup`; re-layout on change. Frontend-only.
2. **Camera controls + play/pause** — zoom in/out, fit-to-view, focus-selected, clear; play/pause the FA2 worker. Toolbar buttons (themed icons).
3. **Cmd-K node search palette** — upgrade search into a `Command`/`Dialog` palette over all graph nodes (name + kind dot), keyboard nav, Enter flies camera to node (existing reveal logic). Keep inspector Results tab for code-search hits.
4. **Theme-aware legend** (A4).
5. **Processes panel + Mermaid flow modal** — derive flows from graph data already returned by `get_code_graph` (process nodes + `entry_point_of` + step-indexed `step_in_process`). Panel lists processes (entry label, step count); modal renders the ordered call-chain as a **Mermaid** flowchart with zoom/pan + "Copy Mermaid"; highlight a process's nodes in the canvas. (Reference: GitNexus ProcessesPanel/ProcessFlowModal — patterns, not code.)
6. **Community cluster coloring + navigator** — a "color by: type | community" toggle; in community mode color nodes by `member_of` cluster (stable hue per community_id); a cluster list (size, label) that highlights/zooms a community.
7. **Symbol browser** — new inspector tab backed by the latent `GET /code/symbols` (kind/q/file filters + pagination + total); rows click-to-focus the node. New `useCodeSymbols` hook.
8. **Blast-radius surfacing** — show the returned `risk` (LOW/MED/HIGH/CRITICAL) badge + per-depth buckets (`by_depth`) histogram; keep red overlay (now `--destructive`).

## File structure

| File | Change |
| --- | --- |
| `features/graph/lib/code-graph-theme.ts` | **new** — token resolver + accent-aware node/edge color maps |
| `features/graph/components/code-graph-renderer.tsx` | token-resolved colors; theme re-resolve key; layout switcher hooks; camera/play-pause API |
| `routes/_authenticated/code-graph.tsx` | chrome→tokens; toolbar gains layout switcher, camera controls, Cmd-K trigger, color-by toggle; remove duplicated color maps (use module) |
| `features/graph/components/code-inspector-panel.tsx` | chrome→tokens; new **Symbols** tab |
| `features/graph/components/code-analysis-panel.tsx` | chrome→tokens; theme-aware legend; blast-radius risk/buckets; community navigator |
| `features/graph/components/code-graph-search.tsx` | **new** — Cmd-K node search palette |
| `features/graph/components/process-panel.tsx` | **new** — processes list |
| `features/graph/components/process-flow-modal.tsx` | **new** — Mermaid flow modal |
| `features/graph/lib/code-processes.ts` | **new** — derive ordered flows from graph nodes/edges |
| `hooks/api/use-code-api.ts` | **new** `useCodeSymbols` (GET /code/symbols) |
| `src/styles/globals.css` | replace `.code-*` cyberpunk panel CSS with token-based |
| tests | renderer color-from-token unit; process-derivation unit; symbol-browser render; legend render |

## Build sequence (phases — each independently shippable + verified: tsc -b, vite build, vitest)

1. **Theme foundation** — `code-graph-theme.ts` + unit tests; renderer reads tokens + re-resolves on theme change; remove duplicated color maps. (Visible: colors track accent/mode.)
2. **Chrome → tokens** — `code-graph.tsx`, 3 panels, `globals.css`; theme-aware legend. (Visible: no cyberpunk chrome; matches app theme.)
3. **Graph UX parity** — layout switcher, camera controls + play/pause, Cmd-K search.
4. **Processes** — `code-processes.ts` + panel + Mermaid modal + highlight.
5. **Community + symbol browser + blast-radius surfacing.**

Each phase: TDD where testable (color module, process derivation, hooks), manual/visual for canvas paint (jsdom can't verify WebGL). A new dependency is needed for Mermaid (`mermaid`); confirm before adding, else render the flow with the existing graph stack.

## Non-goals recap
No raw Cypher box (no graph-query backend), no chat-over-graph agent (separate system), no in-browser embeddings. These are explicitly excluded and noted to the user.
