import { describe, it, expect } from "vitest"
import { syntheticMemoryGraph } from "../synthetic-graph"

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
