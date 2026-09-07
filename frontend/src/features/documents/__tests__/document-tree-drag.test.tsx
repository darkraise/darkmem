import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import {
  DocumentTree,
  DRAG_PREFIX,
  DROP_PREFIX,
  ROOT_DROP_ID,
  buildPathMap,
  dropTargetFor,
  preferInnermost,
  resolveDrop,
} from "../components/document-tree"
import { buildUriTree } from "../uri-tree"
import type { DocumentListItem } from "@/hooks/api"

function doc(id: string, uri: string): DocumentListItem {
  return { id, title: null, uri, source_type: "md", project: "p", block_count: 1 }
}

const ITEMS = [doc("1", "docs/a.md"), doc("2", "notes/b.md")]

const DROP_ITEMS = [
  doc("1", "docs/a.md"),
  doc("2", "docs/b.md"),
  doc("3", "notes/c.md"),
]
const DROP_PATHS = buildPathMap(buildUriTree(DROP_ITEMS))
const drop = (active: string, over: string | null) =>
  resolveDrop(DROP_PATHS, `${DRAG_PREFIX}${active}`, over === null ? null : over)

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

  it("carries no draggable role or roledescription anywhere", () => {
    const { container } = render(
      <DocumentTree
        items={ITEMS}
        selectedId={null}
        onSelect={vi.fn()}
        truncated={false}
        onMove={vi.fn()}
      />,
    )
    // Two folders and two leaves; a `role="button"` from a spread
    // `attributes` would take one of them out of the tree.
    expect(screen.getAllByRole("treeitem")).toHaveLength(4)
    expect(
      container.querySelectorAll('[aria-roledescription="draggable"]'),
    ).toHaveLength(0)
  })

  it("mounts no drag layer at all when the caller passes no onMove", () => {
    const { container } = render(
      <DocumentTree items={ITEMS} selectedId={null} onSelect={vi.fn()} truncated={false} />,
    )
    expect(container.querySelectorAll("[data-drag-handle]")).toHaveLength(0)
    expect(screen.getAllByRole("treeitem").length).toBeGreaterThan(0)
  })
})

describe("resolveDrop", () => {
  it("resolves a leaf drop to that leaf's parent folder, not to the root", () => {
    // The likeliest accidental release position in the whole interaction.
    // Landing it on the parent makes a sibling drop the "already there"
    // refusal rather than a silent move to the top level.
    expect(drop("docs/a.md", `${DROP_PREFIX}docs/b.md`)).toBeNull()
    expect(drop("notes/c.md", `${DROP_PREFIX}docs/b.md`)).toEqual({
      kind: "document",
      documentId: "3",
      uri: "docs/c.md",
    })
  })

  it("resolves a folder drop into that folder", () => {
    expect(drop("docs/a.md", `${DROP_PREFIX}notes`)).toEqual({
      kind: "document",
      documentId: "1",
      uri: "notes/a.md",
    })
  })

  it("resolves the pane drop to the top level", () => {
    expect(drop("docs/a.md", ROOT_DROP_ID)).toEqual({
      kind: "document",
      documentId: "1",
      uri: "a.md",
    })
  })

  it("resolves a cancelled drag to nothing", () => {
    expect(drop("docs/a.md", null)).toBeNull()
  })

  it("refuses a folder into its own subtree", () => {
    expect(drop("docs", `${DROP_PREFIX}docs/a.md`)).toBeNull()
  })
})

describe("dropTargetFor", () => {
  it("gives a folder itself and a leaf its parent", () => {
    expect(dropTargetFor(DROP_PATHS, DROP_PATHS.get("docs")!)?.path).toBe("docs")
    expect(dropTargetFor(DROP_PATHS, DROP_PATHS.get("docs/a.md")!)?.path).toBe("docs")
    expect(dropTargetFor(DROP_PATHS, DROP_PATHS.get("notes/c.md")!)?.path).toBe("notes")
  })
})

describe("preferInnermost", () => {
  it("drops the enclosing pane whenever a row also matched", () => {
    // The pane droppable encloses every row, so an area-ranking detector
    // would let it win every hover.
    const hit = (id: string) => ({ id, data: {} }) as never
    expect(preferInnermost([hit(ROOT_DROP_ID), hit(`${DROP_PREFIX}docs`)]).map((c) => c.id))
      .toEqual([`${DROP_PREFIX}docs`])
    expect(preferInnermost([hit(ROOT_DROP_ID)]).map((c) => c.id)).toEqual([ROOT_DROP_ID])
  })
})
