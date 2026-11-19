import { describe, expect, it } from "vitest"
import {
  HOVER_EDGE_SIZE,
  SELECTED_EDGE_SIZE,
  memoryEdgeSize,
  restEdgeSize,
} from "../memory-edge-width"

const KINDS = ["memory", "relation", "membership"] as const
const rest = { selected: false, hovered: false }

describe("memory edge widths", () => {
  it("draws thin edges: similarity 1.6, relation 1.2, membership 0.8, hover 2.4, selected 3.2", () => {
    expect(KINDS.map((k) => memoryEdgeSize(k, rest))).toEqual([1.6, 1.2, 0.8])
    expect(HOVER_EDGE_SIZE).toBe(2.4)
    expect(SELECTED_EDGE_SIZE).toBe(3.2)
  })

  it("keeps similarity over relation over membership at rest", () => {
    expect(restEdgeSize("memory")).toBeGreaterThan(restEdgeSize("relation"))
    expect(restEdgeSize("relation")).toBeGreaterThan(restEdgeSize("membership"))
  })

  it.each(KINDS)("draws a %s edge heavier on hover and heavier still on selection", (kind) => {
    const r = memoryEdgeSize(kind, rest)
    const h = memoryEdgeSize(kind, { selected: false, hovered: true })
    const s = memoryEdgeSize(kind, { selected: true, hovered: false })
    expect(r).toBeLessThan(h)
    expect(h).toBeLessThan(s)
    // Hovering a selected edge never thins it.
    expect(memoryEdgeSize(kind, { selected: true, hovered: true })).toBe(s)
  })

  it("treats an unknown kind as a similarity edge", () => {
    expect(restEdgeSize(undefined)).toBe(restEdgeSize("memory"))
  })
})
