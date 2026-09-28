import { describe, it, expect } from "vitest"
import {
  CURVED_EDGE_LIMIT,
  clusterAnchors,
  scaleSettings,
  scaleTier,
  seedAroundAnchor,
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
    expect(s.hideOnMove).toBe(false)
    expect(s.slowDown).toBe(12)
    expect(s.layoutMs).toBe(8000)
    expect(s.arrows3D).toBe(true)
    expect(s.hulls3D).toBe(true)
  })

  it("straightens edges past the curve limit", () => {
    expect(scaleSettings(200, CURVED_EDGE_LIMIT).curvedEdges).toBe(true)
    expect(scaleSettings(200, CURVED_EDGE_LIMIT + 1).curvedEdges).toBe(false)
  })

  it("trades detail for speed on huge graphs", () => {
    const s = scaleSettings(20000, 100000)
    expect(s.hideOnMove).toBe(true)
    expect(s.barnesHutOptimize).toBe(true)
    expect(s.layoutMs).toBe(20000)
    expect(s.sphereSegments).toEqual([8, 6])
    expect(s.arrows3D).toBe(false)
    expect(s.hulls3D).toBe(false)
    expect(s.slowDown).toBeLessThan(scaleSettings(200, 0).slowDown)
  })
})

describe("clusterAnchors", () => {
  it("places the largest cluster at the centre and skips unclustered nodes", () => {
    const memories = [
      ...Array.from({ length: 9 }, () => ({ cluster: 3 })),
      ...Array.from({ length: 4 }, () => ({ cluster: 1 })),
      { cluster: -1 },
    ]
    const anchors = clusterAnchors(memories)
    expect([...anchors.keys()]).toEqual([3, 1])
    expect(anchors.get(3)).toMatchObject({ x: 0, y: 0 })
    expect(anchors.get(3)!.spread).toBeGreaterThan(anchors.get(1)!.spread)
    expect(anchors.has(-1)).toBe(false)
  })

  it("is deterministic", () => {
    const memories = [{ cluster: 0 }, { cluster: 1 }, { cluster: 1 }]
    expect([...clusterAnchors(memories)]).toEqual([...clusterAnchors(memories)])
  })
})

describe("seedAroundAnchor", () => {
  it("stays within the anchor's spread", () => {
    const anchor = { x: 5, y: -3, spread: 2 }
    for (const [u, v] of [[0, 0], [0.25, 1], [0.9, 0.5]] as const) {
      const p = seedAroundAnchor(anchor, u, v)
      expect(Math.hypot(p.x - 5, p.y + 3)).toBeLessThanOrEqual(2 + 1e-9)
    }
  })
})
