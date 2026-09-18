import { fireEvent, render, screen, within } from "@testing-library/react"
import { describe, expect, it, vi, beforeEach } from "vitest"

import type { PageListItem } from "@/hooks/api"
import { buildPageTree, pageNodeIndex } from "../lib/build-page-tree"
import { PageTree, notesExpansionStorageKey } from "../page-tree"

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

const ROWS = [row("a", null, 0, "Alpha"), row("b", "a", 0, "Beta"), row("c", null, 1, null)]

/** Seeds the persisted expansion, because `TreeViewBranchContent` renders
 *  nothing while its branch is closed -- a test that expects a child row has to
 *  open its parent first. */
function seedExpanded(...ids: string[]) {
  window.localStorage.setItem(
    notesExpansionStorageKey("personal"),
    JSON.stringify(ids),
  )
}

function renderTree(props: Partial<Parameters<typeof PageTree>[0]> = {}) {
  const roots = buildPageTree(ROWS)
  const handlers = {
    onSelect: vi.fn(),
    onNewChild: vi.fn(),
    onRename: vi.fn(),
    onDelete: vi.fn(),
    onMove: vi.fn(),
  }
  render(
    <PageTree
      roots={roots}
      index={pageNodeIndex(roots)}
      project="personal"
      selectedId={null}
      {...handlers}
      {...props}
    />,
  )
  return handlers
}

beforeEach(() => {
  window.localStorage.clear()
})

describe("PageTree", () => {
  it("renders the roots, untitled ones by their fallback", () => {
    renderTree()
    expect(screen.getByText("Alpha")).toBeInTheDocument()
    expect(screen.getByText("Untitled")).toBeInTheDocument()
    // The branch is closed, so its child is not in the document at all.
    expect(screen.queryByText("Beta")).toBeNull()
  })

  it("renders a child once its parent is expanded", () => {
    seedExpanded("a")
    renderTree()
    expect(screen.getByText("Beta")).toBeInTheDocument()
  })

  it("reports a selection by page id", () => {
    const { onSelect } = renderTree()
    fireEvent.click(screen.getByText("Alpha"))
    expect(onSelect).toHaveBeenCalledWith("a")
  })

  it("offers new child, rename and delete on a row", () => {
    const { onNewChild, onRename, onDelete } = renderTree()
    fireEvent.click(screen.getByRole("button", { name: "New page under Alpha" }))
    expect(onNewChild).toHaveBeenCalledWith("a")

    fireEvent.click(screen.getByRole("button", { name: "Actions for Alpha" }))
    const menu = screen.getByRole("menu")
    fireEvent.click(within(menu).getByText("Rename"))
    expect(onRename).toHaveBeenCalledWith(expect.objectContaining({ id: "a" }))

    fireEvent.click(screen.getByRole("button", { name: "Actions for Alpha" }))
    fireEvent.click(within(screen.getByRole("menu")).getByText("Delete"))
    expect(onDelete).toHaveBeenCalledWith(expect.objectContaining({ id: "a" }))
  })

  it("writes the expanded set when a branch is toggled", () => {
    seedExpanded("a")
    renderTree()
    // `TreeViewBranchControl`'s own click handler calls `toggleExpanded`, so
    // clicking the label closes the branch.
    fireEvent.click(screen.getByText("Alpha"))
    expect(screen.queryByText("Beta")).toBeNull()
    expect(
      JSON.parse(window.localStorage.getItem(notesExpansionStorageKey("personal"))!),
    ).toEqual([])
  })

  // Storage can be absent or throw (private browsing, blocked site data), and
  // the tree must render either way.
  it("renders collapsed when storage throws", () => {
    const getItem = vi
      .spyOn(window.localStorage, "getItem")
      .mockImplementation(() => {
        throw new Error("blocked")
      })
    expect(() => renderTree()).not.toThrow()
    expect(screen.getByText("Alpha")).toBeInTheDocument()
    getItem.mockRestore()
  })

  it("shows an empty state with a create affordance when there are no pages", () => {
    render(
      <PageTree
        roots={[]}
        index={new Map()}
        project="personal"
        selectedId={null}
        onSelect={vi.fn()}
        onNewChild={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
        onMove={vi.fn()}
      />,
    )
    expect(screen.getByText(/No pages yet/)).toBeInTheDocument()
  })
})
