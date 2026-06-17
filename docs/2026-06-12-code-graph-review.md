# Code Graph page & feature — full review (2026-06-12)

Multi-dimensional review (state/correctness, rendering/performance,
accessibility, UX coherence, API contracts, maintainability) of
`routes/_authenticated/code-graph.tsx`, the `features/graph` code-graph
components and libs, `hooks/api/use-code-api.ts`, and their backend
contracts. Six parallel finder agents produced 73 unique findings; every
finding was then adversarially verified by an independent agent with a
default-refute stance. **71 confirmed (15 high / 32 medium / 24 low), 2
refuted.**

> **Remediation status (2026-06-12, same day):** the correctness and
> performance clusters are FIXED and verified (backend 617 passed,
> frontend tsc/119 tests/build green; a second adversarial review of the
> fix batch confirmed 13 follow-up defects, all also fixed): root causes
> 1-8 below, plus the renderer performance work — identity-keyed rebuilds
> instead of teardown-per-filter-toggle, camera carry within a repo,
> multigraph with real parallel-edge curvature, cached reducer colors,
> pointer-indexed BFS, stable memo identities so selection clicks no
> longer rebuild the scene or the file tree, FileTree memo + per-repo key
> + collapsed default above 50 directories, deferred focus re-centering
> after FA2 settles, and renderer-reported layout-running state.
> STILL OPEN: most of the accessibility cluster (§9 except ⌘K-over-modal
> and the ToggleGroup labels), the UX polish items in §10 (repo-in-URL,
> Depth explainer, edge-count/filter mismatch, toolbar overflow, palette
> query persistence, Symbols dropdown pollution), and the §11
> maintainability refactors (buildGraph split, reveal-helper dedupe,
> test coverage for page wiring/layout math, duplicate state/interfaces,
> dead exports, curated-table cleanup).

Many findings are one root cause seen from several review angles. The
consolidated picture:

## Root causes, by impact

### 1. Owner-qualified symbol ids break every method lookup — HIGH

Backend graph node ids for nested symbols are `name::file_path::owner`
(`graph_keys.compose_key`), but `useCodeSymbolDetail` splits
`[name, ...rest]` and joins the rest into `file_path` — so for any class
method the lookup sends `file_path=src/x.py::Owner`, which matches
nothing: guaranteed 404, retried once, swallowed. Clicking any method or
nested function shows no Source/Signature/Docstring and no AI summary,
silently. Fix: take only segment [1] as file_path (mirror backend
`split_symbol_key`); optionally pass owner for disambiguation.
(`use-code-api.ts:291-296`)

Related: the symbol-detail gate is a blocklist (`kind !== "file" &&
kind !== "module"`), so process/community/route/tool/property selections
fire guaranteed-422 `GET /code/symbols/{plain-name}` requests (the path
param is typed UUID server-side), and Run Blast Radius is offered for
kinds that always 404. Should be an allowlist of symbol kinds.

### 2. Repo switch resets nothing — HIGH

No state resets on `selectedRepoId` change. With Depth active and a node
selected, the focus BFS seeds from the old repo's node id and filters
out *everything*: a fully indexed repo renders the "No graph data —
Index this repo" empty state until the user resets Depth. Even without
Depth, the panels keep showing the previous repo's selection, symbol
detail, blast radius, search results, process, and community; the
SymbolsTab pagination offset also survives. Fix: reset selection-derived
state (and focusDepth) on repo change. (`code-graph.tsx:215-240`)

### 3. Blast-radius canvas overlay is dead code — HIGH

The reducers gate the destructive highlight on `hasHighlights && !sel`,
but running blast radius *requires* a selection, and deselecting clears
the blast state in the same handler — the spec'd red on-canvas overlay
is unreachable in every flow; only the panel list/histogram works.
Additionally, blast data survives selection switches (node B shows node
A's affected list/risk) and the in-flight `onSuccess` closure commits
results under whatever is selected when the response lands. Fix: let the
highlight branch win over selection; clear/tag blast state per symbol id.
(`code-graph-renderer.tsx:691,783`; `code-graph.tsx:262-284,562-577`)

### 4. Errors are silent or misleading — HIGH

- Graph fetch failure renders the "No graph data — Index this repo"
  empty state: wrong diagnosis, no error message, no retry
  (`isError` never consumed).
- Code search and blast radius mutations pass only `onSuccess`; on
  failure the spinner stops and nothing happens (no global MutationCache
  handler either). Other routes consistently attach onError toasts.
- Toolbar symbol search also gives no success/no-results feedback, and
  results land in a possibly hidden Results tab (Enter appears to do
  nothing when the inspector is collapsed).

### 5. Reindex never refreshes the graph — HIGH

`useReindexRepo` invalidates repo queries but never
`codeGraph`/`codeSymbols`/`codeSymbol`; after a reindex the page can
serve the stale graph indefinitely (staleTime only shields 60s; with no
invalidation and no refetchOnWindowFocus, the cached entry just lives
on). (`use-code-api.ts:218-237`)

### 6. Backend graph payload double-emits nodes — MEDIUM (backend)

`get_code_graph` emits every file and symbol twice (file rows + nodes
keyed `kind='symbol'` alongside kind-specific rows), inflating toolbar
counts, producing duplicate React keys in lists, and duplicate ⌘K
palette entries. (`backend/app/services/code_query.py:212-247`)

### 7. Renderer architecture issues — HIGH/MEDIUM

- `new Graph()` is a *simple* graph: the second edge between the same
  node pair throws and the catch swallows it — every class→method
  `has_method` edge is dropped before render (edges are ordered by
  type, `contains` lands first). The code even calls
  `indexParallelEdgesIndex`, which only matters on a multigraph.
  Fix: `new Graph({ multi: true, type: "directed" })`.
- Every node-type toggle, depth change, color-mode flip, and theme
  change tears down Sigma, restarts FA2, and resets the camera
  (full rebuild keyed on `graphKey`).
- `graphKey` is a lossy hash (counts + first/last id): it can miss real
  data changes (stale canvas vs fresh panels) and false-fire on
  reordering.
- Play/pause desyncs: rebuilds auto-start FA2 but the route's resync
  effect only watches `[graphData, layout]`; pause + toggle a filter →
  simulation runs while the toolbar shows Play.
- Hot-path waste: per-node regex color parsing in reducers on every
  refresh, hover triggers full-graph reprocess, O(n²) `Array.shift` BFS
  (a fixed pattern exists in the same file).

### 8. `namespace` kind is invisible — MEDIUM

The parser emits `kind='namespace'` (C++/PHP), the renderer treats it as
a structural anchor, but `ALL_NODE_TYPES` omits it — the nodes are
always filtered out and no checkbox can restore them. Consider deriving
the filter list from the loaded graph's kinds. (`code-graph.tsx:86-104`)

### 9. Accessibility — MEDIUM

- ⌘K listener fires with the process modal open; Escape then closes
  both layers.
- The WebGL canvas has no accessible name/role or programmatic link to
  its text alternatives.
- `role="toolbar"` without the arrow-key roving pattern (~19 raw tab
  stops) announces a pattern it doesn't implement.
- Focus drops to `<body>` when activated buttons disable themselves.
- Process/community active rows are color-only (no `aria-pressed`/
  `aria-current`); tree Enter on the selected file doesn't re-notify
  (the earlier mouse-only fix); `text-destructive/70` labels sit near
  2.7:1 contrast; dangling `aria-labelledby` on the file tree; the two
  ToggleGroups are unlabeled radio groups.

### 10. UX polish — MEDIUM/LOW

Jump-to-node on a filtered-out target reveals but never focuses the
camera (focusNode runs before the rebuild); selecting a process row
while a node is selected leaves emphasis permanently invisible (missing
`handleSelect(null)`, unlike its sibling handlers); the page forgets
everything on navigation (repo not in the URL search params); Depth is a
silent no-op without a selection; edge counts ignore edge-type filters;
the Symbols kind dropdown lists graph-only kinds that can never match;
the toolbar overflows at common laptop widths; the palette keeps its
query after picking.

### 11. Maintainability — MEDIUM

`buildGraph` is ~510 lines mixing six concerns with near-duplicate
highlight/emphasis reducer branches and a thrice-repeated camera block;
the reveal-hidden-node-and-select logic is copy-pasted five times with
behavioral drift (the camera-focus inconsistency above is a direct
casualty); zero tests cover the page wiring, focus-depth BFS, blast-id
assembly, or the pure layout functions (module-private, so untestable
as-is); duplicated selection state (`selectedNodeId` + `selectedNode`);
plus a handful of lows: dead `drawHullForGroup` export, unused
`language` prop field, redundant as-cast, duplicate 12-field interfaces,
triplicated overlay wrapper, quadruplicated "analyzable symbol"
predicate, GitNexus-inherited dead rows in the kind/edge tables.

## Refuted claims

- "Symbol search responses can apply out of order" — TanStack Query
  mutation callbacks are last-call-wins through a single
  MutationObserver; the race is impossible as claimed.
- "`undefined as any` cast in node-diamond-program" — forced by sigma's
  upstream typing; correct as written.

<!-- appendix below is generated from the verified findings JSON -->
## Appendix: all confirmed findings by dimension

Each finding was adversarially verified by an independent agent against the actual code (frontend, backend, and darkraise-ui/sigma dist where relevant); evidence chains live in the review transcript. Severity in brackets.


### State & correctness (15)

- **[high] Blast-radius canvas highlight is unreachable (masked by selection, cleared by deselect)**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:691, 783 (renderer); code-graph.tsx 271-281, 562-577`  
  Running blast radius requires a selected node (handleBlastRadius guards on selectedNode; the button only renders for a selection). Both nodeReducer and edgeReducer gate the destructive highlight on `hasHighlights && !sel`, so while that selection exists the red overlay never renders. The only way to drop the selection (stage click or Eraser -> handleSelect(null)) clears blastRadiusIds/blastRadiusData in the same handler. Net effect: the on-canvas red overlay required by docs/superpowers/specs/2026-06-03-code-graph-revamp-design.md ('keep red overlay (now --destructive)') is dead code in every reachable state; only the panel list/histogram works. Fix: let the highlight branch take precedence over selection (drop `!sel`), or stop clearing blast state on deselect.

- **[high] Symbol detail 404s for every method: owner-qualified id split joins owner into file_path**  
  `frontend/src/hooks/api/use-code-api.ts:291-296`  
  Graph node ids for nested symbols are `name::file_path::owner` (backend/app/utils/graph_keys.py:24; get_code_graph composes them at backend/app/services/code_query.py:230). useCodeSymbolDetail does `const [name, ...rest] = symbolId.split("::"); const filePath = rest.join("::")`, so for a method the lookup is called with file_path=`src/x.py::Owner`, which matches no code_files row -> GET /code/symbols/lookup returns 404 (retried once via retry:1). Every click on a method or nested-function node therefore shows no Source/Signature/Docstring in the inspector and no AI summary/path in the analysis panel, silently. Fix: use only the second segment as file_path (mirror backend split_symbol_key); optionally pass owner so the backend can disambiguate same-named methods.

- **[high] Repo switch keeps stale selection/focusDepth: indexed repo renders as 'No graph data'**  
  `frontend/src/routes/_authenticated/code-graph.tsx:215-240, 963-971`  
  No state resets when selectedRepoId changes. With focusDepth set and a node selected, the filteredNodes BFS seeds from the old repo's selectedNodeId, which does not exist in the new repo's edges, so visited={oldId} and every node is filtered out -> the page shows the 'No graph data — Index this repo from the Repositories page' empty state for a fully indexed repo, with the renderer unmounted so there is nothing to click; only resetting Depth to All recovers. Even without focusDepth, selectedNode/symbolDetail/blastRadiusData/searchResults/selectedProcess/selectedCommunityId from the previous repo keep rendering in both side panels under the new repo. Fix: reset selection-derived state (and ideally focusDepth) in an effect on selectedRepoId.

- **[medium] Play/pause toggle desyncs: rebuilds restart FA2 but the sync effect only watches [graphData, layout]**  
  `frontend/src/routes/_authenticated/code-graph.tsx:194-196; renderer 414, 907-908`  
  buildGraph auto-starts the FA2 worker on every graphKey rebuild, and graphKey changes on node-type filter toggles, focus-depth changes, selection changes while a depth filter is active, colorMode flips, and theme changes — not just on graphData/layout. The route's resync effect (`if (layout === "force") setIsPlaying(true)`) only depends on [graphData, layout], so: pause the layout, toggle any node-type checkbox -> the simulation restarts while the toolbar Toggle still shows Play (pressed=false). The first click is then a silent state correction (setLayoutRunning(true) no-ops). Fix: key the resync to the same inputs that rebuild (e.g. have the renderer report layout-running changes, or include filteredNodes/colorMode in the effect deps).

- **[medium] Blast-radius data survives selection switches and in-flight races, shown under the wrong symbol**  
  `frontend/src/routes/_authenticated/code-graph.tsx:262-284, 562-577`  
  handleSelect clears blast state only when node is null. Selecting node B directly after analyzing node A (clickNode, palette, file tree) keeps A's affected list, risk badge, and depth histogram rendered under B's header in the analysis panel, presenting A's impact analysis as if it were B's. Additionally the mutate onSuccess closure captures selectedNode at call time: if the user switches selection while the request is pending, the resolved result (including the old node's id added to blastRadiusIds) is committed into the new selection's context. Fix: clear blast state on any selection change, or tag blastRadiusData with its symbol id and only render it when it matches selectedNode.id.

- **[medium] Graph payload duplicates every file and symbol node, causing duplicate React keys and inflated counts**  
  `backend/app/services/code_query.py:212-247; frontend code-graph-search.tsx 76-79; code-graph.tsx 366-374, 895-904`  
  get_code_graph emits file nodes from code_files AND re-emits the same key from code_graph_nodes (kind 'file' rows, key = file_path since only 'symbol' is composite), and emits every symbol twice: once from code_symbols with its real kind and once from the aux 'symbol'-kind row with an identical id. Frontend consequences: searchNodes feeds CodeGraphSearch where CommandItem uses key={node.id}, so searching a file or symbol name in the cmd-K palette renders duplicate-key items (React warning, confusing doubled rows, one badged 'symbol'); the toolbar node count counts every file twice (both copies pass the kind filter); the renderer only survives because addNode dedups on hasNode. Fix on the backend by excluding kinds already emitted from relational tables ('file', 'symbol') from the aux query, or dedupe by id in useCodeGraph.

- **[medium] Selecting a process row while a node is selected leaves emphasis permanently invisible**  
  `frontend/src/routes/_authenticated/code-graph.tsx:451-465 (vs 467-497, 504-529); renderer 708`  
  handleProcessSelect sets selectedProcess and opens the modal but, unlike handleCommunitySelect and handleProcessFocus, does not clear the node selection. The renderer gates emphasis on `!sel`, so the highlight is masked while the selection exists; closing the modal shows the panel row as active with no canvas emphasis, and clearing the selection (stage click) wipes selectedProcess via handleSelect(null) before the emphasis could ever render. It is only reachable through the modal's 'Focus in graph' button. Also note process emphasis does not reveal flow nodes hidden by filters (handleProcessFocus does). Fix: call handleSelect(null) at the top of handleProcessSelect, mirroring handleCommunitySelect.

- **[medium] Graph fetch errors render the 'No graph data — Index this repo' empty state**  
  `frontend/src/routes/_authenticated/code-graph.tsx:963-971`  
  useCodeGraph's error state is never consumed. After a 500/timeout/network failure on GET /code/graph/{repo_id} (retried once), isLoading is false and data is undefined, so filteredNodes is empty and the page shows the empty state instructing the user to index the repo — a misleading diagnosis with no error message or retry affordance. Fix: branch on isError with a distinct error overlay before the empty-state check.

- **[low] Non-symbol node kinds trigger invalid symbol-detail requests and silent blast-radius failures**  
  `frontend/src/routes/_authenticated/code-graph.tsx:201-207, 1008; code-analysis-panel.tsx 175-178, 253-283`  
  The only gate for symbol detail and the 'Run Blast Radius' button is kind !== file/module. Route, tool, process, community, and property node keys are bare names with no '::' (backend/app/utils/graph_keys.py:9), so selecting one fires GET /code/symbols/{key} with a non-UUID path param -> 422, retried once, on every selection. Clicking Run Blast Radius on a route/tool/community/process node POSTs a symbol_id the backend cannot resolve -> 404; the mutation has no onError and there is no global mutation handler (app-providers.tsx), so the button spinner just stops with zero feedback. Fix: gate both on an allowlist of real symbol kinds, and add an onError toast to handleBlastRadius.

- **[low] Parallel edges of different types are silently dropped by the simple graphology Graph**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:433, 592-607`  
  `new Graph()` defaults to a simple graph, so the second same-direction edge between a pair throws and is swallowed by the catch labelled 'duplicate edge'. The backend does emit such pairs — e.g. a process's entry symbol carries both entry_point_of and step_in_process to the same process node; only the alphabetically-first type survives (backend orders by edge_type). Consequences: the dropped relation can never be revealed by the edge-type filters (hiding the surviving type hides the pair entirely), the toolbar edge count (filteredEdges.length) overstates what is drawn, and indexParallelEdgesIndex at line 610 is dead code on a simple graph. Fix: construct with {multi: true} (the parallel-edge index + curvature plumbing already anticipates it).

- **[low] graphKey is a lossy hash: distinct filtered subgraphs can collide and skip the rebuild**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:414`  
  graphKey = node count + edge count + first/last node id + theme + colorMode. With focusDepth active, moving the selection between two same-degree nodes whose filtered neighborhoods share the same first/last survivors in graphData order produces a different node set with an identical key, so buildGraph never re-runs and the canvas keeps rendering the previous neighborhood while the route state (panels, counts, selection) describes the new one. The renderer reads nodes/edges only inside buildGraph, so nothing else corrects it. Fix: include the actual filter inputs (selectedNodeId+focusDepth+visible kinds) or a real content hash in the key.

- **[low] 'namespace' symbols are invisible by default with no filter checkbox to restore them**  
  `frontend/src/routes/_authenticated/code-graph.tsx:86-104`  
  The parser emits kind 'namespace' (backend/app/services/code_parser.py:160, namespace_definition) but ALL_NODE_TYPES omits it, so visibleNodeTypes never contains it: every namespace node in a C++/C# repo is filtered out of filteredNodes and the Node Types checklist never lists it. The renderer even treats 'namespace' as a structural layout root (STRUCTURAL_TYPES, code-graph-renderer.tsx:126-132) that can never receive nodes. Only the search/palette reveal paths can resurrect them by side effect. Fix: add 'namespace' to ALL_NODE_TYPES (and consider deriving the list from the loaded graph's kinds to prevent recurrence).

- **[low] Jump to a filtered-out node reveals it but never focuses the camera**  
  `frontend/src/routes/_authenticated/code-graph.tsx:343-352, 537-546; renderer 1049-1058`  
  handleSymbolSelect and handlePalettePick update visibleNodeTypes/focusDepth and immediately call rendererRef.focusNode(id). When the target was hidden, focusNode no-ops (graphRef.hasNode(id) is false on the current sigma instance) and the rebuild that adds the node happens on the next animation frame with no follow-up focus; the selectedId camera effect also ran against the old instance. On a large graph the user picks a node from the cmd-K palette or symbol browser and the camera goes nowhere (the rebuild even resets it), leaving the selection off-screen. Fix: defer focusNode until after the rebuild (e.g. renderer focuses selectedId post-build when it newly exists).

- **[low] Command palette query persists after picking a result**  
  `frontend/src/features/graph/components/code-graph-search.tsx:38-46`  
  handleOpenChange resets the query only on close, but handlePick calls the onOpenChange prop directly, bypassing the reset. Closing via Escape clears the filter; closing by picking a node does not, so the next cmd-K open shows the stale query and a pre-filtered list. Fix: route handlePick's close through handleOpenChange(false).

- **[low] SymbolsTab pagination offset not reset when the repo changes**  
  `frontend/src/features/graph/components/code-inspector-panel.tsx:168-170`  
  The offset-reset effect watches only [debouncedQuery, kind]. Switching repos while paginated keeps the old offset in the new repo's query (useCodeSymbols keys on repoId+offset), so if the new repo has fewer symbols the list shows an empty page with a nonsensical range readout (e.g. '51-12 of 12') until the user pages back. Fix: add repoId to the reset effect's dependencies.


### Rendering & performance (11)

- **[high] Symbol detail lookup breaks for every class method (owner-qualified ids) and non-symbol kinds**  
  `frontend/src/hooks/api/use-code-api.ts:290-298`  
  useCodeSymbolDetail splits the node id as `[name, ...rest]` and sends `rest.join("::")` as file_path. The backend composes graph node ids as `name::file_path::owner` for any symbol with a parent (compose_key in backend/app/utils/graph_keys.py:19-26; get_code_graph at backend/app/services/code_query.py:230 passes owner). For a method id like `render::src/app.tsx::Widget`, the hook requests /code/symbols/lookup?file_path=src/app.tsx::Widget, which matches no CodeFile row (lookup_symbol, code_query.py:147-152) and 404s. Result: clicking any class/struct/interface method in the graph leaves the Inspector Source tab and the Analysis symbol header permanently on the empty state — methods are among the most-clicked node kinds. The backend already handles 3-segment keys via split_symbol_key (take segment 2 only); the frontend must mirror that. Additionally, the route only excludes kinds 'file' and 'module' before calling this hook (code-graph.tsx:201-207), so clicking property/route/tool/community/process nodes (ids are plain names, no '::') sends the name to GET /code/symbols/{id} which expects a UUID and 422s — 2 doomed requests per click with retry:1.

- **[high] Every node-type toggle, focus-depth change, color-mode switch, and theme change tears down Sigma + restarts FA2 + resets the camera**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:413-431, 887-923`  
  buildGraph is keyed on graphKey (line 414), which embeds node/edge counts, themeKey, and colorMode. Any change kills the Sigma instance and FA2 worker (419-431), reseeds all positions, spawns a new worker, restarts the force simulation for getLayoutDuration (20-45s of WebWorker CPU on 1000+ nodes), and resets the camera to default (a new Sigma instance loses zoom/pan). Triggers: every Node Types checkbox click (changes filteredNodes length), every node click while focus Depth is active (new BFS neighborhood), switching color-by type/community (only colors differ), and every theme accent/mode change (themeKey, line 413). Edge-type toggles prove the cheap path exists — they go through visibleEdgeTypesRef + reducer res.hidden + refresh (991-994) with no rebuild. Node visibility, colors, and theme tokens could likewise be applied in place via graph.updateEachNodeAttributes/setSetting, preserving camera and layout progress. On a 10k-node graph each checkbox click costs a full O(N+E) rebuild, a worker respawn, an indexParallelEdgesIndex pass, and up to 45s of re-simulation with nodes visibly shuffling.

- **[medium] graphKey fingerprint both misses real data changes (stale render) and false-fires on nondeterministic backend ordering**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:414`  
  graphKey is `${nodes.length}:${edges.length}:${first.id}:${last.id}:${themeKey}:${colorMode}`. Node labels, kinds, and edge wiring are not fingerprinted, and nodes/edges prop changes are otherwise ignored (buildGraph deps = [graphKey] only). Concrete miss: after a reindex where a symbol is renamed, the refetched payload has identical counts, the same first node (files are emitted first and the file set is unchanged), and the same last node — the graph keeps rendering the old name/edges until an unrelated filter toggle forces a rebuild. Conversely, get_code_graph's node SELECTs have no ORDER BY (backend/app/services/code_query.py:212-247), so heap-order changes between refetches can flip nodes[0]/nodes[last] and trigger a spurious full rebuild + camera reset while the user is mid-exploration. Also, themeKey only covers primary/background/isDark; node colors derive from --chart-N tokens (code-graph-theme.ts buildCodeGraphColorMaps), so a preset change that alters chart hues without moving primary/background leaves the graph rendered in stale colors. A content hash over ids+kinds (or explicit rebuild-on-data-identity with in-place color updates) would close both directions.

- **[medium] Simple (non-multi) graphology Graph silently drops every second edge type between the same node pair — has_method never renders**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:433, 592-613`  
  new Graph() (line 433) defaults to multi:false; graphology throws UsageGraphError on a second directed edge between the same source/target regardless of type (verified in node_modules/graphology/dist/graphology.cjs.js:2895), and the catch at line 605 swallows it as "duplicate edge". The backend systematically emits two edges per class→method pair: 'contains' (code_pipeline.py:1616-1623) and 'has_method' (1636-1643) between identical keys. get_code_graph orders edges alphabetically by edge_type (code_query.py:254), so 'contains' always wins and the 'has_method' edge is dropped for every method of every class. User impact: the has_method checkbox in Edge Types is a no-op for these pairs, hiding 'contains' (a common move to declutter hierarchy) removes class→method links entirely, and the toolbar edge counter (filteredEdges from the API) overstates what is actually drawn. It also makes the indexParallelEdgesIndex call (610-613) dead weight: its parallelIndex/parallelMaxIndex attributes are never read (curvature is set independently at line 602), and a simple graph cannot contain the parallel edges it indexes. Fix: new Graph({ multi: true }) plus curvature derived from the parallel index.

- **[medium] GET /code/graph ships every file node twice and every symbol twice (once as kind 'symbol'), inflating counts and producing duplicate React keys**  
  `backend/app/services/code_query.py:207-247`  
  get_code_graph concatenates code_files rows (id=file_path, kind 'file'), code_symbols rows (id=name::path[::owner], real kind), and then ALL code_graph_nodes rows — which include kind='file' rows keyed by the same file_path (code_pipeline.py:1556-1563, compose_key('file', path) returns the bare path) and kind='symbol' rows keyed by the same symbol key (1598-1606). Net effect on the frontend: (1) node payload is roughly doubled; (2) the toolbar node counter (code-graph.tsx:895-904) and the Files tab badge (fileList includes each path twice, code-graph.tsx:253-260) overstate reality — the renderer only dedups incidentally via graph.hasNode (renderer line 512); (3) the ⌘K palette maps graphData.nodes directly (code-graph.tsx:366-374), so searching a filename shows the file twice and renders two CommandItems with the same key={node.id} (code-graph-search.tsx:77), a React duplicate-key violation; (4) nodeCount-based sizing/mass heuristics in the renderer are skewed. The aux query should exclude kinds 'file' and 'symbol' (or the primary queries should be dropped in favor of code_graph_nodes).

- **[medium] 'namespace' symbols are silently filtered out of the graph with no way to re-enable them**  
  `frontend/src/routes/_authenticated/code-graph.tsx:86-104, 209-212`  
  The parser emits kind 'namespace' for C++/C# namespace_definition nodes (backend/app/services/code_parser.py:160, KIND_MAP), but ALL_NODE_TYPES omits it. filteredNodes keeps only kinds in visibleNodeTypes (initialized from ALL_NODE_TYPES), so namespace symbols — and all their edges, since filteredEdges requires both endpoints — vanish from the graph, the counters, and the Node Types checkbox list. The renderer specifically treats 'namespace' as a structural root (STRUCTURAL_TYPES, code-graph-renderer.tsx:126-132) for the spiral seeding and the tree/circles layouts' BFS depth computation, so for C++/C# repos those layouts lose their intended roots and the namespace level of the hierarchy. The only accidental escape hatches are the search-result/palette reveal paths that add arbitrary kinds to visibleNodeTypes. Adding 'namespace' to ALL_NODE_TYPES fixes display, filtering, and layout in one line.

- **[medium] Repo switch keeps stale selection/blast-radius/process/search state — new repo's graph renders fully dimmed**  
  `frontend/src/routes/_authenticated/code-graph.tsx:126-162, 639-654`  
  Changing the repo Select only sets selectedRepoId; selectedNodeId, selectedNode, blastRadiusIds/Data, selectedProcess, selectedCommunityId, and searchResults all survive. When the new repo's graph mounts, selectedIdRef still holds the old repo's node id, so the renderer's nodeReducer takes the `sel` branch (code-graph-renderer.tsx:722-741) and dims every node to 0.25 toward background at 0.6 size — the user sees an inexplicably faded graph until they click a node or empty stage. The Inspector/Analysis panels keep showing the previous repo's symbol, blast-radius results stay as if they applied to the new graph, and stale search results toast "isn't in the current graph" when clicked. A repo-change effect (or onValueChange handler) should clear selection, blast radius, process/community emphasis, and search results.

- **[medium] Reducer hot path allocates regex-parsed color strings per node/edge per refresh; hover triggers full-graph reprocess**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:681-860`  
  nodeReducer/edgeReducer call dimColor/brightenColor in the dim branches; each call runs hexToRgb's regex exec plus 2-3 string allocations (lines 22-67). Sigma re-runs reducers for the whole graph on every refresh, and while the FA2 worker is running it updates positions continuously, so with a selection, blast radius, or emphasis active on a 10k-node graph this is ~10k regex parses + object spreads per processing pass for the entire 20-45s simulation — measurable GC pressure and frame drops. enterNode/leaveNode also call sigma.refresh() (851-860), a full O(N+E) reprocess; sweeping the cursor across a dense graph fires these many times per second. Mitigations that fit the current structure: precompute the dimmed/brightened variant per base color once per build (only ~20 node colors and ~18 edge colors exist, all from the theme maps) in a Map keyed by hex, and use sigma's partial refresh (refresh({ partialGraph, skipIndexation: true })) for hover transitions.

- **[low] O(n^2) Array.shift BFS in buildGraph and in the focus-depth filter; fixed pattern already exists in the same file**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:569-582`  
  The child-positioning BFS pops with queue.shift() (line 573). The backend emits a 'defines' edge from the single repo module node to every file (code_pipeline.py:1565-1580), so the BFS frontier after that node is the entire file list — for a 5k-file repo that is ~25M element moves per build, and builds re-run on every filter/theme/color-mode change (see rebuild-churn finding). The route's focus-depth BFS has the same queue.shift() pattern (code-graph.tsx:228-237) and runs on every node click while Depth is active. computeStructuralDepths in the same renderer file already uses the head-pointer technique (lines 256-266); applying it to both BFS loops is mechanical.

- **[low] Play/pause toggle desyncs from the actual FA2 state in three ways; pause leaves the auto-stop timer armed**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:912-921, 1060-1074`  
  (1) The auto-stop timeout (912-921) stops FA2 after 20-45s and runs noverlap, but nothing notifies the route, so isPlaying stays true and the toolbar shows the Pause icon for a stopped simulation; the first click on the toggle is then a visual no-op. (2) setLayoutRunning(false) (1070-1073) stops the worker but does not clear layoutTimeoutRef, so if the user pauses early, the timer still fires at the original deadline and noverlap.assign visibly snaps node positions seconds after the user froze the layout. (3) The route effect `if (layout === "force") setIsPlaying(true)` keyed on [graphData, layout] (code-graph.tsx:194-196) flips the toggle to playing on any graphData refetch identity change even when graphKey is unchanged and no rebuild/auto-start happened. An onLayoutStopped callback prop (invoked from the timeout) plus clearing the timer in the pause branch resolves all three.

- **[low] Toolbar search keystrokes re-render the whole page, and every node click churns filteredNodes/fileList identity, rebuilding the FileTree**  
  `frontend/src/routes/_authenticated/code-graph.tsx:136, 209-243, 253-260`  
  searchQuery lives on the route root, so each keystroke in "Search symbols…" re-renders the entire page: toolbar, CodeGraphRenderer wrapper, CodeAnalysisPanel (33 filter checkboxes + process/community lists), and CodeInspectorPanel including every TreeView row — none of these components are memoized. Separately, filteredNodes depends on selectedNodeId even when focusDepth is null (line 243), so every graph node click re-runs the O(N) kind filter, the O(E) edge filter, and the O(F log F) fileList sort, producing new array identities that cascade into FileTree's useMemo (code-inspector-panel.tsx:61-87) rebuilding the entire tree structure per click — on a 2k-file repo that is a per-click rebuild and re-render of thousands of tree rows. Colocating searchQuery in a small toolbar component and keying the BFS dep as `focusDepth === null ? null : selectedNodeId` removes both churn sources without behavior change.


### Accessibility & interaction (12)

- **[high] Toolbar symbol search gives no feedback on success, no-results, or when the inspector panel is hidden**  
  `frontend/src/routes/_authenticated/code-graph.tsx:286-299, 667-671, 925-945`  
  Pressing Enter in the 'Search symbols…' input runs the mutation and stores results, but nothing else happens: the inspector's active tab is not switched to 'results' (it defaults to 'source', code-inspector-panel.tsx:305), so results land in a background tab whose only cue is a small count badge; when the search returns 0 rows the badge is suppressed (`count: searchResults.length || undefined`) so there is zero visible change; and when the user has toggled the inspector off (`showInspector === false` gates the whole panel at line 925), results are stored into state that renders nowhere — the search is a complete silent no-op. For screen-reader users the only output in every case is the unlabeled toolbar Spinner (renders generic sr-only 'Loading' via role=status), with no completion or result-count announcement ever. Impact: sighted users with the panel hidden and all assistive-tech users perceive the search feature as broken.

- **[high] Code search and blast-radius failures are completely silent (no onError, isError never read)**  
  `frontend/src/routes/_authenticated/code-graph.tsx:289-296, 562-577`  
  Both `codeSearchRef.current.mutate(...)` and `blastRadius.mutate(...)` pass only `onSuccess`. The app's QueryClient (src/providers/app-providers.tsx:13-20) defines no global mutationCache onError, apiFetch just throws (src/lib/api.ts:42-49), and the page never reads `codeSearch.isError` / `blastRadius.isError`. On a 4xx/5xx the spinner stops and absolutely nothing else happens — no toast, no inline message, no live-region text. For 'Run Blast Radius' the keyboard user has additionally just lost focus to <body> (the button disabled itself), so a failure leaves them with no focus and no feedback. Other features in this codebase (e.g. jobs-panel.tsx) consistently use onError toasts; these two mutations are the outliers.

- **[medium] Global ⌘K listener fires with a modal dialog open; sibling-layer stack then closes both dialogs on Escape**  
  `frontend/src/routes/_authenticated/code-graph.tsx:606-616`  
  The window keydown handler has no guard for open overlays, so pressing Ctrl/⌘+K while the ProcessFlowModal is open stacks the CommandDialog palette on top of it. darkraise-ui's DismissableLayer `isTopLayer` (dist/chunk-YCVHR2NN.js) only demotes a layer when another layer's node is *contained inside* it; the two dialogs are sibling portals, so both count as top: one Escape press fires onEscapeKeyDown on BOTH layers and closes the palette and the process modal simultaneously, and any pointerdown inside the palette is 'outside' the modal's layer and dismisses the modal underneath. Additionally the check `e.key === "k"` is strict lowercase — with Caps Lock on, e.key is 'K' and the shortcut silently stops working. Fix: skip the toggle (or close the modal first) when another dialog is open, and compare `e.key.toLowerCase()`.

- **[medium] Graph canvas has no accessible name, role, or programmatic link to its text alternatives**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:1080-1086`  
  The renderer returns a bare <div> into which sigma.js injects unlabeled <canvas> elements. There is no role, no aria-label, and no off-screen description, so the page's central region is anonymous to screen readers — a SR user landing after the toolbar encounters nothing between the left and right panels. Node interaction on the canvas (click-to-select, hover labels, drag-to-pan) is pointer-only. Working non-visual alternatives do exist (⌘K palette, Symbols tab, Files tree all drive selection), but nothing labels the canvas or points AT users toward them. Minimum fix: role="img" (or role="application" if interactivity is claimed) plus an aria-label like 'Code dependency graph, N nodes, M edges; use the search palette or Symbols tab to select nodes' on the container div.

- **[medium] role="toolbar" without the toolbar keyboard pattern: ~19 raw tab stops and a misleading role announcement**  
  `frontend/src/routes/_authenticated/code-graph.tsx:622-920`  
  darkraise-ui's Toolbar (dist/chunk-IABBO3D3.js) is a plain div that sets role="toolbar" but implements no roving tabindex or arrow-key navigation. The ARIA toolbar pattern promises a single tab stop with arrow-key movement; here a keyboard user must Tab through roughly 19 controls (panel toggle, repo select, search input, palette button, 3 layout radios, 2 color radios, 5 camera buttons, play toggle, depth radiogroup, analysis toggle) before reaching the panels or canvas, on every visit, while their screen reader announces a toolbar whose expected arrow-key behavior does nothing. (The layout/color ToggleGroups and the depth SegmentGroup do rove internally, which only partly reduces the count.) Root cause is the library component; the page is where users feel it. Either implement roving focus or drop the toolbar role to stop promising it.

- **[medium] Keyboard focus is dropped to <body> when activated buttons disable themselves**  
  `frontend/src/routes/_authenticated/code-graph.tsx:833-846`  
  Three controls disable themselves as a direct result of their own activation, which makes the browser silently move focus to <body>, forcing keyboard users to re-Tab from the top of the document: (1) 'Clear selection' (code-graph.tsx:833-846) — activating it clears selectedNodeId, which flips its own `disabled={!selectedNodeId}`; the adjacent 'Focus selected node' disables at the same moment; (2) 'Run Blast Radius' (code-analysis-panel.tsx:256-272) — `disabled={isBlastRadiusLoading}` disables the focused button for the duration of the request, and completion is never announced; (3) symbols pagination Prev/Next (code-inspector-panel.tsx:269-288) — reaching the first/last page disables the button under focus. Standard fixes: keep the button enabled and no-op (aria-disabled), or move focus somewhere sensible before disabling.

- **[medium] Active process and community rows expose no selected state to assistive tech (color-only)**  
  `frontend/src/features/graph/components/process-panel.tsx:30-39`  
  The Execution Flows rows (process-panel.tsx:30-39) and the Communities rows (code-analysis-panel.tsx:398-422) render the active item solely via `bg-primary/15 text-primary` class swaps — no aria-pressed, aria-current, or aria-selected. Both behave as toggles (re-click deactivates, per handleProcessSelect/handleCommunitySelect in code-graph.tsx), so a screen-reader user cannot tell which flow/community is currently emphasized in the graph, nor that a second activation will turn the emphasis off rather than on. For sighted users the distinction is also conveyed by color alone (the icon tint change is itself a color cue). Adding aria-pressed={active} to both Buttons fixes the AT side.

- **[medium] Graph/symbols query errors render as misleading empty states ('No graph data — Index this repo')**  
  `frontend/src/routes/_authenticated/code-graph.tsx:963-971`  
  useCodeGraph's error state is never read; when GET /code/graph/{repo} fails, `isLoading` is false and `graphData` undefined, so filteredNodes is empty and the page shows the 'No graph data / Index this repo from the Repositories page' EmptyState — actively wrong guidance that sends the user off to re-index a repo that may be perfectly indexed. The Symbols tab has the same conflation: a failed useCodeSymbols query shows 'No symbols found' (code-inspector-panel.tsx:255-261). Both should branch on isError with a retry affordance.

- **[medium] File tree: keyboard Enter on the already-selected file does not re-notify the graph (mouse-only fix)**  
  `frontend/src/features/graph/components/code-inspector-panel.tsx:110-119`  
  The known re-click fix routes the 'same file clicked again' case through TreeViewItem's onClick, because single-select toggleSelected short-circuits on the same id. But darkraise-ui TreeView handles keyboard Enter/Space inside the tree's onKeyDown by calling toggleSelected(node.id) directly (dist/chunk-KRTZWUXM.js, 'Enter' case) — it never synthesizes a click. So the short-circuit still swallows the event for keyboard users: select a file, deselect the node by clicking the stage (tree still shows the file selected), arrow back to it and press Enter — nothing happens, while a mouse re-click works. The keyboard path needs the same re-notify handling (e.g. an onKeyDown on the item mirroring the onClick guard).

- **[low] Blast-radius depth labels use text-destructive/70 — roughly 2.7-2.9:1 contrast, failing WCAG 4.5:1**  
  `frontend/src/features/graph/components/code-analysis-panel.tsx:131, 325`  
  The 'd1/d2/d3+' histogram labels (line 131) and the per-row 'd{distance}' markers in the affected list (line 325) render small (text-sm) mono text in `text-destructive/70`. With the default destructive token (hsl 0 84% 60%) the 70% alpha blend computes to about 2.9:1 against the default dark background and about 2.7:1 against white in light mode — well under the 4.5:1 minimum for normal-size text in both modes, so this is not theme-edge-case noise. These labels carry real information (impact depth). Using full-opacity destructive, or destructive only as an accent with the digits in text-foreground, would fix it.

- **[low] File tree has a dangling aria-labelledby: TreeViewLabel is never rendered**  
  `frontend/src/features/graph/components/code-inspector-panel.tsx:121-141`  
  darkraise-ui's TreeViewTree always emits aria-labelledby pointing at `${baseId}-label` (dist/chunk-KRTZWUXM.js:379), an id that only exists if TreeViewLabel is rendered. FileTree renders TreeView > TreeViewTree without a TreeViewLabel, so the role="tree" widget references a nonexistent element and ends up with no accessible name — screen readers announce an anonymous tree. Rendering a visually-hidden <TreeViewLabel>Repository files</TreeViewLabel> (or equivalent) fixes it.

- **[low] Layout and color-mode ToggleGroups are unlabeled radio groups**  
  `frontend/src/routes/_authenticated/code-graph.tsx:692-697, 743-748`  
  darkraise-ui ToggleGroup type="single" renders a role="group" container whose items are role="radio" (dist/chunk-ABWQJQ4Y.js). Neither group carries an accessible name, so a screen-reader user hears bare radios ('Force layout, radio, 1 of 3') with no indication of what the set controls, and the two adjacent unlabeled groups (layout switcher vs color-by switcher) are indistinguishable when navigating by landmarks/groups. The depth SegmentGroup nearby does this correctly (aria-label="Focus depth", role="radiogroup"). Add aria-label="Graph layout" and aria-label="Node color mode" to the two ToggleGroups.


### UX coherence (13)

- **[high] Blast-radius highlight can never render on the canvas (dead reducer branch)**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:691, 783 (renderer); D:/Repositories/_local_projects/darkmem/frontend/src/routes/_authenticated/code-graph.tsx:273-281`  
  Both nodeReducer and edgeReducer gate the destructive blast-radius styling on `hasHighlights && !sel`, i.e. it only renders when no node is selected. But running blast radius REQUIRES a selected node (handleBlastRadius early-returns without one, and the button only appears for a selected symbol), so immediately after a successful run sel is always set and the canvas shows plain selection styling — visually nothing changes. The only paths that clear the selection (clickStage, the Eraser toolbar button, clearSelection) all go through handleSelect(null) at code-graph.tsx:273-281, which wipes blastRadiusIds/blastRadiusData before the highlight could ever appear. Net effect: the feature's central visualization (red affected-node rings + edge emphasis, code-graph-renderer.tsx:691-720 and 783-801) is unreachable in any user flow; users only get the side-panel list. No test covers this path (no blast/highlightedIds tests exist under __tests__), which is why it passes the green gate.

- **[high] Clicking any class method (owner-qualified node id) silently fails to load symbol detail**  
  `frontend/src/hooks/api/use-code-api.ts:290-297`  
  Graph symbol node ids are composed by the backend as `name::file_path` or, for symbols with a parent (methods, nested functions), `name::file_path::owner` (backend/app/utils/graph_keys.py:19-26, emitted at backend/app/services/code_query.py:230 via the parent_symbol_id join). useCodeSymbolDetail splits on '::' and rejoins EVERYTHING after the first segment as file_path, so for a method it calls /code/symbols/lookup?file_path=src/foo.py::MyClass — the backend compares that literally against CodeFile.file_path (code_query.py:147-154) and 404s. Result: clicking any method node (or selecting it via the Symbols tab / search) loads no source, signature, docstring, or AI summary; the Source tab shows the 'Select a symbol to inspect' empty state while a node IS selected, with zero error surfaced. Blast radius for the same node works (the backend's split_symbol_key handles 3-part keys), making the inspector failure look random. Related: aux node ids like 'community:3'/'process:…' contain no '::' and are sent to GET /code/symbols/{id}, which 422s on UUID parsing — another doomed silent request on every community/process node click.

- **[high] Failed graph load is indistinguishable from 'repo not indexed' — wrong guidance, no retry**  
  `frontend/src/routes/_authenticated/code-graph.tsx:191, 963-971`  
  useCodeGraph's error state is never consumed (line 191 destructures only data/isLoading) and there is no global QueryCache error handler (src/providers/app-providers.tsx:13-20). When GET /code/graph/{id} fails (500, network, backend down), isLoading goes false, filteredNodes is empty, and the page shows the EmptyState 'No graph data — Index this repo from the Repositories page'. That sends the user on a pointless reindex errand for what is actually a fetch failure, with no retry affordance. The same single message also covers two more distinct states: a genuinely unindexed repo, and a fully-indexed repo where the user's own Node Types filters (or a stale Depth focus, see repo-switch finding) excluded every node — in the filter case the message is outright false. The EmptyState also offers no action/link to the Repos page, making it a dead end either way.

- **[high] Switching repos leaks all per-repo state; with Depth active the new repo renders as 'No graph data'**  
  `frontend/src/routes/_authenticated/code-graph.tsx:126-162, 215-243`  
  No effect resets per-repo state when selectedRepoId changes. selectedNode/selectedNodeId, focusDepth, searchResults, blastRadiusIds/Data, selectedProcess, and selectedCommunityId all survive a repo switch. Worst case: with focusDepth set, the BFS at lines 215-240 seeds from the stale selectedNodeId, which does not exist in the new repo's graph, so filteredNodes becomes [] and the page shows 'No graph data — Index this repo from the Repositories page' for a perfectly indexed repo; the user has no clue the Depth control is the cause. Lesser cases: the Analysis panel keeps showing the previous repo's symbol (header, summary, blast results) next to the new repo's graph, and the Results tab keeps the old repo's search hits — clicking one just toasts 'isn't in the current graph'.

- **[high] Run Blast Radius is offered for node kinds that always 404, and both mutations fail silently**  
  `frontend/src/features/graph/components/code-analysis-panel.tsx:175-178, 253-283 (gating/button); code-graph.tsx:286-299, 562-577 (no onError)`  
  isAnalyzableSymbol only excludes kind file/module, so the destructive 'Run Blast Radius' button renders for process, community, route, tool, property, and unknown nodes. For all of those the backend cannot resolve a CodeSymbol (code_query.py:267-295: ids without '::' must parse as a UUID; '::' ids must match a code_symbols row) and returns 404. Neither blastRadius.mutate (code-graph.tsx:562-577) nor codeSearch.mutate (code-graph.tsx:286-299) passes onError, and there is no global MutationCache handler, so the outcome is: button shows 'Analyzing…', then resets, forever, with zero feedback — a guaranteed silent dead end on a prominent CTA. The toolbar symbol search has the same failure mode: on a network/500 error the spinner just disappears.

- **[medium] GET /code/graph double-emits file and symbol nodes — inflated counts and duplicate ⌘K palette entries**  
  `backend/app/services/code_query.py:212-247 (backend); code-graph.tsx:209-243, 366-374; code-graph-search.tsx:76-79 (frontend symptoms)`  
  get_code_graph emits file nodes from code_files (lines 212-217) AND again from the aux code_graph_nodes table, which contains a kind='file' row per file with the identical key (code_pipeline.py:1554-1563); it likewise emits every symbol twice (real kind from code_symbols, plus the aux kind='symbol' row with the same composite key, code_pipeline.py:1590-1605). Frontend consequences: (1) filteredNodes counts both file copies, so the toolbar 'n' count and Analysis 'Nodes' stat overcount by the file count versus what the renderer actually draws (graph.addNode dedups by id); (2) searchNodes feeds ALL nodes to the ⌘K palette, so every file appears twice and every symbol appears twice (once badged with its real kind, once badged 'symbol'), and CommandItem key={node.id} produces duplicate React keys; (3) 'symbol', 'file', 'module' leak into derived kind lists. Fix belongs on the backend payload or a frontend dedup-by-id at the query boundary.

- **[medium] Node-type/Depth changes rebuild the whole scene: camera reset, paused simulation silently restarts, Play/Pause desyncs**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:414, 907-921; code-graph.tsx:192-196`  
  graphKey includes filtered node/edge counts, so toggling a single Node Types checkbox, changing Depth, or revealing hidden kinds via community/process focus kills and recreates the Sigma instance. Three user-visible costs: (1) the camera resets to origin — zoom/pan context is lost on every checkbox click; (2) buildGraph unconditionally restarts the FA2 worker in force mode (line 907), so a layout the user explicitly paused starts moving again and re-simulates for up to 20-45s (getLayoutDuration); (3) the page's isPlaying sync effect (code-graph.tsx:192-196) only watches [graphData, layout], not filter-driven rebuilds, so the toolbar shows the 'Play' icon while the simulation is actively running — clicking it once is then a no-op (setLayoutRunning(true) on an already-running worker), requiring two clicks to actually pause.

- **[medium] Page forgets everything on navigation; repo selection is not in the URL**  
  `frontend/src/routes/_authenticated/code-graph.tsx:82-84, 126-162`  
  All state is local useState with no validateSearch/search-param or storage persistence: selected repo, layout, color mode, Depth, node/edge type filters, and panel visibility reset on every visit. This interacts badly with the page's own guidance: the empty state tells users to go to the Repositories page to index, and the round trip back means re-selecting the repo and waiting through a fresh 20-45s force layout, plus re-applying every filter. It also means a specific repo's graph view cannot be linked, bookmarked, or refreshed in place. Putting at least selectedRepoId in the route search params would fix the worst of it.

- **[medium] Search results land in a non-activated (possibly hidden) tab — pressing Enter appears to do nothing**  
  `frontend/src/routes/_authenticated/code-graph.tsx:286-299, 657-688; code-inspector-panel.tsx:305-316`  
  Toolbar search (Enter) writes results into the left Inspector's 'Results' tab, but the active tab is internal to CodeInspectorPanel (defaults to 'source') and is never switched on search completion — the only signal is a count badge on an inactive tab. If the Inspector is toggled off (showInspector=false), there is no signal at all: spinner stops and nothing on screen changes. A zero-result search likewise produces no feedback (badge is suppressed for count 0). Compounding the confusion, the toolbar presents two adjacent magnifier-icon affordances with different semantics — 'Search symbols…' (async semantic chunk search → hidden Results tab) and 'Jump to node ⌘K' (instant graph-node jump) — so users reasonably expect Enter in the input to jump-to-node and conclude search is broken. Auto-activating the Results tab (and ensuring the panel is shown) on success would close the loop.

- **[medium] Depth control is a silent no-op without a node selection and never explains itself**  
  `frontend/src/routes/_authenticated/code-graph.tsx:873-891, 215-216`  
  The Depth segmented control (All/1/2/3/5) only takes effect when a node is selected (the filter at line 215 requires focusDepth !== null && selectedNodeId), but it is always enabled, carries no tooltip, and its label 'Depth' does not convey that it means 'neighborhood hops around the selected node'. A user clicking '1' with nothing selected sees the graph not change at all and gets no hint why; the control then sits in an active-looking state. Conversely, deselecting (stage click) while Depth is active silently snaps the view back to the full graph. Either disabling the control without a selection (with a tooltip explaining the dependency) or showing a hint would make the behavior discoverable. Also worth noting: the panel-side selection misattribution risk — stale blast radius results stay rendered under a newly selected node's header (code-graph.tsx:262-284 never clears blastRadiusData on a non-null selection change), labeling node A's affected-count/risk as if they belonged to node B.

- **[low] Edge counts ignore edge-type filters (canvas hides edges, counts don't)**  
  `frontend/src/routes/_authenticated/code-graph.tsx:245-251, 895-904`  
  Node-type filters remove nodes from filteredNodes/filteredEdges (counts respond), but edge-type filters are applied only inside the renderer's edgeReducer via visibleEdgeTypesRef (code-graph-renderer.tsx:767-772). Unchecking 'calls' in the Edge Types panel visibly removes edges from the canvas while the toolbar 'e' count and the Analysis panel 'Edges' stat stay unchanged — inconsistent feedback that makes the filter look broken. The Depth BFS (lines 216-237) also traverses edges of hidden types, so the depth neighborhood includes nodes connected only by edges the user has filtered out.

- **[low] Symbols-tab kind dropdown polluted with graph-only kinds that can never match**  
  `frontend/src/routes/_authenticated/code-graph.tsx:356-364; code-inspector-panel.tsx:206-218`  
  symbolKinds is derived from all graphData node kinds excluding only 'community' and 'process', so the Symbols tab's kind filter offers 'file', 'module', 'symbol', 'property', 'route', and 'tool' — kinds that exist only as graph nodes, never as code_symbols rows the /code/symbols endpoint filters on (its kind column holds parser kinds: function, method, class, struct, interface, trait, enum, impl, type). Selecting any of them returns a guaranteed 'No symbols found' dead end. The exclusion list should match the symbol-table vocabulary rather than the graph vocabulary.

- **[low] Toolbar overflows at common laptop widths; search input is the only shrinkable element**  
  `frontend/src/routes/_authenticated/code-graph.tsx:622-920`  
  Every toolbar group except the center search container is shrink-0: panel toggle + repo select (w-44) + jump button + 3 layout toggles + 2 color toggles + 6 camera/play buttons + 'Depth' label + 5-item SegmentGroup + node/edge stats + panel toggle + separators and gap-3 spacing total roughly 1100-1150px of fixed width. With the sidebar expanded on a 1366px laptop, the flexible search input is squeezed toward its min-content first and the bar then overflows with no wrap or overflow handling, clipping the right-side controls (Depth, stats, Analysis toggle). There is no responsive collapse (e.g. overflow menu) for the 20+ controls.


### API contracts (5)

- **[high] Owner-qualified symbol node ids break /code/symbols/lookup — method nodes show no source or details**  
  `frontend/src/hooks/api/use-code-api.ts:291-296`  
  Graph node ids for symbols are composed by backend graph_keys.compose_key as 'name::file_path' or, for symbols nested under an owner (every class method), 'name::file_path::owner' (backend/app/utils/graph_keys.py:19-26; get_code_graph composes them with owner at backend/app/services/code_query.py:230). useCodeSymbolDetail splits the id with `const [name = "", ...rest] = symbolId.split("::"); const filePath = rest.join("::")`, so a method node id 'render::src/app.tsx::Widget' sends file_path='src/app.tsx::Widget' to GET /code/symbols/lookup. The backend matches CodeFile.file_path exactly (code_query.py:147-152), which never contains '::' — guaranteed 404. The backend's own split_symbol_key handles the 3-segment case correctly (parts[1] is the file path); the frontend must do the same. User impact: clicking any class-method node in the graph (or any owner-qualified symbol) leaves the Source tab on the 'Select a symbol to inspect' empty state and the Analysis panel without path/visibility/enrichment/summary — with no error shown (the query error is discarded at code-graph.tsx:201-207). Methods are a large fraction of nodes in OO repos, so a core inspector flow is broken for them.

- **[high] codeGraph/codeSymbols/codeSymbol caches are never invalidated after reindex — stale graph persists indefinitely**  
  `frontend/src/hooks/api/use-code-api.ts:218-237`  
  useReindexRepo's onSuccess invalidates only ['repos'] and ['repoStats'] (lines 232-235), and reindex is a 202 background task so invalidating at mutation time could not capture completion anyway. The websocket handler for repo.indexing_completed (frontend/src/lib/websocket.ts:125-160) also only invalidates ['repos'], ['repoTasks'], ['repoStats'] — nothing in the app ever invalidates ['codeGraph', repoId], ['codeSymbols', ...] or ['codeSymbol', id] (verified by repo-wide grep). With the global QueryClient config (staleTime 60s, refetchOnWindowFocus: false — app-providers.tsx:18, whose comment claims 'freshness comes from the WebSocket + explicit mutation invalidations'), a user sitting on the Code Graph page after triggering a reindex sees the 'Indexed N files, M symbols' success toast but the graph, symbol browser, and symbol details never refresh; even navigating away and back within 60s serves the stale cache. Same applies to enrichment.batch_completed (websocket.ts:162-164), which refreshes repoStats but leaves symbol summary/enrichment_status badges stale. Fix: invalidate the code* keys on repo.indexing_completed (and enrichment.batch_completed for codeSymbol/codeSymbols).

- **[medium] Graph fetch errors render the misleading 'No graph data — Index this repo' empty state**  
  `frontend/src/routes/_authenticated/code-graph.tsx:191, 963-971`  
  useCodeGraph's error state is never read: `const { data: graphData, isLoading } = useCodeGraph(selectedRepoId)`. On a 500 from GET /api/v1/code/graph/{repo_id} (apiFetch throws, retry:1 then status='error', isLoading=false, data=undefined), filteredNodes is empty and the page falls into the `!isLoading && filteredNodes.length === 0` branch, showing 'No graph data / Index this repo from the Repositories page'. A user with a fully indexed repo hitting a transient server error is told to reindex instead of being shown an error/retry affordance. The Symbols tab has the same pattern: a failed /code/symbols request renders 'No symbols found' (code-inspector-panel.tsx:255-260) because only `data` and `isFetching` are consumed.

- **[medium] Renderer uses a simple (non-multi) graphology Graph — the second edge type between the same node pair is silently dropped (every class→method has_method edge)**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:433, 592-608`  
  `new Graph()` (line 433) creates a simple directed graph; graphology's addEdge throws when an edge already links the same source/target, and the try/catch at lines 594-607 (commented '/* duplicate edge */') swallows it. But the backend legitimately emits multiple edge types per node pair: for every class method it writes both 'contains' (parent symbol → child, code_pipeline.py:1616-1623) and 'has_method' (class key → owner-qualified method key, code_pipeline.py:1630-1643) — identical (source, target) endpoints. The graph endpoint orders edges by edge_type (code_query.py:254), so 'contains' always lands first and every class→method 'has_method' edge is dropped before render; 'extends'+'calls' between the same pair collide the same way. The code even calls indexParallelEdgesIndex (line 610), which only does anything on a multigraph. User impact: the 'has_method' edge-type checkbox appears dead for nested methods, edge colors/legend lie about what is drawn, and the toolbar edge count (filteredEdges.length, computed from raw data at code-graph.tsx:245-251) disagrees with the rendered edge set. Fix: `new Graph({ multi: true, type: "directed" })` (the parallel-edge index and per-edge curvature are already in place to render them).

- **[low] Selecting plain-name node kinds fires guaranteed-422 GET /code/symbols/{name} requests**  
  `frontend/src/routes/_authenticated/code-graph.tsx:201-207`  
  The symbol-detail gate is a blocklist (`kind !== "file" && kind !== "module"`), so selecting a process, community, route, tool, or property node passes its id to useCodeSymbolDetail. Those ids are plain names with no '::' (graph_keys.py:9), so the hook calls GET /code/symbols/{id} (use-code-api.ts:298) where the path parameter is typed UUID (backend/app/api/routes/code.py:85-87) — FastAPI rejects with 422 every time, retried once by the global retry:1. Impact: two guaranteed-failing requests plus console noise on every such selection; the UI degrades to the empty 'Select a symbol to inspect' state, indistinguishable from finding #1. The gate should be an allowlist of symbol kinds (or skip ids that cannot resolve).


### Maintainability (15)

- **[high] Owner-qualified symbol keys break the symbol-detail lookup for all methods**  
  `frontend/src/hooks/api/use-code-api.ts:291-293`  
  useCodeSymbolDetail splits composite ids as `const [name = "", ...rest] = symbolId.split("::"); const filePath = rest.join("::")`. The backend composes graph node ids for parented symbols as `name::file_path::owner` (backend/app/utils/graph_keys.py:24, used by get_code_graph at backend/app/services/code_query.py:230), and its own split_symbol_key docstring states file paths never contain '::', so parts[1] is the file path. The frontend instead sends `file_path=app/x.py::OwnerClass` to GET /code/symbols/lookup, which exact-matches CodeFile.file_path (code_query.py:150) and returns 404. Result: clicking ANY method or nested-function node in the graph (or picking it from the Symbols tab via handleSymbolSelect) silently yields no Source tab content and no AI-summary/visibility badges in the Analysis panel — the query error is swallowed (no onError, no global handler) and the empty state renders. Fix: take only parts[1] as file_path (and optionally forward owner once the endpoint accepts it to disambiguate overloads).

- **[medium] ALL_NODE_TYPES omits 'namespace': namespace symbols are silently invisible with no checkbox to reveal them**  
  `frontend/src/routes/_authenticated/code-graph.tsx:86-104`  
  filteredNodes drops any node whose kind is not in visibleNodeTypes (line 211-213), and the Node Types filter list is built from ALL_NODE_TYPES — which lacks 'namespace'. The backend KIND_MAP emits kind='namespace' for namespace_definition (backend/app/services/code_parser.py:160), and the renderer itself expects it: NODE_SIZES, STRUCTURAL_TYPES and getNodeMass in code-graph-renderer.tsx (lines 91, 126-132, 146-147) all treat namespace as a structural anchor. For C++/C#/PHP repos these nodes (and every edge touching them) never render, there is no UI to enable them, and because namespaces are BFS roots for the tree/circles layouts and FA2 mass anchors, layout quality degrades too. Add 'namespace' to ALL_NODE_TYPES, or derive the filter list from kinds present in graphData instead of a hardcoded table.

- **[medium] Play/pause toggle desyncs on rebuilds triggered by filters, color mode, or theme**  
  `frontend/src/routes/_authenticated/code-graph.tsx:194-196`  
  The sync effect (`if (layout === "force") setIsPlaying(true)`) only depends on [graphData, layout], but buildGraph in the renderer rebuilds and auto-starts the FA2 worker whenever graphKey changes — which also happens on node-type filter toggles (filteredNodes count changes), colorMode switches, and theme/accent changes (code-graph-renderer.tsx:413-414, fa2.start() at 907). Repro: pause the layout, then toggle any Node Types checkbox — the simulation restarts and nodes move while the toolbar still shows the Play icon claiming it is paused; the first click on the toggle is then a no-op state correction. The renderer's own comment at 192-193 states the intent is to keep the toggle in sync with auto-start, so the dependency list is simply incomplete. Either key the effect on the same inputs as graphKey, or have the renderer report run-state changes via a callback.

- **[medium] Symbol search and blast-radius failures are completely silent**  
  `frontend/src/routes/_authenticated/code-graph.tsx:289-296, 564-577`  
  codeSearch.mutate and blastRadius.mutate pass only onSuccess, and the QueryClient has no global MutationCache/QueryCache onError (src/providers/app-providers.tsx:13-20). If POST /code/search or POST /code/blast-radius fails (backend down, 404 symbol, 500), the spinner stops and nothing else happens — stale results stay in the Results tab and the user gets no feedback that 'Run Blast Radius' did nothing. Other routes in the app (repos.tsx, settings.tsx) consistently attach onError toasts, so this is also a convention drift. Add onError toasts to both mutations (and consider surfacing the symbolDetail query error in the Source tab instead of the generic empty state).

- **[medium] graphKey endpoint-hash can miss real data changes, rendering a stale graph**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:414, 922-923`  
  The full rebuild is keyed on `${nodes.length}:${edges.length}:${nodes[0]?.id}:${nodes[last]?.id}:${themeKey}:${colorMode}` with an eslint-disable suppressing the real nodes/edges dependency. Any update that preserves both counts and the first/last node ids — e.g. a codeGraph refetch after reindex where middle symbols were renamed or re-kinded, or a filter change that swaps equal-sized type sets — leaves the canvas showing the old data with no error and no visual hint. Because every downstream feature (selection, search jump, blast-radius highlight) resolves ids against the new props while the canvas holds old nodes, the mismatch surfaces as 'isn't in the current graph' toasts or highlights that target missing nodes. A content hash over sorted ids (or an explicit version/updated_at from the API) would make the key trustworthy; at minimum the heuristic deserves a comment acknowledging the collision window.

- **[medium] buildGraph is a ~510-line function mixing six concerns, with near-duplicate reducer branches and a thrice-repeated camera block**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:416-923`  
  buildGraph constructs the graphology graph, resolves colors, seeds positions (BFS + spiral), configures Sigma (including a 40-line hover canvas drawer), defines both reducers inline, wires events, and manages the FA2 worker lifecycle — all inside one useCallback. Concrete duplication inside it: (1) the highlight branch (nodeReducer 691-703, edgeReducer 783-801) and the emphasis branch (708-720, 803-821) are structurally identical, differing only in token (destructive vs primary) and scale constants (1.8/0.4/0.15 vs 1.6/0.45/0.18) — a parameterized helper would halve them and keep the two modes from drifting; (2) the camera animate-to-node block `{x, y, ratio: 0.15}, {duration: 400}` appears three times (clickNode 870-878, selectedId effect 968-978, focusNode 1049-1057); (3) structural-node insertion (548-566) duplicates addNode's body (530-545); (4) the module-level GOLDEN_ANGLE constant (220) is re-derived as a local `goldenAngle` (496). Extracting the pure pieces (position seeding, reducers, hover drawer) to module functions would also make them unit-testable — today none of this 1087-line file has any test.

- **[medium] Reveal-hidden-node-and-select logic is copy-pasted five times with behavioral drift between copies**  
  `frontend/src/routes/_authenticated/code-graph.tsx:301-354, 451-548`  
  handleSearchResultClick (301), handleSymbolSelect (330), handleCommunitySelect (467), handleProcessFocus (504) and handlePalettePick (531) each re-implement 'if target not in filteredNodes: setFocusDepth(null) + add kind(s) to visibleNodeTypes, then select' — three of the comments literally say 'mirroring handleSearchResultClick'. The copies have already drifted: handleSymbolSelect and handlePalettePick call rendererRef.current?.focusNode() after selecting while handleSearchResultClick does not (so clicking a Results-tab row selects but never moves the camera if the node was already selected once), and the community/process variants batch hiddenKinds while the pick variants add a single kind. A single `revealAndSelect(node)` / `revealKinds(nodes)` helper would remove ~60 lines and make the camera-focus behavior uniform. Note also that in the reveal path the focusNode call is a silent no-op: it runs before the rebuild (graphRef has no such node yet), so a just-revealed node is selected but never focused — another symptom only a shared, tested helper would have caught.

- **[medium] Zero test coverage for the page wiring and renderer layout math — the layer where regressions are silent**  
  `frontend/src/routes/_authenticated/code-graph.tsx:209-260, 562-577`  
  Existing tests cover CodeGraphSearch, ProcessPanel, SymbolsTab, code-processes, and code-graph-theme — all leaf components/libs. Untested and easily breakable without any typecheck/build signal: (1) the focus-depth BFS filter (code-graph.tsx:209-243) — an off-by-one in `depth >= focusDepth` changes every depth preset; (2) blast-radius id assembly `a.key ?? name::file_path` (562-577) — the owner-key matching that a prior review already had to fix once; (3) the reveal-and-select handlers and the process/community emphasis mutual-exclusion invariants (442-497) — all pure enough to test with a mocked renderer ref; (4) computeStructuralDepths/assignTreeLayout/assignConcentricLayout in code-graph-renderer.tsx (235-324) are pure functions but module-private, so the tree and circles layouts have no coverage at all — exporting them would make them trivially testable without touching Sigma/WebGL; (5) FileTree in code-inspector-panel.tsx (54-143) carries three documented workarounds for past bugs (tabIndex seeding, re-click notify, leaf-only select) yet has no test pinning any of them against a darkraise-ui upgrade.

- **[low] Duplicated selection state: selectedNodeId is always derivable from selectedNode, and four call sites set both redundantly**  
  `frontend/src/routes/_authenticated/code-graph.tsx:126-135, 324, 349, 543, 552`  
  The page keeps `selectedNodeId` and `selectedNode` as separate useState slots even though handleSelect (262-284) always sets both and selectedNodeId === selectedNode?.id everywhere. Four handlers call `setSelectedNodeId(matchNode.id)` immediately before `handleSelect(matchNode)` which sets it again (lines 324-325, 349-350, 543-544, 552-553). The redundant calls are harmless today but the split state is a drift trap: any future code path that updates one without the other desyncs the renderer highlight (keyed on selectedNodeId) from the panels (keyed on selectedNode). Derive selectedNodeId via `selectedNode?.id ?? null` and delete the second state.

- **[low] Dead export: drawHullForGroup and its vis-network stub type have no callers**  
  `frontend/src/features/graph/lib/graph-geometry.ts:4-9, 86-138`  
  rg across src/ shows graph-2d-renderer imports computeHullGroups + drawHullForSigma and graph-3d-renderer imports computeHullGroups; nothing imports drawHullForGroup. The function exists solely to serve the removed vis-network MiniGraph (its own comment says so), and it drags along the fake `Network` type and an unused `_label` parameter. Delete the function and the Network stub; the file's own comment already concedes the dependency is gone.

- **[low] Unused 'language' field in CodeGraphRendererProps node shape**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:347`  
  The nodes prop type declares `language?: string` but nothing in the 1087-line renderer reads node.language (colors come from kind, labels from label). The backend graph payload does not even emit a language field on nodes (code_query.get_code_graph emits id/label/kind/file_path/properties). It misleads readers into thinking language drives some visual channel. Remove the field, or better, replace the four inline structural node/edge type literals in this file with the shared CodeGraphNode/CodeGraphEdge types from use-code-api.ts so the prop contract cannot drift from the API shape.

- **[low] Redundant as-cast re-declares a property the node type already has**  
  `frontend/src/routes/_authenticated/code-graph.tsx:404-405`  
  `const props = (n as { properties?: Record<string, unknown> | null }).properties` — but `n` is a CodeGraphNode from useCodeGraph, and CodeGraphNode already declares `properties?: Record<string, unknown> | null` (use-code-api.ts:54). `n.properties` typechecks without the cast. The cast pattern actively hides future type errors: if the field were renamed on the interface, this cast would keep compiling and silently read undefined, making every community fall back to counted membership size.

- **[low] CodeSymbolResponse and CodeSymbolDetail are 13-field duplicates differing in one nullability**  
  `frontend/src/hooks/api/use-code-api.ts:80-108`  
  The two interfaces are field-for-field identical except file_path (string vs string | null), yet both shadow the same backend CodeSymbolResponse schema (the backend serves /code/symbols, /code/symbols/lookup and /code/symbols/{id} from one schema that returns "" for a missing file, never null — so the | null variant doesn't even match the wire format). Any backend field addition must now be applied twice or the two consumers diverge. Collapse to one interface (CodeSymbolDetail = CodeSymbolResponse) or derive one from the other with a mapped type.

- **[low] Triplicated overlay wrapper and quadruplicated 'analyzable symbol' predicate**  
  `frontend/src/routes/_authenticated/code-graph.tsx:949-971, 201-207, 928-934, 999-1005`  
  Two repeated inline patterns: (1) the centered overlay div `<div className="absolute inset-0 z-10 flex flex-col items-center justify-center">` wraps all three canvas states (no repo / loading / no data) — a tiny CanvasOverlay wrapper would keep the three states' positioning from drifting; (2) the predicate `selectedNode && selectedNode.kind !== "file" && selectedNode.kind !== "module"` is written out three times (the useCodeSymbolDetail arg, both panel symbolDetail props) and a fourth time as isAnalyzableSymbol in code-analysis-panel.tsx:175-178. One `const analyzableNode = useMemo(...)` would replace all three route copies and let the panel receive the already-gated value instead of re-deriving it; today adding another non-symbol kind (e.g. 'community' or 'process', which currently DO trigger a doomed symbol-detail fetch when clicked) requires editing four sites.

- **[low] Curated kind/edge tables drifted from the backend contract: dead entries and inconsistent casing handling**  
  `frontend/src/features/graph/components/code-graph-renderer.tsx:71-122`  
  EDGE_SIZE_MULTIPLIERS includes 'queries' and 'fetches' (lines 120-121) but no backend code inserts those edge_types anywhere (verified across backend/app/services — the emitted set is calls/contains/defines/imports/extends/implements/has_method/has_property/handles_route/handles_tool/method_overrides/method_implements/accesses/member_of/step_in_process/entry_point_of). NODE_SIZES likewise carries ~10 kinds the indexer never emits (project, package, folder, record, variable, import, decorator, model, const, static — KIND_MAP in code_parser.py:144-163 plus aux kinds is the full set). These GitNexus-inherited entries cost little at runtime but mislead maintenance: someone tuning visuals for 'package' nodes is editing a dead row. Related casing drift: process-flow-modal.tsx:90-92 looks up `nodeColors[step.kind] ?? nodeColors[step.kind.toLowerCase()]` while code-inspector-panel.tsx:237 and code-graph-search.tsx:87 use the raw kind — since the backend emits lowercase kinds exclusively, the toLowerCase fallback is dead in one place and the defensive posture is inconsistent across the three swatch call sites; pick one convention (raw, given the backend contract) and apply it everywhere.


### Refuted claims (2)

- **Symbol search responses can apply out of order** — FALSE. The claimed race is impossible with TanStack Query's mutation design. Both searches go through one MutationObserver: code-graph.tsx:197-199 creates a single useCodeSearch() instance (codeSearchRef merely forwards the latest result object), and

- **`undefined as any` cast to clear an inherited hover drawer** — The line exists as quoted (node-diamond-program.ts:100: `this.drawHover = undefined as any`), but the claim fails as a real finding on three grounds.

1. The cast is forced by an upstream typing defect, not sloppiness. Sigma's base class explicitly p
