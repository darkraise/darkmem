import { describe, it, expect } from "vitest"
import { hullTopAnchor, regionChipLabel } from "../graph-geometry"

describe("hullTopAnchor", () => {
  it("is null when there is no region to anchor to", () => {
    expect(hullTopAnchor([])).toBeNull()
  })

  // The chip hangs off the top of the territory, so the anchor is the
  // highest point — smallest y, since the viewport counts downward.
  it("takes the topmost point of the region", () => {
    const anchor = hullTopAnchor([
      { x: 10, y: 90 },
      { x: 40, y: 20 },
      { x: 70, y: 60 },
    ])
    expect(anchor).toEqual({ x: 40, y: 20 })
  })

  it("breaks a tie on the leftmost of the tied points", () => {
    const anchor = hullTopAnchor([
      { x: 70, y: 20 },
      { x: 30, y: 20 },
    ])
    expect(anchor).toEqual({ x: 30, y: 20 })
  })
})

describe("regionChipLabel", () => {
  it("names the region and how much is in it", () => {
    expect(regionChipLabel("Retrieval & ranking", 4)).toBe(
      "Retrieval & ranking · 4",
    )
  })

  it("does not pluralise a count that is already a number", () => {
    expect(regionChipLabel("Storage", 1)).toBe("Storage · 1")
  })

  // A cluster id is a legitimate group key when no name has been derived, and
  // rendering it raw is more honest than inventing a name for it.
  it("passes a bare group key through unchanged", () => {
    expect(regionChipLabel("7", 3)).toBe("7 · 3")
  })
})
