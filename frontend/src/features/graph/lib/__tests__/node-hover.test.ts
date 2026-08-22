import { describe, it, expect } from "vitest"
import { drawThemedDiscNodeHover, hoverChrome } from "../node-hover"
import { hslToHex } from "../graph-colors"
import type { SelectionTreatment } from "../graph-prefs"
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

const NODE_COLOR = hslToHex(152, 68, 58)
const TREATMENTS: SelectionTreatment[] = ["halo", "keyline", "invert"]
const TABLE: [string, GraphThemeTokens][] = [
  ["dark", DARK],
  ["light", LIGHT],
]

describe("hoverChrome", () => {
  // The label plate has to be readable in its own right. This is the property
  // that broke twice — sigma's hardcoded #FFF, then --popover, which sits
  // within a few percent lightness of --background by design.
  it.each(
    TABLE.flatMap(([theme, t]) =>
      TREATMENTS.map((tr) => [theme, tr, t] as [string, SelectionTreatment, GraphThemeTokens]),
    ),
  )("keeps the %s %s label readable on its own plate", (_theme, treatment, t) => {
    const c = hoverChrome(t, treatment, "focus", NODE_COLOR)
    expect(contrast(c.text, c.fill)).toBeGreaterThanOrEqual(4.5)
  })

  // A plate must be distinguishable from the page — either by its own fill or
  // by an outline. An outlined plate whose fill matches the canvas is fine;
  // an unoutlined one that matches it is the original bug.
  it.each(
    TABLE.flatMap(([theme, t]) =>
      TREATMENTS.map((tr) => [theme, tr, t] as [string, SelectionTreatment, GraphThemeTokens]),
    ),
  )("separates the %s %s plate from the page", (_theme, treatment, t) => {
    const c = hoverChrome(t, treatment, "focus", NODE_COLOR)
    const standsAlone = contrast(c.fill, t.background) > 1.6
    expect(standsAlone || c.plateStroke !== null).toBe(true)
  })

  it("picks the text colour by contrast, not by theme polarity", () => {
    const pale = tokens({ primary: hslToHex(217, 91, 88) })
    const deep = tokens({ primary: hslToHex(217, 91, 22) })
    expect(hoverChrome(pale, "halo", "focus", NODE_COLOR).text).toBe(pale.background)
    expect(hoverChrome(deep, "halo", "focus", NODE_COLOR).text).toBe(deep.foreground)
  })

  it("gives the halo an accent ring and a glow", () => {
    const c = hoverChrome(DARK, "halo", "focus", NODE_COLOR)
    expect(c.ring).toBe(DARK.primary)
    expect(c.glow).toBe(true)
  })

  // The keyline is the quiet option: it leaves the accent free for relation
  // edges by drawing the ring in the node's own colour instead.
  it("draws the keyline ring in the node's own colour", () => {
    const c = hoverChrome(DARK, "keyline", "focus", NODE_COLOR)
    expect(c.ring).toBe(NODE_COLOR)
    expect(c.glow).toBe(false)
  })

  it("backs the inverted treatment with the foreground", () => {
    const c = hoverChrome(DARK, "invert", "focus", NODE_COLOR)
    expect(c.fill).toBe(DARK.foreground)
    expect(c.text).toBe(DARK.background)
  })

  // Hover reading as selection is the defect this whole model replaces, so
  // the two must differ under every treatment.
  it.each(TREATMENTS)("makes hover distinguishable from focus under %s", (treatment) => {
    const focus = hoverChrome(DARK, treatment, "focus", NODE_COLOR)
    const hover = hoverChrome(DARK, treatment, "hover", NODE_COLOR)
    expect(hover.ringWidth).toBeLessThan(focus.ringWidth)
    expect(hover).not.toEqual(focus)
  })

  it("keeps hover identical across treatments — it is not a selection", () => {
    const [a, b, c] = TREATMENTS.map((tr) => hoverChrome(DARK, tr, "hover", NODE_COLOR))
    expect(a).toEqual(b)
    expect(b).toEqual(c)
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
    save: () => {},
    restore: () => {},
    setLineDash: () => {},
    fill: () => painted.push({ op: "fill", style: ctx.fillStyle }),
    stroke: () => painted.push({ op: "stroke", style: ctx.strokeStyle }),
    fillText: () => painted.push({ op: "fillText", style: ctx.fillStyle }),
  }
  return { ctx, painted }
}

const NODE = { x: 10, y: 10, size: 8, label: "postgres", color: NODE_COLOR }
const SETTINGS = { labelSize: 12, labelFont: "Inter", labelWeight: "400" } as never

describe("drawThemedDiscNodeHover", () => {
  it("paints the plate and label in the chrome's own colours", () => {
    const { ctx, painted } = recordingContext()
    drawThemedDiscNodeHover(ctx as never, NODE as never, SETTINGS, DARK, "halo", "focus")

    const chrome = hoverChrome(DARK, "halo", "focus", NODE_COLOR)
    expect(painted.find((p) => p.op === "fill")?.style).toBe(chrome.fill)
    expect(painted.find((p) => p.op === "fillText")?.style).toBe(chrome.text)
  })

  // The regression this replaces: the plate was painted in a surface token,
  // which is the page's own colour.
  it("never paints the default plate in a surface token", () => {
    const { ctx, painted } = recordingContext()
    drawThemedDiscNodeHover(ctx as never, NODE as never, SETTINGS, DARK, "halo", "focus")

    const plate = painted.find((p) => p.op === "fill")?.style
    expect(plate).not.toBe(DARK.popover)
    expect(plate).not.toBe(DARK.card)
    expect(plate).not.toBe(DARK.background)
    expect(plate).not.toBe("#FFF")
  })
})
