import { describe, it, expect, vi } from "vitest"
import type Sigma from "sigma"
import {
  computeHullGroups,
  createHullShapeCache,
  drawFramedHull,
  framedHullVertices,
  roundedHullCorners,
  type HullMode,
} from "../graph-geometry"

const POSITIONS: Record<string, { x: number; y: number }> = {
  a: { x: 0, y: 0 },
  b: { x: 1, y: 0 },
  c: { x: 1, y: 1 },
  d: { x: 0, y: 1 },
  inner: { x: 0.5, y: 0.5 },
}

function fakeSigma() {
  const framedGraphToViewport = vi.fn((p: { x: number; y: number }) => ({
    x: p.x * 100 + 10,
    y: -p.y * 100 + 200,
  }))
  const sigma = {
    getNodeDisplayData: (id: string) => POSITIONS[id],
    framedGraphToViewport,
  } as unknown as Sigma
  return { sigma, framedGraphToViewport }
}

function fakeContext(): CanvasRenderingContext2D {
  return new Proxy({} as Record<string, unknown>, {
    get: (target, key) => {
      if (!(key in target)) target[key as string] = vi.fn()
      return target[key as string]
    },
    set: (target, key, value) => {
      target[key as string] = value
      return true
    },
  }) as unknown as CanvasRenderingContext2D
}

describe("framedHullVertices", () => {
  it("keeps only the hull's corners, in framed space", () => {
    const { sigma } = fakeSigma()
    const hull = framedHullVertices(sigma, ["a", "b", "c", "d", "inner", "missing"])
    expect(hull).toHaveLength(4)
    expect(hull).not.toContainEqual(POSITIONS.inner)
  })

  it("passes one or two members through", () => {
    const { sigma } = fakeSigma()
    expect(framedHullVertices(sigma, ["a", "b"])).toEqual([POSITIONS.a, POSITIONS.b])
  })
})

describe("drawFramedHull", () => {
  it("maps only the stored vertices to the viewport", () => {
    const { sigma, framedGraphToViewport } = fakeSigma()
    const framed = framedHullVertices(sigma, ["a", "b", "c", "d", "inner"])
    const drawn = drawFramedHull(fakeContext(), sigma, framed, "#336699", 0.06, 0.28)
    expect(framedGraphToViewport).toHaveBeenCalledTimes(4)
    expect(drawn).toHaveLength(4)
  })

  it("draws nothing for fewer than two vertices", () => {
    const { sigma } = fakeSigma()
    const ctx = fakeContext()
    expect(drawFramedHull(ctx, sigma, [POSITIONS.a!], "#336699", 0.06, 0.28)).toHaveLength(1)
    expect(ctx.fill).not.toHaveBeenCalled()
  })
})

describe("roundedHullCorners", () => {
  const TAU = 2 * Math.PI
  const sweep = (c: { from: number; to: number }) => c.to - c.from
  // Each arc starts on the previous edge's outward normal and ends on the next
  // one's, so the outline turns once, smoothly, with no kink or loop.
  const joinsSmoothly = (corners: ReturnType<typeof roundedHullCorners>) => {
    for (let i = 0; i < corners.length; i++) {
      const next = corners[(i + 1) % corners.length]!
      const d = (corners[i]!.to - next.from) % TAU
      expect(Math.min(Math.abs(d), TAU - Math.abs(d))).toBeCloseTo(0, 9)
    }
  }

  it("turns a square through four quarter arcs, once round", () => {
    const corners = roundedHullCorners([
      { x: 0, y: 0 },
      { x: 10, y: 0 },
      { x: 10, y: 10 },
      { x: 0, y: 10 },
    ])
    expect(corners).toHaveLength(4)
    for (const c of corners) expect(sweep(c)).toBeCloseTo(Math.PI / 2, 9)
    joinsSmoothly(corners)
  })

  it("draws the same outline whichever way the hull winds", () => {
    const cw = roundedHullCorners([
      { x: 0, y: 0 },
      { x: 10, y: 0 },
      { x: 5, y: 8 },
    ])
    const ccw = roundedHullCorners([
      { x: 5, y: 8 },
      { x: 10, y: 0 },
      { x: 0, y: 0 },
    ])
    const total = (cs: typeof cw) => cs.reduce((s, c) => s + sweep(c), 0)
    expect(total(cw)).toBeCloseTo(TAU, 9)
    expect(total(ccw)).toBeCloseTo(TAU, 9)
    for (const c of [...cw, ...ccw]) expect(sweep(c)).toBeGreaterThanOrEqual(0)
    joinsSmoothly(cw)
    joinsSmoothly(ccw)
  })

  it("keeps closely spaced vertices smooth, with tiny arcs rather than spikes", () => {
    const corners = roundedHullCorners([
      { x: 0, y: 0 },
      { x: 100, y: 0 },
      { x: 100.5, y: 0.4 },
      { x: 100, y: 60 },
      { x: 0, y: 60 },
    ])
    for (const c of corners) {
      expect(sweep(c)).toBeGreaterThanOrEqual(0)
      expect(sweep(c)).toBeLessThan(Math.PI)
    }
    joinsSmoothly(corners)
  })

  it("gives two points a capsule and one point a circle", () => {
    const capsule = roundedHullCorners([
      { x: 0, y: 0 },
      { x: 10, y: 0 },
    ])
    expect(capsule.map(sweep)).toEqual([Math.PI, Math.PI].map((v) => expect.closeTo(v, 9)))
    const circle = roundedHullCorners([{ x: 3, y: 4 }])
    expect(circle).toEqual([{ x: 3, y: 4, from: 0, to: TAU }])
    expect(roundedHullCorners([])).toEqual([])
  })

  it("draws the outline as arcs only, with a solid stroke", () => {
    const { sigma } = fakeSigma()
    const ctx = fakeContext()
    drawFramedHull(ctx, sigma, framedHullVertices(sigma, ["a", "b", "c", "d"]), "#336699", 0.06, 0.28)
    expect(ctx.arc).toHaveBeenCalledTimes(4)
    expect(ctx.bezierCurveTo).not.toHaveBeenCalled()
    expect(ctx.setLineDash).not.toHaveBeenCalled()
  })
})

describe("createHullShapeCache", () => {
  const GROUPS = new Map([["0", ["a", "b", "c", "d", "inner"]]])
  const groupsOf = (_memories: { id: string }[], _mode: HullMode) => GROUPS

  it("regroups only when the memories or the mode change", () => {
    const { sigma } = fakeSigma()
    const compute = vi.fn(groupsOf)
    const cache = createHullShapeCache(compute, 250)
    const memories = [{ id: "a" }]
    cache.update(memories, "cluster", sigma, false, 0)
    cache.update(memories, "cluster", sigma, true, 1000)
    expect(compute).toHaveBeenCalledTimes(1)
    const next = [...memories]
    cache.update(next, "cluster", sigma, false, 2000)
    expect(compute).toHaveBeenCalledTimes(2)
    cache.update(next, "none", sigma, false, 3000)
    expect(compute).toHaveBeenCalledTimes(3)
  })

  it("islands UI-1: turning the mode off leaves no group and no shape to draw, and on again restores them", () => {
    const { sigma } = fakeSigma()
    const cache = createHullShapeCache(computeHullGroups, 250)
    const memories = [
      { id: "a", cluster: 0 },
      { id: "b", cluster: 0 },
      { id: "c", cluster: 0 },
      { id: "d", cluster: 0 },
      { id: "inner", cluster: -1 },
    ]
    expect([...cache.update(memories, "cluster", sigma, false, 0).keys()]).toEqual(["0"])
    expect(cache.shape("0").length).toBeGreaterThan(2)
    expect(cache.update(memories, "none", sigma, false, 1).size).toBe(0)
    expect(cache.shape("0")).toEqual([])
    expect([...cache.update(memories, "cluster", sigma, false, 2).keys()]).toEqual(["0"])
    expect(cache.shape("0").length).toBeGreaterThan(2)
  })

  it("reshapes at most every refreshMs while the layout runs, and once after invalidate", () => {
    const { sigma } = fakeSigma()
    const reads = vi.spyOn(sigma, "getNodeDisplayData")
    const cache = createHullShapeCache(groupsOf, 250)
    const memories = [{ id: "a" }]
    cache.update(memories, "cluster", sigma, true, 0)
    expect(reads).toHaveBeenCalledTimes(5)
    cache.update(memories, "cluster", sigma, true, 100)
    expect(reads).toHaveBeenCalledTimes(5)
    cache.update(memories, "cluster", sigma, true, 300)
    expect(reads).toHaveBeenCalledTimes(10)
    cache.update(memories, "cluster", sigma, false, 1000)
    expect(reads).toHaveBeenCalledTimes(10)
    cache.invalidate()
    cache.update(memories, "cluster", sigma, false, 1001)
    expect(reads).toHaveBeenCalledTimes(15)
    expect(cache.shape("0")).toHaveLength(4)
    expect(cache.shape("missing")).toEqual([])
  })
})
