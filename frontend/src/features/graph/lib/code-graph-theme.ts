import { useEffect, useMemo, useState, type RefObject } from "react"
import { darkenHex, hslToHex } from "./graph-colors"

export { hslToHex }

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

// Mirrors lib/graph-colors.ts stableHash (Math.imul 31-step, abs).
export function stableHash(str: string): number {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = (Math.imul(31, hash) + str.charCodeAt(i)) | 0
  }
  return Math.abs(hash)
}

// Deterministic [0,1) value derived from a string seed, replacing Math.random()
// for layout jitter/curvature so rebuilds and theme switches reposition nodes
// identically. `salt` distinguishes multiple draws for the same seed (e.g. x vs
// y). Mixing follows the splitmix32 finalizer for good avalanche behaviour.
export function seededUnit(seed: string, salt = 0): number {
  let h = (stableHash(seed) ^ Math.imul(salt + 1, 0x9e3779b9)) >>> 0
  h ^= h >>> 16
  h = Math.imul(h, 0x21f0aaad)
  h ^= h >>> 15
  h = Math.imul(h, 0x735a2d97)
  h ^= h >>> 15
  return (h >>> 0) / 4294967296
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

// Deterministic accent-anchored color for a community cluster, mirroring the
// node long-tail tier: rotate the accent hue by a stable per-id offset so every
// community keeps a fixed, distinct hue that still tracks the active accent.
export function communityColor(
  communityId: string | number,
  t: GraphThemeTokens,
): string {
  const key = String(communityId)
  const offset = stableHash(key) % 360
  const hue = (((t.primaryHue + offset) % 360) + 360) % 360
  const s = t.isDark ? 70 : 62
  const l = t.isDark ? 62 : 45
  return hslToHex(hue, s, l)
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

const FALLBACK_TOKENS: GraphThemeTokens = {
  background: hslToHex(FALLBACK.background.h, FALLBACK.background.s, FALLBACK.background.l),
  foreground: hslToHex(FALLBACK.foreground.h, FALLBACK.foreground.s, FALLBACK.foreground.l),
  card: hslToHex(FALLBACK.card.h, FALLBACK.card.s, FALLBACK.card.l),
  cardForeground: hslToHex(
    FALLBACK.cardForeground.h,
    FALLBACK.cardForeground.s,
    FALLBACK.cardForeground.l,
  ),
  popover: hslToHex(FALLBACK.popover.h, FALLBACK.popover.s, FALLBACK.popover.l),
  popoverForeground: hslToHex(
    FALLBACK.popoverForeground.h,
    FALLBACK.popoverForeground.s,
    FALLBACK.popoverForeground.l,
  ),
  muted: hslToHex(FALLBACK.muted.h, FALLBACK.muted.s, FALLBACK.muted.l),
  mutedForeground: hslToHex(
    FALLBACK.mutedForeground.h,
    FALLBACK.mutedForeground.s,
    FALLBACK.mutedForeground.l,
  ),
  border: hslToHex(FALLBACK.border.h, FALLBACK.border.s, FALLBACK.border.l),
  primary: hslToHex(FALLBACK.primary.h, FALLBACK.primary.s, FALLBACK.primary.l),
  ring: hslToHex(FALLBACK.ring.h, FALLBACK.ring.s, FALLBACK.ring.l),
  destructive: hslToHex(FALLBACK.destructive.h, FALLBACK.destructive.s, FALLBACK.destructive.l),
  chart: FALLBACK.chart.map((c) => hslToHex(c.h, c.s, c.l)),
  primaryHue: FALLBACK.primary.h,
  isDark: FALLBACK.background.l < 50,
  fontMono: FALLBACK_FONT_MONO,
}

export interface CodeGraphTheme {
  tokens: GraphThemeTokens
  nodeColors: Record<string, string>
  edgeColors: Record<string, string>
}

/**
 * Resolve graph theme tokens from the page root and re-resolve whenever the
 * active darkraise-ui theme changes (accent, surface, mode, preset, gradient,
 * and any preset-specific axis values).
 *
 * The provider commits the CSS custom properties to documentElement inside its
 * own passive effect. React flushes passive effects child-before-parent, so a
 * consumer effect keyed on theme state (even a layout effect) runs before the
 * provider has written the new variables and would read the stale values. To
 * stay correct regardless of effect ordering we observe the documentElement
 * `style` attribute and re-resolve once the provider actually mutates the DOM.
 *
 * @param rootRef - element to resolve tokens from; defaults to documentElement.
 */
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

export function useCodeGraphTheme(
  rootRef: RefObject<HTMLElement | null>,
  nodeTypes: readonly string[],
  edgeTypes: readonly string[],
): CodeGraphTheme {
  const tokens = useGraphThemeTokens(rootRef)

  return useMemo(() => {
    const { nodeColors, edgeColors } = buildCodeGraphColorMaps(
      [...nodeTypes],
      [...edgeTypes],
      tokens,
    )
    return { tokens, nodeColors, edgeColors }
  }, [tokens, nodeTypes, edgeTypes])
}
