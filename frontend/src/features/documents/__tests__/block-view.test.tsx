import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"

import { BlockView } from "../components/block-view"
import type { BlockRow } from "@/hooks/api"

function block(over: Partial<BlockRow>): BlockRow {
  return {
    block_id: "b1", type: "paragraph", text: "body", order_index: 0,
    char_span: null, parent_id: null, properties: null, source: "body", ...over,
  }
}

describe("BlockView — heading rendering", () => {
  it("renders the real heading level, not a fixed h3", () => {
    // `properties.level` has been on the read surface since increment 8 and
    // was unused, so an h1 and an h4 rendered identically.
    for (const level of [1, 2, 3, 4, 5, 6]) {
      const { unmount } = render(
        <BlockView block={block({ type: "heading", text: `H${level}`, properties: { level } })} />,
      )
      expect(screen.getByRole("heading", { level, name: `H${level}` })).toBeTruthy()
      unmount()
    }
  })

  it("falls back to h2 when the level is absent or out of range", () => {
    // Parsed documents always carry a level; a block minted by the editor
    // may not. Clamping beats rendering an invalid tag.
    render(<BlockView block={block({ type: "heading", text: "No level" })} />)
    expect(screen.getByRole("heading", { level: 2, name: "No level" })).toBeTruthy()
  })

  it("renders heading text as markdown so inline code is not literal backticks", () => {
    render(
      <BlockView
        block={block({ type: "heading", text: "The `parent_id` column", properties: { level: 2 } })}
      />,
    )
    const heading = screen.getByRole("heading", { level: 2 })
    expect(heading.querySelector("code")?.textContent).toBe("parent_id")
    expect(heading.textContent).not.toContain("`")
  })
})

describe("BlockView — tables", () => {
  const header = block({
    block_id: "t1", type: "table", text: "Name | Role",
    properties: { header: ["Name", "Role"], alignments: [null, null] },
  })
  const rowA = block({
    block_id: "r1", type: "table_row", text: "Ana | Lead",
    parent_id: "t1", properties: { cells: ["Ana", "Lead"] },
  })
  const rowB = block({
    block_id: "r2", type: "table_row", text: "Bo | Reviewer",
    parent_id: "t1", properties: { cells: ["Bo", "Reviewer"] },
  })

  it("renders a table's header and all its rows as ONE table", () => {
    // Each data row used to render its own <table>, so columns did not line
    // up across rows of what is visually one table.
    render(<BlockView block={header} rows={[rowA, rowB]} />)
    const tables = screen.getAllByRole("table")
    expect(tables).toHaveLength(1)
    expect(screen.getByRole("columnheader", { name: "Name" })).toBeTruthy()
    expect(screen.getByRole("cell", { name: "Ana" })).toBeTruthy()
    expect(screen.getByRole("cell", { name: "Reviewer" })).toBeTruthy()
  })

  it("still renders a header-only table when it has no data rows", () => {
    render(<BlockView block={header} />)
    expect(screen.getAllByRole("table")).toHaveLength(1)
    expect(screen.getByRole("columnheader", { name: "Role" })).toBeTruthy()
  })

  it("renders an orphan table_row on its own, for a block_ids drill-down", () => {
    // `block_ids` scopes strictly, so a row can legitimately arrive without
    // its table. Dropping it would silently lose content.
    render(<BlockView block={rowA} />)
    expect(screen.getByRole("cell", { name: "Ana" })).toBeTruthy()
  })
})

describe("BlockView — list markers", () => {
  it("renders a bullet for an unordered item", () => {
    render(
      <BlockView
        block={block({ type: "list", text: "alpha", properties: { ordered: false, marker: "-" } })}
      />,
    )
    expect(screen.getByText("•")).toBeTruthy()
  })

  it("renders the item's own number for an ordered item", () => {
    // A list may not start at 1, so the number is the item's, not its index.
    render(
      <BlockView
        block={block({
          type: "list", text: "three",
          properties: { ordered: true, marker: "3.", number: 3 },
        })}
      />,
    )
    expect(screen.getByText("3.")).toBeTruthy()
    expect(screen.queryByText("•")).toBeNull()
  })

  it("keeps a paren delimiter rather than normalising it to a dot", () => {
    render(
      <BlockView
        block={block({
          type: "list", text: "one",
          properties: { ordered: true, marker: "1)", number: 1 },
        })}
      />,
    )
    expect(screen.getByText("1)")).toBeTruthy()
  })

  it("falls back to a bullet when no marker was recorded", () => {
    // Every document filed before increment 5 carries `properties: null` on
    // its list blocks, and stays readable until it is reparsed.
    render(<BlockView block={block({ type: "list", text: "legacy" })} />)
    expect(screen.getByText("•")).toBeTruthy()
  })
})
