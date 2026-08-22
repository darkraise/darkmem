import { describe, it, expect } from "vitest"
import {
  focusTier,
  groundNodeAlpha,
  groundEdgeAlpha,
  labelVisible,
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
})
