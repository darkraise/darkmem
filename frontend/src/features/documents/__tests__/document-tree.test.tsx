import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { DocumentTree } from "../components/document-tree"
import type { DocumentListItem } from "@/hooks/api"

function doc(id: string, uri: string): DocumentListItem {
  return { id, title: null, uri, source_type: "md", project: "p", block_count: 1 }
}

const ITEMS = [
  doc("1", "docs/plans/a.md"),
  doc("2", "docs/spec.md"),
  doc("3", "readme.md"),
]

describe("DocumentTree", () => {
  it("renders folders and leaves from the uri segments", () => {
    render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    expect(screen.getByText("docs")).toBeInTheDocument()
    expect(screen.getByText("readme.md")).toBeInTheDocument()
  })

  it("calls back with the document when a leaf is selected", async () => {
    const onSelect = vi.fn()
    render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={onSelect} truncated={false} />,
    )
    await userEvent.click(screen.getByText("readme.md"))
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "3" }))
  })

  it("shows the truncation banner rather than a quietly short tree", () => {
    // Invariant 14: the pagination guard is a real limit and the surface has
    // to say so -- an incomplete tree that looks complete is the defect.
    render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated />,
    )
    expect(screen.getByText(/cut at the pagination guard/i)).toBeInTheDocument()
  })

  it("renders the empty state when the project holds nothing", () => {
    render(
      <DocumentTree items={[]} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    expect(screen.getByText(/No documents filed in this project/i)).toBeInTheDocument()
  })
})

describe("DocumentTree expansion", () => {
  it("shows only what the controlled expanded set opens", () => {
    // The defect this fixes: the component expanded every folder, so 475
    // documents rendered as one wall.
    render(
      <DocumentTree
        items={ITEMS}
        selectedId={null}
        onSelect={vi.fn()}
        truncated={false}
        expanded={["docs"]}
        onExpandedChange={vi.fn()}
      />,
    )
    expect(screen.getByText("spec.md")).toBeInTheDocument()
    expect(screen.queryByText("a.md")).not.toBeInTheDocument()
  })

  it("reports expansion changes as a bare array", async () => {
    const onExpandedChange = vi.fn()
    render(
      <DocumentTree
        items={ITEMS}
        selectedId={null}
        onSelect={vi.fn()}
        truncated={false}
        expanded={[]}
        onExpandedChange={onExpandedChange}
      />,
    )
    await userEvent.click(screen.getByText("docs"))
    expect(onExpandedChange).toHaveBeenCalledWith(expect.any(Array))
  })

  it("keeps expand-everything behaviour when expanded is omitted", () => {
    // Increment 8's editor call site passes neither prop and must be
    // unaffected by the controlled-expansion addition.
    render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    expect(screen.getByText("a.md")).toBeInTheDocument()
    expect(screen.getByText("spec.md")).toBeInTheDocument()
  })
})
