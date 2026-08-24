import { describe, it, expect } from "vitest"
import {
  edgeEmphasis,
  litByHover,
  groundEdgeAlpha,
  hoverGroundEdgeAlpha,
} from "../focus-model"

// The canvas sorts on two inputs, and the pointer used to be ignored whenever
// a node was committed: hovering a neighbour bumped its edge width while the
// selection branch had already receded its colour, so the gesture answered
// nothing. Both inputs now light their own spokes.
describe("edgeEmphasis", () => {
  describe("with nothing focused", () => {
    it("leaves every edge alone", () => {
      expect(edgeEmphasis("a", "b", null, null)).toEqual({
        lit: false,
        zIndex: 0,
        ground: null,
      })
    })
  })

  describe("under a selection", () => {
    it("lights an edge on either endpoint of the selected node", () => {
      expect(edgeEmphasis("sel", "b", "sel", null).lit).toBe(true)
      expect(edgeEmphasis("b", "sel", "sel", null).lit).toBe(true)
    })

    it("recedes an edge that does not touch it into the selection ground", () => {
      expect(edgeEmphasis("a", "b", "sel", null)).toEqual({
        lit: false,
        zIndex: 0,
        ground: "selection",
      })
    })
  })

  describe("hovering while a node is selected", () => {
    it("lights the hovered node's own edges", () => {
      expect(edgeEmphasis("hov", "x", "sel", "hov").lit).toBe(true)
      expect(edgeEmphasis("x", "hov", "sel", "hov").lit).toBe(true)
    })

    it("keeps the selection's edges lit at the same time", () => {
      expect(edgeEmphasis("sel", "y", "sel", "hov").lit).toBe(true)
    })

    it("still grounds an edge touching neither", () => {
      expect(edgeEmphasis("a", "b", "sel", "hov").ground).toBe("selection")
    })
  })

  describe("hovering with nothing selected", () => {
    it("recedes the rest into the shallower hover ground", () => {
      expect(edgeEmphasis("a", "b", null, "hov").ground).toBe("hover")
    })

    // The hover ground is deliberately the shallower of the two: pointing is a
    // transient gesture, selecting is a committed one.
    it("is a shallower ground than a selection's", () => {
      expect(hoverGroundEdgeAlpha(15)).toBeGreaterThan(groundEdgeAlpha(15))
    })
  })

  describe("paint order", () => {
    // Every edge shares one program, so this index is the only thing standing
    // between a lit spoke and the ground being drawn across it.
    it("orders a lit edge above the ground", () => {
      const lit = edgeEmphasis("sel", "b", "sel", null)
      const ground = edgeEmphasis("a", "b", "sel", null)
      expect(lit.zIndex).toBeGreaterThan(ground.zIndex)
    })

    it("leaves the order flat when nothing is focused", () => {
      expect(edgeEmphasis("a", "b", null, null).zIndex).toBe(0)
      expect(edgeEmphasis("c", "d", null, null).zIndex).toBe(0)
    })
  })
})

describe("litByHover", () => {
  it("is false while the pointer is off the canvas", () => {
    expect(litByHover("a", null, false)).toBe(false)
    expect(litByHover("a", null, true)).toBe(false)
  })

  it("lights the hovered node", () => {
    expect(litByHover("a", "a", false)).toBe(true)
  })

  // Paired with the edge rule: an undimmed spoke ending on a node still
  // pushed back to the ground reads as an edge to nowhere.
  it("lights a neighbour of the hovered node", () => {
    expect(litByHover("b", "a", true)).toBe(true)
  })

  it("leaves an unrelated node in the ground", () => {
    expect(litByHover("c", "a", false)).toBe(false)
  })
})
