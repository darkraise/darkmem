import type Graph from "graphology"

/**
 * The nodes and edges whose reducer output a hover move can change when hover
 * does not dim the graph: both hovered nodes, their neighbours (a selection
 * lets hover pull them out of the ground) and their incident edges.
 */
export function hoverRepaintSet(
  graph: Graph,
  previous: string | null,
  next: string | null,
): { nodes: string[]; edges: string[] } {
  const nodes = new Set<string>()
  const edges = new Set<string>()
  for (const id of [previous, next]) {
    if (!id || !graph.hasNode(id)) continue
    nodes.add(id)
    graph.forEachNeighbor(id, (n) => nodes.add(n))
    graph.forEachEdge(id, (e) => edges.add(e))
  }
  return { nodes: [...nodes], edges: [...edges] }
}
