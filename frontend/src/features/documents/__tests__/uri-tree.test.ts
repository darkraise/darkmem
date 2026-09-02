import { describe, it, expect } from "vitest"

import { buildUriTree, NO_PATH } from "../uri-tree"
import type { DocumentListItem } from "@/hooks/api"

function doc(id: string, uri: string | null, title: string | null = null): DocumentListItem {
  return { id, title, uri, source_type: "md", project: "p", block_count: 1 }
}

describe("buildUriTree", () => {
  it("groups by uri segments", () => {
    const tree = buildUriTree([
      doc("1", "docs/plans/a.md"),
      doc("2", "docs/plans/b.md"),
      doc("3", "docs/spec.md"),
    ])
    expect(tree.map((n) => n.name)).toEqual(["docs"])
    const docs = tree[0]!
    expect(docs.children.map((n) => n.name)).toEqual(["plans", "spec.md"])
    const plans = docs.children[0]!
    expect(plans.children.map((n) => n.name)).toEqual(["a.md", "b.md"])
    expect(plans.children[0]!.document?.id).toBe("1")
  })

  it("lets one node be both a document and a folder", () => {
    // uris are opaque keys, not a filesystem: this is legal and must not
    // drop either row.
    const tree = buildUriTree([doc("1", "a/b.md"), doc("2", "a/b.md/c.md")])
    const b = tree[0]!.children[0]!
    expect(b.name).toBe("b.md")
    expect(b.document?.id).toBe("1")
    expect(b.children[0]!.document?.id).toBe("2")
  })

  it("collects null-uri documents under a trailing node rather than dropping them", () => {
    const tree = buildUriTree([doc("1", "docs/a.md"), doc("2", null, "a note")])
    expect(tree[tree.length - 1]!.name).toBe(NO_PATH)
    expect(tree[tree.length - 1]!.children[0]!.document?.id).toBe("2")
  })

  it("sorts folders before files, then by name", () => {
    const tree = buildUriTree([
      doc("1", "z.md"),
      doc("2", "a.md"),
      doc("3", "m/one.md"),
    ])
    expect(tree.map((n) => n.name)).toEqual(["m", "a.md", "z.md"])
  })
})
