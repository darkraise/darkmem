import { useSyncExternalStore } from "react"
import { hslToHex, stableHash } from "./graph-colors"

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
  destructiveSolid: string
  canvas: string
  nebula: string
  chart: string[]
  primaryHue: number
  isDark: boolean
  fontMono: string
}

// Defaults mirror the darkraise-ui dark theme so the test DOM (which returns "" for
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
  canvas: { h: 40, s: 33, l: 98 },
  nebula: { h: 262, s: 70, l: 88 },
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
    destructiveSolid: triplet("--destructive-solid", FALLBACK.destructive).hex,
    canvas: triplet("--graph-canvas", FALLBACK.canvas).hex,
    nebula: triplet("--graph-nebula", FALLBACK.nebula).hex,
    chart,
    primaryHue: primary.hsl.h,
    isDark: background.hsl.l < 50,
    fontMono: fontMonoRaw || FALLBACK_FONT_MONO,
  }
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
  destructiveSolid: hslToHex(
    FALLBACK.destructive.h,
    FALLBACK.destructive.s,
    FALLBACK.destructive.l,
  ),
  canvas: hslToHex(FALLBACK.canvas.h, FALLBACK.canvas.s, FALLBACK.canvas.l),
  nebula: hslToHex(FALLBACK.nebula.h, FALLBACK.nebula.s, FALLBACK.nebula.l),
  chart: FALLBACK.chart.map((c) => hslToHex(c.h, c.s, c.l)),
  primaryHue: FALLBACK.primary.h,
  isDark: FALLBACK.background.l < 50,
  fontMono: FALLBACK_FONT_MONO,
}

// One observer and one token read per theme change for the whole page, not
// one per consumer.
let sharedTokens: GraphThemeTokens = FALLBACK_TOKENS
let themeObserver: MutationObserver | null = null
const themeListeners = new Set<() => void>()

function resolveSharedTokens() {
  sharedTokens = resolveGraphTokens(document.documentElement)
  for (const listener of themeListeners) listener()
}

function subscribeTheme(listener: () => void): () => void {
  themeListeners.add(listener)
  if (!themeObserver) {
    sharedTokens = resolveGraphTokens(document.documentElement)
    themeObserver = new MutationObserver(resolveSharedTokens)
    themeObserver.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["style"],
    })
  }
  return () => {
    themeListeners.delete(listener)
    if (themeListeners.size === 0) {
      themeObserver?.disconnect()
      themeObserver = null
    }
  }
}

/**
 * Graph theme tokens from the page root, re-resolved whenever the active
 * darkraise-ui theme changes (accent, surface, mode, preset, gradient, and
 * any preset-specific axis values).
 *
 * The provider commits the CSS custom properties to documentElement inside its
 * own passive effect. React flushes passive effects child-before-parent, so a
 * consumer effect keyed on theme state (even a layout effect) runs before the
 * provider has written the new variables and would read the stale values. To
 * stay correct regardless of effect ordering we observe the documentElement
 * `style` attribute and re-resolve once the provider actually mutates the DOM.
 */
export function useGraphThemeTokens(): GraphThemeTokens {
  return useSyncExternalStore(subscribeTheme, () => sharedTokens)
}
