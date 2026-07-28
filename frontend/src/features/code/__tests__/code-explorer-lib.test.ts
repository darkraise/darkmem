import { describe, expect, it, vi } from "vitest"
import {
  ancestorDirs,
  createFileTree,
  flattenTree,
} from "../lib/file-tree"
import { buildWikiLinkIndex } from "../lib/wiki-links"
import { buildFileSource } from "@/demo/code-source"
import type { DemoCodeGraph, DemoCodeNode } from "@/features/code/types"

const PATHS = [
  "services/pipeline.py",
  "services/hybrid_search.py",
  "api/mcp/mcp_tools.py",
  "main.py",
]

const GRAPH: DemoCodeGraph = {
  repo_id: "r",
  communities: [{ id: "c", label: "core", chart: 1 }],
  processes: [],
  nodes: [
    { id: "f", name: "pipeline.py", kind: "file", file: "services/pipeline.py", community: "c" },
    { id: "cls", name: "ProcessingPipeline", kind: "class", file: "services/pipeline.py", community: "c" },
    { id: "m", name: "process_batch", kind: "method", file: "services/pipeline.py", community: "c" },
    { id: "helper", name: "rrf_fuse", kind: "function", file: "services/hybrid_search.py", community: "c" },
  ],
  edges: [
    { source: "f", target: "cls", type: "CONTAINS" },
    { source: "cls", target: "m", type: "CONTAINS" },
    { source: "m", target: "helper", type: "CALLS" },
  ],
}

const symbolsOf = (path: string): DemoCodeNode[] =>
  GRAPH.nodes.filter(
    (n) => n.file === path && n.kind !== "file" && n.kind !== "module",
  )

describe("file tree", () => {
  it("lists directories before files at each level", () => {
    const tree = createFileTree(PATHS)
    expect(tree.childrenOf("")).toEqual([
      { kind: "dir", path: "api", name: "api" },
      { kind: "dir", path: "services", name: "services" },
      { kind: "file", path: "main.py", name: "main.py" },
    ])
  })

  it("materialises a directory's children only when it is expanded", () => {
    const tree = createFileTree(PATHS)
    const spy = vi.fn(tree.childrenOf)
    flattenTree({ childrenOf: spy }, new Set(), symbolsOf)
    // Root only — nothing walked into `api` or `services`.
    expect(spy).toHaveBeenCalledTimes(1)
    expect(spy).toHaveBeenCalledWith("")
  })

  it("hangs a file's symbols off it once the file is expanded", () => {
    const tree = createFileTree(PATHS)
    const rows = flattenTree(
      tree,
      new Set(["services", "services/pipeline.py"]),
      symbolsOf,
    )
    const symbols = rows.filter((r) => r.kind === "symbol")
    expect(symbols.map((r) => r.name)).toEqual([
      "ProcessingPipeline",
      "process_batch",
    ])
    // Symbols sit one level deeper than their file.
    const file = rows.find((r) => r.path === "services/pipeline.py")
    expect(symbols[0]!.depth).toBe(file!.depth + 1)
  })

  it("does not open a collapsed file's symbols", () => {
    const rows = flattenTree(
      createFileTree(PATHS),
      new Set(["services"]),
      symbolsOf,
    )
    expect(rows.some((r) => r.kind === "symbol")).toBe(false)
  })

  it("walks a path's ancestors root-first", () => {
    expect(ancestorDirs("api/mcp/mcp_tools.py")).toEqual(["api", "api/mcp"])
    expect(ancestorDirs("main.py")).toEqual([])
  })
})

describe("demo source synthesis", () => {
  const source = buildFileSource(GRAPH, "services/pipeline.py")

  it("nests a class's members but not the file's own membership edge", () => {
    const text = source.lines.join("\n")
    expect(text).toContain("class ProcessingPipeline:")
    expect(text).toContain("    def process_batch(self, batch):")
    // The file CONTAINS the class; that must not demote it out of the listing.
    expect(source.anchors.map((a) => a.name)).toEqual([
      "ProcessingPipeline",
      "process_batch",
    ])
  })

  it("anchors every symbol to the line it is declared on", () => {
    for (const anchor of source.anchors) {
      expect(source.lines[anchor.line - 1]).toContain(
        anchor.name === "process_batch" ? "process_batch" : anchor.name,
      )
    }
  })

  it("imports the out-of-file call targets it reaches", () => {
    expect(source.lines.join("\n")).toContain(
      "from services.hybrid_search import rrf_fuse",
    )
  })

  it("says so plainly when a tracked file contributed no symbols", () => {
    const empty = buildFileSource(GRAPH, "main.py")
    expect(empty.symbols).toHaveLength(0)
    expect(empty.lines.join("\n")).toContain("No symbols were extracted")
  })
})

describe("wiki code links", () => {
  const index = buildWikiLinkIndex(PATHS, GRAPH)

  it("links a qualified reference as one token, not a stranded suffix", () => {
    const segments = index.linkify(
      "ProcessingPipeline.process_batch is the write path.",
    )
    const codes = segments.filter((s) => s.type === "code")
    expect(codes).toHaveLength(1)
    expect(codes[0]).toMatchObject({
      target: { text: "ProcessingPipeline.process_batch", symbolId: "m" },
    })
  })

  it("prefers the full path over its basename", () => {
    const segments = index.linkify("see services/pipeline.py for the phases")
    const codes = segments.filter((s) => s.type === "code")
    expect(codes[0]).toMatchObject({
      target: { text: "services/pipeline.py", kind: "file" },
    })
  })

  it("leaves English words that happen to name a symbol alone", () => {
    // `main.py` is a path and links; `pipeline` on its own is prose.
    const segments = index.linkify("the pipeline runs in five phases")
    expect(segments.every((s) => s.type === "text")).toBe(true)
  })

  it("resolves a bullet's code value even when it is not in the prose", () => {
    expect(index.resolve("services/hybrid_search.py")).toMatchObject({
      kind: "file",
      file: "services/hybrid_search.py",
    })
  })
})
