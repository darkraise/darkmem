# Unified Graph Merge & Refactor — Design Spec

## Goal

Merge the 2D and 3D unified graph pages into a single page at `/unified-graph` with a view toggle, and refactor the 1,929-line monolithic 2D implementation into focused, maintainable components. The 3D implementation's decomposed architecture serves as the template.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| UX model | Single page with 2D/3D toggle | One route, shared state persists across view switches |
| Feature parity | Shared controls only | Filters and API params shared; layout controls (tightness, tag overlay) stay view-specific; mini-graph stays 2D-only |
| Route cleanup | Remove `/unified-graph-3d` | Single entry point; 3D route existed briefly, no bookmarks to preserve |
| Architecture | Component extraction | Decompose monolith into focused files; no abstract factories for two renderers |
| Migration | Incremental commits | Each step independently testable; no behavior changes until final assembly |

## File Structure

### New files to create

```
frontend/src/
├── components/graph/
│   ├── Graph2DRenderer.tsx       (~400 lines) vis-network canvas, 2D hull drawing, interactions
│   ├── Graph3DRenderer.tsx       (~270 lines) react-force-graph-3d, Three.js, 3D hulls, interactions
│   ├── GraphToolbar.tsx          (~150 lines) shared + view-specific controls, view toggle
│   ├── GraphDetailPanel.tsx      (~200 lines) selected node detail + graph summary
│   ├── GraphFilterPanel.tsx      (~250 lines) tag/type/source/cluster/search filters
│   ├── GraphSkeleton.tsx         (~100 lines) animated loading skeleton
│   └── MiniGraph.tsx             (~190 lines) entity context sub-graph (2D detail panel)
├── lib/
│   ├── graph-colors.ts           (~80 lines)  all color palettes and helpers
│   └── graph-geometry.ts         (~120 lines) convexHull, expandHull, drawSmoothClosed
```

### Files to modify

- `pages/UnifiedGraph.tsx` — rewritten as thin page shell (~150 lines)
- `lib/graph-utils.ts` — expanded with shared types, imports from graph-colors.ts
- `App.tsx` — remove `/unified-graph-3d` route
- `components/Sidebar.tsx` — remove "3D Graph" nav item

### Files to delete

- `pages/UnifiedGraph3D.tsx`
- `components/graph3d/ForceGraph3DWrapper.tsx`
- `components/graph3d/Graph3DDetailPanel.tsx`
- `components/graph3d/Graph3DToolbar.tsx`

## Data Flow

```
UnifiedGraph.tsx (page shell)
│
├── State:
│   viewMode: "2d" | "3d"
│   API params: similarityThreshold, clusterMinScore, minClusterSize (debounced)
│   Layout: sizeMode, nodeSpacing (2D), clusterTightness (2D), spacing3D (3D)
│   Selection: selectedNodeId (string, works across view switches)
│   Filters: searchText, selectedTags/Types/Sources/Clusters
│   UI: showPanel, showFilters, graphReady
│
├── Data pipeline:
│   useUnifiedGraph(debouncedParams) → raw API data
│   useMemo → filteredMemories (applying filters)
│   useMemo → graphData2D (vis-network DataSets from filteredMemories)
│   useMemo → graphData3D (transformToGraphData from filteredMemories)
│
├── Renders:
│   GraphSkeleton (shown until graphReady)
│   GraphToolbar (viewMode, shared + view-specific controls)
│   GraphFilterPanel (filter state + callbacks)
│   viewMode === "2d" ? <Graph2DRenderer /> : <Graph3DRenderer />
│   GraphDetailPanel (selectedNode, graphData)
│     └── MiniGraph (when viewMode === "2d" and node selected)
```

Key rules:
- Filtering happens once at the page level. Both renderers receive already-filtered data.
- `selectedNodeId` is a string, not a renderer-specific object. Persists across view switches.
- `graphReady` resets to false when `viewMode` changes, showing the skeleton during renderer init.
- Each renderer calls `onReady()` when stabilized (vis-network stabilize event / onEngineStop + hulls built).

## Renderer Interface

```typescript
interface GraphRendererProps {
  graphData: any;
  width: number;
  height: number;
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  onReady: () => void;
  sizeMode: SizeMode;
  spacing: number;
}

interface Graph2DRendererProps extends GraphRendererProps {
  clusterTightness: number;
  showTagOverlay: boolean;
}
```

- `onNodeSelect` passes string ID, not renderer-specific node objects
- `onReady` signals the page to remove the skeleton overlay
- `graphData` is typed loosely at the interface; each renderer casts internally
- Spacing is view-specific state: `nodeSpacing` (2D, 100-500, default 100) and `spacing3D` (3D, 30-200, default 50). The toolbar shows the correct slider based on `viewMode`. Each renderer receives its own spacing value via the `spacing` prop.

## Toolbar Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ [2D|3D]  Size: [▾]  │  Edges: ━━  Cluster: ━━  Min: ━━  │ ... │
│  toggle  shared      │  shared API params                 │ ... │
│                      ├────────────────────────────────────┤     │
│                      │  2D: Space ━━  Tight ━━  Tags ☐   │ [↺] │
│                      │  3D: Space ━━                      │     │
└──────────────────────────────────────────────────────────────────┘
```

Three sections:
1. **View toggle** — segmented 2D/3D buttons, left side
2. **Shared controls** — size mode dropdown + API parameter sliders (similarity threshold, cluster score, min size). These affect the data query.
3. **View-specific controls** — 2D: spacing, tightness, tag overlay toggle. 3D: spacing only. Section content swaps when view changes. Reset button at end.

## Shared Utilities

### graph-colors.ts

Consolidates all color logic currently duplicated between `UnifiedGraph.tsx` and `graph-utils.ts`:

- `CLUSTER_PALETTE` (12 colors)
- `TAG_PALETTE` (6 colors)
- `UNCLUSTERED_COLOR` (#8b949e)
- `TYPE_COLOR_PREASSIGNED` (7 type-to-color mappings)
- `TYPE_COLOR_DYNAMIC` (8 fallback colors)
- `clusterColor(id)`, `typeColor(memoryType)`, `tagColor(idx)`
- `hexToRgba()`, `lightenHex()`, `darkenHex()`

### graph-geometry.ts

2D canvas geometry helpers extracted from UnifiedGraph.tsx:

- `convexHull(points)` — Andrew's monotone chain algorithm
- `expandHull(hull, padding)` — outward expansion
- `drawSmoothClosed(ctx, hull)` — Bezier-smoothed polygon
- `drawHullForGroup(ctx, network, memberIds, color, fillAlpha, strokeAlpha, label?)` — composite hull drawing

### graph-utils.ts (expanded)

Existing file, updated to import colors from graph-colors.ts:

- `SizeMode`, `Node3D`, `Link3D`, `GraphData3D`, `FilterState` types
- `computeNodeVal()` (3D sizing)
- `computeSize()` (2D sizing, moved from UnifiedGraph.tsx)
- `matchesFilter()` (shared filter logic)
- `transformToGraphData()` (3D data transform with cluster attraction links + seeded positions)

## Migration Order

Each step is an independent commit. No behavior changes until step 5.

1. **Extract utilities** — create `graph-colors.ts` and `graph-geometry.ts`. Update 2D graph to import from them instead of using inline definitions. Both pages still work independently.

2. **Extract shared components** — create `GraphSkeleton.tsx`, `GraphFilterPanel.tsx`, `GraphDetailPanel.tsx`, `MiniGraph.tsx`. The 2D page imports these. Verify 2D renders correctly.

3. **Extract Graph2DRenderer** — pull vis-network logic out of `UnifiedGraph.tsx` into `Graph2DRenderer.tsx`. The page becomes a thin shell passing props. Verify 2D still works.

4. **Restructure 3D** — rename `ForceGraph3DWrapper.tsx` to `Graph3DRenderer.tsx`, move to `components/graph/`. Wire it to shared components (GraphDetailPanel, GraphSkeleton). Delete `components/graph3d/` directory, `Graph3DDetailPanel.tsx`, `Graph3DToolbar.tsx`. Verify 3D still works.

5. **Build unified page** — create new `UnifiedGraph.tsx` with view toggle, shared state, conditional 2D/3D rendering. Remove `UnifiedGraph3D.tsx`, remove route and sidebar entry. Verify both views work.

6. **Build unified toolbar** — create `GraphToolbar.tsx` with shared + view-specific sections, view toggle integrated. Verify controls work in both views.

## Testing

- Unit tests: existing `graph-utils.test.ts` tests still pass (update imports for moved functions)
- Manual: verify 2D view renders identically to before refactor
- Manual: verify 3D view renders identically to before refactor
- Manual: verify view toggle preserves filters, selection, sliders
- Manual: verify skeleton shows during load and renderer init for both views
- Build: `npm run build` succeeds with no errors

## Out of Scope

- Adding filters to 3D view (3D already receives filtered data; filter UI is shared)
- 3D mini-graph equivalent
- 3D tag overlay mode
- Performance optimization (lazy loading renderers, code splitting)
- Shared `useDebouncedValue` extraction (stays in page file, single consumer)
