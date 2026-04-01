# Unified Graph Merge & Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the 2D and 3D unified graph pages into a single page with a view toggle, decomposing the 1,929-line monolith into focused components.

**Architecture:** Extract shared utilities (colors, geometry) into lib modules, extract inline components (skeleton, filters, detail panel, mini-graph) into `components/graph/`, extract renderers into self-contained components, then wire everything through a thin page shell with 2D/3D toggle.

**Tech Stack:** React 19, TypeScript, vis-network (2D), react-force-graph-3d + Three.js (3D), Tailwind CSS 4, shadcn/ui

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `frontend/src/lib/graph-colors.ts` | All color palettes and helper functions |
| Create | `frontend/src/lib/graph-geometry.ts` | 2D canvas geometry: convex hull, smooth drawing |
| Create | `frontend/src/components/graph/GraphSkeleton.tsx` | Animated loading skeleton |
| Create | `frontend/src/components/graph/MiniGraph.tsx` | Entity context sub-graph (vis-network) |
| Create | `frontend/src/components/graph/GraphFilterPanel.tsx` | Tag/type/source/cluster/search filters |
| Create | `frontend/src/components/graph/GraphDetailPanel.tsx` | Selected node detail + graph summary |
| Create | `frontend/src/components/graph/Graph2DRenderer.tsx` | vis-network rendering, 2D hulls, interactions |
| Create | `frontend/src/components/graph/Graph3DRenderer.tsx` | react-force-graph-3d, Three.js, 3D hulls |
| Create | `frontend/src/components/graph/GraphToolbar.tsx` | View toggle + shared + view-specific controls |
| Modify | `frontend/src/lib/graph-utils.ts` | Remove color defs (moved to graph-colors), add computeSize |
| Modify | `frontend/src/pages/UnifiedGraph.tsx` | Rewrite as thin page shell (~150 lines) |
| Modify | `frontend/src/App.tsx` | Remove `/unified-graph-3d` route + import |
| Modify | `frontend/src/components/Sidebar.tsx` | Remove "3D Graph" nav item + Box import |
| Modify | `frontend/src/__tests__/graph-utils.test.ts` | Update imports for moved functions |
| Delete | `frontend/src/pages/UnifiedGraph3D.tsx` | Replaced by unified page |
| Delete | `frontend/src/components/graph3d/ForceGraph3DWrapper.tsx` | Replaced by Graph3DRenderer |
| Delete | `frontend/src/components/graph3d/Graph3DDetailPanel.tsx` | Replaced by shared GraphDetailPanel |
| Delete | `frontend/src/components/graph3d/Graph3DToolbar.tsx` | Replaced by shared GraphToolbar |

---

### Task 1: Extract graph-colors.ts

**Files:**
- Create: `frontend/src/lib/graph-colors.ts`
- Modify: `frontend/src/lib/graph-utils.ts`
- Modify: `frontend/src/__tests__/graph-utils.test.ts`

Extract all color palettes and helpers from both `UnifiedGraph.tsx` (lines 26-89, 231-267) and `graph-utils.ts` (lines 43-77) into a single source of truth.

- [ ] **Step 1: Create graph-colors.ts**

Create `frontend/src/lib/graph-colors.ts` with the following content. This consolidates colors from both `UnifiedGraph.tsx` and `graph-utils.ts`:

```typescript
export const CLUSTER_PALETTE = [
  "#a855f7", "#3fb950", "#f97316", "#06b6d4",
  "#ec4899", "#eab308", "#6366f1", "#14b8a6",
  "#f43f5e", "#84cc16", "#8b5cf6", "#0ea5e9",
];

export const TAG_PALETTE = [
  "#22d3ee", "#2dd4bf", "#4ade80",
  "#a3e635", "#facc15", "#fb923c",
];

export const UNCLUSTERED_COLOR = "#8b949e";

export const TYPE_COLOR_PREASSIGNED: Record<string, string> = {
  fact: "#58a6ff",
  decision: "#d2a8ff",
  debug: "#f85149",
  architecture: "#3fb950",
  preference: "#ffa657",
  session: "#79c0ff",
  workflow: "#56d364",
};

const TYPE_COLOR_DYNAMIC = [
  "#f778ba", "#bb86fc", "#4fc3f7", "#aed581",
  "#ffb74d", "#ff6b6b", "#22d3ee", "#e879f9",
];

const typeColorAssignments = new Map<string, string>();
let nextDynamicIdx = 0;

export function clusterColor(clusterId: number): string {
  if (clusterId < 0) return UNCLUSTERED_COLOR;
  return CLUSTER_PALETTE[clusterId % CLUSTER_PALETTE.length];
}

export function tagColor(idx: number): string {
  return TAG_PALETTE[idx % TAG_PALETTE.length];
}

export function typeColor(memoryType: string | null): string {
  if (!memoryType) return UNCLUSTERED_COLOR;
  if (TYPE_COLOR_PREASSIGNED[memoryType]) return TYPE_COLOR_PREASSIGNED[memoryType];
  if (!typeColorAssignments.has(memoryType)) {
    typeColorAssignments.set(memoryType, TYPE_COLOR_DYNAMIC[nextDynamicIdx % TYPE_COLOR_DYNAMIC.length]);
    nextDynamicIdx++;
  }
  return typeColorAssignments.get(memoryType)!;
}

export function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

export function lightenHex(hex: string, amount = 0.35): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const lr = Math.min(255, Math.round(r + (255 - r) * amount));
  const lg = Math.min(255, Math.round(g + (255 - g) * amount));
  const lb = Math.min(255, Math.round(b + (255 - b) * amount));
  return `#${lr.toString(16).padStart(2, "0")}${lg.toString(16).padStart(2, "0")}${lb.toString(16).padStart(2, "0")}`;
}

export function darkenHex(hex: string, amount = 0.45): string {
  let r = parseInt(hex.slice(1, 3), 16);
  let g = parseInt(hex.slice(3, 5), 16);
  let b = parseInt(hex.slice(5, 7), 16);
  r = Math.max(0, Math.round(r * (1 - amount)));
  g = Math.max(0, Math.round(g * (1 - amount)));
  b = Math.max(0, Math.round(b * (1 - amount)));
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}
```

- [ ] **Step 2: Update graph-utils.ts**

Remove all color-related constants and functions from `graph-utils.ts` (lines 43-82: CLUSTER_PALETTE, UNCLUSTERED_COLOR, TYPE_COLOR_PREASSIGNED, TYPE_COLOR_DYNAMIC, typeColorAssignments, nextDynamicIdx, typeColor, clusterColor). Replace with imports from graph-colors.ts:

At the top of graph-utils.ts, add:
```typescript
import { clusterColor, typeColor } from "@/lib/graph-colors";
export { clusterColor, typeColor };
```

Remove the deleted constants/functions. Keep `computeNodeVal`, `matchesFilter`, `transformToGraphData`, and all type definitions. The `transformToGraphData` function already calls `typeColor()` and `clusterColor()` — those now come from the re-export.

- [ ] **Step 3: Update UnifiedGraph.tsx imports**

In `frontend/src/pages/UnifiedGraph.tsx`, remove the inline definitions of CLUSTER_PALETTE, TAG_PALETTE, clusterColor, tagColor, hexToRgba, lightenHex, darkenHex, TYPE_COLOR_PREASSIGNED, TYPE_COLOR_DYNAMIC, typeColorAssignments, nextDynamicIdx, getTypeColor (lines 26-267).

Add import at top:
```typescript
import {
  CLUSTER_PALETTE, TAG_PALETTE, UNCLUSTERED_COLOR,
  clusterColor, tagColor, typeColor, hexToRgba, lightenHex, darkenHex,
} from "@/lib/graph-colors";
```

Replace all calls to `getTypeColor(...)` with `typeColor(...)` throughout the file.

- [ ] **Step 4: Update 3D component imports**

In `ForceGraph3DWrapper.tsx`, change:
```typescript
import { clusterColor } from "@/lib/graph-utils";
```
to:
```typescript
import { clusterColor } from "@/lib/graph-colors";
```

In `Graph3DDetailPanel.tsx`, change:
```typescript
import { clusterColor, typeColor } from "@/lib/graph-utils";
```
to:
```typescript
import { clusterColor, typeColor } from "@/lib/graph-colors";
```

- [ ] **Step 5: Update tests**

In `frontend/src/__tests__/graph-utils.test.ts`, change:
```typescript
import {
  transformToGraphData,
  clusterColor,
  computeNodeVal,
  CLUSTER_PALETTE,
  UNCLUSTERED_COLOR,
} from "@/lib/graph-utils";
```
to:
```typescript
import { transformToGraphData, computeNodeVal } from "@/lib/graph-utils";
import { clusterColor, CLUSTER_PALETTE, UNCLUSTERED_COLOR } from "@/lib/graph-colors";
```

- [ ] **Step 6: Verify and commit**

```bash
cd frontend && npx tsc --noEmit && npx vitest run && npm run build
```

Expected: All 15 tests pass, build succeeds.

```bash
git add frontend/src/lib/graph-colors.ts frontend/src/lib/graph-utils.ts frontend/src/__tests__/graph-utils.test.ts frontend/src/pages/UnifiedGraph.tsx frontend/src/components/graph3d/ForceGraph3DWrapper.tsx frontend/src/components/graph3d/Graph3DDetailPanel.tsx
git commit -m "refactor(ui): extract graph-colors.ts from duplicated color logic"
```

---

### Task 2: Extract graph-geometry.ts

**Files:**
- Create: `frontend/src/lib/graph-geometry.ts`
- Modify: `frontend/src/pages/UnifiedGraph.tsx`

- [ ] **Step 1: Create graph-geometry.ts**

Move the four geometry functions from `UnifiedGraph.tsx` (lines 93-213) into `frontend/src/lib/graph-geometry.ts`. These are: `convexHull`, `expandHull`, `drawSmoothClosed`, `drawHullForGroup`.

The `drawHullForGroup` function references the `Network` type from vis-network. Import it:

```typescript
import type { Network } from "vis-network/standalone";
```

Export all four functions.

- [ ] **Step 2: Update UnifiedGraph.tsx**

Remove lines 93-213 from `UnifiedGraph.tsx`. Add import:
```typescript
import { drawHullForGroup } from "@/lib/graph-geometry";
```

Note: only `drawHullForGroup` is called from UnifiedGraph.tsx. The other three are internal helpers used by `drawHullForGroup`.

- [ ] **Step 3: Verify and commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

```bash
git add frontend/src/lib/graph-geometry.ts frontend/src/pages/UnifiedGraph.tsx
git commit -m "refactor(ui): extract graph-geometry.ts for 2D canvas helpers"
```

---

### Task 3: Extract GraphSkeleton.tsx

**Files:**
- Create: `frontend/src/components/graph/GraphSkeleton.tsx`
- Modify: `frontend/src/pages/UnifiedGraph.tsx`
- Modify: `frontend/src/pages/UnifiedGraph3D.tsx`

- [ ] **Step 1: Create GraphSkeleton.tsx**

Create `frontend/src/components/graph/GraphSkeleton.tsx`. Use the 2D version's skeleton data (it has 5 clusters vs 3D's 4, so it's richer) with a `label` prop for customizable loading text.

Move the `SKEL_CLUSTERS`, `SKEL_EDGES`, `SKEL_BARS` constants and `GraphSkeleton` component from `UnifiedGraph.tsx` (lines 272-445). Change the component signature to accept a `label` prop:

```typescript
export function GraphSkeleton({ label = "Loading graph data..." }: { label?: string }) {
```

The JSX stays the same except the bottom loading text uses `{label}` instead of the hardcoded string.

- [ ] **Step 2: Update UnifiedGraph.tsx**

Remove lines 272-445 (SKEL_CLUSTERS, SKEL_EDGES, SKEL_BARS, GraphSkeleton). Add import:
```typescript
import { GraphSkeleton } from "@/components/graph/GraphSkeleton";
```

- [ ] **Step 3: Update UnifiedGraph3D.tsx**

Remove the inline SKEL_CLUSTERS, SKEL_EDGES, and GraphSkeleton from the bottom of the file (lines 145-270). Add import:
```typescript
import { GraphSkeleton } from "@/components/graph/GraphSkeleton";
```

The existing usage `<GraphSkeleton label={...} />` already matches the new interface.

- [ ] **Step 4: Verify and commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

```bash
git add frontend/src/components/graph/GraphSkeleton.tsx frontend/src/pages/UnifiedGraph.tsx frontend/src/pages/UnifiedGraph3D.tsx
git commit -m "refactor(ui): extract GraphSkeleton into shared component"
```

---

### Task 4: Extract MiniGraph.tsx

**Files:**
- Create: `frontend/src/components/graph/MiniGraph.tsx`
- Modify: `frontend/src/pages/UnifiedGraph.tsx`

- [ ] **Step 1: Create MiniGraph.tsx**

Move the `MiniGraph` component from `UnifiedGraph.tsx` (lines ~449-642 after previous extractions — line numbers shift as code is removed; find the `interface MiniGraphProps` and the function through its closing brace).

The component needs these imports:
```typescript
import { useRef, useEffect } from "react";
import { Network, DataSet } from "vis-network/standalone";
import { useMemoryContext } from "@/hooks/useApi";
import { typeColor } from "@/lib/graph-colors";
```

The `MiniGraphProps` interface:
```typescript
interface MiniGraphProps {
  memoryId: string;
  onNavigate: (id: string) => void;
}
```

Export the component as a named export.

- [ ] **Step 2: Update UnifiedGraph.tsx**

Remove the MiniGraph component and its props interface. Add import:
```typescript
import { MiniGraph } from "@/components/graph/MiniGraph";
```

The existing usage `<MiniGraph memoryId={...} onNavigate={...} />` stays the same.

- [ ] **Step 3: Verify and commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

```bash
git add frontend/src/components/graph/MiniGraph.tsx frontend/src/pages/UnifiedGraph.tsx
git commit -m "refactor(ui): extract MiniGraph into standalone component"
```

---

### Task 5: Extract GraphFilterPanel.tsx

**Files:**
- Create: `frontend/src/components/graph/GraphFilterPanel.tsx`
- Modify: `frontend/src/pages/UnifiedGraph.tsx`

- [ ] **Step 1: Create GraphFilterPanel.tsx**

Move the `FilterPanel` component from `UnifiedGraph.tsx` (find `interface FilterPanelProps` through the component's closing brace, originally lines ~646-911).

Rename it to `GraphFilterPanel` and export it. The component needs these imports:
```typescript
import { Button } from "@/components/ui/button";
import { clusterColor, typeColor } from "@/lib/graph-colors";
```

The `GraphFilterPanelProps` interface (same as the original `FilterPanelProps`):
```typescript
export interface GraphFilterPanelProps {
  tagGroups: [string, [string, number][]][];
  allTypes: [string, number][];
  allSources: [string, number][];
  allClusters: [number, number][];
  clusterNames: Record<string, string>;
  selectedTags: Set<string>;
  selectedTypes: Set<string>;
  selectedSources: Set<string>;
  selectedClusters: Set<number>;
  searchText: string;
  onSearchChange: (v: string) => void;
  onTagToggle: (tag: string) => void;
  onTypeToggle: (type: string) => void;
  onSourceToggle: (src: string) => void;
  onClusterToggle: (cid: number) => void;
  onShowAll: () => void;
}
```

- [ ] **Step 2: Update UnifiedGraph.tsx**

Remove the FilterPanel component and its props interface. Add import:
```typescript
import { GraphFilterPanel } from "@/components/graph/GraphFilterPanel";
```

Update all references from `<FilterPanel` to `<GraphFilterPanel`.

- [ ] **Step 3: Verify and commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

```bash
git add frontend/src/components/graph/GraphFilterPanel.tsx frontend/src/pages/UnifiedGraph.tsx
git commit -m "refactor(ui): extract GraphFilterPanel into standalone component"
```

---

### Task 6: Extract GraphDetailPanel.tsx

**Files:**
- Create: `frontend/src/components/graph/GraphDetailPanel.tsx`
- Modify: `frontend/src/pages/UnifiedGraph.tsx`

Create a unified detail panel that works for both 2D and 3D views. This replaces the inline detail JSX in `UnifiedGraph.tsx` (lines ~1725-1925) and `Graph3DDetailPanel.tsx`.

- [ ] **Step 1: Create GraphDetailPanel.tsx**

Create `frontend/src/components/graph/GraphDetailPanel.tsx`. The component shows either memory detail (when a node is selected) or a graph summary (when no node is selected). The mini-graph is rendered via a slot prop so the parent controls whether to include it.

```typescript
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { clusterColor, typeColor } from "@/lib/graph-colors";
import type { UnifiedMemory } from "@/hooks/useApi";

interface GraphDetailPanelProps {
  selectedMemory: UnifiedMemory | null;
  clusterName: string;
  nodeColor: string;
  memories: UnifiedMemory[];
  clusterNames: Record<string, string>;
  visibleEdgeCount: number;
  onClose: () => void;
  children?: React.ReactNode;
}

export function GraphDetailPanel({
  selectedMemory,
  clusterName,
  nodeColor,
  memories,
  clusterNames,
  visibleEdgeCount,
  onClose,
  children,
}: GraphDetailPanelProps) {
  if (!selectedMemory) {
    return <GraphSummary memories={memories} clusterNames={clusterNames} visibleEdgeCount={visibleEdgeCount} />;
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">Memory Detail</h3>
        <Button variant="ghost" size="icon" onClick={onClose} className="h-6 w-6">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <p className="text-sm text-muted-foreground leading-relaxed">
        {selectedMemory.content}
      </p>

      {selectedMemory.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selectedMemory.tags.map((tag) => (
            <span key={tag} className="rounded-md bg-accent px-2 py-0.5 text-xs text-foreground">
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <span className="text-muted-foreground">Source</span>
          <p className="text-foreground font-medium">{selectedMemory.source}</p>
        </div>
        {selectedMemory.memory_type && (
          <div>
            <span className="text-muted-foreground">Type</span>
            <p className="text-foreground font-medium">{selectedMemory.memory_type}</p>
          </div>
        )}
        <div>
          <span className="text-muted-foreground">Importance</span>
          <p className="text-foreground font-medium">{selectedMemory.importance.toFixed(2)}</p>
        </div>
        {selectedMemory.cluster >= 0 && (
          <div>
            <span className="text-muted-foreground">Cluster</span>
            <div className="flex items-center gap-1.5">
              <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ backgroundColor: nodeColor }} />
              <span className="text-foreground font-medium">{clusterName || `#${selectedMemory.cluster}`}</span>
            </div>
          </div>
        )}
      </div>

      {children}
    </div>
  );
}
```

Add the `GraphSummary` helper function below the main component (same pattern as in `Graph3DDetailPanel.tsx` lines 83-187, with cluster/type/source breakdowns). It receives `memories`, `clusterNames`, and `visibleEdgeCount` and computes counts internally.

- [ ] **Step 2: Update UnifiedGraph.tsx**

Remove the inline detail panel JSX (the right panel content showing memory detail and graph summary). Replace with:
```typescript
import { GraphDetailPanel } from "@/components/graph/GraphDetailPanel";
```

In the render, use:
```tsx
<GraphDetailPanel
  selectedMemory={selectedMemory}
  clusterName={data?.cluster_names?.[String(selectedMemory?.cluster)] ?? ""}
  nodeColor={typeColor(selectedMemory?.memory_type ?? null)}
  memories={filteredMemories}
  clusterNames={data?.cluster_names ?? {}}
  visibleEdgeCount={filteredEdges.length}
  onClose={() => { setSelectedMemoryId(null); setShowPanel(false); }}
>
  {selectedMemory && (
    <MiniGraph memoryId={selectedMemory.id} onNavigate={(id) => setSelectedMemoryId(id)} />
  )}
</GraphDetailPanel>
```

- [ ] **Step 3: Verify and commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

```bash
git add frontend/src/components/graph/GraphDetailPanel.tsx frontend/src/pages/UnifiedGraph.tsx
git commit -m "refactor(ui): extract GraphDetailPanel into shared component"
```

---

### Task 7: Extract Graph2DRenderer.tsx

**Files:**
- Create: `frontend/src/components/graph/Graph2DRenderer.tsx`
- Modify: `frontend/src/pages/UnifiedGraph.tsx`
- Modify: `frontend/src/lib/graph-utils.ts` (add computeSize)

This is the largest extraction — the vis-network rendering logic moves out of `UnifiedGraph.tsx`.

- [ ] **Step 1: Add computeSize to graph-utils.ts**

Add to `frontend/src/lib/graph-utils.ts`:

```typescript
export function computeSize(
  mode: SizeMode,
  connections: number,
  importance: number,
): number {
  if (mode === "uniform") return 18;
  if (mode === "importance") return 12 + importance * 28;
  return 12 + Math.min(28, Math.log1p(connections) * 8);
}
```

Remove the inline `computeSize` from `UnifiedGraph.tsx` and the `SizeMode` type definition (it's already exported from graph-utils.ts).

Also export `matchesFilter` — change `function matchesFilter(` to `export function matchesFilter(` in graph-utils.ts. This will be used by the unified page in Task 10.

- [ ] **Step 2: Create Graph2DRenderer.tsx**

Create `frontend/src/components/graph/Graph2DRenderer.tsx`. This component encapsulates everything the `buildGraph` callback does in the 2D monolith.

Props interface:
```typescript
import type { UnifiedMemory, UnifiedGraphData } from "@/hooks/useApi";
import type { SizeMode } from "@/lib/graph-utils";

interface Graph2DRendererProps {
  data: UnifiedGraphData;
  filteredMemories: UnifiedMemory[];
  filteredClusters: Record<string, string[]>;
  filteredEdges: { source: string; target: string; score: number }[];
  width: number;
  height: number;
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  onReady: () => void;
  sizeMode: SizeMode;
  spacing: number;
  clusterTightness: number;
  showTagOverlay: boolean;
}
```

The component body contains:
- A `containerRef` for the vis-network canvas
- A `useEffect` that builds the vis-network graph (move the `buildGraph` callback logic, ~370 lines)
- The `afterDrawing` handler for cluster hulls and tag overlays
- The focus/unfocus logic for node selection
- Click handlers that call `onNodeSelect(nodeId)` with a string ID

The component calls `onReady()` after the network stabilizes (add a `stabilized` event listener on the Network instance).

Import dependencies:
```typescript
import { useRef, useEffect, useCallback } from "react";
import { Network, DataSet } from "vis-network/standalone";
import { computeSize } from "@/lib/graph-utils";
import type { SizeMode } from "@/lib/graph-utils";
import { clusterColor, tagColor, typeColor, hexToRgba, lightenHex, darkenHex } from "@/lib/graph-colors";
import { drawHullForGroup } from "@/lib/graph-geometry";
```

Return JSX:
```tsx
return <div ref={containerRef} className="absolute inset-0" />;
```

- [ ] **Step 3: Update UnifiedGraph.tsx**

Remove the `buildGraph` useCallback and all vis-network-specific logic. Remove the `containerRef`, `networkRef`, `nodesDataSetRef`, `connectionsMapRef`, `exitFocusModeRef`, `focusOnNodeRef` refs. Remove vis-network imports.

Add:
```typescript
import { Graph2DRenderer } from "@/components/graph/Graph2DRenderer";
```

In the render, replace the canvas div with:
```tsx
<Graph2DRenderer
  data={data}
  filteredMemories={filteredMemories}
  filteredClusters={filteredClusters}
  filteredEdges={filteredEdges}
  width={dimensions.width}
  height={dimensions.height}
  selectedNodeId={selectedMemoryId}
  onNodeSelect={setSelectedMemoryId}
  onReady={() => setGraphReady(true)}
  sizeMode={sizeMode}
  spacing={nodeSpacing}
  clusterTightness={clusterTightness}
  showTagOverlay={showTagOverlay}
/>
```

- [ ] **Step 4: Verify and commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Manually verify: open `/unified-graph`, confirm the 2D graph renders identically to before.

```bash
git add frontend/src/components/graph/Graph2DRenderer.tsx frontend/src/lib/graph-utils.ts frontend/src/pages/UnifiedGraph.tsx
git commit -m "refactor(ui): extract Graph2DRenderer from monolithic page"
```

---

### Task 8: Restructure Graph3DRenderer

**Files:**
- Create: `frontend/src/components/graph/Graph3DRenderer.tsx` (copy + adapt from ForceGraph3DWrapper.tsx)
- Modify: `frontend/src/pages/UnifiedGraph3D.tsx` (temporarily update import)

- [ ] **Step 1: Create Graph3DRenderer.tsx**

Copy `frontend/src/components/graph3d/ForceGraph3DWrapper.tsx` to `frontend/src/components/graph/Graph3DRenderer.tsx`.

Rename the component from `ForceGraph3DWrapper` to `Graph3DRenderer`.

Update the props interface to align with the shared pattern:
```typescript
interface Graph3DRendererProps {
  graphData: GraphData3D;
  width: number;
  height: number;
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  onReady: () => void;
  spacing: number;
}
```

Key change: `onNodeSelect` now passes a **string ID** instead of a `Node3D` object. Update the click handler:
```typescript
onNodeClick={(node: Node3D) => {
  onNodeSelect(node.id);  // was: onNodeSelect(node)
  // ... camera animation stays the same
}}
```

And background click:
```typescript
onBackgroundClick={() => onNodeSelect(null)}
```

Update color import to use graph-colors:
```typescript
import { clusterColor } from "@/lib/graph-colors";
```

- [ ] **Step 2: Update UnifiedGraph3D.tsx temporarily**

Change the import to use the new location:
```typescript
import { Graph3DRenderer } from "@/components/graph/Graph3DRenderer";
```

Update the usage — since `onNodeSelect` now receives a string ID instead of a Node3D object, update the handler:
```typescript
const handleNodeSelect = useCallback((nodeId: string | null) => {
  const node = nodeId ? graphData.nodes.find(n => n.id === nodeId) ?? null : null;
  setSelectedNode(node);
  if (node) setShowPanel(true);
}, [graphData.nodes]);
```

- [ ] **Step 3: Verify and commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Manually verify: open `/unified-graph-3d`, confirm 3D graph works.

```bash
git add frontend/src/components/graph/Graph3DRenderer.tsx frontend/src/pages/UnifiedGraph3D.tsx
git commit -m "refactor(ui): create Graph3DRenderer in shared location"
```

---

### Task 9: Build GraphToolbar.tsx

**Files:**
- Create: `frontend/src/components/graph/GraphToolbar.tsx`

- [ ] **Step 1: Create GraphToolbar.tsx**

Create `frontend/src/components/graph/GraphToolbar.tsx` with the unified toolbar:

```typescript
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { RotateCcw } from "lucide-react";
import type { SizeMode } from "@/lib/graph-utils";

type ViewMode = "2d" | "3d";

interface GraphToolbarProps {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  sizeMode: SizeMode;
  onSizeModeChange: (mode: SizeMode) => void;
  similarityThreshold: number;
  onSimilarityChange: (v: number) => void;
  clusterMinScore: number;
  onClusterMinScoreChange: (v: number) => void;
  minClusterSize: number;
  onMinClusterSizeChange: (v: number) => void;
  spacing: number;
  onSpacingChange: (v: number) => void;
  clusterTightness: number;
  onClusterTightnessChange: (v: number) => void;
  showTagOverlay: boolean;
  onShowTagOverlayChange: (v: boolean) => void;
  onReset: () => void;
}

export function GraphToolbar({ ... }: GraphToolbarProps) {
  return (
    <div className="absolute top-3 left-1/2 z-10 flex -translate-x-1/2 items-center gap-3 rounded-lg border border-border bg-card/90 px-4 py-2 shadow-lg backdrop-blur-sm">
      {/* View toggle */}
      <div className="flex rounded-md border border-border overflow-hidden">
        <button
          className={`px-2 py-1 text-xs ${viewMode === "2d" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent"}`}
          onClick={() => onViewModeChange("2d")}
        >2D</button>
        <button
          className={`px-2 py-1 text-xs ${viewMode === "3d" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent"}`}
          onClick={() => onViewModeChange("3d")}
        >3D</button>
      </div>

      <div className="h-4 w-px bg-border" />

      {/* Shared: Size mode */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Size</span>
        <Select value={sizeMode} onValueChange={(v) => onSizeModeChange(v as SizeMode)}>
          <SelectTrigger className="h-7 w-[120px] text-xs"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="connections">Connections</SelectItem>
            <SelectItem value="importance">Importance</SelectItem>
            <SelectItem value="uniform">Uniform</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="h-4 w-px bg-border" />

      {/* Shared: API params */}
      <Slider label="Edges" value={similarityThreshold} onChange={onSimilarityChange} min={0.3} max={0.95} step={0.05} />
      <Slider label="Cluster" value={clusterMinScore} onChange={onClusterMinScoreChange} min={0.2} max={0.8} step={0.05} />
      <Slider label="Min" value={minClusterSize} onChange={onMinClusterSizeChange} min={2} max={10} step={1} />

      <div className="h-4 w-px bg-border" />

      {/* View-specific */}
      {viewMode === "2d" ? (
        <>
          <Slider label="Space" value={spacing} onChange={onSpacingChange} min={100} max={500} step={25} />
          <Slider label="Tight" value={clusterTightness} onChange={onClusterTightnessChange} min={30} max={300} step={10} />
          <button
            className={`rounded px-2 py-1 text-xs ${showTagOverlay ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent"}`}
            onClick={() => onShowTagOverlayChange(!showTagOverlay)}
          >Tags</button>
        </>
      ) : (
        <Slider label="Space" value={spacing} onChange={onSpacingChange} min={30} max={200} step={10} />
      )}

      <div className="h-4 w-px bg-border" />

      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onReset} title="Reset to defaults">
        <RotateCcw className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}

function Slider({ label, value, onChange, min, max, step }: {
  label: string; value: number; onChange: (v: number) => void;
  min: number; max: number; step: number;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted-foreground">{label}</span>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-1 w-24 cursor-pointer accent-primary"
      />
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/graph/GraphToolbar.tsx
git commit -m "feat(ui): add unified GraphToolbar with view toggle"
```

---

### Task 10: Build unified UnifiedGraph.tsx

**Files:**
- Modify: `frontend/src/pages/UnifiedGraph.tsx` (rewrite as thin shell)

This is the assembly step — the page becomes a ~150-line shell that owns state and wires components together.

- [ ] **Step 1: Rewrite UnifiedGraph.tsx**

Replace the entire content of `frontend/src/pages/UnifiedGraph.tsx` with the unified page shell:

```typescript
import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { PanelRightClose, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUnifiedGraph } from "@/hooks/useApi";
import type { UnifiedMemory } from "@/hooks/useApi";
import { Graph2DRenderer } from "@/components/graph/Graph2DRenderer";
import { Graph3DRenderer } from "@/components/graph/Graph3DRenderer";
import { GraphToolbar } from "@/components/graph/GraphToolbar";
import { GraphDetailPanel } from "@/components/graph/GraphDetailPanel";
import { GraphFilterPanel } from "@/components/graph/GraphFilterPanel";
import { GraphSkeleton } from "@/components/graph/GraphSkeleton";
import { MiniGraph } from "@/components/graph/MiniGraph";
import { transformToGraphData, type SizeMode, type FilterState, matchesFilter } from "@/lib/graph-utils";
import { typeColor } from "@/lib/graph-colors";

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    if (Object.is(debounced, value)) return;
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay, debounced]);
  return debounced;
}

type ViewMode = "2d" | "3d";

export default function UnifiedGraph() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number } | null>(null);

  // View mode
  const [viewMode, setViewMode] = useState<ViewMode>("2d");
  const [graphReady, setGraphReady] = useState(false);

  // API params (shared, debounced)
  const [similarityThreshold, setSimilarityThreshold] = useState(0.5);
  const [clusterMinScore, setClusterMinScore] = useState(0.2);
  const [minClusterSize, setMinClusterSize] = useState(3);
  const debouncedSimilarity = useDebouncedValue(similarityThreshold, 500);
  const debouncedClusterScore = useDebouncedValue(clusterMinScore, 500);
  const debouncedMinSize = useDebouncedValue(minClusterSize, 500);

  // Layout (view-specific)
  const [sizeMode, setSizeMode] = useState<SizeMode>("connections");
  const [nodeSpacing, setNodeSpacing] = useState(100);
  const [clusterTightness, setClusterTightness] = useState(300);
  const [showTagOverlay, setShowTagOverlay] = useState(false);
  const [spacing3D, setSpacing3D] = useState(50);

  // Selection & UI
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [showPanel, setShowPanel] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  // Filters
  const [searchText, setSearchText] = useState("");
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set());
  const [selectedClusters, setSelectedClusters] = useState<Set<number>>(new Set());
  const debouncedSearchText = useDebouncedValue(searchText, 1000);

  // Data
  const { data, isLoading, error } = useUnifiedGraph(debouncedSimilarity, debouncedClusterScore, debouncedMinSize);

  // Filtered data (shared by both renderers)
  const filteredMemories = useMemo(() => {
    if (!data) return [];
    const filters: FilterState = { searchText: debouncedSearchText, selectedTags, selectedTypes, selectedSources, selectedClusters };
    const hasFilter = debouncedSearchText.trim() || selectedTags.size || selectedTypes.size || selectedSources.size || selectedClusters.size;
    if (!hasFilter) return data.memories;
    return data.memories.filter((m) => matchesFilter(m, filters));
  }, [data, debouncedSearchText, selectedTags, selectedTypes, selectedSources, selectedClusters]);

  // ... compute filteredClusters, filteredEdges, tagGroups, allTypes, allSources, allClusters
  // (same useMemo blocks as current UnifiedGraph.tsx)

  // 3D graph data
  const graphData3D = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    const filters: FilterState = { searchText: debouncedSearchText, selectedTags, selectedTypes, selectedSources, selectedClusters };
    return transformToGraphData(data, sizeMode, filters);
  }, [data, sizeMode, debouncedSearchText, selectedTags, selectedTypes, selectedSources, selectedClusters]);

  // Selected memory lookup
  const selectedMemory = useMemo(() =>
    selectedNodeId ? data?.memories.find(m => m.id === selectedNodeId) ?? null : null,
  [selectedNodeId, data]);

  // Reset graphReady on view switch
  useEffect(() => { setGraphReady(false); }, [viewMode]);

  // Handle node selection
  const handleNodeSelect = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId);
    if (nodeId) setShowPanel(true);
  }, []);

  // Resize observer
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) setDimensions({ width, height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  // Reset handler
  const handleReset = useCallback(() => {
    setSimilarityThreshold(0.5);
    setClusterMinScore(0.2);
    setMinClusterSize(3);
    setSizeMode("connections");
    setNodeSpacing(100);
    setClusterTightness(300);
    setShowTagOverlay(false);
    setSpacing3D(50);
  }, []);

  return (
    <div className="relative flex h-full">
      <div ref={containerRef} className="relative flex-1 min-w-0 overflow-hidden">
        {/* Renderer */}
        {dimensions && viewMode === "2d" && (
          <Graph2DRenderer
            data={data!}
            filteredMemories={filteredMemories}
            filteredClusters={filteredClusters}
            filteredEdges={filteredEdges}
            width={dimensions.width}
            height={dimensions.height}
            selectedNodeId={selectedNodeId}
            onNodeSelect={handleNodeSelect}
            onReady={() => setGraphReady(true)}
            sizeMode={sizeMode}
            spacing={nodeSpacing}
            clusterTightness={clusterTightness}
            showTagOverlay={showTagOverlay}
          />
        )}
        {dimensions && viewMode === "3d" && (
          <Graph3DRenderer
            graphData={graphData3D}
            width={dimensions.width}
            height={dimensions.height}
            selectedNodeId={selectedNodeId}
            onNodeSelect={handleNodeSelect}
            onReady={() => setGraphReady(true)}
            spacing={spacing3D}
          />
        )}

        {/* Loading overlay */}
        {(!graphReady || isLoading || error) && (
          <div className="absolute inset-0 z-20 overflow-hidden bg-[#0d1117]">
            {error ? (
              <div className="flex h-full items-center justify-center">
                <div className="text-destructive">Failed to load graph: {(error as Error).message}</div>
              </div>
            ) : (
              <GraphSkeleton label={isLoading ? "Loading graph data..." : "Rendering graph..."} />
            )}
          </div>
        )}

        {/* Controls (shown when graph ready) */}
        {graphReady && !error && (
          <>
            <GraphToolbar
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              sizeMode={sizeMode}
              onSizeModeChange={setSizeMode}
              similarityThreshold={similarityThreshold}
              onSimilarityChange={setSimilarityThreshold}
              clusterMinScore={clusterMinScore}
              onClusterMinScoreChange={setClusterMinScore}
              minClusterSize={minClusterSize}
              onMinClusterSizeChange={setMinClusterSize}
              spacing={viewMode === "2d" ? nodeSpacing : spacing3D}
              onSpacingChange={viewMode === "2d" ? setNodeSpacing : setSpacing3D}
              clusterTightness={clusterTightness}
              onClusterTightnessChange={setClusterTightness}
              showTagOverlay={showTagOverlay}
              onShowTagOverlayChange={setShowTagOverlay}
              onReset={handleReset}
            />

            <div className="absolute top-3 left-3 z-10">
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setShowFilters(f => !f)}>
                <Filter className="h-4 w-4" />
              </Button>
            </div>

            <div className="absolute top-3 right-3 z-10">
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setShowPanel(p => !p)}>
                <PanelRightClose className="h-4 w-4" />
              </Button>
            </div>
          </>
        )}

        {/* Filter panel */}
        {showFilters && (
          <div className="absolute top-14 left-3 z-30 w-72 max-h-[70vh] overflow-y-auto rounded-lg border border-border bg-card shadow-lg">
            <GraphFilterPanel
              tagGroups={tagGroups}
              allTypes={allTypes}
              allSources={allSources}
              allClusters={allClusters}
              clusterNames={data?.cluster_names ?? {}}
              selectedTags={selectedTags}
              selectedTypes={selectedTypes}
              selectedSources={selectedSources}
              selectedClusters={selectedClusters}
              searchText={searchText}
              onSearchChange={setSearchText}
              onTagToggle={(tag) => setSelectedTags(s => { const n = new Set(s); n.has(tag) ? n.delete(tag) : n.add(tag); return n; })}
              onTypeToggle={(t) => setSelectedTypes(s => { const n = new Set(s); n.has(t) ? n.delete(t) : n.add(t); return n; })}
              onSourceToggle={(src) => setSelectedSources(s => { const n = new Set(s); n.has(src) ? n.delete(src) : n.add(src); return n; })}
              onClusterToggle={(cid) => setSelectedClusters(s => { const n = new Set(s); n.has(cid) ? n.delete(cid) : n.add(cid); return n; })}
              onShowAll={() => { setSelectedTags(new Set()); setSelectedTypes(new Set()); setSelectedSources(new Set()); setSelectedClusters(new Set()); setSearchText(""); }}
            />
          </div>
        )}
      </div>

      {/* Right panel */}
      {showPanel && (
        <div className="w-72 shrink-0 overflow-y-auto border-l border-border bg-card">
          <GraphDetailPanel
            selectedMemory={selectedMemory}
            clusterName={data?.cluster_names?.[String(selectedMemory?.cluster)] ?? ""}
            nodeColor={typeColor(selectedMemory?.memory_type ?? null)}
            memories={filteredMemories}
            clusterNames={data?.cluster_names ?? {}}
            visibleEdgeCount={filteredEdges.length}
            onClose={() => { setSelectedNodeId(null); setShowPanel(false); }}
          >
            {viewMode === "2d" && selectedMemory && (
              <MiniGraph memoryId={selectedMemory.id} onNavigate={handleNodeSelect} />
            )}
          </GraphDetailPanel>
        </div>
      )}
    </div>
  );
}
```

Note: The `filteredClusters`, `filteredEdges`, `tagGroups`, `allTypes`, `allSources`, `allClusters` useMemo blocks from the original file need to be preserved in this rewrite. They compute derived data from `filteredMemories` and `data`.

- [ ] **Step 2: Verify and commit**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Manually verify: both 2D and 3D views work from `/unified-graph`.

```bash
git add frontend/src/pages/UnifiedGraph.tsx
git commit -m "feat(ui): unify 2D and 3D graph into single page with view toggle"
```

---

### Task 11: Route cleanup and file deletion

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`
- Delete: `frontend/src/pages/UnifiedGraph3D.tsx`
- Delete: `frontend/src/components/graph3d/ForceGraph3DWrapper.tsx`
- Delete: `frontend/src/components/graph3d/Graph3DDetailPanel.tsx`
- Delete: `frontend/src/components/graph3d/Graph3DToolbar.tsx`

- [ ] **Step 1: Remove 3D route from App.tsx**

Remove the import:
```typescript
import UnifiedGraph3D from "@/pages/UnifiedGraph3D";
```

Remove the route:
```tsx
<Route path="/unified-graph-3d" element={<UnifiedGraph3D />} />
```

- [ ] **Step 2: Remove 3D sidebar entry from Sidebar.tsx**

Remove `Box` from the lucide-react import.

Remove the nav item:
```typescript
{ to: "/unified-graph-3d", label: "3D Graph", icon: Box },
```

- [ ] **Step 3: Delete old files**

```bash
rm frontend/src/pages/UnifiedGraph3D.tsx
rm frontend/src/components/graph3d/ForceGraph3DWrapper.tsx
rm frontend/src/components/graph3d/Graph3DDetailPanel.tsx
rm frontend/src/components/graph3d/Graph3DToolbar.tsx
rmdir frontend/src/components/graph3d
```

- [ ] **Step 4: Verify and commit**

```bash
cd frontend && npx tsc --noEmit && npx vitest run && npm run build
```

Expected: All tests pass, build succeeds, no references to deleted files.

```bash
git add -u && git add frontend/src/App.tsx frontend/src/components/Sidebar.tsx
git commit -m "chore(ui): remove 3D graph page, route, and old components"
```

---

### Task 12: Final verification

- [ ] **Step 1: Run full test suite**

```bash
cd frontend && npx vitest run
```

Expected: All tests pass.

- [ ] **Step 2: Production build**

```bash
cd frontend && npm run build
```

Expected: Build succeeds.

- [ ] **Step 3: Manual verification checklist**

Open `http://localhost:3636/unified-graph`:

- [ ] 2D view loads with skeleton, then renders graph
- [ ] 3D view loads with skeleton, then renders graph
- [ ] View toggle switches between 2D and 3D
- [ ] Filters persist across view switches
- [ ] Slider changes persist across view switches
- [ ] Node selection persists across view switches
- [ ] Detail panel shows memory info when node selected
- [ ] Detail panel shows graph summary when no node selected
- [ ] Mini-graph appears in detail panel (2D view only)
- [ ] Filter panel opens/closes
- [ ] Search, tag, type, source, cluster filters work
- [ ] API param sliders (Edges, Cluster, Min) trigger data refetch
- [ ] 2D-specific: spacing, tightness, tag overlay work
- [ ] 3D-specific: spacing works
- [ ] Reset button restores all defaults
- [ ] `/unified-graph-3d` returns 404 (route removed)
- [ ] Sidebar has one "Unified Graph" entry, no "3D Graph"

- [ ] **Step 4: Commit if any fixes needed**

```bash
git add -u
git commit -m "fix(ui): polish unified graph integration"
```
