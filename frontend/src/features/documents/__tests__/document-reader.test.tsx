import { describe, it, expect } from "vitest"
import { blockSpacing, DocumentReader } from "../components/document-reader"
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

describe("DocumentReader — render cost", () => {
  it("is memoised against its parent's scroll state", () => {
    // The reader reports the heading the body is under; the artifacts
    // workspace stores that report and renders the outline rail from it. So
    // every heading crossed during a scroll is a `setState` in this
    // component's own parent. Measured on a 120-heading, 1200-block document
    // before this memo: a ~1.4s frozen frame per crossing, 41 dropped frames
    // over a 200-step scroll. After: no frame over 17ms. Its props are stable
    // across that state change, so the memo is sound rather than a papering
    // over -- if a future prop starts changing per scroll, this guard stops
    // being enough and the state has to move instead.
    expect((DocumentReader as unknown as { $$typeof: symbol }).$$typeof).toBe(
      Symbol.for("react.memo"),
    )
  })
})
