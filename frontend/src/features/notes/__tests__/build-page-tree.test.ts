import { describe, expect, it } from "vitest"
import type { PageListItem } from "@/hooks/api"
import { buildPageTree, pageNodeIndex } from "../lib/build-page-tree"

function row(
  id: string,
  parent_id: string | null,
  order_index: number,
  title: string | null = id,
): PageListItem {
  return {
    id,
    project: "personal",
    parent_id,
    order_index,
    title,
    content_hash: "h",
    properties: null,
    created_at: "2026-09-18T00:00:00Z",
    updated_at: "2026-09-18T00:00:00Z",
  }
}

const ids = (nodes: { id: string }[]) => nodes.map((n) => n.id)

describe("buildPageTree", () => {
  it("nests children under their parent and sorts by order_index", () => {
    const roots = buildPageTree([
      row("b", null, 1),
      row("a", null, 0),
      row("a2", "a", 1),
      row("a1", "a", 0),
    ])
    expect(ids(roots)).toEqual(["a", "b"])
    expect(ids(roots[0]!.children)).toEqual(["a1", "a2"])
    expect(roots[1]!.children).toEqual([])
  })

  // The route orders by (parent_id, order_index) with NULL parents last, so
  // the list carries no parent-before-child guarantee at all.
  it("is indifferent to row order", () => {
    const rows = [row("c", "b", 0), row("b", "a", 0), row("a", null, 0)]
    const forward = buildPageTree(rows)
    const reversed = buildPageTree([...rows].reverse())
    expect(ids(forward[0]!.children[0]!.children)).toEqual(["c"])
    expect(JSON.stringify(reversed)).toBe(JSON.stringify(forward))
  })

  it("breaks an order_index tie on id, so the tree is stable", () => {
    const roots = buildPageTree([row("z", null, 0), row("m", null, 0)])
    expect(ids(roots)).toEqual(["m", "z"])
  })

  it("treats a row whose parent is not in the list as a root", () => {
    const roots = buildPageTree([row("orphan", "gone", 3), row("a", null, 0)])
    expect(ids(roots)).toEqual(["a", "orphan"])
  })

  it("carries the title through, null included", () => {
    const roots = buildPageTree([row("a", null, 0, null)])
    expect(roots[0]!.title).toBeNull()
  })

  it("returns no roots for an empty list", () => {
    expect(buildPageTree([])).toEqual([])
  })
})

describe("pageNodeIndex", () => {
  it("indexes every node at every depth", () => {
    const roots = buildPageTree([row("a", null, 0), row("b", "a", 0), row("c", "b", 0)])
    const index = pageNodeIndex(roots)
    expect([...index.keys()].sort()).toEqual(["a", "b", "c"])
    expect(index.get("c")!.parent_id).toBe("b")
  })
})
