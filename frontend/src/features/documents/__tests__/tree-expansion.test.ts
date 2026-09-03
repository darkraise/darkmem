import { describe, expect, it } from "vitest"
import {
  expansionStorageKey,
  pathsToDocument,
  rootFolderPaths,
} from "../tree-expansion"
import type { UriTreeNode } from "../uri-tree"

const node = (
  path: string,
  name: string,
  children: UriTreeNode[] = [],
  document: unknown = null,
): UriTreeNode => ({ path, name, children, document } as UriTreeNode)

const ROOTS: UriTreeNode[] = [
  node("docs", "docs", [
    node("docs/planning", "planning", [
      node("docs/planning/progress.md", "progress.md", [], { id: "doc-1" }),
    ]),
    node("docs/readme.md", "readme.md", [], { id: "doc-2" }),
    node("docs/notes.md", "notes.md", [
      node("docs/notes.md/appendix.md", "appendix.md", [], { id: "doc-5" }),
    ], { id: "doc-4" }),
  ]),
  node("src", "src", [node("src/main.ts", "main.ts", [], { id: "doc-3" })]),
]

describe("tree expansion", () => {
  it("keys storage per project so two projects do not share expansion", () => {
    expect(expansionStorageKey("darkmem")).not.toEqual(expansionStorageKey("other"))
    expect(expansionStorageKey("darkmem")).toContain("darkmem")
  })

  it("expands only the folders on the path to the selected document", () => {
    // The whole point: 475 documents must not all expand. Only the ancestors
    // of the open document open.
    expect(pathsToDocument(ROOTS, "doc-1").sort()).toEqual(
      ["docs", "docs/planning"].sort(),
    )
  })

  it("returns no paths when nothing is selected", () => {
    expect(pathsToDocument(ROOTS, null)).toEqual([])
  })

  it("returns no paths when the id matches no document", () => {
    expect(pathsToDocument(ROOTS, "missing")).toEqual([])
  })

  it("opens only the top level as the no-selection default", () => {
    expect(rootFolderPaths(ROOTS).sort()).toEqual(["docs", "src"].sort())
  })

  it("does not treat a leaf as a folder", () => {
    expect(rootFolderPaths([node("a.md", "a.md", [], { id: "x" })])).toEqual([])
  })

  it("treats a dual node (document and folder) as a folder", () => {
    // A dual node at root level: both a document and a folder with children
    const dualNode = node("config.md", "config.md", [
      node("config.md/details.md", "details.md", [], { id: "doc-6" }),
    ], { id: "doc-4" })
    expect(rootFolderPaths([dualNode]).sort()).toContain("config.md")
  })

  it("expands to a dual node's own path when selecting its document", () => {
    // pathsToDocument for doc-4 (the dual node itself) should return ancestors
    // but NOT the dual node's own path
    expect(pathsToDocument(ROOTS, "doc-4").sort()).toEqual(["docs"].sort())
  })

  it("expands through a dual node to reach its child document", () => {
    // pathsToDocument for doc-5 (child of dual node) should include the dual node's path
    expect(pathsToDocument(ROOTS, "doc-5").sort()).toEqual(
      ["docs", "docs/notes.md"].sort(),
    )
  })
})
