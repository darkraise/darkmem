import { render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { PageListItem } from "@/hooks/api"
import { buildPageTree, pageNodeIndex } from "../lib/build-page-tree"
import {
  DRAG_PREFIX,
  DROP_PREFIX,
  PageTree,
  pointerZone,
  resolveDrop,
  shouldHoverExpand,
} from "../page-tree"

function row(id: string, parent_id: string | null, order_index: number): PageListItem {
  return {
    id,
    project: "personal",
    parent_id,
    order_index,
    title: id,
    content_hash: "h",
    properties: null,
    created_at: "2026-09-18T00:00:00Z",
    updated_at: "2026-09-18T00:00:00Z",
  }
}

const roots = buildPageTree([
  row("a", null, 0),
  row("b", "a", 0),
  row("d", null, 1),
])
const index = pageNodeIndex(roots)

// The expanded set is per-viewer storage shared across this file, so a case
// that seeds it would otherwise decide what the cases after it render.
beforeEach(() => {
  window.localStorage.clear()
})

describe("pointerZone", () => {
  it("reads the zone from the pointer's offset inside the row's own rect", () => {
    const rect = { top: 100, height: 30 } as { top: number; height: number }
    expect(pointerZone(rect, 102)).toBe("before")
    expect(pointerZone(rect, 115)).toBe("inside")
    expect(pointerZone(rect, 128)).toBe("after")
  })

  it("is inside when there is no rect to measure", () => {
    expect(pointerZone(null, 115)).toBe("inside")
  })
})

describe("resolveDrop", () => {
  it("strips the drag and drop prefixes before resolving", () => {
    expect(
      resolveDrop(roots, index, `${DRAG_PREFIX}d`, `${DROP_PREFIX}a`, "inside"),
    ).toEqual({ parentId: "a", afterId: "b" })
  })

  it("refuses when nothing is under the pointer", () => {
    expect(resolveDrop(roots, index, `${DRAG_PREFIX}d`, null, "inside")).toBeNull()
  })

  it("refuses a drop onto a descendant", () => {
    expect(
      resolveDrop(roots, index, `${DRAG_PREFIX}a`, `${DROP_PREFIX}b`, "after"),
    ).toBeNull()
  })
})

describe("PageTree drag layer", () => {
  it("mounts a drag handle on every rendered row", () => {
    render(
      <PageTree
        roots={roots}
        index={index}
        project="personal"
        selectedId={null}
        onSelect={vi.fn()}
        onNewChild={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
        onMove={vi.fn()}
      />,
    )
    // Two: the tree starts collapsed, so only the roots `a` and `d` render.
    expect(document.querySelectorAll("[data-drag-handle]")).toHaveLength(2)
    expect(screen.getByText("a")).toBeInTheDocument()
  })

  it("mounts a handle on a nested row too, once its parent is open", () => {
    window.localStorage.setItem(
      "darkmem:notes:expanded:personal",
      JSON.stringify(["a"]),
    )
    render(
      <PageTree
        roots={roots}
        index={index}
        project="personal"
        selectedId={null}
        onSelect={vi.fn()}
        onNewChild={vi.fn()}
        onRename={vi.fn()}
        onDelete={vi.fn()}
        onMove={vi.fn()}
      />,
    )
    expect(document.querySelectorAll("[data-drag-handle]")).toHaveLength(3)
  })

})

// dnd-kit's pointer pipeline does not run under the test DOM, so the hover-to-expand
// DECISION is a pure function and is tested here. The `setTimeout` that fires
// it is untested, and is stated as such rather than left to look covered.
describe("shouldHoverExpand", () => {
  it("opens a closed branch that has children", () => {
    expect(shouldHoverExpand(index, [], "a")).toBe(true)
  })

  it("leaves an already-open branch alone", () => {
    expect(shouldHoverExpand(index, ["a"], "a")).toBe(false)
  })

  it("does not arm on a leaf or an unknown id", () => {
    expect(shouldHoverExpand(index, [], "d")).toBe(false)
    expect(shouldHoverExpand(index, [], "missing")).toBe(false)
  })
})
