import { describe, it, expect } from "vitest"
import type { CodeGraphEdge, CodeGraphNode } from "@/hooks/api"
import {
  deriveCodeGraph,
  deriveCommunities,
  deriveProcesses,
  fileOfGraphKey,
} from "../lib/graph-derive"

describe("deriveCommunities", () => {
  it("groups symbols by member_of edges and assigns a cycling chart index", () => {
    const nodes: CodeGraphNode[] = [
      { id: "sym:a", label: "ProcessingPipeline", kind: "class" },
      { id: "sym:b", label: "process_batch", kind: "method" },
      { id: "comm:1", label: "ingestion", kind: "community" },
      { id: "comm:2", label: "retrieval", kind: "community" },
    ]
    const edges: CodeGraphEdge[] = [
      { source: "sym:a", target: "comm:1", type: "member_of" },
      { source: "sym:b", target: "comm:1", type: "member_of" },
    ]

    const communities = deriveCommunities(nodes, edges)
    expect(communities).toEqual([
      { id: "comm:1", label: "ingestion", chart: 1 },
      { id: "comm:2", label: "retrieval", chart: 2 },
    ])
  })

  it("cycles the chart index back to 1 after 5 communities", () => {
    const nodes: CodeGraphNode[] = Array.from({ length: 6 }, (_, i) => ({
      id: `comm:${i}`,
      label: `c${i}`,
      kind: "community",
    }))
    const communities = deriveCommunities(nodes, [])
    expect(communities.map((c) => c.chart)).toEqual([1, 2, 3, 4, 5, 1])
  })

  it("never materialises a singleton community node — CommunityDetector's own len(members) >= 2 filter", () => {
    // A symbol whose only community would be a singleton gets no
    // code_graph_nodes row at all for that community and no member_of
    // edge — nothing to derive, not an edge case to special-case here,
    // but the symbol itself must still resolve to "" in deriveCodeGraph
    // (covered below) rather than crash.
    const nodes: CodeGraphNode[] = [
      { id: "sym:lonely", label: "lonely_fn", kind: "function" },
    ]
    expect(deriveCommunities(nodes, [])).toEqual([])
  })
})

describe("deriveProcesses", () => {
  it("orders steps by the edge's own step property, not edge array order", () => {
    const nodes: CodeGraphNode[] = [
      { id: "proc:ingest", label: "proc:ingest", kind: "process" },
    ]
    // Deliberately inserted out of step order.
    const edges: CodeGraphEdge[] = [
      {
        source: "sym:c",
        target: "proc:ingest",
        type: "step_in_process",
        properties: { step: 3 },
      },
      {
        source: "sym:a",
        target: "proc:ingest",
        type: "step_in_process",
        properties: { step: 1 },
      },
      {
        source: "sym:b",
        target: "proc:ingest",
        type: "step_in_process",
        properties: { step: 2 },
      },
    ]

    const processes = deriveProcesses(nodes, edges)
    expect(processes).toEqual([
      { id: "proc:ingest", label: "proc:ingest", steps: ["sym:a", "sym:b", "sym:c"] },
    ])
  })

  it("keeps two processes' steps independent when a symbol is a step in both", () => {
    const nodes: CodeGraphNode[] = [
      { id: "proc:a", label: "proc:a", kind: "process" },
      { id: "proc:b", label: "proc:b", kind: "process" },
    ]
    const edges: CodeGraphEdge[] = [
      {
        source: "sym:shared",
        target: "proc:a",
        type: "step_in_process",
        properties: { step: 1 },
      },
      {
        source: "sym:shared",
        target: "proc:b",
        type: "step_in_process",
        properties: { step: 1 },
      },
      {
        source: "sym:only-a",
        target: "proc:a",
        type: "step_in_process",
        properties: { step: 2 },
      },
    ]

    const processes = deriveProcesses(nodes, edges)
    expect(processes.find((p) => p.id === "proc:a")?.steps).toEqual([
      "sym:shared",
      "sym:only-a",
    ])
    expect(processes.find((p) => p.id === "proc:b")?.steps).toEqual([
      "sym:shared",
    ])
  })

  it("returns an empty step list for a process with no step_in_process edges", () => {
    const nodes: CodeGraphNode[] = [
      { id: "proc:empty", label: "proc:empty", kind: "process" },
    ]
    expect(deriveProcesses(nodes, [])).toEqual([
      { id: "proc:empty", label: "proc:empty", steps: [] },
    ])
  })
})

describe("deriveCodeGraph", () => {
  const nodes: CodeGraphNode[] = [
    { id: "file:main.py", label: "main.py", kind: "file", file_path: "main.py" },
    {
      id: "sym:a",
      label: "ProcessingPipeline",
      kind: "class",
      file_path: "main.py",
    },
    // A symbol that is a member of zero communities — CommunityDetector's
    // singleton filter means this is a real, expected shape, not a bug.
    {
      id: "sym:lonely",
      label: "lonely_fn",
      kind: "function",
      file_path: "main.py",
    },
    { id: "comm:1", label: "ingestion", kind: "community" },
    { id: "proc:ingest", label: "proc:ingest", kind: "process" },
  ]
  const edges: CodeGraphEdge[] = [
    { source: "sym:a", target: "comm:1", type: "member_of" },
    {
      source: "sym:a",
      target: "proc:ingest",
      type: "step_in_process",
      properties: { step: 1 },
    },
    { source: "file:main.py", target: "sym:a", type: "CONTAINS" },
  ]

  it("assigns a node's community from its member_of edge, and '' when it has none", () => {
    const graph = deriveCodeGraph("r1", { nodes, edges })
    const a = graph.nodes.find((n) => n.id === "sym:a")
    const lonely = graph.nodes.find((n) => n.id === "sym:lonely")
    expect(a?.community).toBe("comm:1")
    expect(lonely?.community).toBe("")
  })

  it("pulls community/process pseudo-nodes out of the node list", () => {
    const graph = deriveCodeGraph("r1", { nodes, edges })
    expect(graph.nodes.map((n) => n.id).sort()).toEqual([
      "file:main.py",
      "sym:a",
      "sym:lonely",
    ])
    expect(graph.communities).toEqual([{ id: "comm:1", label: "ingestion", chart: 1 }])
    expect(graph.processes).toEqual([
      { id: "proc:ingest", label: "proc:ingest", steps: ["sym:a"] },
    ])
  })

  it("drops edges that reference a pulled-out pseudo-node, keeps code-structure edges", () => {
    const graph = deriveCodeGraph("r1", { nodes, edges })
    expect(graph.edges).toEqual([
      { source: "file:main.py", target: "sym:a", type: "CONTAINS" },
    ])
  })
})

describe("the file-level graph", () => {
  it("carries a folded edge's weight to the canvas", () => {
    const graph = deriveCodeGraph("r1", {
      nodes: [
        { id: "a.py", label: "a.py", kind: "file", file_path: "a.py" },
        { id: "b.py", label: "b.py", kind: "file", file_path: "b.py" },
      ],
      edges: [
        {
          source: "a.py",
          target: "b.py",
          type: "depends_on",
          properties: { weight: 12, edge_types: { calls: 12 } },
        },
      ],
    })
    expect(graph.edges).toEqual([
      { source: "a.py", target: "b.py", type: "depends_on", weight: 12 },
    ])
  })

  it("maps a symbol step to its file, and leaves any other key alone", () => {
    expect(fileOfGraphKey("run::pkg/a.py")).toBe("pkg/a.py")
    expect(fileOfGraphKey("start::pkg/a.py::Svc")).toBe("pkg/a.py")
    expect(fileOfGraphKey("pkg/a.py")).toBe("pkg/a.py")
  })
})
