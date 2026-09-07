import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { DocumentTree } from "../components/document-tree"
import type { DocumentListItem } from "@/hooks/api"

function doc(id: string, uri: string): DocumentListItem {
  return { id, title: null, uri, source_type: "md", project: "p", block_count: 1 }
}

const ITEMS = [doc("1", "docs/a.md"), doc("2", "notes/b.md")]

describe("DocumentTree drag layer", () => {
  it("keeps the tree's own row semantics intact under drag", () => {
    render(
      <DocumentTree
        items={ITEMS}
        selectedId={null}
        onSelect={vi.fn()}
        truncated={false}
        onMove={vi.fn()}
      />,
    )
    // dnd-kit's `attributes` carry role="button" and tabIndex=0. Spreading
    // them onto the row would replace the treeitem role and the roving
    // tabIndex the library manages.
    const rows = screen.getAllByRole("treeitem")
    expect(rows.length).toBeGreaterThan(0)
    expect(screen.queryAllByRole("button", { name: /a\.md/i })).toHaveLength(0)
  })

  it("still selects on a plain click", async () => {
    const onSelect = vi.fn()
    render(
      <DocumentTree
        items={ITEMS}
        selectedId={null}
        onSelect={onSelect}
        truncated={false}
        onMove={vi.fn()}
      />,
    )
    await userEvent.click(screen.getByText("a.md"))
    // A PointerSensor with an activation distance is what keeps a click a
    // click rather than a zero-distance drag.
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: "1" }))
  })

  it("gives every row a drag handle that is not the row itself", () => {
    const { container } = render(
      <DocumentTree
        items={ITEMS}
        selectedId={null}
        onSelect={vi.fn()}
        truncated={false}
        onMove={vi.fn()}
      />,
    )
    const handles = container.querySelectorAll("[data-drag-handle]")
    // Two folders and two leaves.
    expect(handles).toHaveLength(4)
    for (const handle of handles) {
      expect(handle.getAttribute("role")).toBeNull()
      expect(handle.getAttribute("tabindex")).toBeNull()
    }
  })

  it("mounts no drag layer at all when the caller passes no onMove", () => {
    const { container } = render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    expect(container.querySelectorAll("[data-drag-handle]")).toHaveLength(0)
    expect(screen.getAllByRole("treeitem").length).toBeGreaterThan(0)
  })
})
