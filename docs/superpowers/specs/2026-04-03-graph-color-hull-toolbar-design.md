# Graph Color Toggle, Hull Mode, and Toolbar Redesign

**Date:** 2026-04-03
**Branch:** feat/backend-foundation
**Approach:** Unified Color/Hull Engine — centralized logic consumed by both 2D and 3D renderers

## Summary

Add a Color toggle (Type / Cluster / Tag), expand Hull mode (None / Cluster / Tag / Source), revamp the color palette to Tailwind CSS tri-shade (200+400+600, 51 colors), reorganize the toolbar so toggles stay top-level and sliders move into a floating settings popover, and achieve full feature parity between 2D and 3D graph views.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Color toggle modes | Type, Cluster, Tag | Three orthogonal ways to understand the graph |
| Tag coloring strategy | Category prefix (part before `/`) | Keeps palette manageable; semantically meaningful groupings |
| Hull modes | None, Cluster, Tag, Source | "None" disables hulls; three grouping dimensions |
| Tag hull grouping | Full tag string (granular) | More spatial detail; nodes can appear in multiple overlapping hulls |
| Hull default | None | Clean initial view, user opts in |
| Color palette | Tailwind 200+400+600 tri-shade, 51 colors | Wide lightness spread, all tiers readable on dark background |
| Palette assignment order | 400 primary, overflow to 200 then 600 | Default view stays vibrant; pastels and deep tones only appear when needed |
| Hull/color color matching | When hull mode matches color mode, use same color for hull as nodes | Visual coherence — cluster hull same color as cluster nodes |
| Toolbar layout | Toggles top-level, sliders in floating popover | Clean separation of quick mode switches vs fine-tuning |
| 3D support | Full parity | All color modes + all hull modes in both 2D and 3D |

## 1. Color Palette and Assignment Engine

### File: `frontend/src/lib/graph-colors.ts`

**New palette constants:**

- `PALETTE_400`: 17 Tailwind 400-shade hex values ordered red, orange, amber, yellow, lime, green, emerald, teal, cyan, sky, blue, indigo, violet, purple, fuchsia, pink, rose
- `PALETTE_200`: 17 matching 200-shade values
- `PALETTE_600`: 17 matching 600-shade values
- `UNIFIED_PALETTE`: concatenation of `PALETTE_400` + `PALETTE_200` + `PALETTE_600` (51 entries). Index 0–16 are vibrant 400s, 17–33 are pastel 200s, 34–50 are deep 600s

**Removed/replaced:**

- `CLUSTER_PALETTE` (12 colors) → replaced by `UNIFIED_PALETTE`
- `TAG_PALETTE` (6 colors) → replaced by `UNIFIED_PALETTE`
- `TYPE_COLOR_PREASSIGNED` → known types get deterministic indices into `UNIFIED_PALETTE` instead of a separate color map
- `TYPE_COLOR_DYNAMIC` → no longer needed; hash-based assignment into `UNIFIED_PALETTE`
- `clusterColor()`, `tagColor()`, `typeColor()` → replaced by `resolveNodeColor()`

**Kept unchanged:**

- `UNCLUSTERED_COLOR` (`#8b949e`) — for nodes with cluster < 0
- `ENTITY_TYPE_COLORS` — entities are a separate visual layer
- `entityTypeColor()` — unchanged
- Utility functions: `hexToRgba`, `lightenHex`, `darkenHex`, `blendHex`

**New type:**

```typescript
type ColorMode = "type" | "cluster" | "tag";
```

**New function: `resolveNodeColor(node, colorMode): string`**

- `"cluster"`: returns `UNIFIED_PALETTE[node.cluster % 51]`. Negative cluster returns `UNCLUSTERED_COLOR`.
- `"type"`: deterministic hash of `node.memory_type` string to palette index (mod 51). Known types (fact, decision, debug, architecture, preference, session, workflow) get fixed indices for stability.
- `"tag"`: extracts category prefix from node's first tag (part before `/`), maps each unique prefix to a palette index deterministically (hash-based).

**New function: `resolveGroupColor(groupKey, groupIndex, colorMode, hullMode): string`**

- When `colorMode === hullMode`: returns the same color the nodes in that group would get (calls into the same logic as `resolveNodeColor` for that dimension).
- When they differ: returns `UNIFIED_PALETTE[groupIndex % 51]` — independent palette cycle.

## 2. Hull Grouping Engine

### File: `frontend/src/lib/graph-geometry.ts`

**New type:**

```typescript
type HullMode = "none" | "cluster" | "tag" | "source";
```

**New function: `computeHullGroups(memories, hullMode): Map<string, string[]>`**

Returns a map from group label to array of memory IDs.

- `"none"`: returns empty map (no hulls rendered)
- `"cluster"`: groups by `memory.cluster`. Key is cluster ID as string.
- `"tag"`: groups by full tag string. A memory with multiple tags appears in multiple groups. Only groups with 2+ members are included.
- `"source"`: groups by `memory.source`. Only groups with 2+ members are included.

**Existing functions unchanged:**

- `convexHull()`, `expandHull()`, `drawSmoothClosed()` — pure geometry, no changes
- `drawHullForSigma()` — still takes members + color, called per group
- `drawHullForGroup()` — vis-network version, kept for MiniGraph

## 3. Toolbar Redesign

### File: `frontend/src/components/graph/GraphToolbar.tsx`

**Top-level toolbar (always visible), left to right:**

1. **View toggle**: `2D | 3D` — pill-shaped segmented control
2. **Color toggle**: `Type | Cluster | Tag` — three-way segmented control
3. **Hull toggle**: `None | Cluster | Tag | Source` — four-way segmented control
4. **Entities button**: toggle on/off
5. **Gear icon (⚙)**: opens/closes settings popover
6. **Reset button (↺)**: resets all parameters to defaults

**Floating settings popover (toggled by gear icon):**

Opens below toolbar as a floating card with semi-transparent backdrop-blur background, close button, and shadow. Closes on close button click or clicking outside.

Contents:
- **Size mode**: `Connections | Importance | Uniform` — segmented control
- **Edges**: slider 0.3–0.95, step 0.05, float (API parameter)
- **Min cluster size**: slider 2–10, step 1 (API parameter)
- **Tightness**: slider 30–300, step 10 (2D only, hidden in 3D)
- **Spacing**: slider with view-dependent range (100–500 step 25 for 2D, 30–200 step 10 for 3D)

**New props added to GraphToolbar:**

- `colorMode: ColorMode`
- `onColorModeChange: (mode: ColorMode) => void`
- `hullMode: HullMode` (replacing the old `"clusters" | "tags"` type)
- `onHullModeChange: (mode: HullMode) => void`
- `showSettings: boolean`
- `onToggleSettings: () => void`

**Props removed:**

- None removed, but the hull mode prop type changes from `"clusters" | "tags"` to `HullMode`

## 4. Renderer Changes

### File: `frontend/src/components/graph/Graph2DRenderer.tsx`

**New props:**
- `colorMode: ColorMode`
- `hullMode` type changes from `"clusters" | "tags"` to `HullMode`

**Node coloring:**
- Replace `clusterColor(m.cluster)` with `resolveNodeColor(memory, colorMode)`
- Edge coloring stays as `darkenHex(sourceNodeColor, 0.6)`

**Hull drawing:**
- Replace inline cluster/tag grouping logic with `computeHullGroups(filteredMemories, hullMode)`
- Hull color per group via `resolveGroupColor(groupKey, groupIndex, colorMode, hullMode)`
- When `hullMode === "none"`: skip hull drawing entirely (clear canvas and return)

### File: `frontend/src/components/graph/Graph3DRenderer.tsx`

**New props:**
- `colorMode: ColorMode`
- `hullMode: HullMode`

**Node coloring:**
- `transformToGraphData` in `graph-utils.ts` accepts `colorMode` parameter
- Replace hard-coded `typeColor(m.memory_type)` with `resolveNodeColor(memory, colorMode)`

**Hull building (post-stabilization):**
- Replace hard-coded cluster hull logic with `computeHullGroups` call
- Build ConvexGeometry mesh per group, same 4-node minimum threshold
- Hull material color via `resolveGroupColor`
- When `hullMode === "none"`: skip hull mesh creation

### File: `frontend/src/lib/graph-utils.ts`

**`transformToGraphData` signature change:**
- Add `colorMode: ColorMode` parameter
- Replace `typeColor(m.memory_type)` with `resolveNodeColor(memory, colorMode)`

## 5. Filter Panel and Detail Panel Color Consistency

### File: `frontend/src/components/graph/GraphFilterPanel.tsx`

**New prop:** `colorMode: ColorMode`

**Behavior:**
- When `colorMode === "type"`: type items show resolved color indicators, cluster items show neutral gray
- When `colorMode === "cluster"`: cluster items show resolved color indicators, type items show neutral gray
- When `colorMode === "tag"`: tag category headers show color indicators based on prefix color, type and cluster items show neutral gray

The active color dimension gets colored indicators; inactive dimensions go neutral.

### File: `frontend/src/components/graph/GraphDetailPanel.tsx`

**New prop:** `colorMode: ColorMode`

**Behavior:**
- Memory detail: cluster name dot and type dot colored only when that dimension is the active color mode
- Summary view: top clusters list, types list, sources list — color dots respect active color mode
- Inactive dimensions show neutral gray dots

## 6. Page-Level State

### File: `frontend/src/pages/UnifiedGraph.tsx`

**New state:**
- `colorMode: ColorMode` — default `"type"`
- `hullMode` default changes from `"clusters"` to `"none"`
- `showSettings: boolean` — default `false`

**Removed state:**
- None removed, but `hullMode` type widens from `"clusters" | "tags"` to `HullMode`

**Reset behavior:**
- `handleReset()` sets `colorMode` to `"type"`, `hullMode` to `"none"`, `showSettings` to `false`, plus all existing resets

**Prop threading:**
- `colorMode` and `hullMode` passed to active renderer, toolbar, filter panel, detail panel
- `showSettings` and `onToggleSettings` passed to toolbar

## Files Changed

| File | Change Type |
|------|-------------|
| `frontend/src/lib/graph-colors.ts` | Major rewrite — new palette, new assignment functions |
| `frontend/src/lib/graph-geometry.ts` | Add `HullMode` type and `computeHullGroups` function |
| `frontend/src/lib/graph-utils.ts` | Add `colorMode` param to `transformToGraphData` |
| `frontend/src/components/graph/GraphToolbar.tsx` | Redesign — add color/hull toggles, settings popover |
| `frontend/src/components/graph/Graph2DRenderer.tsx` | Use `resolveNodeColor`, `computeHullGroups` |
| `frontend/src/components/graph/Graph3DRenderer.tsx` | Use `resolveNodeColor`, `computeHullGroups`, add all hull modes |
| `frontend/src/components/graph/GraphFilterPanel.tsx` | Add `colorMode` prop, conditional color indicators |
| `frontend/src/components/graph/GraphDetailPanel.tsx` | Add `colorMode` prop, conditional color indicators |
| `frontend/src/pages/UnifiedGraph.tsx` | New state, prop threading, settings popover state |

No new files. No backend changes. No new dependencies.
