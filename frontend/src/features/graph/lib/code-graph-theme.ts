import { darkenHex } from "./graph-colors"

export interface GraphThemeTokens {
  background: string
  foreground: string
  card: string
  cardForeground: string
  popover: string
  popoverForeground: string
  muted: string
  mutedForeground: string
  border: string
  primary: string
  ring: string
  destructive: string
  chart: string[]
  primaryHue: number
  isDark: boolean
  fontMono: string
}

// Defaults mirror the darkraise-ui dark theme so jsdom (which returns "" for
// every custom property) still yields valid hex and a non-NaN hue.
const FALLBACK = {
  background: { h: 222, s: 47, l: 6 },
  foreground: { h: 210, s: 40, l: 96 },
  card: { h: 222, s: 47, l: 9 },
  cardForeground: { h: 210, s: 40, l: 96 },
  popover: { h: 222, s: 47, l: 9 },
  popoverForeground: { h: 210, s: 40, l: 96 },
  muted: { h: 222, s: 30, l: 16 },
  mutedForeground: { h: 215, s: 16, l: 60 },
  border: { h: 222, s: 30, l: 20 },
  primary: { h: 217, s: 91, l: 60 },
  ring: { h: 217, s: 91, l: 60 },
  destructive: { h: 0, s: 84, l: 60 },
  chart: [
    { h: 217, s: 91, l: 60 },
    { h: 142, s: 71, l: 45 },
    { h: 350, s: 89, l: 60 },
    { h: 38, s: 92, l: 50 },
    { h: 258, s: 90, l: 66 },
  ],
} as const

const FALLBACK_FONT_MONO = "ui-monospace, monospace"

interface Hsl {
  h: number
  s: number
  l: number
}

export function parseHslTriplet(raw: string): Hsl {
  const m = raw
    .trim()
    .match(/^(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)%?\s+(-?\d+(?:\.\d+)?)%?$/)
  if (!m) return { ...FALLBACK.primary }
  return { h: Number(m[1]), s: Number(m[2]), l: Number(m[3]) }
}

export function parseHsl(raw: string): Hsl {
  const trimmed = raw.trim()
  const wrapped = trimmed.match(/^hsla?\(([^)]*)\)$/i)
  const inner = wrapped?.[1] ?? trimmed
  return parseHslTriplet(inner.replace(/,/g, " ").replace(/\s+/g, " ").trim())
}

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

// Mirrors lib/graph-colors.ts stableHash (Math.imul 31-step, abs).
export function stableHash(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (Math.imul(31, hash) + str.charCodeAt(i)) | 0
  }
  return Math.abs(hash)
}

export function resolveGraphTokens(rootEl: HTMLElement): GraphThemeTokens {
  const cs = getComputedStyle(rootEl)
  const read = (prop: string) => cs.getPropertyValue(prop).trim()

  const triplet = (prop: string, fb: Hsl): { hex: string; hsl: Hsl } => {
    const raw = read(prop)
    const hsl = raw ? parseHslTriplet(raw) : fb
    const safe = Number.isNaN(hsl.h) ? fb : hsl
    return { hex: hslToHex(safe.h, safe.s, safe.l), hsl: safe }
  }

  const chart = FALLBACK.chart.map((fb, i) => {
    const raw = read(`--chart-${i + 1}`)
    const hsl = raw ? parseHsl(raw) : fb
    const safe = Number.isNaN(hsl.h) ? fb : hsl
    return hslToHex(safe.h, safe.s, safe.l)
  })

  const background = triplet("--background", FALLBACK.background)
  const primary = triplet("--primary", FALLBACK.primary)
  const fontMonoRaw = read("--font-mono")

  return {
    background: background.hex,
    foreground: triplet("--foreground", FALLBACK.foreground).hex,
    card: triplet("--card", FALLBACK.card).hex,
    cardForeground: triplet("--card-foreground", FALLBACK.cardForeground).hex,
    popover: triplet("--popover", FALLBACK.popover).hex,
    popoverForeground: triplet("--popover-foreground", FALLBACK.popoverForeground)
      .hex,
    muted: triplet("--muted", FALLBACK.muted).hex,
    mutedForeground: triplet("--muted-foreground", FALLBACK.mutedForeground).hex,
    border: triplet("--border", FALLBACK.border).hex,
    primary: primary.hex,
    ring: triplet("--ring", FALLBACK.ring).hex,
    destructive: triplet("--destructive", FALLBACK.destructive).hex,
    chart,
    primaryHue: primary.hsl.h,
    isDark: background.hsl.l < 50,
    fontMono: fontMonoRaw || FALLBACK_FONT_MONO,
  }
}

const CURATED_NODE_KINDS: Record<string, number> = {
  // structural containers
  file: 0,
  module: 0,
  folder: 0,
  namespace: 0,
  package: 0,
  // types
  class: 1,
  struct: 1,
  interface: 1,
  trait: 1,
  enum: 1,
  type: 1,
  // callables
  function: 2,
  method: 2,
  constructor: 2,
  impl: 2,
  // entrypoints
  route: 3,
  tool: 3,
  process: 3,
  // data
  property: 4,
  community: 4,
  model: 4,
}

// Fixed ~30deg-spread offsets for the common long-tail kinds, so the generated
// tier yields visually distinct hues that still rotate with the accent. Kinds
// absent here fall back to stableHash(kind) % 360.
export const NODE_HUE_OFFSET: Record<string, number> = {
  variable: 30,
  constant: 60,
  field: 90,
  parameter: 120,
  decorator: 150,
  annotation: 180,
  macro: 210,
  typedef: 240,
  union: 270,
  alias: 300,
  generic: 330,
  mixin: 45,
  protocol: 75,
  closure: 105,
  lambda: 135,
  getter: 165,
  setter: 195,
  event: 225,
  signal: 255,
  channel: 285,
  test: 315,
}

const CURATED_EDGE_STRUCTURAL = new Set([
  "defines",
  "contains",
  "imports",
  "has_method",
  "has_property",
])
const CURATED_EDGE_SEMANTIC = new Set([
  "calls",
  "extends",
  "implements",
  "method_overrides",
  "method_implements",
  "accesses",
])
const CURATED_EDGE_ROUTING = new Set([
  "handles_route",
  "handles_tool",
  "entry_point_of",
  "step_in_process",
  "member_of",
])

function generatedNodeHue(kind: string, primaryHue: number): number {
  const offset = NODE_HUE_OFFSET[kind] ?? stableHash(kind) % 360
  return (((primaryHue + offset) % 360) + 360) % 360
}

export function nodeKindColor(kind: string, t: GraphThemeTokens): string {
  const k = kind.toLowerCase()
  const curated = CURATED_NODE_KINDS[k]
  if (curated !== undefined) return t.chart[curated] ?? t.primary

  const s = t.isDark ? 70 : 62
  const l = t.isDark ? 62 : 45
  return hslToHex(generatedNodeHue(k, t.primaryHue), s, l)
}

export function edgeTypeColor(type: string, t: GraphThemeTokens): string {
  const e = type.toLowerCase()
  let seed: string
  if (CURATED_EDGE_STRUCTURAL.has(e)) seed = t.chart[0] ?? t.primary
  else if (CURATED_EDGE_SEMANTIC.has(e)) seed = t.chart[2] ?? t.primary
  else if (CURATED_EDGE_ROUTING.has(e)) seed = t.chart[3] ?? t.primary
  else {
    const s = t.isDark ? 70 : 62
    const l = t.isDark ? 62 : 45
    seed = hslToHex(generatedNodeHue(e, t.primaryHue), s, l)
  }
  return darkenHex(seed, t.isDark ? 0.25 : 0.15)
}

export function buildCodeGraphColorMaps(
  kinds: string[],
  edgeTypes: string[],
  t: GraphThemeTokens,
): { nodeColors: Record<string, string>; edgeColors: Record<string, string> } {
  const nodeColors: Record<string, string> = {}
  for (const kind of kinds) nodeColors[kind] = nodeKindColor(kind, t)
  const edgeColors: Record<string, string> = {}
  for (const type of edgeTypes) edgeColors[type] = edgeTypeColor(type, t)
  return { nodeColors, edgeColors }
}
