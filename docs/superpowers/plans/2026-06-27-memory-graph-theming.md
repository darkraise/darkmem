# Memory Graph Theming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Memory graph (the `unified-graph` route and every surface under `frontend/src/features/graph`) follow the darkraise-ui theme — dark/light first — recoloring live without resettling node positions.

**Architecture:** A pure, mode-aware categorical palette is generated from resolved CSS theme tokens (`buildMemoryPalette`). Node hues keep fixed semantic identity; chrome (backgrounds, edges, labels, hulls, selection, hover pills) is token-derived. Because the Sigma (2D/knowledge) and react-force-graph (3D) instances persist across a theme change, a dark↔light flip recolors the existing scene in place (positions + camera preserved). Shared color helpers keep the build path and recolor path from drifting.

**Tech Stack:** React 19, TypeScript (project refs, `tsc -b`), Vitest, Sigma.js + graphology (2D), react-force-graph-3d + three.js (3D), Tailwind + darkraise-ui theme tokens.

**Spec:** `docs/superpowers/specs/2026-06-26-memory-graph-theming-design.md`

## Global Constraints

- Frontend commands run from `frontend/`. Typecheck = `npm run typecheck` (which is `tsc -b`; plain `tsc` misses project refs). Unit tests = `npm test` (vitest). Build = `npm run build`. `npm run lint` is advisory.
- English only in all code, comments, commits. Conventional Commits: `<type>(<scope>): <subject>`, imperative, ≤50 chars, no trailing period.
- Comments only where the WHY is non-obvious; no WHAT comments, no task references.
- Node hues keep fixed semantic identity (decision→violet, problem→red, fact→blue). The accent never recolors nodes — only chrome tracks the accent. This is a hard requirement, not a preference.
- Do NOT introduce a circular import. `graph-colors.ts` stays React-free and may only `import type` from `code-graph-theme.ts`.
- **Typecheck red window (expected):** Task 1 changes the signatures of `resolveNodeColor` / `resolveGroupColor` / `entityTypeColor` and drops the `UNIFIED_PALETTE` / `UNCLUSTERED_COLOR` / `ENTITY_TYPE_COLORS` exports. Project-wide `tsc -b` is therefore RED from Task 1 until every consumer is migrated (end of Task 8). Validate intermediate tasks with the unit test named in the task and a focused diff review; the full green gate (`tsc -b` + `npm test` + `npm run build` + manual) is Task 9. Each task still commits its own slice.

## File Structure

- `frontend/src/features/graph/lib/graph-colors.ts` — **pure** color math. Gains `hslToHex` (relocated here), `hexToHsl` is NOT needed (base hues are hardcoded constants), `MemoryPalette`, `buildMemoryPalette`, `clusterColor`, and the token-derived edge helpers; `resolveNodeColor`/`resolveGroupColor`/`entityTypeColor` re-signatured to take a `MemoryPalette`. Loses the exported palette constants.
- `frontend/src/features/graph/lib/__tests__/graph-colors.test.ts` — **new** unit tests for the pure palette logic.
- `frontend/src/features/graph/lib/code-graph-theme.ts` — imports `hslToHex` from graph-colors and re-exports it (compat); extracts a reusable `useGraphThemeTokens`.
- `frontend/src/features/graph/lib/memory-graph-theme.ts` — **new** `useMemoryGraphTheme()` → `{ tokens, palette }`.
- `frontend/src/features/graph/lib/graph-utils.ts` — `transformToGraphData` gains a `palette` param; drops the three re-exports.
- `frontend/src/features/graph/components/graph-2d-renderer.tsx` — tokens/palette props, in-place recolor, token-derived edges, themed diamond hover.
- `frontend/src/features/graph/lib/node-diamond-program.ts` — `drawDiamondNodeHover` takes surface colors as params.
- `frontend/src/features/graph/components/graph-3d-renderer.tsx` — reactive chrome + in-place material/link recolor.
- `frontend/src/routes/_authenticated/unified-graph.tsx` — `bg-background`, hook, prop wiring.
- `frontend/src/features/graph/components/graph-filter-panel.tsx`, `graph-detail-panel.tsx` — legend swatches via the hook + `clusterColor`.
- `frontend/src/features/graph/components/mini-graph.tsx`, `graph-skeleton.tsx` — token backgrounds + palette chips.
- `frontend/src/features/graph/components/knowledge-graph-renderer.tsx` — tokens + recolor (currently unmounted).

---

### Task 1: Mode-aware palette core in `graph-colors.ts`

**Files:**
- Modify: `frontend/src/features/graph/lib/graph-colors.ts`
- Modify: `frontend/src/features/graph/lib/code-graph-theme.ts` (move `hslToHex` out, re-export it)
- Test: `frontend/src/features/graph/lib/__tests__/graph-colors.test.ts` (create)

**Interfaces:**
- Consumes: `GraphThemeTokens` (type) from `code-graph-theme.ts`.
- Produces:
  - `hslToHex(h: number, s: number, l: number): string` (moved here, exported)
  - `interface MemoryPalette { palette: string[]; unclustered: string; entityTypeColor: (entityType: string) => string }`
  - `buildMemoryPalette(t: GraphThemeTokens): MemoryPalette`
  - `resolveNodeColor(node: { cluster: number; memory_type: string | null; tags: string[] }, colorMode: ColorMode, palette: MemoryPalette): string`
  - `resolveGroupColor(groupKey: string, groupIndex: number, colorMode: ColorMode, hullMode: string, palette: MemoryPalette): string`
  - `entityTypeColor(entityType: string, palette: MemoryPalette): string`
  - `clusterColor(palette: MemoryPalette, clusterId: number): string`
  - `memoryEdgeColor(srcHex: string, t: GraphThemeTokens): string`
  - `relationEdgeColor(t: GraphThemeTokens): string`
  - `membershipEdgeColor(t: GraphThemeTokens): string`
  - Unchanged exports kept: `hexToRgba`, `lightenHex`, `darkenHex`, `blendHex`, `type ColorMode`, `stableHash` (keep exported for reuse).
  - **Removed exports:** `UNIFIED_PALETTE`, `UNCLUSTERED_COLOR`, `ENTITY_TYPE_COLORS`, `PALETTE_200`, `PALETTE_600` (and `PALETTE_400` becomes internal/unused — delete it).

- [ ] **Step 1: Write the failing test**

Create `frontend/src/features/graph/lib/__tests__/graph-colors.test.ts`:

```ts
import { describe, it, expect } from "vitest"
import {
  buildMemoryPalette,
  resolveNodeColor,
  entityTypeColor,
  clusterColor,
  hslToHex,
} from "../graph-colors"
import type { GraphThemeTokens } from "../code-graph-theme"

function tokens(isDark: boolean): GraphThemeTokens {
  return {
    background: isDark ? "#0b0f17" : "#ffffff",
    foreground: isDark ? "#e6edf3" : "#0b0f17",
    card: "#111",
    cardForeground: "#eee",
    popover: "#111",
    popoverForeground: "#eee",
    muted: "#222",
    mutedForeground: isDark ? "#8b949e" : "#5b636d",
    border: "#333",
    primary: "#5b8cff",
    ring: "#5b8cff",
    destructive: "#ff5b5b",
    chart: ["#1", "#2", "#3", "#4", "#5"],
    primaryHue: 222,
    isDark,
    fontMono: "monospace",
  }
}

// Hue of a #rrggbb string in [0,360).
function hueOf(hex: string): number {
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const d = max - min
  if (d === 0) return 0
  let h: number
  if (max === r) h = ((g - b) / d) % 6
  else if (max === g) h = (b - r) / d + 2
  else h = (r - g) / d + 4
  h *= 60
  return (h + 360) % 360
}

function lightnessOf(hex: string): number {
  const r = parseInt(hex.slice(1, 3), 16) / 255
  const g = parseInt(hex.slice(3, 5), 16) / 255
  const b = parseInt(hex.slice(5, 7), 16) / 255
  return (Math.max(r, g, b) + Math.min(r, g, b)) / 2
}

const node = (memory_type: string | null) => ({
  cluster: -1,
  memory_type,
  tags: [] as string[],
})

describe("buildMemoryPalette", () => {
  it("produces 51 palette slots", () => {
    expect(buildMemoryPalette(tokens(true)).palette).toHaveLength(51)
  })

  it("is deterministic for a given mode", () => {
    expect(buildMemoryPalette(tokens(true)).palette).toEqual(
      buildMemoryPalette(tokens(true)).palette,
    )
  })

  it("sets unclustered to the muted foreground token", () => {
    expect(buildMemoryPalette(tokens(false)).unclustered).toBe("#5b636d")
  })
})

describe("hue identity across modes", () => {
  it("keeps decision violet and problem red in both modes", () => {
    const dark = buildMemoryPalette(tokens(true))
    const light = buildMemoryPalette(tokens(false))
    // violet ≈ 255°, red ≈ 0/360°
    expect(Math.abs(hueOf(resolveNodeColor(node("decision"), "type", dark)) - 255)).toBeLessThan(20)
    expect(Math.abs(hueOf(resolveNodeColor(node("decision"), "type", light)) - 255)).toBeLessThan(20)
    const rp = hueOf(resolveNodeColor(node("problem"), "type", dark))
    expect(Math.min(rp, 360 - rp)).toBeLessThan(20)
  })

  it("keeps entity person-hue stable across modes", () => {
    const hd = hueOf(entityTypeColor("person", buildMemoryPalette(tokens(true))))
    const hl = hueOf(entityTypeColor("person", buildMemoryPalette(tokens(false))))
    expect(Math.abs(hd - hl)).toBeLessThan(12)
  })
})

describe("mode tuning", () => {
  it("makes the base tier darker on a light surface", () => {
    const ld = lightnessOf(resolveNodeColor(node("fact"), "type", buildMemoryPalette(tokens(true))))
    const ll = lightnessOf(resolveNodeColor(node("fact"), "type", buildMemoryPalette(tokens(false))))
    expect(ll).toBeLessThan(ld)
  })
})

describe("clusterColor", () => {
  it("indexes the palette and wraps", () => {
    const p = buildMemoryPalette(tokens(true))
    expect(clusterColor(p, 0)).toBe(p.palette[0])
    expect(clusterColor(p, 51)).toBe(p.palette[0])
  })
  it("falls back to unclustered for negative ids", () => {
    const p = buildMemoryPalette(tokens(true))
    expect(clusterColor(p, -1)).toBe(p.unclustered)
  })
})

describe("entityTypeColor", () => {
  it("returns the neutral for concept and unknown types", () => {
    const p = buildMemoryPalette(tokens(true))
    expect(entityTypeColor("concept", p)).toBe(p.unclustered)
    expect(entityTypeColor("nonsense", p)).toBe(p.unclustered)
  })
})

describe("hslToHex", () => {
  it("matches known conversions", () => {
    expect(hslToHex(0, 100, 50)).toBe("#ff0000")
    expect(hslToHex(0, 0, 0)).toBe("#000000")
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run (from `frontend/`): `npm test -- graph-colors`
Expected: FAIL — `buildMemoryPalette`, `clusterColor`, `MemoryPalette`, and `hslToHex` are not exported from `graph-colors`.

- [ ] **Step 3: Relocate `hslToHex` and add the palette core**

In `graph-colors.ts`, at the top add the type-only import and the relocated `hslToHex` (copy the body verbatim from `code-graph-theme.ts`), then replace the palette constants and the three resolve functions. Final shape of the changed/added regions:

```ts
import type { GraphThemeTokens } from "./code-graph-theme"

export type ColorMode = "type" | "cluster" | "tag"

// Relocated from code-graph-theme.ts to keep all pure color math in one place
// and break the would-be import cycle (code-graph-theme imports darkenHex here).
export function hslToHex(h: number, s: number, l: number): string {
  const sat = s / 100
  const lum = l / 100
  const c = (1 - Math.abs(2 * lum - 1)) * sat
  const hp = (((h % 360) + 360) % 360) / 60
  const x = c * (1 - Math.abs((hp % 2) - 1))
  let r = 0
  let g = 0
  let b = 0
  if (hp >= 0 && hp < 1) [r, g, b] = [c, x, 0]
  else if (hp < 2) [r, g, b] = [x, c, 0]
  else if (hp < 3) [r, g, b] = [0, c, x]
  else if (hp < 4) [r, g, b] = [0, x, c]
  else if (hp < 5) [r, g, b] = [x, 0, c]
  else [r, g, b] = [c, 0, x]
  const m = lum - c / 2
  const toByte = (v: number) =>
    Math.round((v + m) * 255)
      .toString(16)
      .padStart(2, "0")
  return `#${toByte(r)}${toByte(g)}${toByte(b)}`
}

export function stableHash(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (Math.imul(31, hash) + str.charCodeAt(i)) | 0
  }
  return Math.abs(hash)
}

// 17 base hues (degrees), golden-ratio spread. Extracted once from the legacy
// reorder(PALETTE_400) ordering so the semantic identity is unchanged:
// idx4=blue→fact, idx15=violet→decision, idx0=red→problem, idx2=green→
// architecture, idx14=orange→preference, idx10=cyan→reference, idx16=
// emerald→milestone.
const BASE_HUES = [
  0, 234, 142, 351, 213, 82, 330, 199, 48, 289, 189, 43, 270, 172, 27, 255, 160,
]

// Per-mode lightness/saturation for the three palette tiers. Tier 0 carries the
// memory_type colors (all KNOWN_TYPE_INDICES are < 17); tiers 1-2 only widen the
// cluster space. Darker + a touch more saturated on a light surface.
const TIERS: Record<"dark" | "light", { l: number; s: number }[]> = {
  dark: [
    { l: 62, s: 85 },
    { l: 76, s: 70 },
    { l: 50, s: 82 },
  ],
  light: [
    { l: 46, s: 80 },
    { l: 36, s: 85 },
    { l: 58, s: 70 },
  ],
}

const ENTITY_HUES: Record<string, number> = {
  person: 213,
  service: 142,
  project: 255,
  technology: 27,
  organization: 330,
}

const KNOWN_TYPE_INDICES: Record<string, number> = {
  fact: 4,
  decision: 15,
  problem: 0,
  architecture: 2,
  preference: 14,
  reference: 10,
  milestone: 16,
}

export interface MemoryPalette {
  palette: string[]
  unclustered: string
  entityTypeColor: (entityType: string) => string
}

export function buildMemoryPalette(t: GraphThemeTokens): MemoryPalette {
  const tiers = t.isDark ? TIERS.dark : TIERS.light
  const palette: string[] = []
  for (let i = 0; i < 51; i++) {
    const hue = BASE_HUES[i % 17]!
    const tier = tiers[Math.floor(i / 17)]!
    palette.push(hslToHex(hue, tier.s, tier.l))
  }
  const unclustered = t.mutedForeground
  const tier0 = tiers[0]!
  const entityTypeColor = (entityType: string): string => {
    const hue = ENTITY_HUES[entityType]
    return hue === undefined ? unclustered : hslToHex(hue, tier0.s, tier0.l)
  }
  return { palette, unclustered, entityTypeColor }
}

export function resolveNodeColor(
  node: { cluster: number; memory_type: string | null; tags: string[] },
  colorMode: ColorMode,
  palette: MemoryPalette,
): string {
  if (colorMode === "cluster") {
    if (node.cluster < 0) return palette.unclustered
    return palette.palette[node.cluster % 51] ?? palette.unclustered
  }
  if (colorMode === "type") {
    if (!node.memory_type) return palette.unclustered
    const idx = KNOWN_TYPE_INDICES[node.memory_type]
    if (idx !== undefined) return palette.palette[idx] ?? palette.unclustered
    return palette.palette[stableHash(node.memory_type) % 51] ?? palette.unclustered
  }
  if (!node.tags || node.tags.length === 0) return palette.unclustered
  const prefix = (node.tags[0] ?? "").split("/")[0] ?? ""
  return palette.palette[stableHash(prefix) % 51] ?? palette.unclustered
}

export function resolveGroupColor(
  groupKey: string,
  groupIndex: number,
  colorMode: ColorMode,
  hullMode: string,
  palette: MemoryPalette,
): string {
  if (colorMode === hullMode && colorMode === "cluster") {
    const id = parseInt(groupKey, 10)
    if (!isNaN(id) && id >= 0) return palette.palette[id % 51] ?? palette.unclustered
    return palette.unclustered
  }
  if (colorMode === hullMode && colorMode === "tag") {
    const prefix = groupKey.split("/")[0] ?? ""
    return palette.palette[stableHash(prefix) % 51] ?? palette.unclustered
  }
  return palette.palette[groupIndex % 51] ?? palette.unclustered
}

export function entityTypeColor(entityType: string, palette: MemoryPalette): string {
  return palette.entityTypeColor(entityType)
}

export function clusterColor(palette: MemoryPalette, clusterId: number): string {
  if (clusterId < 0) return palette.unclustered
  return palette.palette[clusterId % palette.palette.length] ?? palette.unclustered
}

// Token-derived edge colors. memoryEdgeColor keeps the source-node tint; the
// other two stop being hardcoded so they track the surface.
export function memoryEdgeColor(srcHex: string, t: GraphThemeTokens): string {
  return darkenHex(srcHex, t.isDark ? 0.55 : 0.3)
}

export function relationEdgeColor(t: GraphThemeTokens): string {
  // entity-relation edges: accent-tinted, semi-transparent.
  return hexToRgba(t.primary, t.isDark ? 0.55 : 0.5)
}

export function membershipEdgeColor(t: GraphThemeTokens): string {
  // entity↔memory membership edges: faint, derived from the border token.
  return hexToRgba(t.border, t.isDark ? 0.25 : 0.4)
}
```

Delete the old `PALETTE_400` / `PALETTE_200` / `PALETTE_600` / `HUE_ORDER` / `reorder` / `UNIFIED_PALETTE` / `UNCLUSTERED_COLOR` / `ENTITY_TYPE_COLORS` definitions and the old `resolveNodeColor`/`resolveGroupColor`/`entityTypeColor` bodies. Keep `hexToRgba`, `lightenHex`, `darkenHex`, `blendHex` exactly as they are (they are referenced above and elsewhere).

Then in `code-graph-theme.ts`: delete its local `hslToHex` definition and instead import + re-export it from graph-colors. At the top imports add `hslToHex` to the existing `graph-colors` import line:

```ts
import { darkenHex, hslToHex } from "./graph-colors"
```

and add a re-export near the other exports so the existing test keeps importing it from here:

```ts
export { hslToHex }
```

(`parseHsl` / `parseHslTriplet` stay in `code-graph-theme.ts`; they do not call `hslToHex`.)

- [ ] **Step 4: Run the test to verify it passes**

Run (from `frontend/`): `npm test -- graph-colors`
Expected: PASS (all cases green).

Also run `npm test -- code-graph-theme` and expect PASS (the relocated `hslToHex` is re-exported, so the existing test is unaffected).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/lib/graph-colors.ts \
        frontend/src/features/graph/lib/code-graph-theme.ts \
        frontend/src/features/graph/lib/__tests__/graph-colors.test.ts
git commit -m "feat(graph): mode-aware memory palette + token edge colors"
```

---

### Task 2: Reusable token hook + memory theme hook

**Files:**
- Modify: `frontend/src/features/graph/lib/code-graph-theme.ts`
- Create: `frontend/src/features/graph/lib/memory-graph-theme.ts`

**Interfaces:**
- Consumes: `resolveGraphTokens`, `GraphThemeTokens` (code-graph-theme); `buildMemoryPalette`, `MemoryPalette` (graph-colors).
- Produces:
  - `useGraphThemeTokens(rootRef?: RefObject<HTMLElement | null>): GraphThemeTokens` (in code-graph-theme.ts) — resolves tokens from `rootRef.current` (default `document.documentElement`) and re-resolves on a `MutationObserver` of `document.documentElement`'s `style` attribute.
  - `useMemoryGraphTheme(): { tokens: GraphThemeTokens; palette: MemoryPalette }` (in memory-graph-theme.ts).

- [ ] **Step 1: Extract `useGraphThemeTokens` in `code-graph-theme.ts`**

The existing `useCodeGraphTheme` already contains the resolve-and-observe logic. Extract it into a standalone hook and have `useCodeGraphTheme` call it. Add:

```ts
export function useGraphThemeTokens(
  rootRef?: RefObject<HTMLElement | null>,
): GraphThemeTokens {
  const [tokens, setTokens] = useState<GraphThemeTokens>(FALLBACK_TOKENS)

  useEffect(() => {
    const el = rootRef?.current ?? document.documentElement
    const resolve = () => setTokens(resolveGraphTokens(el))
    resolve()

    const observer = new MutationObserver(resolve)
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["style"],
    })
    return () => observer.disconnect()
  }, [rootRef])

  return tokens
}
```

Refactor the body of `useCodeGraphTheme` so its token state comes from `useGraphThemeTokens(rootRef)` (delete its inline `useState` + `useEffect` for tokens; keep the `useMemo` that builds `nodeColors`/`edgeColors`). Net behavior is unchanged.

- [ ] **Step 2: Create `memory-graph-theme.ts`**

```ts
import { useMemo } from "react"
import { useGraphThemeTokens, type GraphThemeTokens } from "./code-graph-theme"
import { buildMemoryPalette, type MemoryPalette } from "./graph-colors"

export function useMemoryGraphTheme(): {
  tokens: GraphThemeTokens
  palette: MemoryPalette
} {
  const tokens = useGraphThemeTokens()
  const palette = useMemo(() => buildMemoryPalette(tokens), [tokens])
  return { tokens, palette }
}
```

- [ ] **Step 3: Verify the Code graph is unaffected**

Run (from `frontend/`): `npm test -- code-graph-theme`
Expected: PASS (the existing `useCodeGraphTheme` test still green).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/graph/lib/code-graph-theme.ts \
        frontend/src/features/graph/lib/memory-graph-theme.ts
git commit -m "feat(graph): shared theme-token hook + memory theme hook"
```

---

### Task 3: `transformToGraphData` palette param + drop re-exports

**Files:**
- Modify: `frontend/src/features/graph/lib/graph-utils.ts`

**Interfaces:**
- Consumes: `resolveNodeColor`, `entityTypeColor`, `MemoryPalette` (graph-colors).
- Produces: `transformToGraphData(data, sizeMode, filters, colorMode, entityLayerEnabled, entities, entityRelations, palette: MemoryPalette): GraphData3D`.

- [ ] **Step 1: Update imports and remove re-exports**

At the top of `graph-utils.ts`:
- Change `import { resolveNodeColor, entityTypeColor } from "./graph-colors"` to also import the type:
  ```ts
  import {
    resolveNodeColor,
    entityTypeColor,
    type MemoryPalette,
  } from "./graph-colors"
  ```
- Delete the re-export block:
  ```ts
  export { resolveNodeColor, entityTypeColor }
  export {
    UNIFIED_PALETTE,
    UNCLUSTERED_COLOR,
    ENTITY_TYPE_COLORS,
  } from "./graph-colors"
  ```
  Keep `export type { ColorMode }` if present (re-export the type from graph-colors instead: `export type { ColorMode } from "./graph-colors"`).

- [ ] **Step 2: Thread the palette through `transformToGraphData`**

Add `palette: MemoryPalette` as the final parameter of `transformToGraphData`. Update the two color call sites:
- `color: resolveNodeColor(m, colorMode),` → `color: resolveNodeColor(m, colorMode, palette),`
- `color: entityTypeColor(e.entity_type),` → `color: entityTypeColor(e.entity_type, palette),`

- [ ] **Step 3: Typecheck the touched file**

Run (from `frontend/`): `npx tsc -b --noEmit` is not used here (project refs). Instead confirm the file has no local type errors by checking it compiles within the final gate; for now run `npm test -- graph` to ensure no graph-utils-dependent test regressed (none expected). Project-wide `tsc -b` stays red until Task 8 — expected per Global Constraints.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/graph/lib/graph-utils.ts
git commit -m "feat(graph): thread memory palette through graph transform"
```

---

### Task 4: 2D renderer — tokens, in-place recolor, themed edges + hover

**Files:**
- Modify: `frontend/src/features/graph/components/graph-2d-renderer.tsx`
- Modify: `frontend/src/features/graph/lib/node-diamond-program.ts`
- Modify: `frontend/src/routes/_authenticated/unified-graph.tsx` (2D wiring + `bg-background` + hook)

**Interfaces:**
- Consumes: `useMemoryGraphTheme` (route), `MemoryPalette`/`GraphThemeTokens`, the color + edge helpers from graph-colors, `seededUnit` (code-graph-theme).
- Produces: `Graph2DRenderer` gains required props `tokens: GraphThemeTokens` and `palette: MemoryPalette`.

- [ ] **Step 1: Make `drawDiamondNodeHover` take surface colors**

In `node-diamond-program.ts`, change the signature and the two hardcoded colors:

```ts
export function drawDiamondNodeHover(
  context: CanvasRenderingContext2D,
  data: PartialButFor<NodeDisplayData, "x" | "y" | "size" | "label" | "color">,
  settings: Settings,
  fill = "#FFF",
  shadow = "#000",
): void {
```

Replace `context.fillStyle = "#FFF"` with `context.fillStyle = fill` and `context.shadowColor = "#000"` with `context.shadowColor = shadow`. The defaults preserve current behavior for any other caller.

- [ ] **Step 2: Wire tokens/palette into the route and pass to the 2D renderer**

In `unified-graph.tsx`:
- Add the import: `import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"`.
- Inside `UnifiedGraphPage`, add: `const { tokens, palette } = useMemoryGraphTheme()`.
- Swap only the `bg-[#0d1117]` **utility class** for `bg-background` in the two graph-stage divs, preserving every other class. The two tags differ, so do not blanket-replace the whole opening tag:
  - stage (~line 158): `<div className="absolute inset-0 bg-[#0d1117]">` → `<div className="absolute inset-0 bg-background">`
  - loading overlay (~line 193): `<div className="absolute inset-0 z-30 bg-[#0d1117]">` → `<div className="absolute inset-0 z-30 bg-background">` (the `z-30` keeps the overlay above the toolbar/filter button during a refetch — do not drop it).
- On the `<Graph2DRenderer ... />` element add two props: `tokens={tokens}` and `palette={palette}`.

- [ ] **Step 3: Consume tokens/palette in the 2D renderer + add recolor**

In `graph-2d-renderer.tsx`:

- Extend `Graph2DRendererProps` with `tokens: GraphThemeTokens` and `palette: MemoryPalette`; import the types and the new helpers:
  ```ts
  import {
    resolveNodeColor,
    resolveGroupColor,
    entityTypeColor,
    lightenHex,
    darkenHex,
    memoryEdgeColor,
    relationEdgeColor,
    membershipEdgeColor,
    type ColorMode,
    type MemoryPalette,
  } from "@/features/graph/lib/graph-colors"
  import { seededUnit, type GraphThemeTokens } from "@/features/graph/lib/code-graph-theme"
  ```
  (Drop `resolveGraphTokens` from the import — it is no longer called here.)

- Add refs that the reducers/hull-draw/recolor read, kept current every render:
  ```ts
  const tokensRef = useRef(tokens)
  tokensRef.current = tokens
  const paletteRef = useRef(palette)
  paletteRef.current = palette
  ```

- Add a local color dispatcher used by BOTH build and recolor (single source of truth):
  ```ts
  const nodeBaseColor = (attrs: Record<string, unknown>): string => {
    if (attrs._kind === "entity") {
      const et = (attrs._entityData as { entity_type: string } | undefined)?.entity_type ?? ""
      return entityTypeColor(et, paletteRef.current)
    }
    const m = attrs._mem as { cluster: number; memory_type: string | null; tags: string[] }
    return resolveNodeColor(m, colorModeRef.current, paletteRef.current)
  }
  const edgeBaseColor = (kind: string, srcHex: string): string => {
    if (kind === "relation") return relationEdgeColor(tokensRef.current)
    if (kind === "membership") return membershipEdgeColor(tokensRef.current)
    return memoryEdgeColor(srcHex, tokensRef.current)
  }
  ```

- In `buildGraph`, replace the build-time token resolution:
  ```ts
  // remove: const t = resolveGraphTokens(document.documentElement)
  const t = tokensRef.current
  const mutedColor = t.mutedForeground
  const dimColor = t.border
  const labelColorToken = t.foreground
  ```
  Then change node creation to store what recolor needs and use the dispatcher:
  - Memory nodes: compute `const color = nodeBaseColor({ _kind: "memory", _mem: { cluster: m.cluster, memory_type: m.memory_type, tags: m.tags } })`; add `_mem: { cluster: m.cluster, memory_type: m.memory_type, tags: m.tags }` to the node attributes (alongside `_kind: "memory"`). Keep `borderColor: darkenHex(color)`.
  - Memory edges: replace `const edgeColor = darkenHex(srcColor, 0.6)` with `const edgeColor = edgeBaseColor("memory", srcColor)`, and add `_edgeKind: "memory"` to the edge attributes.
  - Entity nodes: `const bg = entityTypeColor(ent.entity_type, paletteRef.current)` (it already stores `_entityData: ent`, which carries `entity_type`).
  - Entity-relation edges: replace `color: "#ffa65770"` with `color: edgeBaseColor("relation", "")` and add `_edgeKind: "relation"`.
  - Membership edges: replace `color: "#58606920"` with `color: edgeBaseColor("membership", "")` and add `_edgeKind: "membership"`.

- Change the diamond hover wrapper to pass surface colors:
  ```ts
  defaultDrawNodeHover: (context, data, settings) => {
    if (data.type === "diamond") {
      drawDiamondNodeHover(
        context, data, settings,
        tokensRef.current.popover,
        tokensRef.current.isDark ? "#000" : tokensRef.current.border,
      )
    } else {
      drawDiscNodeHover(context, data, settings)
    }
  },
  ```

- In `nodeReducer` / `edgeReducer`, replace the captured `mutedColor` / `dimColor` / `labelColorToken` references with reads from `tokensRef.current` (e.g. `const t = tokensRef.current` at the top of each reducer, then `t.mutedForeground` / `t.border` / `t.foreground`). Behavior is identical at build time and now tracks live theme.

- In `drawHulls`, read the live palette/token: pass `paletteRef.current` as the new last arg to `resolveGroupColor(groupKey, idx, colorModeRef.current, hullModeRef.current, paletteRef.current)`, and use `tokensRef.current.foreground` for `hullCtx.strokeStyle` (replacing the captured `labelColorToken`).

- Add the recolor function and effect (place after `buildGraph` and its effect):
  ```ts
  useEffect(() => {
    const sigma = sigmaRef.current
    const graph = graphRef.current
    if (!sigma || !graph) return // initial mount: buildGraph already painted

    graph.forEachNode((id, attrs) => {
      const color = nodeBaseColor(attrs)
      graph.mergeNodeAttributes(id, { color, borderColor: darkenHex(color) })
    })
    graph.forEachEdge((edge, attrs, _s, _t, sAttrs) => {
      const kind = (attrs._edgeKind as string) ?? "memory"
      const srcHex = (sAttrs.color as string) ?? tokensRef.current.mutedForeground
      graph.setEdgeAttribute(edge, "color", edgeBaseColor(kind, srcHex))
    })
    sigma.setSetting("labelColor", { color: tokensRef.current.foreground })
    sigma.setSetting("edgeLabelColor", { color: tokensRef.current.mutedForeground })
    sigma.setSetting("defaultNodeColor", tokensRef.current.mutedForeground)
    sigma.refresh()
    // Keyed on a primitive theme signature so incidental re-renders don't recolor.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [`${tokens.background}:${tokens.isDark}`])
  ```
  Note: `nodeBaseColor` / `edgeBaseColor` read from refs, so they are safe to call here without being effect deps; the inline template string is the only dep.

- [ ] **Step 4: Manual verification**

Run the dev servers (`./scripts/start_dev_server.sh` and `cd frontend && npm run dev`), open the Memory graph in 2D, and toggle the theme mode (light/dark) via the theme switcher. Confirm: the stage background flips, node colors stay semantically the same but readable on both surfaces, edges/labels/hulls/hover pill flip, and **node positions and camera do not move** on the flip.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/graph/components/graph-2d-renderer.tsx \
        frontend/src/features/graph/lib/node-diamond-program.ts \
        frontend/src/routes/_authenticated/unified-graph.tsx
git commit -m "feat(graph): theme-aware 2D memory graph with in-place recolor"
```

---

### Task 5: 3D renderer — reactive chrome + in-place material/link recolor

**Files:**
- Modify: `frontend/src/features/graph/components/graph-3d-renderer.tsx`
- Modify: `frontend/src/routes/_authenticated/unified-graph.tsx` (3D wiring + palette into transform)

**Interfaces:**
- Consumes: `useMemoryGraphTheme` output (route), `resolveNodeColor`, `entityTypeColor`, `memoryEdgeColor`, `relationEdgeColor`, `MemoryPalette`/`GraphThemeTokens`.
- Produces: `Graph3DRenderer` gains required props `tokens: GraphThemeTokens` and `palette: MemoryPalette`.

- [ ] **Step 1: Pass palette into the 3D transform and renderer (route)**

In `unified-graph.tsx`:
- In the `graphData3D` memo, pass `palette` as the final arg to `transformToGraphData(...)`. Add `palette` to the memo dep array's neighbors but guard it: keep node-object identity stable by NOT recomputing on palette alone — append the comment and disable line:
  ```ts
  // palette intentionally excluded from deps: the renderer recolors node
  // materials in place so a theme flip preserves 3D positions. colorMode (a dep)
  // still recomputes with the current palette.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  ```
  (Place the disable comment immediately above the dependency array of the `graphData3D` `useMemo`.)
- On `<Graph3DRenderer ... />` add `tokens={tokens}` and `palette={palette}`.

- [ ] **Step 2: Reactive chrome + recolor in the 3D renderer**

In `graph-3d-renderer.tsx`:

- Extend props with `tokens: GraphThemeTokens` and `palette: MemoryPalette`; import:
  ```ts
  import {
    resolveNodeColor,
    resolveGroupColor,
    entityTypeColor,
    memoryEdgeColor,
    relationEdgeColor,
    type MemoryPalette,
  } from "@/features/graph/lib/graph-colors"
  import { type GraphThemeTokens } from "@/features/graph/lib/code-graph-theme"
  ```
  (Keep the existing `resolveGroupColor` import — it stays a consumer, see Step 3 — and drop `resolveGraphTokens`, which is no longer called.)

- Replace the one-shot `chrome` memo with a reactive value from the prop:
  ```ts
  const chrome = useMemo(
    () => ({ background: tokens.background, highlight: tokens.foreground }),
    [tokens],
  )
  ```

- Add a tokens ref for the link accessor and a palette ref for `buildHulls`:
  ```ts
  const tokensRef = useRef(tokens)
  tokensRef.current = tokens
  const paletteRef = useRef(palette)
  paletteRef.current = palette
  ```

- Add a node-color helper mirroring the 2D dispatcher:
  ```ts
  const colorForNode = (n: Node3D, p: MemoryPalette): string =>
    n.nodeKind === "entity"
      ? entityTypeColor(n.entityType ?? "", p)
      : resolveNodeColor(
          { cluster: n.cluster, memory_type: n.memoryType, tags: n.tags },
          colorMode,
          p,
        )
  ```

- In `nodeThreeObject`, color from the live palette:
  ```ts
  const color = colorForNode(node, palette)
  const material = new THREE.MeshPhongMaterial({
    color, emissive: color, emissiveIntensity: 0.1, transparent: true, opacity: 0.9,
  })
  ```
  (Replace the two `node.color` reads in `nodeThreeObject` with `color`.)

- Migrate the hull-color call (this is the orphaned 5th consumer of the
  re-signatured `resolveGroupColor`). In `buildHulls`, change
  `const hullColor = resolveGroupColor(groupKey, groupIdx, colorMode, hullMode)`
  to `const hullColor = resolveGroupColor(groupKey, groupIdx, colorMode, hullMode, paletteRef.current)`.
  Read `paletteRef.current` (not the `palette` prop) so `buildHulls`'s
  `useCallback` deps (`[graphData, colorMode, hullMode]`) stay unchanged and its
  identity stays stable. Without this the call is a 4-arg invocation against the
  new 5-arg signature — a hard `TS2554` — and 3D hulls would never recolor.

- Add a recolor effect that recomputes node colors in place, rebuilds the hull
  meshes with the current palette, and repaints (none of this touches node
  positions):
  ```ts
  useEffect(() => {
    for (const node of graphData.nodes) {
      const color = colorForNode(node, palette)
      node.color = color
      const obj = (node as any).__threeObj
      if (!obj) continue
      const mat = obj.material as THREE.MeshPhongMaterial
      mat.color.set(color)
      mat.emissive.set(color)
    }
    buildHulls() // disposes + rebuilds hull meshes from current positions + palette
    fgRef.current?.refresh?.()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [`${tokens.background}:${tokens.isDark}:${colorMode}`])
  ```
  (`buildHulls` is intentionally not an effect dep — the effect re-runs on the
  theme/colorMode key and calls the latest `buildHulls` closure, which reads the
  current `paletteRef`.)

- Replace the hardcoded `linkColor` constants with token-derived values read from `tokensRef.current` (so they track the theme), keeping the selected/neighbor logic. Replace the literal returns:
  - `"#ffa65790"` → `relationEdgeColor(tokensRef.current)`
  - `"rgba(76, 201, 240, 0.6)"` → `memoryEdgeColor(tokensRef.current.primary, tokensRef.current)`
  - `"#ffa657"` → `relationEdgeColor(tokensRef.current)`
  - `"#4CC9F0"` → `tokensRef.current.primary`
  - `"#ffa65740"` → `relationEdgeColor(tokensRef.current)`
  - `"rgba(76, 201, 240, 0.25)"` → `memoryEdgeColor(tokensRef.current.primary, tokensRef.current)`
  (Exact saturation/alpha tuning is acceptable to adjust during manual verification; the requirement is no hardcoded hex.)
  The recolor effect's `fgRef.current?.refresh?.()` triggers react-force-graph to re-read `linkColor`. If links do not repaint on a settled graph during manual verification, add a `const [linkVer, setLinkVer] = useState(0)` state, bump it in the recolor effect, and add `key={linkVer}`-style dependency by passing `linkColor` as a `useCallback` keyed on `linkVer` (documented fallback from the spec).

- [ ] **Step 3: Manual verification**

In the running app, switch the Memory graph to 3D, enable a hull mode, and toggle the theme mode. Confirm the scene background, node materials, selection ring, link colors, and hull fills all flip, and that node positions do not re-simulate on the flip.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/graph/components/graph-3d-renderer.tsx \
        frontend/src/routes/_authenticated/unified-graph.tsx
git commit -m "feat(graph): theme-aware 3D memory graph with in-place recolor"
```

---

### Task 6: Legend panels — filter + detail swatches

**Files:**
- Modify: `frontend/src/features/graph/components/graph-filter-panel.tsx`
- Modify: `frontend/src/features/graph/components/graph-detail-panel.tsx`

**Interfaces:**
- Consumes: `useMemoryGraphTheme`, `resolveNodeColor`, `entityTypeColor`, `clusterColor`.

- [ ] **Step 1: Filter panel**

In `graph-filter-panel.tsx`:
- Imports: replace the `graph-colors` import group with
  ```ts
  import { resolveNodeColor, entityTypeColor, clusterColor } from "@/features/graph/lib/graph-colors"
  import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
  ```
  (Remove `UNIFIED_PALETTE`.)
- Inside the component add: `const { palette } = useMemoryGraphTheme()`.
- Pass `palette` to the three color sites:
  - line ~112: `resolveNodeColor({ cluster: -1, memory_type: null, tags: [category + "/x"] }, "tag", palette)`; the `"#8b949e"` fallback → `palette.unclustered`.
  - line ~175: `resolveNodeColor({ cluster: -1, memory_type: realType, tags: [] }, "type", palette)`; `"#8b949e"` → `palette.unclustered`.
  - line ~253 (cluster swatch, a ternary `colorMode === "cluster" ? UNIFIED_PALETTE[cid % UNIFIED_PALETTE.length] : "#8b949e"`): convert **both** branches → `colorMode === "cluster" ? clusterColor(palette, cid) : palette.unclustered`. Do not leave the `: "#8b949e"` else-branch hardcoded — it is the swatch shown in non-cluster modes and must track the theme.
  - line ~295: `entityTypeColor(etype)` → `entityTypeColor(etype, palette)`.

- [ ] **Step 2: Detail panel**

In `graph-detail-panel.tsx`:
- Imports: replace the `graph-colors` import group with
  ```ts
  import { resolveNodeColor, entityTypeColor, clusterColor } from "@/features/graph/lib/graph-colors"
  import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
  ```
  (Remove `UNIFIED_PALETTE`.)
- Inside the component that uses these (the one with `colorMode` at line ~199/206 and the entity helper at line ~107), add `const { palette } = useMemoryGraphTheme()`. If the color calls live in more than one component in this file, call the hook in each component that needs `palette` (hooks are cheap and memoized).
- Update every site found by grep:
  - line ~107 and ~522: `entityTypeColor(entity.entity_type)` / `entityTypeColor(etype)` → add `, palette`.
  - lines ~236, ~259, ~442, ~476: `resolveNodeColor(<node>, <mode>)` → add `, palette`; any `"#8b949e"` fallback → `palette.unclustered`.
  - lines ~289, ~415 (cluster swatches, each a ternary `colorMode === "cluster" ? UNIFIED_PALETTE[<id> % UNIFIED_PALETTE.length] : "#8b949e"`): convert **both** branches → `colorMode === "cluster" ? clusterColor(palette, <id>) : palette.unclustered`. Do not leave the `: "#8b949e"` else-branch hardcoded.

- [ ] **Step 3: Manual verification**

In the running app, open the filter panel and the detail panel with a memory selected; toggle the theme. Confirm the type/cluster/tag/entity swatches recolor with the graph and stay legible in both modes.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/graph/components/graph-filter-panel.tsx \
        frontend/src/features/graph/components/graph-detail-panel.tsx
git commit -m "feat(graph): theme-aware legend swatches in graph panels"
```

---

### Task 7: Mini-graph + skeleton backgrounds

**Files:**
- Modify: `frontend/src/features/graph/components/mini-graph.tsx`
- Modify: `frontend/src/features/graph/components/graph-skeleton.tsx`

**Interfaces:**
- Consumes: `useMemoryGraphTheme`, `entityTypeColor`.

- [ ] **Step 1: Mini-graph**

In `mini-graph.tsx`:
- Replace the import `import { entityTypeColor } from "@/features/graph/lib/graph-colors"` with both:
  ```ts
  import { entityTypeColor } from "@/features/graph/lib/graph-colors"
  import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
  ```
- Add `const { palette } = useMemoryGraphTheme()` in the component.
- Replace the container class `bg-[#0d1117]` with `bg-background`.
- The two chip color sites become `entityTypeColor(e.entity_type, palette) + "30"` and `entityTypeColor(e.entity_type, palette)`.

- [ ] **Step 2: Skeleton**

In `graph-skeleton.tsx`:
- Replace `bg-[#0d1117]` (the outer wrapper) with `bg-background`.
- Replace `bg-[#21262d]` (the skeleton bars) with `bg-muted`.
- Replace the edge style `background: "rgba(139,148,158,0.15)"` with `background: "hsl(var(--border) / 0.5)"`.
- Leave the decorative `SKEL_CLUSTERS` RGB hues and their low-alpha gradients/dots as-is (translucent, theme-neutral).

- [ ] **Step 3: Manual verification**

In the running app: with a memory selected, confirm the mini-graph background follows the theme and its entity chips recolor. Trigger a graph reload (e.g. change a filter that refetches) and confirm the loading skeleton renders on the themed background in both modes.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/graph/components/mini-graph.tsx \
        frontend/src/features/graph/components/graph-skeleton.tsx
git commit -m "feat(graph): theme-aware mini-graph and loading skeleton"
```

---

### Task 8: Knowledge renderer (currently unmounted)

**Files:**
- Modify: `frontend/src/features/graph/components/knowledge-graph-renderer.tsx`

**Interfaces:**
- Consumes: `useGraphThemeTokens` (or accepts a `tokens`/`palette` prop). Since this renderer is not currently mounted by any route, it self-resolves via the hook to stay self-contained.
- Produces: no new external interface; behavior matches the 2D renderer's theming.

- [ ] **Step 1: Resolve tokens/palette from the hook and store refs**

In `knowledge-graph-renderer.tsx`:
- Imports:
  ```ts
  import { entityTypeColor, lightenHex, darkenHex, membershipEdgeColor } from "@/features/graph/lib/graph-colors"
  import { seededUnit } from "@/features/graph/lib/code-graph-theme"
  import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
  ```
  (Drop `resolveGraphTokens`.)
- In the component: `const { tokens, palette } = useMemoryGraphTheme()` and refs `tokensRef`/`paletteRef` kept current every render (as in Task 4).

- [ ] **Step 2: Use tokens/palette at build and add recolor**

- Replace `const t = resolveGraphTokens(document.documentElement)` with `const t = tokensRef.current`.
- Node color: `const color = entityTypeColor(e.entity_type, paletteRef.current)` (store `_entityType: e.entity_type` on the node for recolor).
- Edge color: replace `color: "#58606980"` with `color: membershipEdgeColor(tokensRef.current)` and tag the edge `_edgeKind: "membership"`.
- Reducers: read `tokensRef.current` for muted/dim/label (as in Task 4).
- Add a recolor effect keyed on `` `${tokens.background}:${tokens.isDark}` `` that walks nodes (recompute `entityTypeColor(_entityType, paletteRef.current)` + `darkenHex`), walks edges (`membershipEdgeColor`), updates `labelColor`/`edgeLabelColor`/`defaultNodeColor` settings, and `sigma.refresh()` — mirroring Task 4's effect (no entity/memory split needed).

- [ ] **Step 3: Verify it compiles in isolation**

Since the component is unmounted, there is no manual check. Confirm no type errors remain here at the final gate (Task 9).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/features/graph/components/knowledge-graph-renderer.tsx
git commit -m "feat(graph): theme-aware knowledge-graph renderer"
```

---

### Task 9: Full integration gate

**Files:** none (verification only).

- [ ] **Step 1: Typecheck (project-wide, must be green now)**

Run (from `frontend/`): `npm run typecheck`
Expected: PASS (`tsc -b` clean). If any consumer of the old `UNIFIED_PALETTE`/`UNCLUSTERED_COLOR`/`ENTITY_TYPE_COLORS` exports or the old color-function signatures remains, it surfaces here — fix it and re-run.

- [ ] **Step 2: Unit tests**

Run: `npm test`
Expected: PASS, including the new `graph-colors.test.ts` and the unchanged `code-graph-theme.test.tsx`.

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: PASS.

- [ ] **Step 4: Manual cross-surface verification**

With the dev servers running, on the Memory graph toggle dark↔light and confirm in one pass that **all** of these flip and stay legible, and that a flip preserves 2D/3D node positions and camera:
- 2D graph (nodes, edges, labels, hulls, selection highlight, entity diamond hover pill)
- 3D graph (background, node materials, selection ring, links, hull fills)
- loading skeleton
- mini-graph (background + entity chips)
- filter panel + detail panel legend swatches

- [ ] **Step 5: Final commit (if any tuning landed)**

```bash
git add -A
git commit -m "chore(graph): finalize memory-graph theming gate"
```

(Skip if Steps 1-4 required no edits.)

---

## Self-Review

**Spec coverage:** Every spec section maps to a task — palette/edge model + `hslToHex` relocation (Task 1), token hooks (Task 2), transform + re-export removal (Task 3), 2D renderer + diamond hover + route bg/wiring (Task 4), 3D renderer + 3D wiring (Task 5), legend panels incl. direct `clusterColor` indexing (Task 6), mini-graph + skeleton (Task 7), knowledge renderer (Task 8), full gate + manual matrix (Task 9). The spec's known risks (themeKey-string keying, `refresh()` fallback, colorMode-resettle note) are encoded in Tasks 4/5.

**Placeholder scan:** No TBD/TODO; every code step shows the actual change. The only "tune during verification" notes are color saturation/alpha constants, which are explicitly allowed to be adjusted under the manual gate.

**Type consistency:** `MemoryPalette` shape (`palette`/`unclustered`/`entityTypeColor`) is identical across Tasks 1, 3, 4, 5, 6, 7. `resolveNodeColor`/`resolveGroupColor`/`entityTypeColor`/`clusterColor` signatures used in consumer tasks match Task 1's `Produces`. Both `resolveGroupColor` call sites are migrated to the new 5-arg signature: the 2D hull call in Task 4 Step 3 and the 3D hull call (`buildHulls`) in Task 5 Step 2. Edge helpers (`memoryEdgeColor`/`relationEdgeColor`/`membershipEdgeColor`) are used with the signatures defined in Task 1. The recolor effects in Tasks 4/5/8 all key on the same primitive `` `${tokens.background}:${tokens.isDark}` `` shape (Task 5 adds `:${colorMode}`).

**Post-review corrections (2026-06-27, adversarial multi-agent review):** four verified defects fixed inline — (1) the orphaned 3D `resolveGroupColor`/`buildHulls` consumer is now migrated and hulls recolor on flip (Task 5); (2) the `z-30` loading-overlay swap now preserves the class (Task 4); (3) the unused `type MemoryPalette` import was removed from the Task 1 test so `tsc -b` (`noUnusedLocals`) passes; (4) the three cluster-swatch `: "#8b949e"` else-branches now convert to `palette.unclustered` (Task 6).
