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

  it("refuses an orphan bucket's child too, not only the bucket", () => {
    // `buildUriTree` paths an orphan child `(no path)/<id>` -- a raw
    // document id, never a human-chosen path. A guard checking only
    // `=== NO_PATH` lets this slip through and mints a uri from a uuid.
    expect(moveTarget(doc(`${NO_PATH}/uuid-1`), folder("b"))).toBeNull()
    expect(moveTarget(doc("a/one.md"), folder(`${NO_PATH}/uuid-1`))).toBeNull()
  })

  it("moves a document-and-folder node as a subtree, not a lone document", () => {
    // A node can be both a document and a folder (`a/b.md` above
    // `a/b.md/c.md`). Dispatching on `document` alone would PATCH the
    // document and strand `c.md` under the old prefix.
    const hybrid: UriTreeNode = {
      name: "b.md",
      path: "a/b.md",
      document: {
        id: "d1",
        title: null,
        uri: "a/b.md",
        source_type: "md",
        project: "p",
        block_count: 1,
      },
      children: [folder("a/b.md/c.md")],
    }
    expect(moveTarget(hybrid, folder("z"))).toEqual({
      kind: "subtree",
      uriPrefix: "a/b.md",
      newUriPrefix: "z/b.md",
    })
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
