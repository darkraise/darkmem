import { describe, expect, it } from "vitest"
import { NO_PATH, type UriTreeNode } from "../uri-tree"
import { moveTarget } from "../move-target"

const folder = (path: string): UriTreeNode => ({
  name: path.split("/").pop()!,
  path,
  document: null,
  children: [],
})

const doc = (path: string, id = "d1"): UriTreeNode => ({
  name: path.split("/").pop()!,
  path,
  document: {
    id,
    title: null,
    uri: path,
    source_type: "md",
    project: "p",
    block_count: 1,
  },
  children: [],
})

describe("moveTarget", () => {
  it("moves a document into a folder", () => {
    expect(moveTarget(doc("a/one.md"), folder("b"))).toEqual({
      kind: "document",
      documentId: "d1",
      uri: "b/one.md",
    })
  })

  it("moves a document to the root", () => {
    expect(moveTarget(doc("a/one.md"), null)).toEqual({
      kind: "document",
      documentId: "d1",
      uri: "one.md",
    })
  })

  it("moves a folder as a subtree rename", () => {
    expect(moveTarget(folder("a/inner"), folder("b"))).toEqual({
      kind: "subtree",
      uriPrefix: "a/inner",
      newUriPrefix: "b/inner",
    })
  })

  it("refuses to drop a folder into its own descendant", () => {
    expect(moveTarget(folder("a"), folder("a/deep"))).toBeNull()
  })

  it("refuses a no-op drop into the folder it already sits in", () => {
    expect(moveTarget(doc("a/one.md"), folder("a"))).toBeNull()
  })

  it("refuses to drop a node onto itself", () => {
    expect(moveTarget(folder("a"), folder("a"))).toBeNull()
  })

  it("refuses anything involving the orphan bucket", () => {
    expect(moveTarget(doc("a/one.md"), folder(NO_PATH))).toBeNull()
    expect(moveTarget(folder(NO_PATH), folder("a"))).toBeNull()
  })

  it("does not treat a name prefix as an ancestor", () => {
    // `a` must not be mistaken for an ancestor of `ab` -- a naive
    // `targetPath.startsWith(dragged.path)` (no separator) would refuse
    // this legitimate move.
    expect(moveTarget(folder("a"), folder("ab"))).toEqual({
      kind: "subtree",
      uriPrefix: "a",
      newUriPrefix: "ab/a",
    })
  })
})
