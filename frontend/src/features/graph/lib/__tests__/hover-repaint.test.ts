import { describe, it, expect } from "vitest"
import Graph from "graphology"
import { hoverRepaintSet } from "../hover-repaint"

function star() {
  const g = new Graph()
  for (const n of ["hub", "a", "b", "c", "far", "x"]) g.addNode(n)
  g.addEdgeWithKey("hub-a", "hub", "a")
  g.addEdgeWithKey("b-hub", "b", "hub")
  g.addEdgeWithKey("hub-c", "hub", "c")
  g.addEdgeWithKey("c-far", "c", "far")
  g.addEdgeWithKey("x-far", "x", "far")
  return g
}

const sorted = (r: { nodes: string[]; edges: string[] }) => ({
  nodes: [...r.nodes].sort(),
  edges: [...r.edges].sort(),
})

describe("hoverRepaintSet", () => {
  it("repaints nothing when the pointer was and stays off every node", () => {
    expect(hoverRepaintSet(star(), null, null)).toEqual({ nodes: [], edges: [] })
  })

  it("repaints a newly hovered node, its neighbours in both directions and its edges", () => {
    expect(sorted(hoverRepaintSet(star(), null, "hub"))).toEqual({
      nodes: ["a", "b", "c", "hub"],
      edges: ["b-hub", "hub-a", "hub-c"],
    })
  })

  it("repaints the node the pointer left as well as the one it entered, once each", () => {
    expect(sorted(hoverRepaintSet(star(), "hub", "c"))).toEqual({
      nodes: ["a", "b", "c", "far", "hub"],
      edges: ["b-hub", "c-far", "hub-a", "hub-c"],
    })
  })

  it("lists a self-loop's node and edge once", () => {
    const g = new Graph()
    g.addNode("n")
    g.addEdgeWithKey("loop", "n", "n")
    expect(hoverRepaintSet(g, null, "n")).toEqual({ nodes: ["n"], edges: ["loop"] })
  })

  it("skips a hovered id the current graph no longer holds", () => {
    expect(sorted(hoverRepaintSet(star(), "gone", "x"))).toEqual({
      nodes: ["far", "x"],
      edges: ["x-far"],
    })
  })
})
