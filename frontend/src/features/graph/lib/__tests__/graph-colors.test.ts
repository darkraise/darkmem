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
