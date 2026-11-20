import { describe, it, expect } from "vitest"
import {
  hullTopAnchor,
  placeRegionChips,
  REGION_CHIP_HEIGHT,
  regionChipLabel,
  type RegionChipInput,
} from "../graph-geometry"

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

describe("placeRegionChips", () => {
  const VIEW = { width: 800, height: 600, top: 48 }
  const chip = (key: string, count: number, top: { x: number; y: number }, bottom = 500): RegionChipInput => ({
    key,
    text: `${key} · ${count}`,
    count,
    width: 120,
    top,
    left: top.x - 100,
    right: top.x + 100,
    bottom,
  })
  const overlaps = (a: { x: number; y: number; width: number; height: number }, b: typeof a) =>
    a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height

  it("sits a chip centred just inside its region's top", () => {
    const [placed] = placeRegionChips([chip("a", 10, { x: 400, y: 200 })], VIEW)
    expect(placed!.x + placed!.width / 2).toBe(400)
    expect(placed!.y).toBeGreaterThan(200)
    expect(placed!.y).toBeLessThan(200 + 12)
  })

  it("pulls a chip inside the canvas edges and below the toolbar band", () => {
    const [left] = placeRegionChips([chip("a", 10, { x: 5, y: 10 })], VIEW)
    expect(left!.x).toBeGreaterThanOrEqual(0)
    expect(left!.y).toBeGreaterThanOrEqual(48)
    const [right] = placeRegionChips([chip("b", 10, { x: 795, y: 300 })], VIEW)
    expect(right!.x + right!.width).toBeLessThanOrEqual(800)
  })

  it("drops a chip whose region lies above the visible canvas", () => {
    expect(placeRegionChips([chip("a", 10, { x: 400, y: -300 }, 40)], VIEW)).toEqual([])
  })

  it("drops a chip whose region lies off either side of the canvas", () => {
    expect(placeRegionChips([chip("a", 10, { x: -250, y: 200 })], VIEW)).toEqual([])
    expect(placeRegionChips([chip("b", 10, { x: 1050, y: 200 })], VIEW)).toEqual([])
  })

  it("places larger regions first and moves a colliding chip below the one it hits", () => {
    const placed = placeRegionChips(
      [chip("small", 5, { x: 410, y: 200 }), chip("big", 50, { x: 400, y: 200 })],
      VIEW,
    )
    expect(placed.map((p) => p.key)).toEqual(["big", "small"])
    expect(overlaps(placed[0]!, placed[1]!)).toBe(false)
    expect(placed[1]!.y).toBeGreaterThan(placed[0]!.y + REGION_CHIP_HEIGHT - 1)
  })

  it("drops a chip that collides and has no room left inside its region", () => {
    const placed = placeRegionChips(
      [chip("big", 50, { x: 400, y: 200 }), chip("small", 5, { x: 400, y: 200 }, 205)],
      VIEW,
    )
    expect(placed.map((p) => p.key)).toEqual(["big"])
  })
})
