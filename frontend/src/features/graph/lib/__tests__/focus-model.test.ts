import { describe, it, expect } from "vitest"
import {
  focusTier,
  groundNodeAlpha,
  hoverGroundAlpha,
  groundEdgeAlpha,
  labelVisible,
  recede,
} from "../focus-model"

describe("focusTier", () => {
  it("is none for every node while nothing is focused", () => {
    expect(focusTier("a", null, false)).toBe("none")
    expect(focusTier("a", null, true)).toBe("none")
  })

  it("names the focused node, its neighbours, and the rest", () => {
    expect(focusTier("a", "a", false)).toBe("focus")
    expect(focusTier("b", "a", true)).toBe("adjacent")
    expect(focusTier("c", "a", false)).toBe("ground")
  })
})

describe("ground alphas", () => {
  it("dims nodes to the configured percentage", () => {
    expect(groundNodeAlpha(15)).toBeCloseTo(0.15)
    expect(groundNodeAlpha(40)).toBeCloseTo(0.4)
  })

  // One control, so the two can never drift into disagreeing about how far
  // back "back" is.
  it("takes the edge alpha from the same number", () => {
    expect(groundEdgeAlpha(15)).toBeCloseTo(0.15 * 0.35)
    expect(groundEdgeAlpha(40)).toBeCloseTo(0.4 * 0.35)
  })

  it("keeps edges fainter than the nodes they join at every setting", () => {
    for (const dim of [5, 10, 15, 25, 50]) {
      expect(groundEdgeAlpha(dim)).toBeLessThan(groundNodeAlpha(dim))
    }
  })
})

describe("hoverGroundAlpha", () => {
  // Hovering with nothing selected still sorts the canvas, but it is a
  // transient gesture, so it recedes half as far as a committed selection.
  it("is twice the configured strength", () => {
    expect(hoverGroundAlpha(15)).toBeCloseTo(0.3)
    expect(hoverGroundAlpha(25)).toBeCloseTo(0.5)
  })

  it("leaves more standing than a selection does", () => {
    expect(hoverGroundAlpha(15)).toBeGreaterThan(groundNodeAlpha(15))
  })

  it("never exceeds full strength", () => {
    expect(hoverGroundAlpha(50)).toBeLessThanOrEqual(1)
  })
})

describe("labelVisible", () => {
  const base = { tier: "none" as const, isHub: false, zoomedIn: false, isHovered: false }

  it("hides every ground label, hubs included", () => {
    expect(labelVisible({ ...base, tier: "ground", isHub: true })).toBe(false)
  })

  it("keeps hubs legible at whole-corpus zoom", () => {
    expect(labelVisible({ ...base, isHub: true })).toBe(true)
  })

  it("holds ordinary labels back until you are close enough to read them", () => {
    expect(labelVisible({ ...base })).toBe(false)
    expect(labelVisible({ ...base, zoomedIn: true })).toBe(true)
  })

  // Focusing a node is a request to read its neighbourhood, so the
  // neighbourhood is named regardless of zoom.
  it("reveals the focus and everything adjacent to it at any zoom", () => {
    expect(labelVisible({ ...base, tier: "focus" })).toBe(true)
    expect(labelVisible({ ...base, tier: "adjacent" })).toBe(true)
  })

  it("names whatever the pointer is on", () => {
    expect(labelVisible({ ...base, isHovered: true })).toBe(true)
  })

  // With a node selected, everything unrelated is ground -- but pointing at
  // one is a direct request to know what it is, and the ground rule was
  // swallowing it before the hover rule could answer.
  it("names a grounded node while the pointer is on it", () => {
    expect(labelVisible({ ...base, tier: "ground", isHovered: true })).toBe(true)
  })
})

describe("recede", () => {
  const DARK_BG = "#0b1013"
  const LIGHT_BG = "#ffffff"
  const NODE = "#4ade80"

  // Sigma blends premultiplied (gl.ONE, gl.ONE_MINUS_SRC_ALPHA), so a colour
  // carrying a low alpha contributes at FULL intensity: result = src + dst*(1-a).
  // Against a dark ground that is no dimming at all, which is exactly how the
  // first attempt failed. Receding toward the background needs no alpha and so
  // cannot depend on the blend mode.
  it("returns an opaque colour, never an alpha one", () => {
    expect(recede(NODE, DARK_BG, 0.15)).toMatch(/^#[0-9a-f]{6}$/i)
  })

  it("moves the colour toward the ground it sits on", () => {
    expect(recede(NODE, DARK_BG, 0.15)).not.toBe(recede(NODE, LIGHT_BG, 0.15))
  })

  it("keeps the node itself at full strength", () => {
    expect(recede(NODE, DARK_BG, 1)).toBe(NODE)
  })

  it("lands on the background when nothing is left", () => {
    expect(recede(NODE, DARK_BG, 0)).toBe(DARK_BG)
  })

  // The failure the user saw: a dimmed node on a dark page stayed as bright as
  // an undimmed one.
  it("darkens a bright node against a dark ground", () => {
    const dimmed = recede(NODE, DARK_BG, 0.15)
    const brightness = (hex: string) =>
      parseInt(hex.slice(1, 3), 16) +
      parseInt(hex.slice(3, 5), 16) +
      parseInt(hex.slice(5, 7), 16)
    expect(brightness(dimmed)).toBeLessThan(brightness(NODE) * 0.4)
  })
})
