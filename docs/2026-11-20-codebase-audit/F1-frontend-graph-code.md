# F1 — frontend graph and code features

Reviewer findings for the 2026-11-20 audit, as returned. Summary first where the reviewer gave one, then one entry per finding. Index and verification status: `docs/2026-11-20-codebase-audit.md`.

**Counts:** 2 high, 6 medium, 13 low, plus 2 design critiques.

**Top three:**
1. **High:** the Edit Repository dialog cannot save any repository cloned from a URL. It requires a read-only `path`, and cloned repositories store it as NULL. A plan dated 2026-08-24 flagged this and it is still open (`real-repositories-view.tsx:227,243-247`, `schemas.ts:7`).
2. **High:** the memory graph builds its 3D data on every change even in 2D view, with an O(n²) `nodes.find` and a link for every pair of nodes in a cluster (`real-memory-graph-page.tsx:181-221`, `graph-utils.ts:147-206`).
3. **Medium:** Mermaid export breaks past 26 steps (the backend allows up to 300) and does no escaping, while a correct generator sits in dead code (`demo/explore.ts:307-324` versus `graph/lib/code-processes.ts:144-179`).

**Duplication:** the two graph features do not duplicate each other. The waste is about 3,350 lines of unimported components inside `features/graph`, which are also the only users of `graphology-layout-noverlap`.

---

# F1 — Frontend graph and code features

## Summary
- **The two "graph features" do not duplicate each other.** `memory-graph` holds only two page shells:
  - the demo SVG explorer, which uses its own layout from `demo/explore.ts`;
  - the real page, which composes `features/graph`.
- **The real duplication and dead weight is inside `features/graph`:** about 3,350 lines of components with no production importer. These are an older sigma code renderer, a knowledge-graph renderer, and the analysis, inspector, search and process panels. They are also the only users of `graphology-layout-noverlap`, and of most of `code-graph-theme.ts`.

## Findings

### 1. The Edit Repository dialog cannot save URL-cloned repositories (high, bug, confirmed)
- **Where:** `real-repositories-view.tsx:227,243-247,317-331`, `schemas.ts:7`, backend `repo_manager.py:165-178`.
- **Cause:** `path` defaults to `local_path ?? ""`, and the schema requires `min(1)`. The field is read-only. Cloned repositories never get a `local_path`.
- **Effect:** Save shows "Path required" and sends nothing, so the operator can never change the account, token, branch or polling settings.
- **History:** recorded in `docs/superpowers/plans/2026-08-24-r4-frontend-highs.md:2624-2630` and still open.
- **Fix:** drop `path` from `editRepoSchema` and show the path as display-only. Add a Save test using a fixture with `local_path: null`.

### 2. The 3D graph data is rebuilt in 2D view, in O(n²) (high, performance)
- **Where:** `real-memory-graph-page.tsx:181-221`, `graph-utils.ts:147-206`.
- **Cause:** the memo is not gated on `viewMode`. Inside it:
  - `nodes.find` is called per clustered member, which is O(n²);
  - a hidden link is generated for every pair inside each cluster and for every pair of clusters.
- **Effect:** with "All nodes" enabled (up to 50,000), every filter change in 2D stalls the tab.
- **Fix:**
  - Gate the memo on 3D.
  - Look nodes up in a `Map`.
  - Replace the hidden links with cluster-anchor forces. The unused `clusterAnchors` in `graph-scale.ts:113` can provide the anchors.

### 3. Mermaid export breaks past 26 steps (medium, bug)
- **Where:** `demo/explore.ts:307-324`, used by `real-code-graph-view.tsx:650`.
- **Cause:** node ids come from `String.fromCharCode(65+i)`, so step 27 becomes `[` and so on. Names are not escaped. A one-step process emits an empty chart.
- **Context:** the backend step cap is `max(20, min(symbols//10, 300))` (`process_tracer.py:97`).
- **Fix:** port `escapeMermaid` and the `n${i}` ids from the dead `code-processes.ts:144-179`.

### 4. Blast Radius silently fails (medium, bug)
- **Where:** `real-code-graph-view.tsx:242-248,503-510`, backend `code_query.py:617-645`.
- **Cause:** on the folded (file-level) graph, a file path is sent as `symbol_id` and the backend returns 404. There is no `onError` handler and no global `MutationCache` handler.
- **Effect:** on large repositories the button does nothing at all.
- **Adjacent, backend track:** the backend drops `_owner`, so methods with the same name in one file resolve arbitrarily.

### 5. Code Graph and Wiki show "No repositories indexed yet" while loading or after an error (medium, ui-ux)
- **Where:** `real-code-graph-view.tsx:86-90,200-214`, `real-wiki-view.tsx:73-95`.
- **Cause:** the views never check `isLoading` or `isError`.
- **Effect:** this is the failed-versus-empty conflation the codebase fixed elsewhere (`RealRepositoriesView:533`).

### 6. The code canvas rebuilds Sigma and restarts the layout on every keystroke (medium, performance)
- **Where:** `real-code-graph-view.tsx:156-169,443`, `code-glow-canvas.tsx:268-512`.
- **Cause:** the search filter is not debounced. `shown` replaces `graph`, so each keystroke kills Sigma, creates a new WebGL context and a new FA2 worker, and re-fits the core.
- **Fix:** dim through `visibleIds` instead of swapping `graph`.

### 7. Per-frame string-keyed density grid on the memory canvas (medium, performance)
- **Where:** `node-glow-program.ts:72-101,157-170`.
- **Cause:** `localSpacing` builds two `Map`s with template-string keys over every core node in `beforeRender`.
- **Effect:**
  - Below 2,000 nodes, ambient motion renders at 30 fps, so this runs continuously even when idle.
  - Above 2,000 nodes, it runs on every pan or zoom frame.
- **Fix:** cache by cell size and layout version, and use numeric keys.

### 8. About 3,350 lines of dead graph components (medium, dead-code, confirmed by search, routes and dynamic imports included)

| File | Lines | Importers |
|---|---|---|
| `code-graph-renderer.tsx` | 1,225 | none |
| `code-inspector-panel.tsx` | 548 | tests only |
| `code-analysis-panel.tsx` | 496 | none |
| `knowledge-graph-renderer.tsx` | 443 | none |
| `code-processes.ts` | 179 | dead files and tests |
| `process-flow-modal.tsx` | 146 | none |
| `node-circle-bordered-program.ts` | 134 | the dead KG renderer and a test |
| `code-graph-search.tsx` | 101 | tests only |
| `process-panel.tsx` | 73 | dead panel and a test |

- **Also removable:**
  - `graphology-layout-noverlap` (`package.json:37`);
  - `globals.css:240-257`;
  - about 600 lines of tests that cover only these files.
- **Order:** remove after finding 3 is fixed, because the correct Mermaid generator lives in `code-processes.ts`.

### 9. Dead or test-only exports in live modules (low, about 450 lines)
- `graph-geometry.ts:4-143`: hull helpers and a vis-network type.
- `lightenHex`: no callers at all.
- `clusterAnchors` and `seedAroundAnchor`: tests only.
- The `code-graph-theme.ts` code-colour functions and `useCodeGraphTheme` (`:146-279,:319-375`): tests and dead code only.
- `groupMemories` and `placeIslands`: tests only.
- `zoomLevel`: no callers. `visibleLabelIds`: tests only.
- The `setGraphReady` state, which is written but never read (`real-memory-graph-page.tsx:60`).
- An inner `GraphSkeleton` that can never render (`:295`).
- `stableHash`, defined twice.

### 10. Wiki and edit-repository mutation failures are not reported (low)
- **Where:** `real-wiki-view.tsx:255`, `real-repositories-view.tsx:280`.
- **Cause:** `mutateAsync` rejects inside a `handleSubmit` that nothing awaits.
- **Effect:** an unhandled rejection; the wiki shows no toast.

### 11. Copy Mermaid misreports and fails in production (low)
- **Where:** `real-code-graph-view.tsx:250-258`.
- **Cause:**
  - A rejected clipboard write still sets "Copied".
  - On the plain-HTTP production deploy, `navigator.clipboard` is undefined, so the button does nothing.
- **Fix:** use the darkraise-ui `clipboard` component, which three other screens already use.

### 12. Clicking an entity in 3D shows the graph summary (low, bug)
- **Where:** `graph-3d-renderer.tsx:426`.
- **Cause:** every click goes through `handleNodeSelect`, which clears the selected entity.

### 13. Colour-mode changes rebuild what is already recoloured in place (low, redundancy)
- **Where:** `real-memory-graph-page.tsx:216`, `graph-2d-renderer.tsx:1028`.
- **Effect:**
  - 3D re-seeds its layout.
  - 2D rebuilds its WebGL context, even though both renderers already have an in-place recolour effect.

### 14. The detail panel's close button has no accessible name (low)
- **Where:** `graph-detail-panel.tsx:62-69`.

### 15. Loading and error states are inconsistent (low)
- Error states are a mix of bare `<p>` text with no retry and an `EmptyState` with a Retry button.
- Loading states are a mix of plain text and a skeleton.

### 16. Constants and helpers defined more than once (low)
- `KIND_CHART` is defined three times: `code-explorer`, `code-filters`, `code-glow-canvas`.
- `deriveProcesses` exists twice (one live, one in dead code).
- Node sizing differs between 2D (`memorySizes`) and 3D (`computeNodeVal`).

### 17. Duplicated runner boilerplate and per-frame allocation during layout (low)
- **Where:** `cluster-runner.ts` and `constellation-runner.ts`.
- **Cause:** both carry the same worker, animation-frame and timer code. `arrange` allocates several Maps and point objects per node per frame during the 8-20 s layout run.
- **Also:** `collide()` is O(k²)×350 over islands.

### 18. `symbolsByFile` copies each file's array on every insert (low)
- **Where:** `code-explorer.tsx:56-63`.

### 19. The graph payload carries full memory content for up to 50,000 nodes (low, plausible)
- **Where:** backend `graph.py:154`.
- **Use:** the page needs it only for 30-character labels, the client-side filter and the detail panel.

### 20. Every theme consumer runs its own MutationObserver (low)
- **Where:** `useMemoryGraphTheme` is mounted about six times on the page, each with its own observer and `getComputedStyle` pass.

### 21. Remembered-position maps grow without bound (low)
- **Where:** `positionsRef` in both renderers is never pruned.

### 22. Design critique: demo and real are parallel component trees
- **Size:** about 3,400 lines of demo-only views.
- **Drift:** the real Code Graph lacks the demo's zoom buttons and wiki deep links.
- **Decision:** owner call. Alternatively, drive the real components from demo fixtures.

### 23. Design critique: two layout engines
- **Engines:** island layout for memories, constellation layout for code.
- **Proposal:** the code graph already has communities, so one engine could serve both canvases and retire about 424 lines plus tests.
- **Decision:** owner call, because the code graph would look different.

## Removal candidates (ranked by lines saved and safety)
1. Finding 8: about 3,950 lines including tests, plus the `noverlap` dependency and the dead CSS. Do it after the Mermaid fix.
2. The code-colour half of `code-graph-theme.ts`: about 350 lines including tests.
3. The other dead exports in finding 9: about 200 lines.
4. The duplicate `stableHash` and `KIND_CHART`: about 40 lines.
5. The 3D work done in 2D view: removes cost, not lines.
6. Demo views: about 3,400 lines (owner decision).
7. The constellation engine: about 424 lines (owner decision).

## Checked and found sound
- **Routing:** the route DEMO split is fixed at build time, so it violates no hook rules. The redirects are correct.
- **2D renderer lifecycle:** cleanup covers the animation frame, the FA2 worker, Sigma, the camera, font and resize listeners, and the hull canvas. Values are read through refs, so there are no stale closures. Re-layout is gated by the layout signature.
- **Code canvas and 3D lifecycle:** both clean up and dispose correctly.
- **Motion and backdrop:** ambient motion is capped at 2,000 nodes and 30 fps, pauses on hidden tabs and honours reduced motion. The backdrop resizes only on change.
- **Interaction:** hover refreshes partially, and hit testing uses GPU picking.
- **Layout and tree:** `spreadPoints` uses a grid instead of all pairs. The explorer is virtualised and its tree is lazy.
- **Data:** query keys and `placeholderData` scoping are correct. `PanelResizeHandle` records its darkraise-ui gap. Process steps are ordered by `step`. The fixtures are anonymised.

## Not covered
- Opened only for imports, or not read:
  - `focus-model`, `node-hover`, `node-diamond-program`, `straight-alpha`, `memory-edge-width`, `panel-resize`, `graph-summary-stats`, `synthetic-graph`;
  - `graph-summary`, `graph-filter-panel`, `graph-toolbar`, `settings-rows`, `selection-settings`, `node-count-row`, `entity-type-swatch`;
  - the demo code components: `code-graph-tab`, `repositories-tab`, `wiki-tab`, `reindex-dialog`, `code-inspector`, `phase-ticker`, `repo-status-chip`, `phase-progress`;
  - `git-account-select` and `types.ts`.
- Dead files: headers only.
- Stories and tests: searched, not read.
