import { describe, it, expect } from "vitest"
import {
  entityRenderKey,
  layoutSignature,
  relationRenderKey,
} from "../graph-utils"

const MEM = ["m3", "m1", "m2"]
const ENT = ["e1", "e2"]

describe("layoutSignature", () => {
  it("is stable for the same graph", () => {
    expect(layoutSignature(MEM, ENT)).toBe(
      layoutSignature(MEM, ENT),
    )
  })

  it("ignores the order the server returned things in", () => {
    expect(layoutSignature(["m1", "m2"], ["e1", "e2"])).toBe(
      layoutSignature(["m2", "m1"], ["e2", "e1"]),
    )
  })

  it("does not mutate the caller's arrays while sorting", () => {
    const mem = ["m3", "m1"]
    const ent = ["e2", "e1"]
    layoutSignature(mem, ent)
    expect(mem).toEqual(["m3", "m1"])
    expect(ent).toEqual(["e2", "e1"])
  })

  it("changes when the memory set does", () => {
    expect(layoutSignature.length).toBeLessThanOrEqual(2)
    expect(layoutSignature(["m1"], [])).not.toBe(
      layoutSignature(["m1", "m2"], []),
    )
  })

  // The two states the renderer has to tell apart. A fetch in flight draws the
  // same nodes as the render before it, so nothing should move; the data
  // landing genuinely adds nodes, and the graph should re-settle around them.
  describe("across an entity-layer toggle", () => {
    it("holds still while the fetch is in flight", () => {
      // Switch flipped, request sent, old data still in hand: same nodes.
      const before = layoutSignature(MEM, [])
      const whileFetching = layoutSignature(MEM, [])
      expect(whileFetching).toBe(before)
    })

    it("re-arranges once the entities arrive", () => {
      const whileFetching = layoutSignature(MEM, [])
      const fetched = layoutSignature(MEM, ENT)
      expect(fetched).not.toBe(whileFetching)
    })

    it("re-arranges when the overlay is dropped again", () => {
      expect(layoutSignature(MEM, [])).not.toBe(
        layoutSignature(MEM, ENT),
      )
    })
  })

  it("cannot confuse a memory id for an entity id", () => {
    // Without a separator, ["a"],["b"] and ["a","b"],[] would join to the same
    // string and one of the two states would be invisible.
    expect(layoutSignature(["a"], ["b"])).not.toBe(
      layoutSignature(["a", "b"], []),
    )
  })
})

describe("entityRenderKey", () => {
  const E = [
    { id: "e1", entity_type: "tool" },
    { id: "e2", entity_type: "person" },
  ]

  // The point of the key: a rebuild costs a sigma teardown and a fresh WebGL
  // canvas, so two renders that would draw the same overlay must key the same.
  it("keys the layer-off and fetch-in-flight states identically", () => {
    const off = entityRenderKey(false, E)
    const onButNothingYet = entityRenderKey(true, [])
    expect(onButNothingYet).toBe(off)
    expect(off).toBe("")
  })

  it("keys the arrived overlay differently", () => {
    expect(entityRenderKey(true, E)).not.toBe(entityRenderKey(true, []))
  })

  it("ignores the entity array's identity, only its contents", () => {
    expect(entityRenderKey(true, [...E])).toBe(entityRenderKey(true, E))
  })

  it("changes when an entity's type does, because the type is its colour", () => {
    expect(entityRenderKey(true, [{ id: "e1", entity_type: "tool" }])).not.toBe(
      entityRenderKey(true, [{ id: "e1", entity_type: "person" }]),
    )
  })

  it("stays empty when the layer is off, whatever data is in hand", () => {
    expect(entityRenderKey(false, E)).toBe("")
  })
})

describe("relationRenderKey", () => {
  const R = [{ source: "e1", target: "e2", type: "USES" }]

  it("is empty while there is nothing to draw", () => {
    expect(relationRenderKey(false, R)).toBe("")
    expect(relationRenderKey(true, [])).toBe("")
  })

  it("changes with the relation type, which is its label", () => {
    expect(relationRenderKey(true, R)).not.toBe(
      relationRenderKey(true, [{ source: "e1", target: "e2", type: "REPLACES" }]),
    )
  })
})
