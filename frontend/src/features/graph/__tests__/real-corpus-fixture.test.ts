import { describe, it, expect } from "vitest"
import small from "../fixtures/real-corpus-200.json"
import mid from "../fixtures/real-corpus-1000.json"
import all from "../fixtures/real-corpus-all.json"
import { loadRealCorpus } from "../fixtures/real-corpus"

const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i
const fixtures = [
  ["200", small],
  ["1000", mid],
  ["all", all],
] as const

describe("real-corpus fixtures", () => {
  for (const [name, fx] of fixtures) {
    it(`A13: the ${name} fixture carries no content, tags, project, real names or UUIDs`, () => {
      const text = JSON.stringify(fx)
      expect(text).not.toMatch(UUID)
      expect(text).not.toMatch(/"(content|tags|project|properties)"\s*:/)
      for (const label of Object.values(fx.clusterNames)) expect(label).toMatch(/^Cluster \d+$/)
      for (const e of ("entities" in fx ? fx.entities : []) ?? []) expect(e.name).toMatch(/^Entity \d+$/)
      for (const m of fx.memories) {
        expect(Object.keys(m).sort()).toEqual(["cluster", "id", "importance", "memory_type"])
        expect(m.id).toMatch(/^[0-9a-f]{12}$/)
      }
    })
  }

  it("holds 200, 1,000 and every memory, with edges between fixture memories at 0.5 or more", () => {
    expect(small.memories).toHaveLength(200)
    expect(mid.memories).toHaveLength(1000)
    expect(all.memories.length).toBeGreaterThan(4000)
    for (const [, fx] of fixtures) {
      const ids = new Set(fx.memories.map((m) => m.id))
      for (const e of fx.edges) {
        expect(ids.has(e.source) && ids.has(e.target)).toBe(true)
        expect(e.score).toBeGreaterThanOrEqual(0.5)
      }
    }
  })

  it("loadRealCorpus fills placeholder content in server order and empty tags", () => {
    const c = loadRealCorpus(200)
    expect(c.memories[0]!.content).toBe("Memory 1")
    expect(c.memories[199]!.content).toBe("Memory 200")
    expect(c.memories.every((m) => m.tags.length === 0 && m.source === "fixture")).toBe(true)
    expect(c.edges).toHaveLength(small.edges.length)
    expect(c.entities).toEqual([])
  })

  it("the 1,000 fixture carries entities whose memory ids are fixture memories", () => {
    const c = loadRealCorpus(1000)
    const ids = new Set(c.memories.map((m) => m.id))
    expect(c.entities.length).toBeGreaterThan(0)
    for (const e of c.entities) {
      expect(e.id).toMatch(/^[0-9a-f]{12}$/)
      for (const id of e.memory_ids) expect(ids.has(id)).toBe(true)
    }
  })
})
