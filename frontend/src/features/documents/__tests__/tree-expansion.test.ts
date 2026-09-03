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
})
