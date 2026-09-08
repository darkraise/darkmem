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
  DROP_ROW_ATTR,
  DROP_ROOT_ATTR,
  measureDropRow,
  dropCollisionDetection,
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

describe("the drop hit area is the whole row", () => {
  /** A release lands wherever dnd-kit MEASURED the droppable, and the
   *  droppable's own element is the inner handle span -- roughly two thirds
   *  of a nested row's width and a third of its height. Everything left of
   *  the handle (the indent gutter, the chevron) and everything in the
   *  actions slot right of it therefore missed every row and fell through to
   *  the pane, which resolves as a move to the top level. This models the
   *  real pipeline over real elements: measure each droppable, run the
   *  wired collision detector over the resulting rects, resolve the winner. */
  const ROW_H = 36
  const PANE_W = 260
  const PANE_H = 400
  /** Where the handle starts inside a row: past the chevron column and the
   *  indent. Fixed rather than per-depth -- one offset is enough to put the
   *  gutter outside it. */
  const HANDLE_X = 60

  const PATH_BY_NAME = new Map([
    ["docs", "docs"],
    ["a.md", "docs/a.md"],
    ["b.md", "docs/b.md"],
    ["notes", "notes"],
    ["c.md", "notes/c.md"],
  ])

  function stub(el: Element, box: { top: number; bottom: number; left: number; right: number }) {
    const { top, bottom, left, right } = box
    el.getBoundingClientRect = () =>
      ({
        top,
        bottom,
        left,
        right,
        width: right - left,
        height: bottom - top,
        x: left,
        y: top,
        toJSON: () => ({}),
      }) as DOMRect
  }

  function laidOut() {
    const { container } = render(
      <DocumentTree
        items={DROP_ITEMS.filter((d) => d.uri !== "docs2")}
        selectedId={null}
        onSelect={vi.fn()}
        truncated={false}
        onMove={vi.fn()}
      />,
    )
    const pane = container.querySelector(`[${DROP_ROOT_ATTR}]`) as HTMLElement
    stub(pane, { top: 0, left: 0, right: PANE_W, bottom: PANE_H })
    const rows = Array.from(container.querySelectorAll(`[${DROP_ROW_ATTR}]`))
    rows.forEach((row, index) =>
      stub(row, {
        top: index * ROW_H,
        bottom: (index + 1) * ROW_H,
        left: 0,
        right: PANE_W,
      }),
    )
    for (const handle of container.querySelectorAll("[data-drag-handle]")) {
      const row = handle.closest(`[${DROP_ROW_ATTR}]`)!.getBoundingClientRect()
      stub(handle, {
        top: row.top + 12,
        bottom: row.bottom - 12,
        left: HANDLE_X,
        right: PANE_W,
      })
    }

    const droppableRects = new Map<string, ReturnType<typeof measureDropRow>>()
    droppableRects.set(ROOT_DROP_ID, measureDropRow(pane))
    for (const handle of container.querySelectorAll("[data-drag-handle]")) {
      const name = handle.textContent!.trim()
      droppableRects.set(
        `${DROP_PREFIX}${PATH_BY_NAME.get(name)}`,
        measureDropRow(handle as HTMLElement),
      )
    }
    return { container, droppableRects, rows }
  }

  /** measure -> collide -> resolve, the three steps a real release runs. */
  function releaseAt(dragged: string, x: number, y: number): MoveTarget | null {
    const { droppableRects } = laidOut()
    const hits = dropCollisionDetection({
      droppableContainers: Array.from(droppableRects.keys()).map((id) => ({ id })),
      droppableRects,
      pointerCoordinates: { x, y },
    } as unknown as Parameters<typeof dropCollisionDetection>[0])
    const over = hits[0]
    return resolveDrop(DROP_PATHS, `${DRAG_PREFIX}${dragged}`, over ? String(over.id) : null)
  }

  /** Row order: docs, docs/a.md, docs/b.md, notes, notes/c.md. */
  const rowCentre = (index: number) => index * ROW_H + ROW_H / 2

  it("resolves a release in a nested row's indent gutter to that row", () => {
    expect(releaseAt("docs/a.md", 8, rowCentre(4))).toEqual({
      kind: "document",
      documentId: "1",
      uri: "notes/a.md",
    })
  })

  it("resolves a release on a folder's chevron to that folder", () => {
    expect(releaseAt("docs/a.md", 20, rowCentre(3))).toEqual({
      kind: "document",
      documentId: "1",
      uri: "notes/a.md",
    })
  })

  it("resolves a release in a row's top and bottom margins to that row", () => {
    for (const y of [3 * ROW_H + 2, 4 * ROW_H - 2]) {
      expect(releaseAt("docs/a.md", 120, y)).toEqual({
        kind: "document",
        documentId: "1",
        uri: "notes/a.md",
      })
    }
  })

  it("still resolves a release below the last row to the top level", () => {
    // The deliberate drop-to-root affordance: once rows fill their own boxes
    // the only space left is the strip under them, so it has to be a target.
    expect(releaseAt("docs/a.md", 120, 5 * ROW_H + 20)).toEqual({
      kind: "document",
      documentId: "1",
      uri: "a.md",
    })
  })

  it("never widens a folder's hit area to its whole subtree", () => {
    // The branch `<li>` encloses its descendants' rows, so measuring that
    // instead of the control would make a release anywhere inside `docs`
    // resolve to `docs` itself.
    const { container } = laidOut()
    for (const row of container.querySelectorAll(`[${DROP_ROW_ATTR}]`)) {
      expect(row.querySelector(`[${DROP_ROW_ATTR}]`)).toBeNull()
    }
  })

  it("keeps the pane measuring itself, since it sits under no row", () => {
    const { container } = laidOut()
    const pane = container.querySelector(`[${DROP_ROOT_ATTR}]`) as HTMLElement
    expect(pane.closest(`[${DROP_ROW_ATTR}]`)).toBeNull()
    expect(measureDropRow(pane).height).toBe(PANE_H)
  })
})
