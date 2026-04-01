# 3D Unified Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 3D force-directed graph page at `/unified-graph-3d` using `react-force-graph-3d`, rendering the same unified memory data as the 2D graph with cluster hulls, node selection, and camera controls.

**Architecture:** New page component (`UnifiedGraph3D.tsx`) composed of focused sub-components — `ForceGraph3DWrapper` (rendering), `Graph3DToolbar` (controls), `Graph3DDetailPanel` (selection info). A shared `graph-utils.ts` module provides the data transform, types, and color constants. The backend is untouched — same `/api/v1/graph/unified` endpoint.

**Tech Stack:** React 19, TypeScript, react-force-graph-3d, Three.js, Vite, Tailwind CSS 4, shadcn/ui, vitest

---

## File Structure

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `frontend/src/lib/graph-utils.ts` | Shared types, color palette, sizing, transform function |
| Create | `frontend/src/components/graph3d/ForceGraph3DWrapper.tsx` | 3D graph rendering, camera, interaction |
| Create | `frontend/src/components/graph3d/Graph3DDetailPanel.tsx` | Selected node detail display |
| Create | `frontend/src/components/graph3d/Graph3DToolbar.tsx` | Size mode, spacing controls |
| Create | `frontend/src/pages/UnifiedGraph3D.tsx` | Page layout, state, data fetching |
| Create | `frontend/src/__tests__/graph-utils.test.ts` | Unit tests for transform function |
| Modify | `frontend/src/App.tsx` | Add `/unified-graph-3d` route |
| Modify | `frontend/src/components/Sidebar.tsx` | Add nav item |
| Modify | `frontend/package.json` | Add dependencies |
| Modify | `frontend/vite.config.ts` | Add vitest config |

---

### Task 1: Install dependencies

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`

- [ ] **Step 1: Install runtime dependencies**

Run from `frontend/`:
```bash
npm install react-force-graph-3d three
```

Expected: `react-force-graph-3d` and `three` added to `dependencies` in package.json.

- [ ] **Step 2: Install dev dependencies**

```bash
npm install -D @types/three vitest @vitest/ui
```

- [ ] **Step 3: Add vitest config to vite.config.ts**

In `frontend/vite.config.ts`, add `test` block and the `/// <reference>` triple-slash directive. The current file looks like:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  server: {
    port: 3636,
    proxy: {
      "/api": { target: "http://localhost:8000" },
      "/health": { target: "http://localhost:8000" },
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
```

Add the triple-slash directive at the very top of the file (before imports) and the `test` field inside `defineConfig`:

```typescript
/// <reference types="vitest/config" />
```

```typescript
  test: {
    environment: "node",
    include: ["src/__tests__/**/*.test.ts"],
  },
```

The result should be:

```typescript
/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },
  test: {
    environment: "node",
    include: ["src/__tests__/**/*.test.ts"],
  },
  server: {
    port: 3636,
    proxy: {
      "/api": { target: "http://localhost:8000" },
      "/health": { target: "http://localhost:8000" },
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
```

- [ ] **Step 4: Verify build still works**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts
git commit -m "chore(ui): add react-force-graph-3d and vitest deps"
```

---

### Task 2: Create graph utilities module

**Files:**
- Create: `frontend/src/lib/graph-utils.ts`

This module provides shared types, color palette, and sizing logic for the 3D graph. The constants are duplicated from `UnifiedGraph.tsx` (not extracted — the 2D file is untouched).

- [ ] **Step 1: Create the graph-utils module**

Create `frontend/src/lib/graph-utils.ts`:

```typescript
import type { UnifiedMemory, UnifiedGraphData } from "@/hooks/useApi";

export type SizeMode = "connections" | "importance" | "uniform";

export interface Node3D {
  id: string;
  content: string;
  source: string;
  tags: string[];
  memoryType: string | null;
  importance: number;
  cluster: number;
  clusterName: string;
  color: string;
  val: number;
  x?: number;
  y?: number;
  z?: number;
  fx?: number;
  fy?: number;
  fz?: number;
}

export interface Link3D {
  source: string;
  target: string;
  score: number;
}

export interface GraphData3D {
  nodes: Node3D[];
  links: Link3D[];
}

export interface FilterState {
  searchText: string;
  selectedTags: Set<string>;
  selectedTypes: Set<string>;
  selectedSources: Set<string>;
  selectedClusters: Set<number>;
}

export const CLUSTER_PALETTE = [
  "#a855f7", "#3fb950", "#f97316", "#06b6d4",
  "#ec4899", "#eab308", "#6366f1", "#14b8a6",
  "#f43f5e", "#84cc16", "#8b5cf6", "#0ea5e9",
];

export const UNCLUSTERED_COLOR = "#8b949e";

export function clusterColor(clusterId: number): string {
  if (clusterId < 0) return UNCLUSTERED_COLOR;
  return CLUSTER_PALETTE[clusterId % CLUSTER_PALETTE.length];
}

export function computeNodeVal(
  mode: SizeMode,
  connectionCount: number,
  importance: number,
): number {
  if (mode === "uniform") return 2;
  if (mode === "importance") return 1 + importance * 5;
  return 1 + Math.min(5, Math.log1p(connectionCount) * 1.5);
}

function matchesFilter(memory: UnifiedMemory, filters: FilterState): boolean {
  if (filters.searchText) {
    const term = filters.searchText.toLowerCase();
    if (!memory.content.toLowerCase().includes(term)) return false;
  }
  if (filters.selectedTags.size > 0) {
    if (!memory.tags.some((t) => filters.selectedTags.has(t))) return false;
  }
  if (filters.selectedTypes.size > 0) {
    if (!memory.memory_type || !filters.selectedTypes.has(memory.memory_type))
      return false;
  }
  if (filters.selectedSources.size > 0) {
    if (!filters.selectedSources.has(memory.source)) return false;
  }
  if (filters.selectedClusters.size > 0) {
    if (!filters.selectedClusters.has(memory.cluster)) return false;
  }
  return true;
}

export function transformToGraphData(
  data: UnifiedGraphData,
  sizeMode: SizeMode,
  filters: FilterState,
): GraphData3D {
  const edgeCountMap = new Map<string, number>();
  for (const edge of data.similarity_edges) {
    edgeCountMap.set(edge.source, (edgeCountMap.get(edge.source) ?? 0) + 1);
    edgeCountMap.set(edge.target, (edgeCountMap.get(edge.target) ?? 0) + 1);
  }

  const filteredMemories = data.memories.filter((m) =>
    matchesFilter(m, filters),
  );
  const filteredIds = new Set(filteredMemories.map((m) => m.id));

  const nodes: Node3D[] = filteredMemories.map((m) => ({
    id: m.id,
    content: m.content,
    source: m.source,
    tags: m.tags,
    memoryType: m.memory_type,
    importance: m.importance,
    cluster: m.cluster,
    clusterName: data.cluster_names[String(m.cluster)] ?? "",
    color: clusterColor(m.cluster),
    val: computeNodeVal(sizeMode, edgeCountMap.get(m.id) ?? 0, m.importance),
  }));

  const links: Link3D[] = data.similarity_edges
    .filter((e) => filteredIds.has(e.source) && filteredIds.has(e.target))
    .map((e) => ({ source: e.source, target: e.target, score: e.score }));

  return { nodes, links };
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors related to `graph-utils.ts`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/graph-utils.ts
git commit -m "feat(ui): add graph utilities module for 3D graph"
```

---

### Task 3: Test the transform function

**Files:**
- Create: `frontend/src/__tests__/graph-utils.test.ts`

- [ ] **Step 1: Write tests**

Create `frontend/src/__tests__/graph-utils.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import {
  transformToGraphData,
  clusterColor,
  computeNodeVal,
  CLUSTER_PALETTE,
  UNCLUSTERED_COLOR,
} from "@/lib/graph-utils";
import type { UnifiedGraphData } from "@/hooks/useApi";
import type { FilterState } from "@/lib/graph-utils";

const emptyFilters: FilterState = {
  searchText: "",
  selectedTags: new Set(),
  selectedTypes: new Set(),
  selectedSources: new Set(),
  selectedClusters: new Set(),
};

const sampleData: UnifiedGraphData = {
  memories: [
    { id: "a", content: "Alpha memory", source: "mem0", tags: ["test"], memory_type: "fact", importance: 0.8, cluster: 0 },
    { id: "b", content: "Beta memory", source: "memora", tags: ["debug"], memory_type: "debug", importance: 0.3, cluster: 0 },
    { id: "c", content: "Gamma memory", source: "mem0", tags: ["test"], memory_type: "fact", importance: 0.5, cluster: 1 },
    { id: "d", content: "Delta orphan", source: "mem0", tags: [], memory_type: null, importance: 0.1, cluster: -1 },
  ],
  clusters: { "0": ["a", "b"], "1": ["c"] },
  cluster_names: { "0": "Test Cluster", "1": "Gamma Cluster" },
  similarity_edges: [
    { source: "a", target: "b", score: 0.9 },
    { source: "a", target: "c", score: 0.8 },
    { source: "b", target: "c", score: 0.7 },
  ],
};

describe("clusterColor", () => {
  it("returns palette color for valid cluster", () => {
    expect(clusterColor(0)).toBe(CLUSTER_PALETTE[0]);
    expect(clusterColor(3)).toBe(CLUSTER_PALETTE[3]);
  });

  it("wraps around palette for large cluster IDs", () => {
    expect(clusterColor(12)).toBe(CLUSTER_PALETTE[0]);
  });

  it("returns gray for unclustered (-1)", () => {
    expect(clusterColor(-1)).toBe(UNCLUSTERED_COLOR);
  });
});

describe("computeNodeVal", () => {
  it("returns fixed value for uniform mode", () => {
    expect(computeNodeVal("uniform", 10, 0.9)).toBe(2);
  });

  it("scales by importance", () => {
    const low = computeNodeVal("importance", 0, 0.1);
    const high = computeNodeVal("importance", 0, 0.9);
    expect(high).toBeGreaterThan(low);
  });

  it("scales by connections with log dampening", () => {
    const few = computeNodeVal("connections", 1, 0);
    const many = computeNodeVal("connections", 100, 0);
    expect(many).toBeGreaterThan(few);
  });
});

describe("transformToGraphData", () => {
  it("maps all memories to nodes with no filters", () => {
    const result = transformToGraphData(sampleData, "connections", emptyFilters);
    expect(result.nodes).toHaveLength(4);
    expect(result.links).toHaveLength(3);
  });

  it("assigns cluster color to nodes", () => {
    const result = transformToGraphData(sampleData, "connections", emptyFilters);
    const nodeA = result.nodes.find((n) => n.id === "a")!;
    expect(nodeA.color).toBe(CLUSTER_PALETTE[0]);
    const nodeD = result.nodes.find((n) => n.id === "d")!;
    expect(nodeD.color).toBe(UNCLUSTERED_COLOR);
  });

  it("resolves cluster names", () => {
    const result = transformToGraphData(sampleData, "connections", emptyFilters);
    const nodeA = result.nodes.find((n) => n.id === "a")!;
    expect(nodeA.clusterName).toBe("Test Cluster");
    const nodeD = result.nodes.find((n) => n.id === "d")!;
    expect(nodeD.clusterName).toBe("");
  });

  it("filters by search text", () => {
    const filters: FilterState = { ...emptyFilters, searchText: "alpha" };
    const result = transformToGraphData(sampleData, "connections", filters);
    expect(result.nodes).toHaveLength(1);
    expect(result.nodes[0].id).toBe("a");
  });

  it("filters by source", () => {
    const filters: FilterState = { ...emptyFilters, selectedSources: new Set(["memora"]) };
    const result = transformToGraphData(sampleData, "connections", filters);
    expect(result.nodes).toHaveLength(1);
    expect(result.nodes[0].id).toBe("b");
  });

  it("filters by cluster", () => {
    const filters: FilterState = { ...emptyFilters, selectedClusters: new Set([1]) };
    const result = transformToGraphData(sampleData, "connections", filters);
    expect(result.nodes).toHaveLength(1);
    expect(result.nodes[0].id).toBe("c");
  });

  it("excludes edges where either node is filtered out", () => {
    const filters: FilterState = { ...emptyFilters, selectedSources: new Set(["mem0"]) };
    const result = transformToGraphData(sampleData, "connections", filters);
    expect(result.nodes).toHaveLength(3);
    expect(result.links).toHaveLength(1);
    expect(result.links[0].source).toBe("a");
    expect(result.links[0].target).toBe("c");
  });

  it("filters by tags", () => {
    const filters: FilterState = { ...emptyFilters, selectedTags: new Set(["debug"]) };
    const result = transformToGraphData(sampleData, "connections", filters);
    expect(result.nodes).toHaveLength(1);
    expect(result.nodes[0].id).toBe("b");
  });

  it("filters by type", () => {
    const filters: FilterState = { ...emptyFilters, selectedTypes: new Set(["fact"]) };
    const result = transformToGraphData(sampleData, "connections", filters);
    expect(result.nodes).toHaveLength(2);
    expect(result.nodes.map((n) => n.id).sort()).toEqual(["a", "c"]);
  });
});
```

- [ ] **Step 2: Run tests**

```bash
cd frontend && npx vitest run
```

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/__tests__/graph-utils.test.ts
git commit -m "test(ui): add unit tests for graph transform function"
```

---

### Task 4: Create ForceGraph3DWrapper component

**Files:**
- Create: `frontend/src/components/graph3d/ForceGraph3DWrapper.tsx`

This component wraps `react-force-graph-3d` with custom node rendering, edge styling, hover/click interaction, and cluster hull rendering.

- [ ] **Step 1: Create the component**

Create `frontend/src/components/graph3d/ForceGraph3DWrapper.tsx`:

```typescript
import { useRef, useCallback, useEffect } from "react";
import ForceGraph3D from "react-force-graph-3d";
import * as THREE from "three";
import { ConvexGeometry } from "three/examples/jsm/geometries/ConvexGeometry.js";
import type { Node3D, Link3D, GraphData3D } from "@/lib/graph-utils";

interface ForceGraph3DWrapperProps {
  graphData: GraphData3D;
  width: number;
  height: number;
  spacing: number;
  selectedNodeId: string | null;
  onNodeSelect: (node: Node3D | null) => void;
}

export function ForceGraph3DWrapper({
  graphData,
  width,
  height,
  spacing,
  selectedNodeId,
  onNodeSelect,
}: ForceGraph3DWrapperProps) {
  const fgRef = useRef<any>(null);
  const hoveredRef = useRef<Node3D | null>(null);
  const selectedRef = useRef<Node3D | null>(null);
  const hullMeshesRef = useRef<THREE.Mesh[]>([]);
  const clickTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (!fgRef.current) return;
    fgRef.current.d3Force("charge")?.strength(-120);
    fgRef.current.d3Force("link")?.distance(spacing);
  }, [graphData, spacing]);

  useEffect(() => {
    if (!fgRef.current) return;
    fgRef.current.d3Force("link")?.distance(spacing);
    fgRef.current.d3ReheatSimulation();
  }, [spacing]);

  useEffect(() => {
    // Reset previous selected glow
    if (selectedRef.current?.__threeObj) {
      const mat = (selectedRef.current as any).__threeObj
        .material as THREE.MeshPhongMaterial;
      mat.emissiveIntensity = 0.1;
    }
    // Apply glow to newly selected node
    const newSel = graphData.nodes.find((n) => n.id === selectedNodeId);
    if (newSel?.__threeObj) {
      const mat = (newSel as any).__threeObj
        .material as THREE.MeshPhongMaterial;
      mat.emissiveIntensity = 0.6;
    }
    selectedRef.current = newSel ?? null;
  }, [selectedNodeId, graphData.nodes]);

  const buildClusterHulls = useCallback(() => {
    const scene = fgRef.current?.scene();
    if (!scene) return;

    hullMeshesRef.current.forEach((m) => {
      m.geometry.dispose();
      (m.material as THREE.Material).dispose();
      scene.remove(m);
    });
    hullMeshesRef.current = [];

    const clusterNodes = new Map<number, Node3D[]>();
    for (const node of graphData.nodes) {
      if (node.cluster >= 0 && node.x != null) {
        const group = clusterNodes.get(node.cluster) ?? [];
        group.push(node);
        clusterNodes.set(node.cluster, group);
      }
    }

    clusterNodes.forEach((nodes) => {
      if (nodes.length < 4) return;
      const points = nodes.map(
        (n) => new THREE.Vector3(n.x!, n.y!, n.z!),
      );
      try {
        const geometry = new ConvexGeometry(points);
        const material = new THREE.MeshPhongMaterial({
          color: nodes[0].color,
          transparent: true,
          opacity: 0.08,
          side: THREE.DoubleSide,
          depthWrite: false,
        });
        const mesh = new THREE.Mesh(geometry, material);
        scene.add(mesh);
        hullMeshesRef.current.push(mesh);
      } catch {
        // ConvexGeometry can throw if points are coplanar
      }
    });
  }, [graphData]);

  const handleNodeClick = useCallback(
    (node: Node3D) => {
      if (clickTimerRef.current) {
        clearTimeout(clickTimerRef.current);
        clickTimerRef.current = null;
        const distance = 80;
        const distRatio =
          1 + distance / Math.hypot(node.x!, node.y!, node.z!);
        fgRef.current?.cameraPosition(
          {
            x: node.x! * distRatio,
            y: node.y! * distRatio,
            z: node.z! * distRatio,
          },
          node,
          2000,
        );
      } else {
        clickTimerRef.current = window.setTimeout(() => {
          clickTimerRef.current = null;
          onNodeSelect(node);
        }, 300);
      }
    },
    [onNodeSelect],
  );

  const handleNodeHover = useCallback((node: Node3D | null) => {
    const prev = hoveredRef.current;
    if (prev?.__threeObj) {
      const mat = (prev as any).__threeObj.material as THREE.MeshPhongMaterial;
      mat.emissiveIntensity = 0.1;
    }
    if (node?.__threeObj) {
      const mat = (node as any).__threeObj.material as THREE.MeshPhongMaterial;
      mat.emissiveIntensity = 0.4;
    }
    hoveredRef.current = node;
  }, []);

  const nodeThreeObject = useCallback((node: Node3D) => {
    const geometry = new THREE.SphereGeometry(node.val, 16, 12);
    const material = new THREE.MeshPhongMaterial({
      color: node.color,
      emissive: node.color,
      emissiveIntensity: 0.1,
      transparent: true,
      opacity: 0.9,
    });
    return new THREE.Mesh(geometry, material);
  }, []);

  const linkColor = useCallback(
    (link: Link3D) =>
      `rgba(76, 201, 240, ${(0.15 + link.score * 0.6).toFixed(2)})`,
    [],
  );

  const nodeLabel = useCallback(
    (node: Node3D) =>
      `<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:8px 12px;max-width:300px;color:#c9d1d9;font-size:12px;">${node.content.slice(0, 150)}${node.content.length > 150 ? "…" : ""}</div>`,
    [],
  );

  return (
    <ForceGraph3D
      ref={fgRef}
      graphData={graphData}
      width={width}
      height={height}
      backgroundColor="#0d1117"
      nodeThreeObject={nodeThreeObject}
      nodeThreeObjectExtend={false}
      nodeLabel={nodeLabel}
      linkColor={linkColor}
      linkWidth={0.3}
      linkOpacity={0.6}
      onNodeClick={handleNodeClick}
      onNodeHover={handleNodeHover}
      onNodeDragEnd={(node: Node3D) => {
        node.fx = node.x;
        node.fy = node.y;
        node.fz = node.z;
      }}
      onEngineStop={buildClusterHulls}
      d3AlphaDecay={0.02}
      d3VelocityDecay={0.3}
      warmupTicks={100}
      cooldownTicks={200}
      controlType="orbit"
    />
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

If the `ConvexGeometry` import fails with a type error, change the import to:

```typescript
// @ts-expect-error - Three.js examples lack types in some setups
import { ConvexGeometry } from "three/examples/jsm/geometries/ConvexGeometry.js";
```

If the runtime import fails (Vite can't resolve the path), install `three-stdlib` as a fallback:

```bash
npm install three-stdlib
```

Then change the import to:

```typescript
import { ConvexGeometry } from "three-stdlib";
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/graph3d/ForceGraph3DWrapper.tsx
git commit -m "feat(ui): add ForceGraph3DWrapper component"
```

---

### Task 5: Create Graph3DDetailPanel component

**Files:**
- Create: `frontend/src/components/graph3d/Graph3DDetailPanel.tsx`

Shows selected node details — content, tags, source, type, importance, cluster.

- [ ] **Step 1: Create the component**

Create `frontend/src/components/graph3d/Graph3DDetailPanel.tsx`:

```typescript
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Node3D, GraphData3D } from "@/lib/graph-utils";
import { clusterColor } from "@/lib/graph-utils";

interface Graph3DDetailPanelProps {
  selectedNode: Node3D | null;
  graphData: GraphData3D;
  onClose: () => void;
}

export function Graph3DDetailPanel({
  selectedNode,
  graphData,
  onClose,
}: Graph3DDetailPanelProps) {
  if (!selectedNode) {
    return <GraphSummary graphData={graphData} />;
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
        {selectedNode.content}
      </p>

      {selectedNode.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selectedNode.tags.map((tag) => (
            <span
              key={tag}
              className="rounded-md bg-accent px-2 py-0.5 text-xs text-foreground"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <span className="text-muted-foreground">Source</span>
          <p className="text-foreground font-medium">{selectedNode.source}</p>
        </div>
        {selectedNode.memoryType && (
          <div>
            <span className="text-muted-foreground">Type</span>
            <p className="text-foreground font-medium">{selectedNode.memoryType}</p>
          </div>
        )}
        <div>
          <span className="text-muted-foreground">Importance</span>
          <p className="text-foreground font-medium">
            {selectedNode.importance.toFixed(2)}
          </p>
        </div>
        {selectedNode.cluster >= 0 && (
          <div>
            <span className="text-muted-foreground">Cluster</span>
            <div className="flex items-center gap-1.5">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: selectedNode.color }}
              />
              <span className="text-foreground font-medium">
                {selectedNode.clusterName || `#${selectedNode.cluster}`}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function GraphSummary({ graphData }: { graphData: GraphData3D }) {
  const clusterCounts = new Map<number, number>();
  for (const node of graphData.nodes) {
    if (node.cluster >= 0) {
      clusterCounts.set(node.cluster, (clusterCounts.get(node.cluster) ?? 0) + 1);
    }
  }

  return (
    <div className="flex flex-col gap-4 p-4">
      <h3 className="text-sm font-semibold text-foreground">Graph Summary</h3>
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="rounded-md bg-accent p-2">
          <span className="text-muted-foreground">Nodes</span>
          <p className="text-lg font-bold text-foreground">{graphData.nodes.length}</p>
        </div>
        <div className="rounded-md bg-accent p-2">
          <span className="text-muted-foreground">Edges</span>
          <p className="text-lg font-bold text-foreground">{graphData.links.length}</p>
        </div>
        <div className="rounded-md bg-accent p-2">
          <span className="text-muted-foreground">Clusters</span>
          <p className="text-lg font-bold text-foreground">{clusterCounts.size}</p>
        </div>
      </div>

      {clusterCounts.size > 0 && (
        <div className="flex flex-col gap-1.5">
          <span className="text-xs text-muted-foreground">Clusters</span>
          {[...clusterCounts.entries()]
            .sort((a, b) => b[1] - a[1])
            .map(([id, count]) => {
              const node = graphData.nodes.find((n) => n.cluster === id);
              return (
                <div key={id} className="flex items-center gap-2 text-xs">
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: clusterColor(id) }}
                  />
                  <span className="text-foreground">
                    {node?.clusterName || `Cluster ${id}`}
                  </span>
                  <span className="text-muted-foreground ml-auto">{count}</span>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/graph3d/Graph3DDetailPanel.tsx
git commit -m "feat(ui): add Graph3DDetailPanel component"
```

---

### Task 6: Create Graph3DToolbar component

**Files:**
- Create: `frontend/src/components/graph3d/Graph3DToolbar.tsx`

Provides size mode selector and spacing slider. Mirrors the 2D toolbar style but only includes Tier 1 controls.

- [ ] **Step 1: Create the component**

Create `frontend/src/components/graph3d/Graph3DToolbar.tsx`:

```typescript
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { RotateCcw } from "lucide-react";
import type { SizeMode } from "@/lib/graph-utils";

interface Graph3DToolbarProps {
  sizeMode: SizeMode;
  onSizeModeChange: (mode: SizeMode) => void;
  spacing: number;
  onSpacingChange: (value: number) => void;
}

export function Graph3DToolbar({
  sizeMode,
  onSizeModeChange,
  spacing,
  onSpacingChange,
}: Graph3DToolbarProps) {
  return (
    <div className="absolute top-3 left-1/2 z-10 flex -translate-x-1/2 items-center gap-3 rounded-lg border border-border bg-card/90 px-4 py-2 shadow-lg backdrop-blur-sm">
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Size</span>
        <Select value={sizeMode} onValueChange={(v) => onSizeModeChange(v as SizeMode)}>
          <SelectTrigger className="h-7 w-[120px] text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="connections">Connections</SelectItem>
            <SelectItem value="importance">Importance</SelectItem>
            <SelectItem value="uniform">Uniform</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="h-4 w-px bg-border" />

      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Space</span>
        <input
          type="range"
          min={30}
          max={200}
          step={10}
          value={spacing}
          onChange={(e) => onSpacingChange(Number(e.target.value))}
          className="h-1 w-24 cursor-pointer accent-primary"
        />
      </div>

      <div className="h-4 w-px bg-border" />

      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7"
        onClick={() => {
          onSizeModeChange("connections");
          onSpacingChange(50);
        }}
        title="Reset to defaults"
      >
        <RotateCcw className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/graph3d/Graph3DToolbar.tsx
git commit -m "feat(ui): add Graph3DToolbar component"
```

---

### Task 7: Create UnifiedGraph3D page component

**Files:**
- Create: `frontend/src/pages/UnifiedGraph3D.tsx`

Page component that wires data fetching, state management, and sub-components together.

- [ ] **Step 1: Create the page component**

Create `frontend/src/pages/UnifiedGraph3D.tsx`:

```typescript
import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { PanelRightClose, Hexagon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUnifiedGraph } from "@/hooks/useApi";
import { ForceGraph3DWrapper } from "@/components/graph3d/ForceGraph3DWrapper";
import { Graph3DDetailPanel } from "@/components/graph3d/Graph3DDetailPanel";
import { Graph3DToolbar } from "@/components/graph3d/Graph3DToolbar";
import {
  transformToGraphData,
  type Node3D,
  type SizeMode,
  type FilterState,
} from "@/lib/graph-utils";

export default function UnifiedGraph3D() {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  const [sizeMode, setSizeMode] = useState<SizeMode>("connections");
  const [spacing, setSpacing] = useState(50);
  const [selectedNode, setSelectedNode] = useState<Node3D | null>(null);
  const [showPanel, setShowPanel] = useState(false);

  const [filters] = useState<FilterState>({
    searchText: "",
    selectedTags: new Set(),
    selectedTypes: new Set(),
    selectedSources: new Set(),
    selectedClusters: new Set(),
  });

  const { data, isLoading, error } = useUnifiedGraph();

  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    return transformToGraphData(data, sizeMode, filters);
  }, [data, sizeMode, filters]);

  const handleNodeSelect = useCallback((node: Node3D | null) => {
    setSelectedNode(node);
    if (node) setShowPanel(true);
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-muted-foreground">Loading graph data…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-destructive">
          Failed to load graph: {(error as Error).message}
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex h-full">
      <div ref={containerRef} className="relative flex-1">
        <Graph3DToolbar
          sizeMode={sizeMode}
          onSizeModeChange={setSizeMode}
          spacing={spacing}
          onSpacingChange={setSpacing}
        />

        <div className="absolute top-3 left-3 z-10 flex gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            onClick={() => navigate("/unified-graph")}
            title="Switch to 2D view"
          >
            <Hexagon className="mr-1.5 h-3.5 w-3.5" />
            2D View
          </Button>
        </div>

        <div className="absolute top-3 right-3 z-10">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setShowPanel((p) => !p)}
          >
            <PanelRightClose className="h-4 w-4" />
          </Button>
        </div>

        <ForceGraph3DWrapper
          graphData={graphData}
          width={dimensions.width}
          height={dimensions.height}
          spacing={spacing}
          selectedNodeId={selectedNode?.id ?? null}
          onNodeSelect={handleNodeSelect}
        />
      </div>

      {showPanel && (
        <div className="w-72 shrink-0 overflow-y-auto border-l border-border bg-card">
          <Graph3DDetailPanel
            selectedNode={selectedNode}
            graphData={graphData}
            onClose={() => {
              setSelectedNode(null);
              setShowPanel(false);
            }}
          />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/UnifiedGraph3D.tsx
git commit -m "feat(ui): add UnifiedGraph3D page component"
```

---

### Task 8: Add route and sidebar navigation

**Files:**
- Modify: `frontend/src/App.tsx:1-46`
- Modify: `frontend/src/components/Sidebar.tsx:25-37`

- [ ] **Step 1: Add import and route to App.tsx**

In `frontend/src/App.tsx`, add the import alongside other page imports (around line 10-20):

```typescript
import UnifiedGraph3D from "@/pages/UnifiedGraph3D";
```

Add the route inside `<Routes>`, after the `/unified-graph` route (around line 39):

```tsx
<Route path="/unified-graph-3d" element={<UnifiedGraph3D />} />
```

- [ ] **Step 2: Add sidebar nav item**

In `frontend/src/components/Sidebar.tsx`, add the `Box` import from lucide-react (line 1 area):

```typescript
import { Box } from "lucide-react";
```

Add the nav item in the `navItems` array, right after the `Unified Graph` entry (after line 29):

```typescript
{ to: "/unified-graph-3d", label: "3D Graph", icon: Box },
```

The result should be:

```typescript
{ to: "/unified-graph", label: "Unified Graph", icon: Hexagon },
{ to: "/unified-graph-3d", label: "3D Graph", icon: Box },
```

- [ ] **Step 3: Verify TypeScript compiles and build succeeds**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Sidebar.tsx
git commit -m "feat(ui): add 3D graph route and sidebar navigation"
```

---

### Task 9: Integration verification

**Files:** None (manual testing)

- [ ] **Step 1: Start the dev server**

```bash
cd frontend && npm run dev
```

Expected: Vite dev server starts on port 3636.

- [ ] **Step 2: Open the app and navigate to 3D Graph**

Open `http://localhost:3636/unified-graph-3d` in the browser.

Verify:
- The sidebar shows the "3D Graph" nav item with a cube icon
- The page loads and shows "Loading graph data…" then the 3D graph
- Nodes render as colored spheres (cluster-colored)
- Edges render as cyan lines
- The "2D View" button in the top-left navigates to `/unified-graph`
- Orbit: left-click drag rotates the camera
- Zoom: scroll wheel zooms
- Pan: right-click drag pans
- Hover: nodes show tooltip with content preview + glow effect
- Click: selects node, opens detail panel with memory info
- Double-click: flies camera to the node
- Cluster hulls appear as translucent volumes after simulation stabilizes
- Toolbar: size mode selector changes node sizes
- Toolbar: spacing slider affects layout
- Detail panel: shows graph summary when no node selected, memory detail when selected
- Reset button restores defaults

- [ ] **Step 3: Run tests one final time**

```bash
cd frontend && npx vitest run
```

Expected: All tests pass.

- [ ] **Step 4: Final commit if any fixes were needed**

If any fixes were made during verification:

```bash
git add -u
git commit -m "fix(ui): polish 3D graph integration"
```

---

## Notes

- **ConvexGeometry import:** If `three/examples/jsm/geometries/ConvexGeometry.js` doesn't resolve with Vite, install `three-stdlib` and import from there instead.
- **`__threeObj` property:** This is an internal property of react-force-graph that stores the Three.js Object3D on each node. It's stable but undocumented — if a future version removes it, the hover glow logic in `ForceGraph3DWrapper` will need adjustment.
- **Spacing slider:** Wired via `useEffect` in `ForceGraph3DWrapper` — updates `d3Force('link').distance()` and reheats the simulation.
