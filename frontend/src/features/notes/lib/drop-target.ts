import type { PageListItem } from "@/hooks/api"
import type { PageNode } from "./build-page-tree"

export type DropZone = "before" | "after" | "inside"

/** What the move sends. A null `afterId` places FIRST among `parentId`'s
 *  children -- `PagePatchRequest.after_id`'s own semantics, and the opposite of
 *  `POST /pages`, where an absent `after_id` appends. */
export interface DropPlacement {
  parentId: string | null
  afterId: string | null
}

export function dropZoneFor(offsetY: number, height: number): DropZone {
  if (height <= 0) return "inside"
  const ratio = offsetY / height
  if (ratio < 1 / 3) return "before"
  if (ratio > 2 / 3) return "after"
  return "inside"
}

export function isDescendant(node: PageNode, candidateId: string): boolean {
  for (const child of node.children) {
    if (child.id === candidateId || isDescendant(child, candidateId)) return true
  }
  return false
}

function siblingsOf(
  roots: PageNode[],
  index: Map<string, PageNode>,
  node: PageNode,
): PageNode[] {
  if (node.parent_id === null) return roots
  return index.get(node.parent_id)?.children ?? roots
}

function placementOf(
  roots: PageNode[],
  index: Map<string, PageNode>,
  node: PageNode,
): DropPlacement {
  const siblings = siblingsOf(roots, index, node)
  const at = siblings.findIndex((s) => s.id === node.id)
  return { parentId: node.parent_id, afterId: at > 0 ? siblings[at - 1]!.id : null }
}

/** Pointer release to a move, or `null` for a refusal.
 *
 *  Every sibling read excludes the dragged page: it is still in the tree the
 *  caller holds, so anchoring on it would send the page after itself.
 */
export function resolvePageDrop(
  roots: PageNode[],
  index: Map<string, PageNode>,
  draggedId: string,
  overId: string | null,
  zone: DropZone,
): DropPlacement | null {
  if (overId === null || overId === draggedId) return null
  const dragged = index.get(draggedId)
  const over = index.get(overId)
  if (!dragged || !over) return null
  // The server refuses a cycle again under its own lock; refusing here is what
  // keeps the optimistic tree from showing one for a round trip.
  if (isDescendant(dragged, overId)) return null

  let placement: DropPlacement
  if (zone === "inside") {
    const children = over.children.filter((c) => c.id !== draggedId)
    placement = {
      parentId: over.id,
      afterId: children.length > 0 ? children[children.length - 1]!.id : null,
    }
  } else if (zone === "after") {
    placement = { parentId: over.parent_id, afterId: over.id }
  } else {
    const siblings = siblingsOf(roots, index, over).filter((s) => s.id !== draggedId)
    const at = siblings.findIndex((s) => s.id === over.id)
    placement = {
      parentId: over.parent_id,
      afterId: at > 0 ? siblings[at - 1]!.id : null,
    }
  }

  const current = placementOf(roots, index, dragged)
  if (current.parentId === placement.parentId && current.afterId === placement.afterId) {
    return null
  }
  return placement
}

/** The same placement applied to the flat list, for the optimistic update.
 *
 *  The move is shown before the server answers and the refusal path rolls it
 *  back, so this has to reproduce the server's own ordering: a null `afterId`
 *  places FIRST, and the new sibling run is renumbered from zero because
 *  `buildPageTree` sorts on `(order_index, id)`.
 */
export function applyPlacement(
  rows: PageListItem[],
  pageId: string,
  placement: DropPlacement,
): PageListItem[] {
  if (!rows.some((row) => row.id === pageId)) return rows

  const moved = { ...rows.find((row) => row.id === pageId)!, parent_id: placement.parentId }
  const others = rows.filter((row) => row.id !== pageId)
  const siblings = others
    .filter((row) => row.parent_id === placement.parentId)
    .sort((a, b) =>
      a.order_index === b.order_index
        ? a.id.localeCompare(b.id)
        : a.order_index - b.order_index,
    )

  const at =
    placement.afterId === null
      ? 0
      : siblings.findIndex((row) => row.id === placement.afterId) + 1
  siblings.splice(at, 0, moved)

  const renumbered = new Map(
    siblings.map((row, order_index) => [row.id, { ...row, order_index }]),
  )
  return [...others, moved].map((row) => renumbered.get(row.id) ?? row)
}
