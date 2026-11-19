import { describe, it, expect, vi } from "vitest"
import type Sigma from "sigma"
import {
  computeHullGroups,
  createHullShapeCache,
  drawFramedHull,
  framedHullVertices,
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
