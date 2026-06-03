import { describe, it, expect } from "vitest"

import {
  deriveProcesses,
  processToMermaid,
  type CodeProcess,
} from "../code-processes"

// Fixture mirrors the GET /code/graph payload: nodes carry {id,label,kind,file_path}
// and process edges (entry_point_of, step_in_process) carry an ordered step index
// in properties.step, exactly as ProcessTracer writes it on the backend.
function fixture() {
  const nodes = [
    { id: "main::app.py", label: "main", kind: "function", file_path: "app.py" },
    { id: "load::app.py", label: "load", kind: "function", file_path: "app.py" },
    { id: "save::db.py", label: "save", kind: "method", file_path: "db.py" },
    { id: "render::ui.py", label: "render", kind: "function", file_path: "ui.py" },
    { id: "boot::cli.py", label: "boot", kind: "function", file_path: "cli.py" },
    { id: "exit::cli.py", label: "exit", kind: "function", file_path: "cli.py" },
    { id: "process:scored:main::app.py", label: "scored:main", kind: "process" },
    { id: "process:scored:boot::cli.py", label: "scored:boot", kind: "process" },
  ]
  const edges = [
    // Process A — 3 steps, entry main; step indices deliberately out of order.
    {
      source: "main::app.py",
      target: "process:scored:main::app.py",
      type: "entry_point_of",
    },
    {
      source: "render::ui.py",
      target: "process:scored:main::app.py",
      type: "step_in_process",
      properties: { step: 3 },
    },
    {
      source: "main::app.py",
      target: "process:scored:main::app.py",
      type: "step_in_process",
      properties: { step: 1 },
    },
    {
      source: "save::db.py",
      target: "process:scored:main::app.py",
      type: "step_in_process",
      properties: { step: 2 },
    },
    // Process B — 2 steps, entry boot.
    {
      source: "boot::cli.py",
      target: "process:scored:boot::cli.py",
      type: "entry_point_of",
    },
    {
      source: "boot::cli.py",
      target: "process:scored:boot::cli.py",
      type: "step_in_process",
      properties: { step: 1 },
    },
    {
      source: "exit::cli.py",
      target: "process:scored:boot::cli.py",
      type: "step_in_process",
      properties: { step: 2 },
    },
    // Noise: a non-process edge that must be ignored entirely.
    { source: "main::app.py", target: "load::app.py", type: "calls" },
  ]
  return { nodes, edges }
}

describe("deriveProcesses", () => {
  it("returns one CodeProcess per process node, sorted by stepCount desc", () => {
    const { nodes, edges } = fixture()
    const procs = deriveProcesses(nodes, edges)
    expect(procs).toHaveLength(2)
    expect(procs.map((p) => p.stepCount)).toEqual([3, 2])
    expect(procs[0]!.id).toBe("process:scored:main::app.py")
    expect(procs[1]!.id).toBe("process:scored:boot::cli.py")
  })

  it("orders steps ascending by the edge step index regardless of edge order", () => {
    const { nodes, edges } = fixture()
    const a = deriveProcesses(nodes, edges).find(
      (p) => p.id === "process:scored:main::app.py",
    )!
    expect(a.steps.map((s) => s.nodeId)).toEqual([
      "main::app.py",
      "save::db.py",
      "render::ui.py",
    ])
    expect(a.steps.map((s) => s.index)).toEqual([1, 2, 3])
  })

  it("resolves label, kind, and file for each step from the node map", () => {
    const { nodes, edges } = fixture()
    const a = deriveProcesses(nodes, edges).find(
      (p) => p.id === "process:scored:main::app.py",
    )!
    const save = a.steps.find((s) => s.nodeId === "save::db.py")!
    expect(save.label).toBe("save")
    expect(save.kind).toBe("method")
    expect(save.file).toBe("db.py")
  })

  it("identifies the entry node from the entry_point_of edge", () => {
    const { nodes, edges } = fixture()
    const a = deriveProcesses(nodes, edges).find(
      (p) => p.id === "process:scored:main::app.py",
    )!
    expect(a.entryNodeId).toBe("main::app.py")
    expect(a.entryKind).toBe("function")
    expect(a.entryFile).toBe("app.py")
  })

  it("builds a unique nodeIds list with the entry first, then ordered steps", () => {
    const { nodes, edges } = fixture()
    const a = deriveProcesses(nodes, edges).find(
      (p) => p.id === "process:scored:main::app.py",
    )!
    // entry main is also step 1, so it must not appear twice.
    expect(a.nodeIds).toEqual([
      "main::app.py",
      "save::db.py",
      "render::ui.py",
    ])
  })

  it("falls back to insertion order when step indices are absent", () => {
    const nodes = [
      { id: "a", label: "a", kind: "function" },
      { id: "b", label: "b", kind: "function" },
      { id: "c", label: "c", kind: "function" },
      { id: "p", label: "flow", kind: "process" },
    ]
    const edges = [
      { source: "a", target: "p", type: "entry_point_of" },
      { source: "b", target: "p", type: "step_in_process" },
      { source: "a", target: "p", type: "step_in_process" },
      { source: "c", target: "p", type: "step_in_process" },
    ]
    const p = deriveProcesses(nodes, edges)[0]!
    expect(p.steps.map((s) => s.nodeId)).toEqual(["b", "a", "c"])
  })

  it("reads properties.index or properties.order as alternate step fields", () => {
    const nodes = [
      { id: "a", label: "a", kind: "function" },
      { id: "b", label: "b", kind: "function" },
      { id: "p", label: "flow", kind: "process" },
    ]
    const edges = [
      {
        source: "b",
        target: "p",
        type: "step_in_process",
        properties: { index: 2 },
      },
      {
        source: "a",
        target: "p",
        type: "step_in_process",
        properties: { order: 1 },
      },
    ]
    const p = deriveProcesses(nodes, edges)[0]!
    expect(p.steps.map((s) => s.nodeId)).toEqual(["a", "b"])
  })

  it("returns an empty array when there are no process nodes", () => {
    const nodes = [{ id: "a", label: "a", kind: "function" }]
    const edges = [{ source: "a", target: "a", type: "calls" }]
    expect(deriveProcesses(nodes, edges)).toEqual([])
  })

  it("uses the entry node label for the process label when available", () => {
    const { nodes, edges } = fixture()
    const a = deriveProcesses(nodes, edges).find(
      (p) => p.id === "process:scored:main::app.py",
    )!
    expect(a.label).toBe("main")
  })
})

describe("processToMermaid", () => {
  const make = (): CodeProcess => {
    const { nodes, edges } = fixture()
    return deriveProcesses(nodes, edges).find(
      (p) => p.id === "process:scored:main::app.py",
    )!
  }

  it("emits a flowchart TD header", () => {
    expect(processToMermaid(make())).toMatch(/^flowchart TD/)
  })

  it("emits sequential node ids and arrows in step order", () => {
    const out = processToMermaid(make())
    expect(out).toContain("n0 --> n1")
    expect(out).toContain("n1 --> n2")
    // Three steps -> exactly two arrows.
    expect(out.match(/-->/g)).toHaveLength(2)
  })

  it("labels each node with its text and kind", () => {
    const out = processToMermaid(make())
    expect(out).toContain("main")
    expect(out).toContain("function")
    expect(out).toContain("save")
    expect(out).toContain("method")
  })

  it("marks the entry node distinctly from plain steps", () => {
    const out = processToMermaid(make())
    // Entry uses a stadium ([...]) shape; plain steps use rectangles.
    expect(out).toMatch(/n0\(\[/)
  })

  it("escapes quotes and brackets in labels", () => {
    const nodes = [
      { id: "a", label: 'fn"x"', kind: "function" },
      { id: "b", label: "arr[0]", kind: "function" },
      { id: "p", label: "flow", kind: "process" },
    ]
    const edges = [
      { source: "a", target: "p", type: "entry_point_of" },
      {
        source: "a",
        target: "p",
        type: "step_in_process",
        properties: { step: 1 },
      },
      {
        source: "b",
        target: "p",
        type: "step_in_process",
        properties: { step: 2 },
      },
    ]
    const p = deriveProcesses(nodes, edges)[0]!
    const out = processToMermaid(p)
    expect(out).not.toContain('"x"')
    expect(out).not.toContain("[0]")
    expect(out).toContain("&quot;")
    expect(out).toContain("#91;")
    expect(out).toContain("#93;")
  })
})
