import { describe, it, expect } from "vitest"
import {
  CURVED_EDGE_LIMIT,
  scaleSettings,
  scaleTier,
} from "../graph-scale"

describe("scaleTier", () => {
  it("uses the code graph's boundaries", () => {
    expect(scaleTier(499)).toBe("small")
    expect(scaleTier(500)).toBe("medium")
    expect(scaleTier(1999)).toBe("medium")
    expect(scaleTier(2000)).toBe("large")
    expect(scaleTier(9999)).toBe("large")
    expect(scaleTier(10000)).toBe("huge")
  })
})

describe("scaleSettings", () => {
  it("keeps today's small-graph behaviour", () => {
    const s = scaleSettings(200, 500)
    expect(s.curvedEdges).toBe(true)
    expect(s.hideLabelsOnMove).toBe(false)
    expect(s.hoverDims).toBe(true)
    expect(s.slowDown).toBe(12)
    expect(s.layoutMs).toBe(8000)
    expect(s.arrows3D).toBe(true)
    expect(s.hulls3D).toBe(true)
  })

  it("straightens edges past the curve limit", () => {
    expect(scaleSettings(200, CURVED_EDGE_LIMIT).curvedEdges).toBe(true)
    expect(scaleSettings(200, CURVED_EDGE_LIMIT + 1).curvedEdges).toBe(false)
  })

  it("stops dimming the graph on hover from the large tier", () => {
    expect(scaleSettings(1999, 0).hoverDims).toBe(true)
    expect(scaleSettings(2000, 0).hoverDims).toBe(false)
  })

  it("trades detail for speed on huge graphs", () => {
    const s = scaleSettings(20000, 100000)
    expect(s.hideLabelsOnMove).toBe(true)
    expect(s.hoverDims).toBe(false)
    expect(s.barnesHutOptimize).toBe(true)
    expect(s.layoutMs).toBe(20000)
    expect(s.sphereSegments).toEqual([8, 6])
    expect(s.arrows3D).toBe(false)
    expect(s.hulls3D).toBe(false)
    expect(s.slowDown).toBeLessThan(scaleSettings(200, 0).slowDown)
  })
})
