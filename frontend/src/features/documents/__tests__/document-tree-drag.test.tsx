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
  ROW_DROP_DISABLED,
} from "../components/document-tree"
import { buildUriTree } from "../uri-tree"
import type { DocumentListItem } from "@/hooks/api"
import type { MoveTarget } from "../move-target"

function doc(id: string, uri: string): DocumentListItem {
  return { id, title: null, uri, source_type: "md", project: "p", block_count: 1 }
}

const ITEMS = [doc("1", "docs/a.md"), doc("2", "notes/b.md")]

const DROP_ITEMS = [
  doc("1", "docs/a.md"),
  doc("2", "docs/b.md"),
  doc("3", "notes/c.md"),
  // A root-level leaf whose name minus its last character is a folder path.
  // `path.lastIndexOf("/")` is -1 here, and an unguarded `slice(0, -1)`
  // makes "docs2" resolve into "docs".
  doc("4", "docs2"),
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

describe("what dnd-kit actually delivers to resolveDrop", () => {
  /** Models dnd-kit's own pipeline rather than calling `resolveDrop` with an
   *  id it would never produce. `DndContext` filters droppables through
   *  `getEnabled()` BEFORE it calls the collision detector, so a row
   *  droppable that is `disabled` is not a candidate at all -- it falls
   *  through to the pane, which encloses it, and resolves as a move to the
   *  top level. That residue is the whole failure mode and it lives outside
   *  `resolveDrop`, so a test that feeds the function directly cannot see
   *  it. */
  function deliver(dragged: string, hitPaths: string[]): MoveTarget | null {
    const rowHits = ROW_DROP_DISABLED
      ? []
      : hitPaths.map((path) => ({ id: `${DROP_PREFIX}${path}`, data: {} }) as never)
    // The pane encloses every row, so it is always under the pointer too.
    const hits = [{ id: ROOT_DROP_ID, data: {} } as never, ...rowHits]
    const over = preferInnermost(hits)[0]
    return resolveDrop(DROP_PATHS, `${DRAG_PREFIX}${dragged}`, over ? String(over.id) : null)
  }

  it("refuses a release over a sibling leaf instead of moving to the root", () => {
    expect(deliver("docs/a.md", ["docs/b.md"])).toBeNull()
  })

  it("refuses a release over the dragged row itself", () => {
    expect(deliver("docs/a.md", ["docs/a.md"])).toBeNull()
  })

  it("refuses a release over the dragged row's own parent folder", () => {
    expect(deliver("docs/a.md", ["docs"])).toBeNull()
  })

  it("still moves into another folder, and to the root over empty pane", () => {
    expect(deliver("docs/a.md", ["notes"])).toEqual({
      kind: "document",
      documentId: "1",
      uri: "notes/a.md",
    })
    expect(deliver("docs/a.md", [])).toEqual({
      kind: "document",
      documentId: "1",
      uri: "a.md",
    })
  })
})

describe("dropTargetFor on a root-level leaf", () => {
  it("resolves to the top level, never into a folder its name shadows", () => {
    expect(dropTargetFor(DROP_PATHS, DROP_PATHS.get("docs2")!)).toBeNull()
    expect(drop("notes/c.md", `${DROP_PREFIX}docs2`)).toEqual({
      kind: "document",
      documentId: "3",
      uri: "c.md",
    })
  })
})
