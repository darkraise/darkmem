import { describe, it, expect } from "vitest"
import { layoutSignature } from "../graph-utils"

const MEM = ["m3", "m1", "m2"]
const ENT = ["e1", "e2"]

describe("layoutSignature", () => {
  it("is stable for the same graph", () => {
    expect(layoutSignature(100, 300, MEM, ENT)).toBe(
      layoutSignature(100, 300, MEM, ENT),
    )
  })

  it("ignores the order the server returned things in", () => {
    expect(layoutSignature(100, 300, ["m1", "m2"], ["e1", "e2"])).toBe(
      layoutSignature(100, 300, ["m2", "m1"], ["e2", "e1"]),
    )
  })

  it("does not mutate the caller's arrays while sorting", () => {
    const mem = ["m3", "m1"]
    const ent = ["e2", "e1"]
    layoutSignature(100, 300, mem, ent)
    expect(mem).toEqual(["m3", "m1"])
    expect(ent).toEqual(["e2", "e1"])
  })

  it("changes when the memory set does", () => {
    expect(layoutSignature(100, 300, ["m1"], [])).not.toBe(
      layoutSignature(100, 300, ["m1", "m2"], []),
    )
  })

  it.each([
    ["spacing", 200, 300],
    ["tightness", 100, 120],
  ])("changes when %s does", (_n, spacing, tightness) => {
    expect(layoutSignature(spacing, tightness, MEM, ENT)).not.toBe(
      layoutSignature(100, 300, MEM, ENT),
    )
  })

  // The two states the renderer has to tell apart. A fetch in flight draws the
  // same nodes as the render before it, so nothing should move; the data
  // landing genuinely adds nodes, and the graph should re-settle around them.
  describe("across an entity-layer toggle", () => {
    it("holds still while the fetch is in flight", () => {
      // Switch flipped, request sent, old data still in hand: same nodes.
      const before = layoutSignature(100, 300, MEM, [])
      const whileFetching = layoutSignature(100, 300, MEM, [])
      expect(whileFetching).toBe(before)
    })

    it("re-arranges once the entities arrive", () => {
      const whileFetching = layoutSignature(100, 300, MEM, [])
      const fetched = layoutSignature(100, 300, MEM, ENT)
      expect(fetched).not.toBe(whileFetching)
    })

    it("re-arranges when the overlay is dropped again", () => {
      expect(layoutSignature(100, 300, MEM, [])).not.toBe(
        layoutSignature(100, 300, MEM, ENT),
      )
    })
  })

  it("cannot confuse a memory id for an entity id", () => {
    // Without a separator, ["a"],["b"] and ["a","b"],[] would join to the same
    // string and one of the two states would be invisible.
    expect(layoutSignature(100, 300, ["a"], ["b"])).not.toBe(
      layoutSignature(100, 300, ["a", "b"], []),
    )
  })
})
