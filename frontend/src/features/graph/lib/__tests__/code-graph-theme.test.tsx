import { describe, it, expect, vi, afterEach } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"
import { createRef } from "react"
import {
  hslToHex,
  parseHsl,
  parseHslTriplet,
  resolveGraphTokens,
  nodeKindColor,
  edgeTypeColor,
  communityColor,
  buildCodeGraphColorMaps,
  useCodeGraphTheme,
  type GraphThemeTokens,
} from "../code-graph-theme"

const HEX = /^#[0-9a-f]{6}$/

afterEach(() => {
  vi.restoreAllMocks()
  document.documentElement.style.removeProperty("--primary")
})

// A token element whose getPropertyValue returns scripted values. Mirrors the
// shape getComputedStyle exposes so resolveGraphTokens can read it directly.
function stubRoot(map: Record<string, string>): HTMLElement {
  const el = document.createElement("div")
  vi.spyOn(window, "getComputedStyle").mockReturnValue({
    getPropertyValue: (prop: string) => map[prop] ?? "",
  } as unknown as CSSStyleDeclaration)
  return el
}

const DARK_TOKENS: Record<string, string> = {
  "--background": "222 47% 6%",
  "--foreground": "210 40% 96%",
  "--card": "222 47% 9%",
  "--card-foreground": "210 40% 96%",
  "--popover": "222 47% 9%",
  "--popover-foreground": "210 40% 96%",
  "--muted": "222 30% 16%",
  "--muted-foreground": "215 16% 60%",
  "--border": "222 30% 20%",
  "--primary": "217 91% 60%",
  "--ring": "217 91% 60%",
  "--destructive": "0 84% 60%",
  "--chart-1": "hsl(217 91% 60%)",
  "--chart-2": "hsl(142 71% 45%)",
  "--chart-3": "hsl(350 89% 60%)",
  "--chart-4": "hsl(38 92% 50%)",
  "--chart-5": "hsl(258 90% 66%)",
  "--font-mono": '"JetBrains Mono", ui-monospace, monospace',
  "--graph-canvas": "258 35% 4%",
  "--graph-nebula": "266 75% 42%",
  "--destructive-solid": "0 72% 51%",
}

const LIGHT_TOKENS: Record<string, string> = {
  ...DARK_TOKENS,
  "--background": "210 40% 98%",
}

describe("hslToHex", () => {
  it("converts known hsl values to exact hex", () => {
    expect(hslToHex(0, 100, 50)).toBe("#ff0000")
    expect(hslToHex(120, 100, 25)).toBe("#008000")
    expect(hslToHex(240, 100, 50)).toBe("#0000ff")
    expect(hslToHex(0, 0, 100)).toBe("#ffffff")
    expect(hslToHex(0, 0, 0)).toBe("#000000")
  })
})

describe("parseHslTriplet", () => {
  it("parses a bare H S% L% triplet", () => {
    expect(parseHslTriplet("217 91% 60%")).toEqual({ h: 217, s: 91, l: 60 })
  })
})

describe("parseHsl", () => {
  it("parses a bare triplet", () => {
    expect(parseHsl("0 100% 50%")).toEqual({ h: 0, s: 100, l: 50 })
  })

  it("parses a wrapped hsl() with spaces", () => {
    expect(parseHsl("hsl(120 71% 45%)")).toEqual({ h: 120, s: 71, l: 45 })
  })

  it("parses a wrapped hsl() with commas", () => {
    expect(parseHsl("hsl(258, 90%, 66%)")).toEqual({ h: 258, s: 90, l: 66 })
  })
})

describe("resolveGraphTokens", () => {
  it("resolves dark tokens to hex with primaryHue and isDark", () => {
    const root = stubRoot(DARK_TOKENS)
    const t = resolveGraphTokens(root)

    expect(t.background).toMatch(HEX)
    expect(t.primary).toBe(hslToHex(217, 91, 60))
    expect(t.destructive).toBe(hslToHex(0, 84, 60))
    expect(t.chart).toHaveLength(5)
    expect(t.chart[0]).toBe(hslToHex(217, 91, 60))
    expect(t.chart[1]).toBe(hslToHex(142, 71, 45))
    expect(t.primaryHue).toBe(217)
    expect(t.isDark).toBe(true)
    expect(t.fontMono).toBe('"JetBrains Mono", ui-monospace, monospace')
    expect(t.canvas).toBe(hslToHex(258, 35, 4))
    expect(t.nebula).toBe(hslToHex(266, 75, 42))
    expect(t.destructiveSolid).toBe(hslToHex(0, 72, 51))
  })

  it("reports light mode when background lightness is high", () => {
    const root = stubRoot(LIGHT_TOKENS)
    const t = resolveGraphTokens(root)
    expect(t.isDark).toBe(false)
  })

  it("falls back to sane defaults on empty values (no NaN)", () => {
    const root = stubRoot({})
    const t = resolveGraphTokens(root)
    expect(t.background).toMatch(HEX)
    expect(t.primary).toMatch(HEX)
    expect(t.chart).toHaveLength(5)
    t.chart.forEach((c) => expect(c).toMatch(HEX))
    expect(Number.isNaN(t.primaryHue)).toBe(false)
    expect(t.fontMono.length).toBeGreaterThan(0)
    expect(t.canvas).toMatch(HEX)
    expect(t.nebula).toMatch(HEX)
    expect(t.destructiveSolid).toMatch(HEX)
  })
})

function darkT(overrides: Partial<GraphThemeTokens> = {}): GraphThemeTokens {
  const root = stubRoot(DARK_TOKENS)
  return { ...resolveGraphTokens(root), ...overrides }
}

describe("nodeKindColor", () => {
  it("maps curated kinds to the matching chart entry", () => {
    const t = darkT()
    expect(nodeKindColor("file", t)).toBe(t.chart[0])
    expect(nodeKindColor("module", t)).toBe(t.chart[0])
    expect(nodeKindColor("class", t)).toBe(t.chart[1])
    expect(nodeKindColor("interface", t)).toBe(t.chart[1])
    expect(nodeKindColor("function", t)).toBe(t.chart[2])
    expect(nodeKindColor("method", t)).toBe(t.chart[2])
    expect(nodeKindColor("route", t)).toBe(t.chart[3])
    expect(nodeKindColor("process", t)).toBe(t.chart[3])
    expect(nodeKindColor("property", t)).toBe(t.chart[4])
    expect(nodeKindColor("community", t)).toBe(t.chart[4])
  })

  it("returns valid hex for a generated long-tail kind", () => {
    const t = darkT()
    expect(nodeKindColor("variable", t)).toMatch(HEX)
  })

  it("is deterministic for the same kind across calls", () => {
    const t = darkT()
    expect(nodeKindColor("variable", t)).toBe(nodeKindColor("variable", t))
    expect(nodeKindColor("zzz_unknown", t)).toBe(
      nodeKindColor("zzz_unknown", t),
    )
  })

  it("tracks the accent: changing primaryHue changes a generated kind", () => {
    const a = darkT({ primaryHue: 217 })
    const b = darkT({ primaryHue: 30 })
    expect(nodeKindColor("variable", a)).not.toBe(nodeKindColor("variable", b))
  })

  it("keeps an unknown kind stable", () => {
    const t = darkT()
    const first = nodeKindColor("totally_unknown_kind", t)
    const second = nodeKindColor("totally_unknown_kind", t)
    expect(first).toBe(second)
    expect(first).toMatch(HEX)
  })
})

describe("edgeTypeColor", () => {
  it("distinguishes structural from semantic families", () => {
    const t = darkT()
    expect(edgeTypeColor("contains", t)).not.toBe(edgeTypeColor("calls", t))
  })

  it("returns a valid #rrggbb", () => {
    const t = darkT()
    expect(edgeTypeColor("contains", t)).toMatch(HEX)
    expect(edgeTypeColor("calls", t)).toMatch(HEX)
    expect(edgeTypeColor("handles_route", t)).toMatch(HEX)
    expect(edgeTypeColor("some_unknown_edge", t)).toMatch(HEX)
  })

  it("darkens edges relative to the node family seed", () => {
    const t = darkT()
    // structural edges seed from chart[0]; the darkened edge must differ.
    expect(edgeTypeColor("contains", t)).not.toBe(t.chart[0])
  })
})

describe("useCodeGraphTheme", () => {
  // Drives getComputedStyle from a mutable map so the test can flip the
  // "committed" CSS variables after mount, the way ThemeProvider does in its
  // own passive effect. Exercises the MutationObserver path: keying off React
  // theme state would read stale values because passive effects flush
  // child-before-parent.
  function mockComputed(map: Record<string, string>) {
    vi.spyOn(window, "getComputedStyle").mockImplementation(
      () =>
        ({
          getPropertyValue: (prop: string) => map[prop] ?? "",
        }) as unknown as CSSStyleDeclaration,
    )
  }

  it("re-resolves when documentElement style mutates after mount", async () => {
    const computed: Record<string, string> = { ...DARK_TOKENS }
    mockComputed(computed)

    const root = createRef<HTMLElement>()
    root.current = document.createElement("div")

    const { result } = renderHook(() =>
      useCodeGraphTheme(root, ["file"], ["calls"]),
    )

    await waitFor(() =>
      expect(result.current.tokens.primary).toBe(hslToHex(217, 91, 60)),
    )

    // Simulate the provider committing a new accent in its passive effect:
    // first the computed values change, then the inline style attribute is
    // mutated (which is what the hook observes).
    act(() => {
      computed["--primary"] = "30 91% 60%"
      document.documentElement.style.setProperty("--primary", "30 91% 60%")
    })

    await waitFor(() =>
      expect(result.current.tokens.primary).toBe(hslToHex(30, 91, 60)),
    )
    expect(result.current.tokens.primaryHue).toBe(30)
  })
})

describe("communityColor", () => {
  it("returns a valid #rrggbb", () => {
    const t = darkT()
    expect(communityColor(0, t)).toMatch(HEX)
    expect(communityColor("7", t)).toMatch(HEX)
  })

  it("is deterministic for the same id across calls", () => {
    const t = darkT()
    expect(communityColor(3, t)).toBe(communityColor(3, t))
    expect(communityColor("abc", t)).toBe(communityColor("abc", t))
  })

  it("treats a numeric id and its string form identically", () => {
    const t = darkT()
    expect(communityColor(12, t)).toBe(communityColor("12", t))
  })

  it("distinguishes different community ids", () => {
    const t = darkT()
    expect(communityColor(1, t)).not.toBe(communityColor(2, t))
  })

  it("tracks the accent: changing primaryHue changes the color", () => {
    const a = darkT({ primaryHue: 217 })
    const b = darkT({ primaryHue: 30 })
    expect(communityColor(5, a)).not.toBe(communityColor(5, b))
  })
})

describe("buildCodeGraphColorMaps", () => {
  it("maps every kind and edge type through the color functions", () => {
    const t = darkT()
    const kinds = ["file", "class", "function", "variable"]
    const edgeTypes = ["contains", "calls", "weird_edge"]
    const { nodeColors, edgeColors } = buildCodeGraphColorMaps(
      kinds,
      edgeTypes,
      t,
    )
    expect(Object.keys(nodeColors)).toEqual(kinds)
    expect(Object.keys(edgeColors)).toEqual(edgeTypes)
    expect(nodeColors.file).toBe(nodeKindColor("file", t))
    expect(edgeColors.calls).toBe(edgeTypeColor("calls", t))
    Object.values(nodeColors).forEach((c) => expect(c).toMatch(HEX))
    Object.values(edgeColors).forEach((c) => expect(c).toMatch(HEX))
  })
})
