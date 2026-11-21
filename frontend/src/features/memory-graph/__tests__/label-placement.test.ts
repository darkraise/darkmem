import { describe, expect, it } from "vitest"
import { labelSide, placeLabels } from "../lib/label-placement"
import { MAX_ZOOM, MIN_ZOOM, panView, zoomViewAt } from "../lib/viewbox"

describe("placeLabels collisions", () => {
  it("keeps labels that do not collide", () => {
    const ids = placeLabels([
      { id: "a", x: 0, y: 0, text: "postgres" },
      { id: "b", x: 0, y: 40, text: "redis" },
    ]).keys()
    expect([...ids]).toEqual(["a", "b"])
  })

  it("hides a label that would overlap one already placed", () => {
    const ids = placeLabels([
      { id: "a", x: 0, y: 0, text: "postgres" },
      { id: "b", x: 20, y: 4, text: "pgvector" },
      { id: "c", x: 200, y: 0, text: "redis" },
    ]).keys()
    expect([...ids]).toEqual(["a", "c"])
  })
})

describe("placeLabels", () => {
  it("flips a label that would run past the right edge to the left", () => {
    const sides = placeLabels(
      [{ id: "a", x: 600, y: 50, text: "embedder_fingerprint" }],
      680,
    )
    expect(sides.get("a")).toBe("left")
  })

  it("tries the other side before hiding a colliding label", () => {
    const sides = placeLabels(
      [
        { id: "a", x: 200, y: 100, text: "hybrid_search" },
        { id: "b", x: 210, y: 104, text: "confidence_rank_gamma" },
      ],
      680,
    )
    expect(sides.get("a")).toBe("right")
    expect(sides.has("b")).toBe(true)
    expect(sides.get("b")).toBe("left")
  })

  it("keeps every placed label inside the canvas", () => {
    expect(
      labelSide({ id: "a", x: 20, y: 0, text: "a_long_label_name" }, 680),
    ).toBe("right")
  })
})

describe("viewbox zoom", () => {
  const base = { x: 0, y: 0, w: 680, h: 400 }

  it("keeps the zoom point fixed and clamps the level", () => {
    const zoomed = zoomViewAt(base, base, 0.5, 340, 200)
    expect(zoomed).toEqual({ x: 170, y: 100, w: 340, h: 200 })
    let view = base
    for (let i = 0; i < 40; i += 1) view = zoomViewAt(view, base, 0.5, 0, 0)
    expect(base.w / view.w).toBeCloseTo(MAX_ZOOM)
    for (let i = 0; i < 40; i += 1) view = zoomViewAt(view, base, 2, 0, 0)
    expect(base.w / view.w).toBeCloseTo(MIN_ZOOM)
  })

  it("pans against the drag", () => {
    expect(panView(base, 10, -5)).toEqual({ x: -10, y: 5, w: 680, h: 400 })
  })
})
