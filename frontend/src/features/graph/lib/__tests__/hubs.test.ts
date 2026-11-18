import { describe, it, expect } from "vitest"
import { topHubs } from "../hubs"
import { loadRealCorpus } from "../../fixtures/real-corpus"

describe("topHubs", () => {
  it("A10: takes the top 2% by degree then id, only at 5 or more edges, at least one when any qualifies", () => {
    const d = new Map<string, number>(Array.from({ length: 500 }, (_, i) => [`m${String(i).padStart(3, "0")}`, i % 10] as const))
    const hubs = topHubs(d)
    expect(hubs.size).toBe(10)
    for (const id of hubs) expect(d.get(id)).toBe(9)
    expect([...hubs].sort()[0]).toBe("m009")
    expect(topHubs(new Map([["a", 5], ["b", 1]])).size).toBe(1)
    expect(topHubs(new Map([["a", 4], ["b", 1]])).size).toBe(0)
  })

  it("A10: the 1,000-memory fixture has at most 20 hubs", () => {
    const c = loadRealCorpus(1000)
    const deg = new Map(c.memories.map((m) => [m.id, 0]))
    for (const e of c.edges) {
      deg.set(e.source, deg.get(e.source)! + 1)
      deg.set(e.target, deg.get(e.target)! + 1)
    }
    const hubs = topHubs(deg)
    expect(hubs.size).toBeGreaterThan(0)
    expect(hubs.size).toBeLessThanOrEqual(20)
  })
})
