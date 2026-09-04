import { describe, it, expect } from "vitest"
import { blockSpacing } from "../components/document-reader"
import type { BlockRow } from "@/hooks/api"

function block(type: string, level?: number): BlockRow {
  return {
    block_id: `${type}-${level ?? 0}`,
    type,
    text: "",
    order_index: 0,
    char_span: null,
    parent_id: null,
    properties: level ? { level } : null,
    source: null,
  }
}

describe("blockSpacing", () => {
  it("gives the first block no leading space", () => {
    expect(blockSpacing(block("heading", 1), undefined, 0)).toBe("")
  })

  it("puts the space above a heading, scaled by level", () => {
    // A uniform gap is what made the document read as one flat column: the
    // same distance between two list items as between a paragraph and the
    // next section's heading.
    expect(blockSpacing(block("heading", 1), block("paragraph"), 3)).toBe("mt-6")
    expect(blockSpacing(block("heading", 4), block("paragraph"), 3)).toBe("mt-5")
  })

  it("keeps the first row close to the heading it belongs to", () => {
    expect(blockSpacing(block("paragraph"), block("heading", 2), 2)).toBe("mt-1.5")
  })

  it("tightens a run of list items into one list", () => {
    expect(blockSpacing(block("list"), block("list"), 4)).toBe("mt-1")
    // A list opening after prose is a new group and keeps the paragraph gap.
    expect(blockSpacing(block("list"), block("paragraph"), 4)).toBe("mt-3")
  })

  it("gives a divider room on both sides", () => {
    expect(blockSpacing(block("divider"), block("paragraph"), 5)).toBe("mt-5")
    expect(blockSpacing(block("paragraph"), block("divider"), 6)).toBe("mt-5")
  })
})
