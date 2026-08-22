import { describe, it, expect } from "vitest"
import {
  LABEL_CLEARANCE,
  drawNodeLabel,
  drawThemedDiscNodeHover,
  hoverChrome,
} from "../node-hover"
import { hslToHex } from "../graph-colors"
import type { SelectionColor } from "../graph-prefs"
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
const COLORS: SelectionColor[] = ["accent", "inverted"]
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
      COLORS.map((c) => [theme, c, t] as [string, SelectionColor, GraphThemeTokens]),
    ),
  )("keeps the %s %s label readable on its own plate", (_theme, color, t) => {
    const c = hoverChrome(t, color, "focus", NODE_COLOR)
    expect(contrast(c.text, c.fill)).toBeGreaterThanOrEqual(4.5)
  })

  it.each(
    TABLE.flatMap(([theme, t]) =>
      COLORS.map((c) => [theme, c, t] as [string, SelectionColor, GraphThemeTokens]),
    ),
  )("separates the %s %s plate from the page", (_theme, color, t) => {
    const c = hoverChrome(t, color, "focus", NODE_COLOR)
    const standsAlone = contrast(c.fill, t.background) > 1.6
    expect(standsAlone || c.plateStroke !== null).toBe(true)
  })

  it("picks the text colour by contrast, not by theme polarity", () => {
    const pale = tokens({ primary: hslToHex(217, 91, 88) })
    const deep = tokens({ primary: hslToHex(217, 91, 22) })
    expect(hoverChrome(pale, "accent", "focus", NODE_COLOR).text).toBe(pale.background)
    expect(hoverChrome(deep, "accent", "focus", NODE_COLOR).text).toBe(deep.foreground)
  })

  it("rings in the accent, or inverts against the page", () => {
    expect(hoverChrome(DARK, "accent", "focus", NODE_COLOR).ring).toBe(DARK.primary)
    expect(hoverChrome(DARK, "inverted", "focus", NODE_COLOR).ring).toBe(DARK.foreground)
  })

  // The halo is a ring around the node, not a collar on it: without a gap it
  // reads as a thick border and the node looks recoloured.
  it.each(["focus", "hover"] as const)("holds the %s halo off the node", (kind) => {
    expect(hoverChrome(DARK, "accent", kind, NODE_COLOR).ringGap).toBeGreaterThan(0)
  })

  // Hover reading as selection is the defect this model replaces.
  it.each(COLORS)("makes hover lighter than focus under %s", (color) => {
    const focus = hoverChrome(DARK, color, "focus", NODE_COLOR)
    const hover = hoverChrome(DARK, color, "hover", NODE_COLOR)
    expect(hover.ringWidth).toBeLessThan(focus.ringWidth)
    expect(hover).not.toEqual(focus)
  })

  it("keeps hover identical across colours — it is not a selection", () => {
    const [a, b] = COLORS.map((c) => hoverChrome(DARK, c, "hover", NODE_COLOR))
    expect(a).toEqual(b)
  })
})

/** Records what was painted, in order, so the assertions are about the plate
 *  the renderer actually draws rather than about the helper alone. */
function recordingContext() {
  const painted: { op: string; style: unknown; x?: number; y?: number }[] = []
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
    fillText: (_t: string, x: number, y: number) =>
      painted.push({ op: "fillText", style: ctx.fillStyle, x, y }),
  }
  return { ctx, painted }
}

const NODE = { x: 10, y: 10, size: 8, label: "postgres", color: NODE_COLOR }
const SETTINGS = { labelSize: 12, labelFont: "Inter", labelWeight: "400" } as never

describe("drawThemedDiscNodeHover", () => {
  it("paints the plate and label in the chrome's own colours", () => {
    const { ctx, painted } = recordingContext()
    drawThemedDiscNodeHover(ctx as never, NODE as never, SETTINGS, DARK, "accent", "focus")

    const chrome = hoverChrome(DARK, "accent", "focus", NODE_COLOR)
    expect(painted.find((p) => p.op === "fill")?.style).toBe(chrome.fill)
    expect(painted.find((p) => p.op === "fillText")?.style).toBe(chrome.text)
  })

  // The regression this replaces: the plate was painted in a surface token,
  // which is the page's own colour.
  it("never paints the default plate in a surface token", () => {
    const { ctx, painted } = recordingContext()
    drawThemedDiscNodeHover(ctx as never, NODE as never, SETTINGS, DARK, "accent", "focus")

    const plate = painted.find((p) => p.op === "fill")?.style
    expect(plate).not.toBe(DARK.popover)
    expect(plate).not.toBe(DARK.card)
    expect(plate).not.toBe(DARK.background)
    expect(plate).not.toBe("#FFF")
  })
})


// The defect this pins: both label paths sat at sigma's hardcoded 3px, which
// is inside the hover ring (gap 2.5 + width 1.5 = 4) and well inside the focus
// ring (gap 4 + width 3 = 7), so the text was drawn under the selection ring.
describe("label clearance", () => {
  const ringOuterEdge = (kind: "hover" | "focus") => {
    const c = hoverChrome(DARK, "accent", kind, NODE_COLOR)
    return c.ringGap + c.ringWidth
  }

  it.each(["hover", "focus"] as const)(
    "clears the %s ring rather than sitting under it",
    (kind) => {
      expect(LABEL_CLEARANCE).toBeGreaterThan(ringOuterEdge(kind))
    },
  )

  it("puts the resting label at the same offset as the plated one", () => {
    const resting = recordingContext()
    drawNodeLabel(resting.ctx as never, NODE as never, {
      ...(SETTINGS as object),
      labelColor: { color: "#fff" },
    } as never)

    const plated = recordingContext()
    drawThemedDiscNodeHover(
      plated.ctx as never, NODE as never, SETTINGS, DARK, "accent", "focus",
    )

    const x = (r: typeof resting) => r.painted.find((p) => p.op === "fillText")?.x
    // Equal, not merely both-large: a label that shifts when you point at a
    // node reads as the node moving.
    expect(x(resting)).toBe(x(plated))
    expect(x(resting)).toBe(NODE.x + NODE.size + LABEL_CLEARANCE)
  })

  it("keeps the plate wide enough for the text it now holds", () => {
    const { ctx, painted } = recordingContext()
    const widths: number[] = []
    const spy = { ...ctx, lineTo: (x: number) => widths.push(x) }
    drawThemedDiscNodeHover(
      spy as never, NODE as never, SETTINGS, DARK, "accent", "focus",
    )
    const textX = painted.find((p) => p.op === "fillText")!.x!
    // measureText is stubbed at 40, and the plate is drawn before the label.
    expect(Math.max(...widths)).toBeGreaterThanOrEqual(textX + 40)
  })
})
