import { describe, it, expect } from "vitest"
import { syntheticMemoryGraph, syntheticShape } from "../synthetic-graph"
import { classify } from "../constellation-layout"

describe("syntheticMemoryGraph", () => {
  it("is deterministic for a seed", () => {
    expect(syntheticMemoryGraph(500, 10, 5, 3)).toEqual(syntheticMemoryGraph(500, 10, 5, 3))
  })

  it("builds the requested nodes and in-cluster edges without duplicates", () => {
    const g = syntheticMemoryGraph(2000, 20, 5)
    expect(g.memories).toHaveLength(2000)
    const cluster = new Map(g.memories.map((m) => [m.id, m.cluster]))
    const keys = new Set<string>()
    for (const e of g.edges) {
      expect(e.source).not.toBe(e.target)
      expect(cluster.get(e.source)).toBe(cluster.get(e.target))
      const key = [e.source, e.target].sort().join("|")
      expect(keys.has(key)).toBe(false)
      keys.add(key)
    }
    expect(g.edges.length).toBeGreaterThan(2000 * 4)
    expect(g.edges.length).toBeLessThanOrEqual(2000 * 5)
    expect(Object.keys(g.clusterNames)).toHaveLength(20)
  })
})

describe("syntheticShape", () => {
  const roles = (shape: Parameters<typeof syntheticShape>[0]) => {
    const g = syntheticShape(shape, 300)
    const c = classify(g.memories.map((m) => m.id), g.edges)
    return { core: c.core.length, sats: c.satellites.length, halo: c.halo.length, n: g.memories.length }
  }

  it.each([
    ["one-component", (r: ReturnType<typeof roles>) => r.core === r.n],
    ["all-orphans", (r: ReturnType<typeof roles>) => r.halo === r.n],
    ["no-orphans", (r: ReturnType<typeof roles>) => r.halo === 0 && r.core > 0],
    ["many-satellites", (r: ReturnType<typeof roles>) => r.sats >= 20],
    ["mixed", (r: ReturnType<typeof roles>) => r.core > 0 && r.sats > 0 && r.halo > 0],
  ] as const)("%s", (shape, holds) => {
    expect(holds(roles(shape))).toBe(true)
  })
})
