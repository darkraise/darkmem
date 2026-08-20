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
  // No initializer: every branch below assigns, and a placeholder 0 that is
  // never read hides a missing branch instead of failing the build.
  let r: number
  let g: number
  let b: number
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

// One index per MEMORY_TYPES value; a type missing here would fall through to
// the hash path and change colour whenever the cluster space shifts.
const KNOWN_TYPE_INDICES: Record<string, number> = {
  fact: 4,
  decision: 15,
  problem: 0,
  architecture: 2,
  preference: 14,
  reference: 10,
  milestone: 16,
  episodic: 8,
  procedural: 6,
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

export function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

export function lightenHex(hex: string, amount = 0.35): string {
  const r = Math.min(
    255,
    Math.round(
      parseInt(hex.slice(1, 3), 16) +
        (255 - parseInt(hex.slice(1, 3), 16)) * amount,
    ),
  )
  const g = Math.min(
    255,
    Math.round(
      parseInt(hex.slice(3, 5), 16) +
        (255 - parseInt(hex.slice(3, 5), 16)) * amount,
    ),
  )
  const b = Math.min(
    255,
    Math.round(
      parseInt(hex.slice(5, 7), 16) +
        (255 - parseInt(hex.slice(5, 7), 16)) * amount,
    ),
  )
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`
}

export function blendHex(hex1: string, hex2: string, ratio = 0.5): string {
  const r = Math.round(
    parseInt(hex1.slice(1, 3), 16) * (1 - ratio) +
      parseInt(hex2.slice(1, 3), 16) * ratio,
  )
  const g = Math.round(
    parseInt(hex1.slice(3, 5), 16) * (1 - ratio) +
      parseInt(hex2.slice(3, 5), 16) * ratio,
  )
  const b = Math.round(
    parseInt(hex1.slice(5, 7), 16) * (1 - ratio) +
      parseInt(hex2.slice(5, 7), 16) * ratio,
  )
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`
}

export function darkenHex(hex: string, amount = 0.45): string {
  const r = Math.max(
    0,
    Math.round(parseInt(hex.slice(1, 3), 16) * (1 - amount)),
  )
  const g = Math.max(
    0,
    Math.round(parseInt(hex.slice(3, 5), 16) * (1 - amount)),
  )
  const b = Math.max(
    0,
    Math.round(parseInt(hex.slice(5, 7), 16) * (1 - amount)),
  )
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`
}
