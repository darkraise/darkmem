import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import path from "node:path"
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
    destructiveSolid: "#e5383b",
    canvas: isDark ? "#09070e" : "#fcfbf8",
    nebula: isDark ? "#5a1bbd" : "#d9cdf6",
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

// The backend owns the entity vocabulary and the frontend keeps no copy, which
// is how ENTITY_HUES came to carry `technology` (rewritten to `tool` before
// storage, so never stored) while `tool` had no colour. Read the closed set
// straight from the taxonomy rather than duplicating it here.
function backendEntityTypes(): string[] {
  const here = path.dirname(fileURLToPath(import.meta.url))
  const taxonomy = path.resolve(here, "../../../../../../backend/app/taxonomy.py")
  const src = readFileSync(taxonomy, "utf8")
  const block = /ENTITY_TYPES:\s*list\[str\]\s*=\s*\[([\s\S]*?)\]/.exec(src)
  if (!block) throw new Error(`ENTITY_TYPES not found in ${taxonomy}`)
  return [...block[1]!.matchAll(/"([a-z_]+)"/g)].map((m) => m[1]!)
}

// Smallest circular distance between two hues, in degrees.
function hueGap(a: number, b: number): number {
  const d = Math.abs(a - b) % 360
  return Math.min(d, 360 - d)
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
  it("colours every type the backend taxonomy can store", () => {
    const p = buildMemoryPalette(tokens(true))
    for (const etype of backendEntityTypes()) {
      expect(entityTypeColor(etype, p), etype).not.toBe(p.unclustered)
    }
  })

  it("colours nothing the taxonomy cannot store", () => {
    const p = buildMemoryPalette(tokens(true))
    const known = new Set(backendEntityTypes())
    // `technology` is the specific regression: a legacy name normalised to
    // `tool` on write, so a hue keyed on it can never be reached.
    for (const dead of ["technology", "framework", "nonsense", ""]) {
      expect(known.has(dead), dead).toBe(false)
      expect(entityTypeColor(dead, p), dead).toBe(p.unclustered)
    }
  })

  it("keeps the hues far enough apart to tell apart", () => {
    const p = buildMemoryPalette(tokens(true))
    const types = backendEntityTypes()
    const hues = types.map((t) => hueOf(entityTypeColor(t, p)))
    for (let i = 0; i < types.length; i++) {
      for (let j = i + 1; j < types.length; j++) {
        expect(
          hueGap(hues[i]!, hues[j]!),
          `${types[i]} vs ${types[j]}`,
        ).toBeGreaterThanOrEqual(18)
      }
    }
  })

  it("keeps the four identities that predate the widened table", () => {
    const p = buildMemoryPalette(tokens(true))
    const fixed: Record<string, number> = {
      person: 213,
      service: 142,
      project: 255,
      organization: 330,
    }
    for (const [etype, hue] of Object.entries(fixed)) {
      expect(hueGap(hueOf(entityTypeColor(etype, p)), hue), etype).toBeLessThan(6)
    }
  })

  it("gives tool the hue the retired technology key held", () => {
    const p = buildMemoryPalette(tokens(true))
    expect(hueGap(hueOf(entityTypeColor("tool", p)), 27)).toBeLessThan(6)
  })
})

describe("entityFill", () => {
  it("is the muted surface token, not a type colour", () => {
    const p = buildMemoryPalette(tokens(true))
    expect(p.entityFill).toBe(tokens(true).muted)
    for (const etype of backendEntityTypes()) {
      expect(entityTypeColor(etype, p), etype).not.toBe(p.entityFill)
    }
  })
})

describe("hslToHex", () => {
  it("matches known conversions", () => {
    expect(hslToHex(0, 100, 50)).toBe("#ff0000")
    expect(hslToHex(0, 0, 0)).toBe("#000000")
  })
})
