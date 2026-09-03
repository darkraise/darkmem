import { describe, it, expect } from "vitest"

import { listDepths } from "../components/document-reader"
import type { BlockRow } from "@/hooks/api"

function block(over: Partial<BlockRow>): BlockRow {
  return {
    block_id: "b", type: "paragraph", text: "", order_index: 0,
    char_span: null, parent_id: null, properties: null, source: null, ...over,
  }
}

describe("listDepths — nesting rebuilt from parent_id", () => {
  it("indents a nested list item under its enclosing item", () => {
    const rows = [
      block({ block_id: "h", type: "heading", text: "Title" }),
      block({ block_id: "o", type: "list", text: "outer", parent_id: "h" }),
      block({ block_id: "i", type: "list", text: "inner", parent_id: "o" }),
      block({ block_id: "d", type: "list", text: "deeper", parent_id: "i" }),
    ]
    expect(listDepths(rows)).toEqual({ h: 0, o: 0, i: 1, d: 2 })
  })

  it("does not indent a paragraph merely because a heading is its parent", () => {
    // Every block under a heading has that heading as its parent, so nesting
    // by parent alone would indent an entire document body under its title.
    const rows = [
      block({ block_id: "h", type: "heading", text: "Title" }),
      block({ block_id: "p", type: "paragraph", text: "body", parent_id: "h" }),
    ]
    expect(listDepths(rows)).toEqual({ h: 0, p: 0 })
  })

  it("indents a code block that sits inside a list item with its item", () => {
    const rows = [
      block({ block_id: "o", type: "list", text: "step one" }),
      block({ block_id: "c", type: "code", text: "npm test", parent_id: "o" }),
    ]
    expect(listDepths(rows)).toEqual({ o: 0, c: 1 })
  })

  it("counts only list ancestors, so a list inside a quote starts at zero", () => {
    const rows = [
      block({ block_id: "q", type: "quote", text: "note" }),
      block({ block_id: "l", type: "list", text: "item", parent_id: "q" }),
      block({ block_id: "n", type: "list", text: "nested", parent_id: "l" }),
    ]
    expect(listDepths(rows)).toEqual({ q: 0, l: 0, n: 1 })
  })

  it("survives a dangling parent without looping forever", () => {
    // `block_ids` scopes a read strictly, so a drill-down can legitimately
    // return a child whose parent was not requested.
    const rows = [block({ block_id: "x", type: "list", text: "orphan", parent_id: "gone" })]
    expect(listDepths(rows)).toEqual({ x: 0 })
  })

  it("terminates on a cycle rather than hanging the reader", () => {
    const rows = [
      block({ block_id: "a", type: "list", parent_id: "b" }),
      block({ block_id: "b", type: "list", parent_id: "a" }),
    ]
    expect(() => listDepths(rows)).not.toThrow()
  })
})
