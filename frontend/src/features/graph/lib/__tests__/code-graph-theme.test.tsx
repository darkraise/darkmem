import { describe, it, expect, vi, afterEach } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"
import {
  hslToHex,
  parseHsl,
  parseHslTriplet,
  resolveGraphTokens,
  useGraphThemeTokens,
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

describe("useGraphThemeTokens", () => {
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

    const { result } = renderHook(() => useGraphThemeTokens())

    await waitFor(() => expect(result.current.primary).toBe(hslToHex(217, 91, 60)))

    // Simulate the provider committing a new accent in its passive effect:
    // first the computed values change, then the inline style attribute is
    // mutated (which is what the hook observes).
    act(() => {
      computed["--primary"] = "30 91% 60%"
      document.documentElement.style.setProperty("--primary", "30 91% 60%")
    })

    await waitFor(() => expect(result.current.primary).toBe(hslToHex(30, 91, 60)))
    expect(result.current.primaryHue).toBe(30)
  })
})
