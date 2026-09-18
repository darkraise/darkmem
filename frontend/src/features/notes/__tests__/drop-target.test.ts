import { describe, expect, it } from "vitest"
import type { PageListItem } from "@/hooks/api"
import { buildPageTree, pageNodeIndex } from "../lib/build-page-tree"
import {
  applyPlacement,
  dropZoneFor,
  isDescendant,
  resolvePageDrop,
} from "../lib/drop-target"

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

//  a          roots: a, d
//  |- b
//  |  |- c
//  |- e
//  d
const ROWS = [
  row("a", null, 0),
  row("b", "a", 0),
  row("c", "b", 0),
  row("e", "a", 1),
  row("d", null, 1),
]
const roots = buildPageTree(ROWS)
const index = pageNodeIndex(roots)
const resolve = (dragged: string, over: string | null, zone: Parameters<typeof resolvePageDrop>[4]) =>
  resolvePageDrop(roots, index, dragged, over, zone)

describe("dropZoneFor", () => {
  it("splits a row into thirds", () => {
    expect(dropZoneFor(1, 30)).toBe("before")
    expect(dropZoneFor(15, 30)).toBe("inside")
    expect(dropZoneFor(29, 30)).toBe("after")
  })

  it("puts the boundaries on the outer side of each third", () => {
    expect(dropZoneFor(10, 30)).toBe("inside")
    expect(dropZoneFor(20, 30)).toBe("inside")
  })

  // jsdom and a collapsed row both produce a zero box; guessing `before`
  // there would make every unmeasured drop a reorder.
  it("falls back to inside when the row has no height", () => {
    expect(dropZoneFor(0, 0)).toBe("inside")
    expect(dropZoneFor(5, -1)).toBe("inside")
  })
})

describe("isDescendant", () => {
  it("finds a descendant at any depth and excludes the node itself", () => {
    expect(isDescendant(index.get("a")!, "c")).toBe(true)
    expect(isDescendant(index.get("a")!, "a")).toBe(false)
    expect(isDescendant(index.get("b")!, "e")).toBe(false)
  })
})

describe("resolvePageDrop", () => {
  it("drops before a row as that row's previous sibling", () => {
    expect(resolve("d", "b", "before")).toEqual({ parentId: "a", afterId: null })
    expect(resolve("d", "e", "before")).toEqual({ parentId: "a", afterId: "b" })
  })

  it("drops after a row as that row itself", () => {
    expect(resolve("d", "b", "after")).toEqual({ parentId: "a", afterId: "b" })
  })

  it("drops inside a row as its last child", () => {
    expect(resolve("d", "a", "inside")).toEqual({ parentId: "a", afterId: "e" })
    expect(resolve("d", "c", "inside")).toEqual({ parentId: "c", afterId: null })
  })

  it("skips the dragged page when reading the target's children", () => {
    // `e` is already a's last child. Unfiltered, "inside a" would anchor it
    // after ITSELF; filtered it resolves to where it already is, which is the
    // no-op the next case refuses.
    expect(resolve("e", "a", "inside")).toBeNull()
    expect(resolve("b", "a", "inside")).toEqual({ parentId: "a", afterId: "e" })
  })

  it("refuses a drop onto the page itself or a descendant of it", () => {
    expect(resolve("a", "a", "inside")).toBeNull()
    expect(resolve("a", "c", "inside")).toBeNull()
    expect(resolve("a", "b", "after")).toBeNull()
  })

  it("refuses a drop on nothing", () => {
    expect(resolve("d", null, "inside")).toBeNull()
    expect(resolve("d", "missing", "inside")).toBeNull()
  })

  it("refuses a placement equal to where the page already is", () => {
    expect(resolve("e", "b", "after")).toBeNull()
    // Before its own next sibling is where `b` already is.
    expect(resolve("b", "e", "before")).toBeNull()
    expect(resolve("d", "a", "after")).toBeNull()
  })
})

describe("applyPlacement", () => {
  const tree = (rows: PageListItem[]) =>
    buildPageTree(rows).map((r) => ({
      id: r.id,
      children: r.children.map((c) => c.id),
    }))

  it("reparents and reorders so the optimistic tree matches the move", () => {
    const next = applyPlacement(ROWS, "d", { parentId: "a", afterId: "b" })
    expect(tree(next)).toEqual([{ id: "a", children: ["b", "d", "e"] }])
  })

  it("places first under a null afterId, as the route does", () => {
    const next = applyPlacement(ROWS, "d", { parentId: "a", afterId: null })
    expect(tree(next)).toEqual([{ id: "a", children: ["d", "b", "e"] }])
  })

  it("moves a page back to the root", () => {
    const next = applyPlacement(ROWS, "b", { parentId: null, afterId: "a" })
    expect(tree(next)).toEqual([
      { id: "a", children: ["e"] },
      { id: "b", children: ["c"] },
      { id: "d", children: [] },
    ])
  })

  it("leaves the input untouched", () => {
    const before = JSON.stringify(ROWS)
    applyPlacement(ROWS, "d", { parentId: "a", afterId: "b" })
    expect(JSON.stringify(ROWS)).toBe(before)
  })

  it("returns the rows unchanged when the page is not in the list", () => {
    expect(applyPlacement(ROWS, "missing", { parentId: null, afterId: null })).toEqual(
      ROWS,
    )
  })
})
