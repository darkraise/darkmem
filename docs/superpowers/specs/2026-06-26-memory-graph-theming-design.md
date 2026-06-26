# Memory graph — theme-system adaptation (dark/light first)

Date: 2026-06-26
Status: design approved (pending written-spec review)
Scope: `frontend/src/features/graph` Memory-graph surfaces + the
`unified-graph` route.

## Problem

The **Code graph** already adapts to the darkraise-ui theme system: it
resolves CSS theme tokens (`code-graph-theme.ts` → `resolveGraphTokens`),
derives every node/edge/chrome color from them, and re-resolves live when
the active theme changes (a `MutationObserver` on `document.documentElement`'s
`style` attribute inside `useCodeGraphTheme`). Its renderer container is
`bg-background`.

The **Memory graph** does none of this. It is hardcoded to the GitHub-dark
palette and never reacts to a theme change:

- The graph stage, loading overlay, skeleton, and mini-graph paint a literal
  `bg-[#0d1117]` (plus `bg-[#21262d]` skeleton bars and a `rgba(139,148,158,…)`
  edge). On a light theme these stay black.
- Node colors come from a frozen hex array `UNIFIED_PALETTE` (Tailwind
  400/200/600 tiers). The pale "200" tier is near-invisible on a light
  background. `ENTITY_TYPE_COLORS` and `UNCLUSTERED_COLOR` (`#8b949e`) are
  likewise fixed hex.
- Edge colors are hardcoded: entity-relation `#ffa65770`, membership
  `#58606920` / `#58606980`, and the 3D link colors `#4CC9F0`,
  `rgba(76,201,240,…)`, `#ffa657…`.
- The diamond entity-node hover pill hardcodes a `#FFF` fill with `#000`
  shadow (dark-only).
- The renderers resolve tokens (for label/muted/border) exactly once at build
  time, so even the partial token usage they have is frozen at first mount and
  does not follow a live theme switch.

## Goal

Make the Memory graph adapt to the theme system, **dark/light first**. Node
hues keep a **fixed semantic identity** (decision → violet, problem → red,
fact → blue …) but are regenerated per mode so they stay legible on both a dark
and a light surface; the accent does **not** recolor nodes. All chrome
(backgrounds, edges, labels, hulls, selection highlight, hover pills) is
token-derived and reacts live. A live dark↔light flip recolors **in place** —
node positions and camera are preserved, no layout re-simulation.

Non-goals: accent-driven node recoloring; new color modes; backend changes;
reworking layout/physics.

## Color model

`graph-colors.ts` stays pure (no React) and becomes token-driven.

### Mode-aware categorical palette

- Keep the 17 hue identities, `HUE_ORDER`, and `KNOWN_TYPE_INDICES` (these
  encode the fixed semantic mapping; all type indices are < 17, i.e. tier 0).
- Derive 17 base **hues** from the existing `PALETTE_400` (extract H from each
  via a `hexToHsl` helper), reordered by `HUE_ORDER`. `PALETTE_200`/`PALETTE_600`
  are dropped — the three tiers were only lightness variants of the same hues.
- `buildMemoryPalette(t: GraphThemeTokens): MemoryPalette` returns:
  - `palette: string[]` of 51 slots. Slot `i` → `hue = BASE_HUES[i % 17]`,
    `tier = Math.floor(i / 17)`. Color = `hslToHex(hue, sat[tier], light[tier])`
    with **per-mode** tier parameters, e.g.
    - dark: `L = [62, 76, 50]`, `S = [85, 70, 82]`
    - light: `L = [46, 36, 58]`, `S = [80, 85, 70]`
    (final constants tuned during implementation against both surfaces.)
  - `unclustered: string` = `t.mutedForeground`.
  - `entityTypeColor(type): string` — each entity type keeps its current hue
    (person ≈217 blue, service ≈142 green, project ≈271 violet, technology ≈27
    orange, organization ≈330 pink) regenerated at tier-0 lightness/sat for the
    mode; `concept` → `unclustered`.
- `MemoryPalette` is the single object threaded to every consumer.

### Re-signatured pure functions

- `resolveNodeColor(node, colorMode, palette: MemoryPalette)`
- `resolveGroupColor(groupKey, groupIndex, colorMode, hullMode, palette)`
- `entityTypeColor(type, palette)` (or `palette.entityTypeColor(type)`)

Existing hex utilities (`hexToRgba`, `lightenHex`, `darkenHex`, `blendHex`)
stay — hover/dim/border variants still derive from a node's own color.

### Edge color helpers (token-derived)

New pure helpers in `graph-colors.ts`:

- `memoryEdgeColor(srcHex, t)` — similarity edges, derived from the source
  node color (replaces inline `darkenHex(srcColor, 0.6)`), mode-aware amount.
- `relationEdgeColor(t)` — entity-relation edges (replaces `#ffa657…`),
  from an accent/chart token with alpha.
- `membershipEdgeColor(t)` — entity↔memory membership edges (replaces
  `#586069…`), from `border`/`muted` with low alpha.

## Reactivity mechanism — recolor in place

Both graph engines keep a **persistent** instance across a theme change
(Sigma for 2D/knowledge, react-force-graph for 3D). Recoloring the existing
scene therefore preserves node positions and camera with no re-simulation and
no `savedCameraRef` machinery.

To prevent the build path and the recolor path from drifting, color assignment
is factored into shared helpers and both paths call them:

- `nodeColorFor(storedAttrs, palette)` and `edgeColorFor(storedKind, srcHex, t)`.

### Token resolution hooks

- `code-graph-theme.ts`: extract a reusable `useGraphThemeTokens(rootRef?)`
  that resolves tokens from `document.documentElement` and re-resolves on the
  `MutationObserver`. Refactor the existing `useCodeGraphTheme` to call it
  (no behavior change for the Code graph).
- New `memory-graph-theme.ts`: `useMemoryGraphTheme(): { tokens, palette }`,
  memoized (`palette = buildMemoryPalette(tokens)`).

### 2D renderer (`graph-2d-renderer.tsx`)

- Accept `tokens` + `palette` props (resolved in the route); store them in
  `tokensRef` / `paletteRef`.
- At build: store on each node what recolor needs — memory nodes carry
  `_mem = { cluster, memory_type, tags }`; entity nodes already carry
  `_entityData` (has `entity_type`). Each edge carries
  `_edgeKind: "memory" | "relation" | "membership"`.
- `nodeReducer` / `edgeReducer` / `drawHulls` read `tokensRef.current` /
  `paletteRef.current` instead of build-time-captured `mutedColor` /
  `dimColor` / `labelColorToken` / palette, so selection-dim, label, and hull
  colors track the live theme.
- New `recolor()`: walk nodes → recompute base `color`/`borderColor` via
  `nodeColorFor`; walk edges → recompute `color` via `edgeColorFor`; update
  `sigma.setSetting("labelColor"/"defaultNodeColor", …)`; `sigma.refresh()`.
- An effect keyed on `[tokens, palette]` calls `recolor()` when a Sigma
  instance exists (skipped on initial mount, where buildGraph already paints
  with the current palette). `buildGraph` is **not** keyed on theme.
- The diamond hover pill (`node-diamond-program.ts` `drawDiamondNodeHover`)
  takes the surface colors as parameters; the renderer passes
  `tokens.popover` (fill) / `tokens.popoverForeground` and drops `#FFF`/`#000`.

### Knowledge renderer (`knowledge-graph-renderer.tsx`)

Same `tokens`/recolor pattern (simpler: all nodes are entities, one edge kind;
replace `#58606980`). Currently unmounted — themed for consistency and
future-proofing; called out as not-yet-rendered.

### 3D renderer (`graph-3d-renderer.tsx`)

- Accept `tokens` + `palette` props. `chrome` (`background`, `highlight`)
  comes from the `tokens` prop, so it is reactive (was `useMemo([])`).
- Node objects already carry `memoryType` / `cluster` / `tags` / `entityType`.
  A recolor effect keyed on `[palette, tokens, colorMode]` recomputes each
  `node.color` in place and updates its material (`mat.color` / `mat.emissive`)
  and the selection ring; positions are untouched (same node objects → r-f-g
  keeps x/y/z).
- `linkColor` reads `tokensRef.current` and returns `memoryEdgeColor` /
  `relationEdgeColor` variants; the recolor effect calls `fgRef.current.refresh()`
  to repaint links.
- The route's `graphData3D` memo is intentionally **not** keyed on `palette`
  (keeping node-object identity stable so positions survive a flip). `transform`
  receives the palette for the correct initial color; later flips are handled by
  the renderer's in-place recolor. (`eslint-disable` with a comment on the memo.)

### Route (`unified-graph.tsx`)

- Replace both `bg-[#0d1117]` with `bg-background`.
- `const { tokens, palette } = useMemoryGraphTheme()`; pass `tokens` + `palette`
  to `Graph2DRenderer` / `Graph3DRenderer`; pass `palette` into
  `transformToGraphData`.

### `graph-utils.ts`

`transformToGraphData(data, sizeMode, filters, colorMode, entityLayerEnabled,
entities, entityRelations, palette)` — node/entity initial colors use the
mode-aware palette.

### Leaf surfaces

- `mini-graph.tsx`: `bg-[#0d1117]` → `bg-background`; entity chips use
  `useMemoryGraphTheme().palette`.
- `graph-skeleton.tsx`: `bg-[#0d1117]` → `bg-background`, `bg-[#21262d]` →
  `bg-muted`, edge `rgba(139,148,158,…)` → `bg-border`. The decorative
  translucent cluster hues stay (low-alpha, theme-neutral).
- `graph-filter-panel.tsx` / `graph-detail-panel.tsx`: legend swatches obtain
  `palette` from the hook; `resolveNodeColor`/`resolveGroupColor`/
  `entityTypeColor` calls get the palette arg; the `#8b949e` fallbacks become
  `palette.unclustered`.

## Components & data flow

```
useMemoryGraphTheme()  ──┬─→ unified-graph route ──→ tokens + palette ──┬─→ Graph2DRenderer (build + recolor)
  ├ useGraphThemeTokens  │                          (+ transformToGraphData)│─→ Graph3DRenderer (build + recolor)
  └ buildMemoryPalette   │                                                  └─→ (props)
                         └─→ leaf hook consumers: mini-graph, filter-panel,
                             detail-panel  (swatches/chips)
```

`graph-colors.ts` (pure) — palette + edge math, consumed everywhere.
`code-graph-theme.ts` — token resolution (shared), unchanged Code-graph behavior.

## Error / edge handling

- jsdom returns `""` for CSS custom properties; `resolveGraphTokens` already
  falls back to the dark defaults, so `buildMemoryPalette` always yields valid
  hex and tests are deterministic.
- Recolor is a no-op when no engine instance exists (early return).
- Color helpers are shared between build and recolor, so the two paths cannot
  produce different colors for the same input.

## Testing

New `graph-colors.test.ts` (mirroring `code-graph-theme.test.tsx`):

- `buildMemoryPalette` is deterministic for a given `isDark`.
- Hue identity is preserved across modes: `resolveNodeColor` for
  `memory_type: "decision"` is violet-family in both dark and light; `problem`
  is red-family in both.
- Light-mode tier-0 lightness < dark-mode tier-0 lightness (darker on light
  surface).
- `entityTypeColor("person")` hue is stable across modes.
- `unclustered` equals the tokens' `mutedForeground`.

Update any test importing the re-signatured color functions.

Gate (from `CLAUDE.md`): `npm run typecheck` (`tsc -b`), `npm test` (vitest),
`npm run build`. Manual: toggle dark↔light in the running app and confirm the
2D graph, 3D graph, loading skeleton, mini-graph, and the filter/detail legends
all flip, and that a flip preserves node positions and camera.

## Out of scope / follow-ups

- Accent-driven node recoloring (kept fixed-identity by decision).
- Wiring `KnowledgeGraphRenderer` into a route.
- Tuning the decorative skeleton cluster hues to chart tokens.
