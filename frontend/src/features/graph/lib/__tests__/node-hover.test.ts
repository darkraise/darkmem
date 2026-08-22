import { describe, it, expect } from "vitest"
import { drawThemedDiscNodeHover, hoverChrome } from "../node-hover"
import { hslToHex } from "../graph-colors"
import type { GraphThemeTokens } from "../code-graph-theme"

function channel(hex: string, at: number): number {
  const c = parseInt(hex.slice(at, at + 2), 16) / 255
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
}
function luminance(hex: string): number {
  return 0.2126 * channel(hex, 1) + 0.7152 * channel(hex, 3) + 0.0722 * channel(hex, 5)
}
function contrast(a: string, b: string): number {
  const hi = Math.max(luminance(a), luminance(b))
  const lo = Math.min(luminance(a), luminance(b))
  return (hi + 0.05) / (lo + 0.05)
}

function tokens(over: Partial<GraphThemeTokens>): GraphThemeTokens {
  return {
    background: hslToHex(222, 47, 6),
    foreground: hslToHex(210, 40, 96),
    card: hslToHex(222, 47, 9),
    cardForeground: hslToHex(210, 40, 96),
    popover: hslToHex(222, 47, 9),
    popoverForeground: hslToHex(210, 40, 96),
    muted: hslToHex(222, 30, 16),
    mutedForeground: hslToHex(215, 16, 60),
    border: hslToHex(222, 30, 20),
    primary: hslToHex(217, 91, 60),
    ring: hslToHex(217, 91, 60),
    destructive: hslToHex(0, 84, 60),
    chart: [],
    primaryHue: 217,
    isDark: true,
    fontMono: "monospace",
    ...over,
  }
}

const DARK = tokens({})
const LIGHT = tokens({
  background: hslToHex(0, 0, 100),
  foreground: hslToHex(222, 47, 11),
  card: hslToHex(0, 0, 100),
  popover: hslToHex(0, 0, 100),
  isDark: false,
})

describe("hoverChrome", () => {
  // The plate marks the selected node. Painted in a surface token it is
  // invisible: --popover and --card sit within a few percent lightness of
  // --background by design, so the selection renders as nothing at all. This
  // has now been the defect twice — sigma's hardcoded #FFF, then --popover.
  it.each([
    ["dark", DARK],
    ["light", LIGHT],
  ])("separates the plate from the %s page background", (_name, t) => {
    expect(contrast(hoverChrome(t).fill, t.background)).toBeGreaterThan(2)
  })

  it.each([
    ["dark", DARK],
    ["light", LIGHT],
  ])("keeps the %s label readable on its own plate", (_name, t) => {
    const { fill, text } = hoverChrome(t)
    expect(contrast(text, fill)).toBeGreaterThanOrEqual(4.5)
  })

  // An accent may land anywhere on the lightness scale — `accentIntensity`
  // alone moves it — so neither foreground nor background is safe to assume.
  it("picks the text colour by contrast, not by theme polarity", () => {
    const paleAccent = tokens({ primary: hslToHex(217, 91, 88) })
    const deepAccent = tokens({ primary: hslToHex(217, 91, 22) })
    expect(hoverChrome(paleAccent).text).toBe(paleAccent.background)
    expect(hoverChrome(deepAccent).text).toBe(deepAccent.foreground)
  })
})

/** Records what was painted, in order, so the assertions are about the plate
 *  the renderer actually draws rather than about the helper alone. */
function recordingContext() {
  const painted: { op: string; style: unknown }[] = []
  const ctx = {
    font: "",
    fillStyle: "" as unknown,
    strokeStyle: "" as unknown,
    lineWidth: 0,
    shadowOffsetX: 0,
    shadowOffsetY: 0,
    shadowBlur: 0,
    shadowColor: "",
    measureText: () => ({ width: 40 }),
    beginPath: () => {},
    closePath: () => {},
    moveTo: () => {},
    lineTo: () => {},
    arc: () => {},
    fill: () => painted.push({ op: "fill", style: ctx.fillStyle }),
    stroke: () => painted.push({ op: "stroke", style: ctx.strokeStyle }),
    fillText: () => painted.push({ op: "fillText", style: ctx.fillStyle }),
  }
  return { ctx, painted }
}

const NODE = { x: 10, y: 10, size: 8, label: "postgres", color: "#22c55e" }
const SETTINGS = {
  labelSize: 12,
  labelFont: "Inter",
  labelWeight: "400",
} as never

describe("drawThemedDiscNodeHover", () => {
  it("paints the plate in the accent and the label in its contrast colour", () => {
    const { ctx, painted } = recordingContext()
    drawThemedDiscNodeHover(ctx as never, NODE as never, SETTINGS, DARK)

    const chrome = hoverChrome(DARK)
    expect(painted.find((p) => p.op === "fill")?.style).toBe(chrome.fill)
    expect(painted.find((p) => p.op === "fillText")?.style).toBe(chrome.text)
  })

  // The regression this replaces: the plate was painted in a surface token,
  // which is the page's own colour.
  it("never paints the plate in a surface token", () => {
    const { ctx, painted } = recordingContext()
    drawThemedDiscNodeHover(ctx as never, NODE as never, SETTINGS, DARK)

    const plate = painted.find((p) => p.op === "fill")?.style
    expect(plate).not.toBe(DARK.popover)
    expect(plate).not.toBe(DARK.card)
    expect(plate).not.toBe(DARK.background)
    expect(plate).not.toBe("#FFF")
  })
})
