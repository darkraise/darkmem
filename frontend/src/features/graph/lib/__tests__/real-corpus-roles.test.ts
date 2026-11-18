import { describe, it, expect } from "vitest"
import { loadRealCorpus, type RealCorpusSize } from "../../fixtures/real-corpus"
import { classifyWithCut, CORE_MIN } from "../constellation-layout"

const RANK = { halo: 0, satellite: 1, core: 2 } as const

describe("roles on the real corpus", () => {
  for (const size of [200, 1000, "all"] as RealCorpusSize[]) {
    it(`A2: the ${size} fixture splits about 45% core, then clumps and halo`, () => {
      const c = loadRealCorpus(size)
      const r = classifyWithCut(c.memories.map((m) => m.id), c.edges)
      const n = c.memories.length
      const core = r.core.length / n
      const sat = r.satellites.flat().length / n
      const halo = r.halo.length / n
      expect(core).toBeGreaterThanOrEqual(0.35)
      expect(core).toBeLessThanOrEqual(0.5)
      expect(sat).toBeGreaterThanOrEqual(0.1)
      expect(sat).toBeLessThanOrEqual(0.25)
      expect(halo).toBeGreaterThanOrEqual(0.25)
      expect(halo).toBeLessThanOrEqual(0.45)
    })
  }

  it("A3: raising Edges from 0.5 to 0.8 never pulls a memory inward while an 8+ core remains", () => {
    const c = loadRealCorpus(1000)
    const ids = c.memories.map((m) => m.id)
    let prev = classifyWithCut(ids, c.edges)
    for (let step = 1; step <= 6; step++) {
      const t = 0.5 + step * 0.05
      const next = classifyWithCut(ids, c.edges.filter((e) => e.score >= t - 1e-9))
      if (next.core.length >= CORE_MIN) {
        for (const id of ids) expect(RANK[next.role.get(id)!]).toBeLessThanOrEqual(RANK[prev.role.get(id)!])
      }
      prev = next
    }
  })
})
