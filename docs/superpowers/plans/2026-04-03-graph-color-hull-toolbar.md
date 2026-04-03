# Graph Color Toggle, Hull Mode & Toolbar Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add color mode toggle (type/cluster/tag), expand hull mode (none/cluster/tag/source), replace ad-hoc palettes with a Tailwind 200+400+600 tri-shade system of 51 colors, reorganize the toolbar into top-level toggles plus a floating settings popover, and achieve full 2D/3D parity.

**Architecture:** A centralized color/hull engine in `graph-colors.ts` and `graph-geometry.ts` replaces scattered per-renderer logic. Both renderers consume `resolveNodeColor()` and `computeHullGroups()`. The toolbar splits into always-visible toggles and a collapsible settings popover.

**Tech Stack:** React, TypeScript, Sigma.js (2D), react-force-graph-3d + THREE.js (3D), graphology, Tailwind CSS

**Spec:** `docs/superpowers/specs/2026-04-03-graph-color-hull-toolbar-design.md`

---

### Task 1: Replace Color Palette and Add resolveNodeColor

**Files:**
- Modify: `frontend/src/lib/graph-colors.ts` (full rewrite of lines 1–71)

- [ ] **Step 1: Replace palette constants and remove old functions**

Replace the entire file content with:

```typescript
export type ColorMode = "type" | "cluster" | "tag";

export const PALETTE_400 = [
  "#f87171", "#fb923c", "#fbbf24", "#facc15", "#a3e635",
  "#4ade80", "#34d399", "#2dd4bf", "#22d3ee", "#38bdf8",
  "#60a5fa", "#818cf8", "#a78bfa", "#c084fc", "#e879f9",
  "#f472b6", "#fb7185",
];

export const PALETTE_200 = [
  "#fecaca", "#fed7aa", "#fde68a", "#fef08a", "#d9f99d",
  "#bbf7d0", "#a7f3d0", "#99f6e4", "#a5f3fc", "#bae6fd",
  "#bfdbfe", "#c7d2fe", "#ddd6fe", "#e9d5ff", "#f5d0fe",
  "#fbcfe8", "#fecdd3",
];

export const PALETTE_600 = [
  "#dc2626", "#ea580c", "#d97706", "#ca8a04", "#65a30d",
  "#16a34a", "#059669", "#0d9488", "#0891b2", "#0284c7",
  "#2563eb", "#4f46e5", "#7c3aed", "#9333ea", "#c026d3",
  "#db2777", "#e11d48",
];

export const UNIFIED_PALETTE = [...PALETTE_400, ...PALETTE_200, ...PALETTE_600];

export const UNCLUSTERED_COLOR = "#8b949e";

const KNOWN_TYPE_INDICES: Record<string, number> = {
  fact: 10,       // blue-400
  decision: 12,   // violet-400
  debug: 0,       // red-400
  architecture: 5, // green-400
  preference: 1,  // orange-400
  session: 8,     // cyan-400
  workflow: 6,    // emerald-400
};

function stableHash(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = ((hash << 5) - hash + str.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

export function resolveNodeColor(
  node: { cluster: number; memory_type: string | null; tags: string[] },
  colorMode: ColorMode,
): string {
  switch (colorMode) {
    case "cluster":
      if (node.cluster < 0) return UNCLUSTERED_COLOR;
      return UNIFIED_PALETTE[node.cluster % UNIFIED_PALETTE.length];
    case "type": {
      if (!node.memory_type) return UNCLUSTERED_COLOR;
      const known = KNOWN_TYPE_INDICES[node.memory_type];
      if (known !== undefined) return UNIFIED_PALETTE[known];
      return UNIFIED_PALETTE[stableHash(node.memory_type) % UNIFIED_PALETTE.length];
    }
    case "tag": {
      if (node.tags.length === 0) return UNCLUSTERED_COLOR;
      const prefix = node.tags[0].split("/")[0];
      return UNIFIED_PALETTE[stableHash(prefix) % UNIFIED_PALETTE.length];
    }
  }
}

export function resolveGroupColor(
  groupKey: string,
  groupIndex: number,
  colorMode: ColorMode,
  hullMode: string,
): string {
  if (colorMode === hullMode) {
    if (colorMode === "cluster") {
      const cid = parseInt(groupKey);
      if (isNaN(cid) || cid < 0) return UNCLUSTERED_COLOR;
      return UNIFIED_PALETTE[cid % UNIFIED_PALETTE.length];
    }
    if (colorMode === "tag") {
      const prefix = groupKey.split("/")[0];
      return UNIFIED_PALETTE[stableHash(prefix) % UNIFIED_PALETTE.length];
    }
  }
  return UNIFIED_PALETTE[groupIndex % UNIFIED_PALETTE.length];
}

export const ENTITY_TYPE_COLORS: Record<string, string> = {
  person: "#60a5fa",
  service: "#4ade80",
  project: "#c084fc",
  technology: "#fb923c",
  concept: "#8b949e",
  organization: "#f472b6",
};

export function entityTypeColor(entityType: string): string {
  return ENTITY_TYPE_COLORS[entityType] ?? "#8b949e";
}

export function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

export function lightenHex(hex: string, amount = 0.35): string {
  const r = Math.min(255, Math.round(parseInt(hex.slice(1, 3), 16) + (255 - parseInt(hex.slice(1, 3), 16)) * amount));
  const g = Math.min(255, Math.round(parseInt(hex.slice(3, 5), 16) + (255 - parseInt(hex.slice(3, 5), 16)) * amount));
  const b = Math.min(255, Math.round(parseInt(hex.slice(5, 7), 16) + (255 - parseInt(hex.slice(5, 7), 16)) * amount));
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}

export function blendHex(hex1: string, hex2: string, ratio = 0.5): string {
  const r = Math.round(parseInt(hex1.slice(1, 3), 16) * (1 - ratio) + parseInt(hex2.slice(1, 3), 16) * ratio);
  const g = Math.round(parseInt(hex1.slice(3, 5), 16) * (1 - ratio) + parseInt(hex2.slice(3, 5), 16) * ratio);
  const b = Math.round(parseInt(hex1.slice(5, 7), 16) * (1 - ratio) + parseInt(hex2.slice(5, 7), 16) * ratio);
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}

export function darkenHex(hex: string, amount = 0.45): string {
  const r = Math.max(0, Math.round(parseInt(hex.slice(1, 3), 16) * (1 - amount)));
  const g = Math.max(0, Math.round(parseInt(hex.slice(3, 5), 16) * (1 - amount)));
  const b = Math.max(0, Math.round(parseInt(hex.slice(5, 7), 16) * (1 - amount)));
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -30`

Expected: Type errors in files that still import the old `clusterColor`, `tagColor`, `typeColor` functions. That's expected — we fix those in subsequent tasks.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/graph-colors.ts
git commit -m "feat(ui): replace color palette with Tailwind 200+400+600 tri-shade system"
```

---

### Task 2: Add computeHullGroups to graph-geometry.ts

**Files:**
- Modify: `frontend/src/lib/graph-geometry.ts` (add after line 171)

- [ ] **Step 1: Add HullMode type and computeHullGroups function**

Add at the top of the file (after the existing imports, before `convexHull`):

```typescript
export type HullMode = "none" | "cluster" | "tag" | "source";
```

Add at the end of the file (after `drawHullForSigma`):

```typescript
export function computeHullGroups(
  memories: { id: string; cluster: number; tags: string[]; source: string }[],
  hullMode: HullMode,
): Map<string, string[]> {
  const groups = new Map<string, string[]>();
  if (hullMode === "none") return groups;

  for (const m of memories) {
    switch (hullMode) {
      case "cluster": {
        if (m.cluster < 0) break;
        const key = String(m.cluster);
        const arr = groups.get(key) ?? [];
        arr.push(m.id);
        groups.set(key, arr);
        break;
      }
      case "tag": {
        for (const tag of m.tags) {
          const arr = groups.get(tag) ?? [];
          arr.push(m.id);
          groups.set(tag, arr);
        }
        break;
      }
      case "source": {
        const arr = groups.get(m.source) ?? [];
        arr.push(m.id);
        groups.set(m.source, arr);
        break;
      }
    }
  }

  if (hullMode === "tag" || hullMode === "source") {
    for (const [key, members] of groups) {
      if (members.length < 2) groups.delete(key);
    }
  }

  return groups;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/graph-geometry.ts
git commit -m "feat(ui): add HullMode type and computeHullGroups engine"
```

---

### Task 3: Update graph-utils.ts exports and transformToGraphData

**Files:**
- Modify: `frontend/src/lib/graph-utils.ts` (lines 1–4, line 124)

- [ ] **Step 1: Update imports and re-exports**

Replace lines 1–4:

```typescript
import type { UnifiedMemory, UnifiedGraphData, GraphEntity, EntityRelation } from "@/hooks/useApi";
import { clusterColor, typeColor, entityTypeColor } from "@/lib/graph-colors";
export { clusterColor, typeColor, entityTypeColor };
export { CLUSTER_PALETTE, UNCLUSTERED_COLOR, ENTITY_TYPE_COLORS } from "@/lib/graph-colors";
```

With:

```typescript
import type { UnifiedMemory, UnifiedGraphData, GraphEntity, EntityRelation } from "@/hooks/useApi";
import { resolveNodeColor, entityTypeColor } from "@/lib/graph-colors";
import type { ColorMode } from "@/lib/graph-colors";
export { resolveNodeColor, entityTypeColor };
export type { ColorMode };
export { UNIFIED_PALETTE, UNCLUSTERED_COLOR, ENTITY_TYPE_COLORS } from "@/lib/graph-colors";
```

- [ ] **Step 2: Add colorMode parameter to transformToGraphData**

Replace the function signature at line 95–102:

```typescript
export function transformToGraphData(
  data: UnifiedGraphData,
  sizeMode: SizeMode,
  filters: FilterState,
  entityLayerEnabled = false,
  entities: GraphEntity[] = [],
  entityRelations: EntityRelation[] = [],
): GraphData3D {
```

With:

```typescript
export function transformToGraphData(
  data: UnifiedGraphData,
  sizeMode: SizeMode,
  filters: FilterState,
  colorMode: ColorMode = "type",
  entityLayerEnabled = false,
  entities: GraphEntity[] = [],
  entityRelations: EntityRelation[] = [],
): GraphData3D {
```

- [ ] **Step 3: Replace typeColor call with resolveNodeColor**

Replace line 124:

```typescript
    color: typeColor(m.memory_type),
```

With:

```typescript
    color: resolveNodeColor(m, colorMode),
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/graph-utils.ts
git commit -m "feat(ui): wire colorMode through graph-utils transformToGraphData"
```

---

### Task 4: Redesign GraphToolbar with Color/Hull Toggles and Settings Popover

**Files:**
- Modify: `frontend/src/components/graph/GraphToolbar.tsx` (full rewrite)

- [ ] **Step 1: Rewrite GraphToolbar**

Replace the entire file with:

```tsx
import { useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Settings, RotateCcw } from "lucide-react";
import type { SizeMode } from "@/lib/graph-utils";
import type { ColorMode } from "@/lib/graph-colors";
import type { HullMode } from "@/lib/graph-geometry";

type ViewMode = "2d" | "3d";

interface GraphToolbarProps {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  colorMode: ColorMode;
  onColorModeChange: (mode: ColorMode) => void;
  hullMode: HullMode;
  onHullModeChange: (mode: HullMode) => void;
  entityLayer: boolean;
  onEntityLayerChange: (v: boolean) => void;
  showSettings: boolean;
  onToggleSettings: () => void;
  sizeMode: SizeMode;
  onSizeModeChange: (mode: SizeMode) => void;
  similarityThreshold: number;
  onSimilarityChange: (v: number) => void;
  minClusterSize: number;
  onMinClusterSizeChange: (v: number) => void;
  spacing: number;
  onSpacingChange: (v: number) => void;
  clusterTightness: number;
  onClusterTightnessChange: (v: number) => void;
  onReset: () => void;
}

function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { label: string; value: T }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex items-center rounded-sm overflow-hidden border border-border">
      {options.map((opt) => (
        <Button
          key={opt.value}
          variant="ghost"
          size="sm"
          className={`h-7 text-xs rounded-none px-2.5 ${
            value === opt.value
              ? "bg-primary/20 text-primary"
              : "text-muted-foreground"
          }`}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </Button>
      ))}
    </div>
  );
}

interface SliderProps {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (v: number) => void;
  float?: boolean;
}

function Slider({ label, min, max, step, value, onChange, float = false }: SliderProps) {
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <label className="w-14 text-right shrink-0">{label}</label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) =>
          onChange(float ? parseFloat(e.target.value) : parseInt(e.target.value))
        }
        className="flex-1"
      />
      <span className="w-8 font-mono text-right">{value}</span>
    </div>
  );
}

export function GraphToolbar({
  viewMode,
  onViewModeChange,
  colorMode,
  onColorModeChange,
  hullMode,
  onHullModeChange,
  entityLayer,
  onEntityLayerChange,
  showSettings,
  onToggleSettings,
  sizeMode,
  onSizeModeChange,
  similarityThreshold,
  onSimilarityChange,
  minClusterSize,
  onMinClusterSizeChange,
  spacing,
  onSpacingChange,
  clusterTightness,
  onClusterTightnessChange,
  onReset,
}: GraphToolbarProps) {
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showSettings) return;
    function handleClick(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onToggleSettings();
      }
    }
    const timer = setTimeout(() => document.addEventListener("click", handleClick), 0);
    return () => {
      clearTimeout(timer);
      document.removeEventListener("click", handleClick);
    };
  }, [showSettings, onToggleSettings]);

  return (
    <div className="absolute top-3 left-0 right-0 z-10 flex flex-col items-center pointer-events-none">
      {/* Top-level toggles */}
      <div className="flex items-center gap-2 bg-card/80 backdrop-blur-sm rounded-md border border-border shadow-lg px-3 py-1.5 pointer-events-auto flex-wrap justify-center">
        <SegmentedControl
          options={[
            { label: "2D", value: "2d" as ViewMode },
            { label: "3D", value: "3d" as ViewMode },
          ]}
          value={viewMode}
          onChange={onViewModeChange}
        />

        <div className="w-px h-4 bg-border" />

        <SegmentedControl
          options={[
            { label: "Type", value: "type" as ColorMode },
            { label: "Cluster", value: "cluster" as ColorMode },
            { label: "Tag", value: "tag" as ColorMode },
          ]}
          value={colorMode}
          onChange={onColorModeChange}
        />

        <SegmentedControl
          options={[
            { label: "None", value: "none" as HullMode },
            { label: "Cluster", value: "cluster" as HullMode },
            { label: "Tag", value: "tag" as HullMode },
            { label: "Source", value: "source" as HullMode },
          ]}
          value={hullMode}
          onChange={onHullModeChange}
        />

        <div className="w-px h-4 bg-border" />

        <Button
          variant="ghost"
          size="sm"
          className={`h-7 text-xs ${entityLayer ? "bg-primary/20 text-primary" : "text-muted-foreground"}`}
          onClick={() => onEntityLayerChange(!entityLayer)}
        >
          Entities
        </Button>

        <Button
          variant="ghost"
          size="sm"
          className={`h-7 text-xs ${showSettings ? "bg-primary/20 text-primary" : "text-muted-foreground"}`}
          onClick={onToggleSettings}
        >
          <Settings className="w-3.5 h-3.5" />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-muted-foreground"
          onClick={onReset}
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </Button>
      </div>

      {/* Floating settings popover */}
      {showSettings && (
        <div
          ref={popoverRef}
          className="mt-2 bg-card/95 backdrop-blur-sm rounded-lg border border-border shadow-xl px-4 py-3 pointer-events-auto"
          style={{ width: 340 }}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-foreground">Settings</span>
          </div>

          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground w-14 text-right shrink-0">Size</span>
              <SegmentedControl
                options={[
                  { label: "Connections", value: "connections" as SizeMode },
                  { label: "Importance", value: "importance" as SizeMode },
                  { label: "Uniform", value: "uniform" as SizeMode },
                ]}
                value={sizeMode}
                onChange={onSizeModeChange}
              />
            </div>

            <Slider
              label="Edges"
              min={0.3}
              max={0.95}
              step={0.05}
              value={similarityThreshold}
              onChange={onSimilarityChange}
              float
            />
            <Slider
              label="Min Size"
              min={2}
              max={10}
              step={1}
              value={minClusterSize}
              onChange={onMinClusterSizeChange}
            />
            {viewMode === "2d" && (
              <Slider
                label="Tightness"
                min={30}
                max={300}
                step={10}
                value={clusterTightness}
                onChange={onClusterTightnessChange}
              />
            )}
            <Slider
              label="Spacing"
              min={viewMode === "2d" ? 100 : 30}
              max={viewMode === "2d" ? 500 : 200}
              step={viewMode === "2d" ? 25 : 10}
              value={spacing}
              onChange={onSpacingChange}
            />
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/graph/GraphToolbar.tsx
git commit -m "feat(ui): redesign toolbar with color/hull toggles and settings popover"
```

---

### Task 5: Update Graph2DRenderer to Use New Color/Hull Engine

**Files:**
- Modify: `frontend/src/components/graph/Graph2DRenderer.tsx`

- [ ] **Step 1: Update imports**

Replace lines 11–17:

```typescript
import {
  clusterColor,
  tagColor,
  entityTypeColor,
  lightenHex,
  darkenHex,
} from "@/lib/graph-colors";
```

With:

```typescript
import {
  resolveNodeColor,
  resolveGroupColor,
  entityTypeColor,
  lightenHex,
  darkenHex,
} from "@/lib/graph-colors";
import type { ColorMode } from "@/lib/graph-colors";
import { computeHullGroups } from "@/lib/graph-geometry";
import type { HullMode } from "@/lib/graph-geometry";
```

- [ ] **Step 2: Update props interface**

Replace lines 25–41 (the `Graph2DRendererProps` interface):

```typescript
interface Graph2DRendererProps {
  data: UnifiedGraphData;
  filteredMemories: UnifiedMemory[];
  filteredEdges: { source: string; target: string; score: number }[];
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  onReady: () => void;
  sizeMode: SizeMode;
  colorMode: ColorMode;
  spacing: number;
  clusterTightness: number;
  hullMode: HullMode;
  entityLayerEnabled: boolean;
  entities: GraphEntity[];
  entityRelations: EntityRelation[];
  onEntitySelect?: (entityId: string | null) => void;
}
```

Note: `filteredClusters` prop is removed — hull groups are now computed internally by `computeHullGroups`.

- [ ] **Step 3: Update component destructuring**

Replace lines 43–56 (the destructuring and refs):

```typescript
export function Graph2DRenderer({
  filteredMemories,
  filteredEdges,
  selectedNodeId,
  onNodeSelect,
  onReady,
  sizeMode,
  colorMode,
  hullMode,
  entityLayerEnabled,
  entities,
  entityRelations,
  onEntitySelect,
}: Graph2DRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const fa2Ref = useRef<FA2Layout | null>(null);
  const selectedNodeIdRef = useRef(selectedNodeId);
  const hoveredNodeRef = useRef<string | null>(null);
  const colorModeRef = useRef(colorMode);
  const hullModeRef = useRef(hullMode);
  const filteredMemoriesRef = useRef(filteredMemories);
```

Note: removed `filteredClustersRef`, added `colorModeRef`.

- [ ] **Step 4: Update node coloring in buildGraph**

Replace lines 91–92 (inside the `for (const m of filteredMemories)` loop):

```typescript
      const color = clusterColor(m.cluster);
```

With:

```typescript
      const color = resolveNodeColor(m, colorModeRef.current);
```

- [ ] **Step 5: Replace hull drawing logic**

Replace lines 281–333 (the entire `drawHulls` function body after the `hullCtx.clearRect` call):

Replace the block starting with `if (hullModeRef.current === "clusters") {` through the closing `}` of the else block (lines 295–332) with:

```typescript
      const hullGroups = computeHullGroups(filteredMemoriesRef.current, hullModeRef.current);
      let idx = 0;
      for (const [groupKey, members] of hullGroups) {
        const color = resolveGroupColor(groupKey, idx, colorModeRef.current, hullModeRef.current);
        drawHullForSigma(
          hullCtx,
          sigmaRef.current,
          members,
          color,
          0.07,
          0.2,
        );
        idx++;
      }
```

- [ ] **Step 6: Update the reactivity effect**

Replace lines 389–394 (the hullMode/filteredClusters/filteredMemories effect):

```typescript
  useEffect(() => {
    hullModeRef.current = hullMode;
    filteredClustersRef.current = filteredClusters;
    filteredMemoriesRef.current = filteredMemories;
    sigmaRef.current?.refresh();
  }, [hullMode, filteredClusters, filteredMemories]);
```

With:

```typescript
  useEffect(() => {
    colorModeRef.current = colorMode;
    hullModeRef.current = hullMode;
    filteredMemoriesRef.current = filteredMemories;
    sigmaRef.current?.refresh();
  }, [colorMode, hullMode, filteredMemories]);
```

- [ ] **Step 7: Add colorMode to buildGraph dependency array**

In the `buildGraph` useCallback dependency array (around line 356), add `colorMode` after `sizeMode`:

```typescript
  ], [
    filteredMemories,
    filteredEdges,
    sizeMode,
    colorMode,
    entityLayerEnabled,
    entities,
    entityRelations,
    onNodeSelect,
    onEntitySelect,
    onReady,
  ]);
```

- [ ] **Step 8: Remove the unused drawHullForSigma import from graph-geometry**

The `drawHullForSigma` import on line 9 stays — it's still used inside `drawHulls`. But remove the `import { drawHullForSigma } from "@/lib/graph-geometry";` line since it's now imported via the new import block in Step 1. Make sure there's only one import from `@/lib/graph-geometry`.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/graph/Graph2DRenderer.tsx
git commit -m "feat(ui): wire 2D renderer to unified color/hull engine"
```

---

### Task 6: Update Graph3DRenderer for Color Mode and All Hull Modes

**Files:**
- Modify: `frontend/src/components/graph/Graph3DRenderer.tsx`

- [ ] **Step 1: Update imports**

Replace line 6:

```typescript
import { clusterColor } from "@/lib/graph-colors";
```

With:

```typescript
import { resolveGroupColor } from "@/lib/graph-colors";
import type { ColorMode } from "@/lib/graph-colors";
import { computeHullGroups } from "@/lib/graph-geometry";
import type { HullMode } from "@/lib/graph-geometry";
```

- [ ] **Step 2: Update props interface**

Replace lines 8–16:

```typescript
interface Graph3DRendererProps {
  graphData: GraphData3D;
  width: number;
  height: number;
  spacing: number;
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  onReady: () => void;
}
```

With:

```typescript
interface Graph3DRendererProps {
  graphData: GraphData3D;
  width: number;
  height: number;
  spacing: number;
  colorMode: ColorMode;
  hullMode: HullMode;
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  onReady: () => void;
}
```

- [ ] **Step 3: Update component destructuring**

Replace lines 18–26:

```typescript
export function Graph3DRenderer({
  graphData,
  width,
  height,
  spacing,
  selectedNodeId,
  onNodeSelect,
  onReady,
}: Graph3DRendererProps) {
```

With:

```typescript
export function Graph3DRenderer({
  graphData,
  width,
  height,
  spacing,
  colorMode,
  hullMode,
  selectedNodeId,
  onNodeSelect,
  onReady,
}: Graph3DRendererProps) {
```

- [ ] **Step 4: Replace buildClusterHulls with generic buildHulls**

Replace the entire `buildClusterHulls` callback (lines 131–206) with:

```typescript
  const buildHulls = useCallback(() => {
    const scene = fgRef.current?.scene();
    if (!scene) return;

    hullMeshesRef.current.forEach((m) => {
      m.geometry.dispose();
      (m.material as THREE.Material).dispose();
      scene.remove(m);
    });
    hullMeshesRef.current = [];

    if (hullMode === "none") return;

    const memoryNodes = graphData.nodes.filter(
      (n) => n.nodeKind === "memory" && n.x != null,
    );
    const hullGroups = computeHullGroups(memoryNodes, hullMode);

    const sampleDirs: THREE.Vector3[] = [];
    const numSamples = 80;
    const goldenRatio = (1 + Math.sqrt(5)) / 2;
    for (let i = 0; i < numSamples; i++) {
      const theta = Math.acos(1 - (2 * (i + 0.5)) / numSamples);
      const phi = (2 * Math.PI * i) / goldenRatio;
      sampleDirs.push(
        new THREE.Vector3(
          Math.sin(theta) * Math.cos(phi),
          Math.sin(theta) * Math.sin(phi),
          Math.cos(theta),
        ),
      );
    }

    const nodeMap = new Map(graphData.nodes.map((n) => [n.id, n]));

    let groupIdx = 0;
    for (const [groupKey, memberIds] of hullGroups) {
      const positions: THREE.Vector3[] = [];
      for (const id of memberIds) {
        const node = nodeMap.get(id);
        if (node && node.x != null) {
          positions.push(new THREE.Vector3(node.x!, node.y!, node.z!));
        }
      }
      if (positions.length < 4) { groupIdx++; continue; }

      const centroid = new THREE.Vector3();
      positions.forEach((p) => centroid.add(p));
      centroid.divideScalar(positions.length);

      const padding = 15;
      const points: THREE.Vector3[] = [];
      for (const dir of sampleDirs) {
        let maxProj = 0;
        for (const p of positions) {
          const proj = p.clone().sub(centroid).dot(dir);
          if (proj > maxProj) maxProj = proj;
        }
        points.push(
          centroid.clone().add(dir.clone().multiplyScalar(maxProj + padding)),
        );
      }

      try {
        const geometry = new ConvexGeometry(points);
        geometry.computeVertexNormals();
        const hullColor = resolveGroupColor(groupKey, groupIdx, colorMode, hullMode);
        const material = new THREE.MeshPhongMaterial({
          color: hullColor,
          transparent: true,
          opacity: 0.06,
          side: THREE.DoubleSide,
          depthWrite: false,
          flatShading: false,
        });
        const mesh = new THREE.Mesh(geometry, material);
        scene.add(mesh);
        hullMeshesRef.current.push(mesh);
      } catch {
        // ConvexGeometry can throw if points are coplanar
      }
      groupIdx++;
    }
  }, [graphData, colorMode, hullMode]);
```

- [ ] **Step 5: Update onEngineStop reference**

Replace `buildClusterHulls` in the `onEngineStop` prop (line 293):

```typescript
      onEngineStop={() => {
        buildClusterHulls();
        onReady();
      }}
```

With:

```typescript
      onEngineStop={() => {
        buildHulls();
        onReady();
      }}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/graph/Graph3DRenderer.tsx
git commit -m "feat(ui): wire 3D renderer to unified color/hull engine"
```

---

### Task 7: Update UnifiedGraph Page — New State and Prop Threading

**Files:**
- Modify: `frontend/src/pages/UnifiedGraph.tsx`

- [ ] **Step 1: Update imports**

Add the new type imports. After line 16 (`} from "@/lib/graph-utils";`), add:

```typescript
import type { ColorMode } from "@/lib/graph-colors";
import type { HullMode } from "@/lib/graph-geometry";
```

- [ ] **Step 2: Add new state variables**

After line 33 (`const [graphReady, setGraphReady] = useState(false);`), add:

```typescript
  const [colorMode, setColorMode] = useState<ColorMode>("type");
  const [showSettings, setShowSettings] = useState(false);
```

- [ ] **Step 3: Change hullMode default and type**

Replace line 60:

```typescript
  const [hullMode, setHullMode] = useState<"clusters" | "tags">("clusters");
```

With:

```typescript
  const [hullMode, setHullMode] = useState<HullMode>("none");
```

- [ ] **Step 4: Add colorMode to transformToGraphData call**

Replace lines 243–246:

```typescript
    return transformToGraphData(
      data, sizeMode, filters,
      entityLayerEnabled, filteredEntities, filteredEntityRelations,
    );
```

With:

```typescript
    return transformToGraphData(
      data, sizeMode, filters, colorMode,
      entityLayerEnabled, filteredEntities, filteredEntityRelations,
    );
```

And add `colorMode` to the dependency array of this `useMemo` (line 247).

- [ ] **Step 5: Update handleReset**

Replace lines 115–128:

```typescript
  function handleReset() {
    setSimilarityThreshold(0.5);

    setMinClusterSize(3);
    setClusterTightness(300);
    setNodeSpacing(100);
    setSpacing3D(50);
    setSizeMode("connections");
    setHullMode("clusters");
    setEntityLayerEnabled(false);
    setSelectedEntityTypes(new Set());
    setSelectedEntityId(null);
    clearFilters();
  }
```

With:

```typescript
  function handleReset() {
    setSimilarityThreshold(0.5);
    setMinClusterSize(3);
    setClusterTightness(300);
    setNodeSpacing(100);
    setSpacing3D(50);
    setSizeMode("connections");
    setColorMode("type");
    setHullMode("none");
    setShowSettings(false);
    setEntityLayerEnabled(false);
    setSelectedEntityTypes(new Set());
    setSelectedEntityId(null);
    clearFilters();
  }
```

- [ ] **Step 6: Update Graph2DRenderer props**

Replace the `<Graph2DRenderer>` JSX (lines 318–334). Remove `filteredClusters` prop, add `colorMode` prop:

```tsx
                <Graph2DRenderer
                  data={data}
                  filteredMemories={filteredMemories}
                  filteredEdges={filteredEdges}
                  selectedNodeId={selectedNodeId}
                  onNodeSelect={handleNodeSelect}
                  onReady={handleGraphReady}
                  sizeMode={sizeMode}
                  colorMode={colorMode}
                  spacing={debouncedSpacing2D}
                  clusterTightness={debouncedTightness}
                  hullMode={hullMode}
                  entityLayerEnabled={entityLayerEnabled}
                  entities={filteredEntities}
                  entityRelations={filteredEntityRelations}
                  onEntitySelect={handleEntitySelect}
                />
```

- [ ] **Step 7: Update Graph3DRenderer props**

Replace the `<Graph3DRenderer>` JSX (lines 337–345). Add `colorMode` and `hullMode`:

```tsx
                <Graph3DRenderer
                  graphData={graphData3D}
                  width={dimensions.width}
                  height={dimensions.height}
                  selectedNodeId={selectedNodeId}
                  onNodeSelect={handleNodeSelect}
                  onReady={handleGraphReady}
                  spacing={spacing3D}
                  colorMode={colorMode}
                  hullMode={hullMode}
                />
```

- [ ] **Step 8: Update GraphToolbar props**

Replace the `<GraphToolbar>` JSX (lines 370–388):

```tsx
            <GraphToolbar
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              colorMode={colorMode}
              onColorModeChange={setColorMode}
              hullMode={hullMode}
              onHullModeChange={setHullMode}
              entityLayer={entityLayerEnabled}
              onEntityLayerChange={setEntityLayerEnabled}
              showSettings={showSettings}
              onToggleSettings={() => setShowSettings((v) => !v)}
              sizeMode={sizeMode}
              onSizeModeChange={setSizeMode}
              similarityThreshold={similarityThreshold}
              onSimilarityChange={setSimilarityThreshold}
              minClusterSize={minClusterSize}
              onMinClusterSizeChange={setMinClusterSize}
              spacing={viewMode === "2d" ? nodeSpacing : spacing3D}
              onSpacingChange={viewMode === "2d" ? setNodeSpacing : setSpacing3D}
              clusterTightness={clusterTightness}
              onClusterTightnessChange={setClusterTightness}
              onReset={handleReset}
            />
```

- [ ] **Step 9: Remove unused filteredClusters computation**

Delete the `filteredClusters` useMemo block (lines 184–193) — no longer used since hulls compute their own groups.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/pages/UnifiedGraph.tsx
git commit -m "feat(ui): wire colorMode, hullMode, and settings popover through page"
```

---

### Task 8: Update GraphFilterPanel for Color-Aware Indicators

**Files:**
- Modify: `frontend/src/components/graph/GraphFilterPanel.tsx`

- [ ] **Step 1: Update imports**

Replace line 2:

```typescript
import { clusterColor, typeColor, entityTypeColor } from "@/lib/graph-colors";
```

With:

```typescript
import { UNIFIED_PALETTE, UNCLUSTERED_COLOR, entityTypeColor, resolveNodeColor } from "@/lib/graph-colors";
import type { ColorMode } from "@/lib/graph-colors";
```

- [ ] **Step 2: Add colorMode to props interface**

Add after line 4 (`export interface GraphFilterPanelProps {`), within the interface:

```typescript
  colorMode: ColorMode;
```

- [ ] **Step 3: Add colorMode to destructuring**

Add `colorMode` to the function parameters destructuring (after `onShowAll` in line 48).

- [ ] **Step 4: Update type color indicators**

Replace the type items section (lines 148–151). Change the color logic:

```typescript
                {allTypes.map(([type, count]) => {
                  const color = colorMode === "type"
                    ? resolveNodeColor({ cluster: -1, memory_type: type === "(none)" ? null : type, tags: [] }, "type")
                    : "#8b949e";
```

- [ ] **Step 5: Update cluster color indicators**

Replace the cluster color logic (line 226):

```typescript
                  const color = colorMode === "cluster"
                    ? UNIFIED_PALETTE[cid % UNIFIED_PALETTE.length]
                    : "#8b949e";
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/graph/GraphFilterPanel.tsx
git commit -m "feat(ui): make filter panel color indicators respect active colorMode"
```

---

### Task 9: Update GraphDetailPanel for Color-Aware Indicators

**Files:**
- Modify: `frontend/src/components/graph/GraphDetailPanel.tsx`

- [ ] **Step 1: Update imports**

Replace line 3:

```typescript
import { clusterColor, typeColor, entityTypeColor } from "@/lib/graph-colors";
```

With:

```typescript
import { UNIFIED_PALETTE, UNCLUSTERED_COLOR, entityTypeColor, resolveNodeColor } from "@/lib/graph-colors";
import type { ColorMode } from "@/lib/graph-colors";
```

- [ ] **Step 2: Add colorMode to props and destructuring**

Add `colorMode: ColorMode;` to the `GraphDetailPanelProps` interface (after line 5).

Add `colorMode` to the destructuring in the component function.

- [ ] **Step 3: Pass colorMode to sub-components**

Pass `colorMode={colorMode}` to `<MemoryDetail>` and `<GraphSummary>`.

Add `colorMode: ColorMode` to the `MemoryDetailProps` and `GraphSummaryProps` interfaces and their destructuring.

- [ ] **Step 4: Update MemoryDetail cluster color**

Replace line 206 (`style={{ backgroundColor: clusterColor(memory.cluster) }}`):

```typescript
                style={{ backgroundColor: colorMode === "cluster" ? UNIFIED_PALETTE[memory.cluster % UNIFIED_PALETTE.length] : "#8b949e" }}
```

- [ ] **Step 5: Update GraphSummary cluster colors**

Replace line 284 (`style={{ backgroundColor: clusterColor(cid) }}`):

```typescript
                  style={{ backgroundColor: colorMode === "cluster" ? UNIFIED_PALETTE[cid % UNIFIED_PALETTE.length] : "#8b949e" }}
```

- [ ] **Step 6: Update GraphSummary type colors**

Replace line 306 (`style={{ backgroundColor: typeColor(type === "(none)" ? null : type) }}`):

```typescript
                  style={{ backgroundColor: colorMode === "type" ? resolveNodeColor({ cluster: -1, memory_type: type === "(none)" ? null : type, tags: [] }, "type") : "#8b949e" }}
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/graph/GraphDetailPanel.tsx
git commit -m "feat(ui): make detail panel color indicators respect active colorMode"
```

---

### Task 10: Thread colorMode Prop to Filter and Detail Panels in UnifiedGraph

**Files:**
- Modify: `frontend/src/pages/UnifiedGraph.tsx`

- [ ] **Step 1: Add colorMode to GraphFilterPanel**

In the `<GraphFilterPanel>` JSX (around line 409), add:

```tsx
                colorMode={colorMode}
```

- [ ] **Step 2: Add colorMode to GraphDetailPanel**

In the `<GraphDetailPanel>` JSX (around line 469), add:

```tsx
            colorMode={colorMode}
```

- [ ] **Step 3: Verify build**

Run: `cd frontend && npx tsc --noEmit`

Expected: No type errors.

- [ ] **Step 4: Run dev server and verify visually**

Run: `cd frontend && npm run dev`

Verify:
- Color toggle switches between type/cluster/tag coloring
- Hull toggle shows none/cluster/tag/source groupings
- Settings popover opens and closes correctly
- Sliders in popover adjust parameters
- 3D view has the same color and hull options
- Filter panel shows colored indicators only for active color mode
- Detail panel shows colored dots only for active color mode
- Reset button restores all defaults

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/UnifiedGraph.tsx
git commit -m "feat(ui): thread colorMode to filter and detail panels"
```

---

### Task 11: Update Tests for New Color System

**Files:**
- Modify: `frontend/src/__tests__/graph-utils.test.ts`

- [ ] **Step 1: Update imports and color tests**

Replace the entire file with:

```typescript
import { describe, it, expect } from "vitest";
import { transformToGraphData, computeNodeVal } from "@/lib/graph-utils";
import { resolveNodeColor, UNIFIED_PALETTE, UNCLUSTERED_COLOR } from "@/lib/graph-colors";
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

describe("resolveNodeColor", () => {
  it("returns palette color for valid cluster", () => {
    expect(resolveNodeColor({ cluster: 0, memory_type: null, tags: [] }, "cluster")).toBe(UNIFIED_PALETTE[0]);
    expect(resolveNodeColor({ cluster: 3, memory_type: null, tags: [] }, "cluster")).toBe(UNIFIED_PALETTE[3]);
  });

  it("wraps around palette for large cluster IDs", () => {
    expect(resolveNodeColor({ cluster: 51, memory_type: null, tags: [] }, "cluster")).toBe(UNIFIED_PALETTE[0]);
  });

  it("returns gray for unclustered (-1)", () => {
    expect(resolveNodeColor({ cluster: -1, memory_type: null, tags: [] }, "cluster")).toBe(UNCLUSTERED_COLOR);
  });

  it("returns consistent color for known types", () => {
    const factColor = resolveNodeColor({ cluster: 0, memory_type: "fact", tags: [] }, "type");
    expect(UNIFIED_PALETTE).toContain(factColor);
    expect(resolveNodeColor({ cluster: 1, memory_type: "fact", tags: [] }, "type")).toBe(factColor);
  });

  it("returns gray for null type", () => {
    expect(resolveNodeColor({ cluster: 0, memory_type: null, tags: [] }, "type")).toBe(UNCLUSTERED_COLOR);
  });

  it("returns consistent color for tag prefix", () => {
    const color1 = resolveNodeColor({ cluster: 0, memory_type: null, tags: ["project/darkmem"] }, "tag");
    const color2 = resolveNodeColor({ cluster: 1, memory_type: null, tags: ["project/homelab"] }, "tag");
    expect(color1).toBe(color2);
    expect(UNIFIED_PALETTE).toContain(color1);
  });

  it("returns gray for no tags", () => {
    expect(resolveNodeColor({ cluster: 0, memory_type: null, tags: [] }, "tag")).toBe(UNCLUSTERED_COLOR);
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

  it("uses type coloring by default", () => {
    const result = transformToGraphData(sampleData, "connections", emptyFilters);
    const nodeA = result.nodes.find((n) => n.id === "a")!;
    expect(nodeA.color).toBe(resolveNodeColor({ cluster: 0, memory_type: "fact", tags: ["test"] }, "type"));
    const nodeD = result.nodes.find((n) => n.id === "d")!;
    expect(nodeD.color).toBe(UNCLUSTERED_COLOR);
  });

  it("uses cluster coloring when specified", () => {
    const result = transformToGraphData(sampleData, "connections", emptyFilters, "cluster");
    const nodeA = result.nodes.find((n) => n.id === "a")!;
    expect(nodeA.color).toBe(UNIFIED_PALETTE[0]);
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

Run: `cd frontend && npx vitest run`

Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/__tests__/graph-utils.test.ts
git commit -m "test(ui): update graph-utils tests for new color system"
```

---

### Task 12: Final Cleanup and Verification

**Files:**
- Possibly: any files with remaining references to old exports

- [ ] **Step 1: Search for remaining references to removed exports**

Run: `grep -rn "clusterColor\|tagColor\|typeColor\|CLUSTER_PALETTE\|TAG_PALETTE" frontend/src/ --include='*.ts' --include='*.tsx'`

Expected: Zero hits. All references should have been replaced in prior tasks. If any consumer files still reference these, update them to use `resolveNodeColor`, `UNIFIED_PALETTE`, or `UNCLUSTERED_COLOR` as appropriate.

- [ ] **Step 2: Final TypeScript check**

Run: `cd frontend && npx tsc --noEmit`

Expected: Clean, no errors.

- [ ] **Step 3: Run all tests**

Run: `cd frontend && npx vitest run`

Expected: All tests pass.

- [ ] **Step 4: Run dev server and visual smoke test**

Run: `cd frontend && npm run dev`

Verify in browser:
1. Color toggle switches nodes between type/cluster/tag coloring in both 2D and 3D
2. Hull toggle shows none/cluster/tag/source groupings in both 2D and 3D
3. When color mode and hull mode match (e.g., both "cluster"), hull colors match node colors
4. When they differ, hulls use their own independent colors
5. Settings popover opens/closes with gear icon and click-outside dismiss
6. All sliders in popover work (edges, min size, tightness for 2D, spacing)
7. Filter panel shows colored indicators only for active color mode
8. Detail panel cluster/type dots respect active color mode
9. Reset restores all defaults (colorMode=type, hullMode=none, popover closed)
10. Entity layer still works in both views

- [ ] **Step 5: Commit any cleanup**

```bash
git add -u frontend/src/
git commit -m "chore(ui): clean up stale color function references"
```
