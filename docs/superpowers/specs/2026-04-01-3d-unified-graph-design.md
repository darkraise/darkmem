# 3D Unified Graph — Design Spec

## Goal

Add a 3D force-directed graph view alongside the existing 2D unified graph. The 3D view provides a richer spatial representation of memory nodes, making dense clusters easier to explore by spreading nodes into three dimensions. Clusters that overlap in 2D often separate cleanly with a third axis, and the natural orbit/fly-through camera interaction makes exploration more intuitive.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Library | `react-force-graph-3d` (3d-force-graph) | Purpose-built for 3D force-directed graphs; handles 1,000+ nodes; built-in orbit/zoom/click/hover/drag; exposes underlying Three.js scene for custom objects. Swap to `ngraph` engine if scaling past 3,000 nodes. |
| Coexistence with 2D | Separate page (`/unified-graph-3d`) | Cleaner separation — 2D graph is already ~2,000 lines. Avoids complicating existing code. Quick-nav link between the two views. |
| Backend changes | None | Same `/api/v1/graph/unified` endpoint. Same data model. |
| Component structure | Decomposed | Unlike the 2D monolith, split into focused sub-components to keep files manageable. |

## Feature Tiers

### Tier 1 — Must Have (Launch)

- Nodes colored by cluster, sized by connections or importance
- Similarity edges with opacity mapped to score
- 3D cluster visualization (translucent convex hulls)
- Node selection with detail panel
- Camera orbit, zoom, pan
- Double-click fly-to node

### Tier 2 — Nice to Have (Fast Follow)

- Search and highlight
- Filter by tags, type, source, cluster
- Focus mode (dim non-neighbors on select)
- Spacing and tightness sliders
- Cluster name labels (HTML sprites at centroids)

### Tier 3 — Later

- Mini-graph panel
- Tag overlay mode
- Size mode switcher (connections/importance/uniform)

## Architecture

### Route

New page at `/unified-graph-3d`, added to the sidebar navigation with a link to toggle between 2D and 3D views.

### Component Tree

```
App.tsx
└── Route: /unified-graph-3d
    └── UnifiedGraph3D.tsx            (page: layout, state, data fetching)
        ├── ForceGraph3DWrapper.tsx    (react-force-graph-3d + custom Three.js)
        ├── Graph3DToolbar.tsx         (controls: sizing, spacing, cluster)
        ├── Graph3DDetailPanel.tsx     (selected node info, metadata)
        └── Graph3DFilters.tsx         (tag, type, source, cluster filters)
```

### Data Flow

1. **Fetch** — `useUnifiedGraph` hook (existing in `useApi.ts`) calls `GET /api/v1/graph/unified` via React Query
2. **Transform** — Pure function `transformToGraphData()` converts `UnifiedGraphData` to `{ nodes: Node3D[], links: Link3D[] }` format expected by `react-force-graph-3d`. Applies active filters, computes node sizes, assigns cluster colors.
3. **Render** — `ForceGraph3DWrapper` passes transformed data to `ForceGraph3D` component. Custom `nodeThreeObject` callback renders styled spheres. Cluster hulls and labels injected into the Three.js scene via ref access.
4. **Interact** — Click/hover callbacks update React state, which drives the detail panel and focus mode dimming.

### Data Types

```typescript
interface Node3D {
  id: string;
  content: string;
  source: string;
  tags: string[];
  memoryType: string | null;
  importance: number;
  cluster: number;
  clusterName: string;
  color: string;       // hex from cluster palette
  size: number;        // computed radius
  x?: number;          // set by force simulation
  y?: number;
  z?: number;
}

interface Link3D {
  source: string;      // node id
  target: string;      // node id
  score: number;       // cosine similarity
}

interface GraphData3D {
  nodes: Node3D[];
  links: Link3D[];
}
```

## Visual Design

### Nodes

- **Shape:** Spheres (`SphereGeometry`) with `MeshPhongMaterial` for directional lighting response
- **Color:** Cluster-based palette, consistent with 2D graph colors. Unclustered nodes are gray (#8b949e)
- **Size:** Radius 2–6, mapped from importance or connection count (log scale)
- **Hover:** Subtle emissive glow + tooltip with content preview
- **Selected:** Brighter emissive, connected edges highlighted

### Edges

- **Color:** Cyan (#4CC9F0) — same as 2D graph
- **Opacity:** Mapped to similarity score (higher similarity = more opaque)
- **Directionality:** None (similarity is symmetric)
- **Focus mode:** Connected edges brighten to full opacity; non-connected fade to near-invisible

### Cluster Hulls

- **Geometry:** `ConvexGeometry` from Three.js wrapping positions of all nodes in the cluster
- **Material:** `MeshPhongMaterial` with transparency, opacity 0.08–0.12
- **Color:** Same cluster color as nodes, very low alpha
- **Update:** Recomputed when force layout stabilizes (listen to `onEngineStop`)
- **Labels:** LLM-generated cluster names rendered as CSS2DObject sprites at cluster centroid (Tier 2)

### Scene Environment

- **Background:** #0d1117 (matches app dark theme)
- **Lighting:** Ambient light (soft white) + one directional light for sphere shading
- **Fog:** Optional subtle depth fog for z-depth perception (togglable)
- **No grid or axes** — the graph is the space, not a chart

### Camera & Interaction

| Action | Input | Behavior |
|---|---|---|
| Orbit | Left-click drag | Rotate around graph center |
| Zoom | Scroll wheel | Dolly in/out |
| Pan | Right-click drag | Translate camera |
| Fly-to | Double-click node | Smooth camera animation to focus on node |
| Hover | Mouse over node | Tooltip + glow effect |
| Select | Click node | Open detail panel |
| Focus mode | On select | Dim non-neighbor nodes/edges, brighten connected (Tier 2) |
| Drag | Click-drag node | Reposition node in 3D (pins it in simulation) |

## Page Layout

```
┌─────────────────────────────────────────────────────────┐
│ [Toolbar]  Size: ● connections ○ importance   Spacing ━━│
├──────────────────────────────────────────┬──────────────┤
│                                          │              │
│                                          │  Detail      │
│           3D Force Graph                 │  Panel       │
│           (WebGL Canvas)                 │              │
│                                          │  - Content   │
│                                          │  - Tags      │
│                                          │  - Source     │
│                                          │  - Cluster   │
│                                          │              │
├──────────────────────────────────────────┴──────────────┤
│ [Filters]  Tags: [multi] Type: [multi] Source: [multi]  │
└─────────────────────────────────────────────────────────┘
```

- Toolbar and filters are collapsible (same pattern as 2D graph)
- Detail panel slides in from right on node selection
- 3D canvas fills remaining space

## Dependencies

New npm packages to add:

| Package | Purpose |
|---|---|
| `react-force-graph-3d` | React wrapper for 3d-force-graph |
| `three` | Three.js (peer dependency) |
| `three-stdlib` | ConvexGeometry and other utilities |

`three` may already be pulled in transitively by `react-force-graph-3d`, but should be listed explicitly for type imports and custom Three.js code.

## Scaling Strategy

| Node Count | Strategy |
|---|---|
| < 1,000 | Default d3-force-3d, individual sphere meshes |
| 1,000–3,000 | Tune force parameters, reduce edge count via threshold |
| 3,000–8,000 | Swap to `ngraph` force engine (one-line config) |
| 8,000+ | Consider InstancedMesh for nodes, edge bundling, or raw Three.js migration |

## Testing

- Manual visual testing for render correctness, camera behavior, and interaction
- Unit tests for `transformToGraphData()` (pure function, easy to test)
- Integration test: verify the page loads, fetches data, and renders without errors

## Out of Scope

- Backend API changes
- VR/AR mode
- Node editing or creation from the 3D view
- Real-time collaborative viewing
- WebGPU rendering
