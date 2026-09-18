import type { PageListItem } from "@/hooks/api"

export interface PageNode {
  id: string
  title: string | null
  parent_id: string | null
  order_index: number
  children: PageNode[]
}

/** What every page surface renders for a page whose title is null. One
 *  constant so the tree, the pane and the trash sheet cannot disagree. */
export const PAGE_TITLE_FALLBACK = "Untitled"

function sortSiblings(nodes: PageNode[]): void {
  // The id tie-break is what makes the tree stable: two siblings can share an
  // order_index, and without it their rendered order would follow whatever
  // order the list happened to arrive in.
  nodes.sort((a, b) =>
    a.order_index === b.order_index
      ? a.id.localeCompare(b.id)
      : a.order_index - b.order_index,
  )
  for (const node of nodes) sortSiblings(node.children)
}

/** Flat rows to a nested tree.
 *
 *  `GET /pages` orders by `(parent_id, order_index)` with NULL parents last,
 *  so a child can arrive before its parent and children of different parents
 *  interleave. Every node is created up front and only then attached, which is
 *  what makes any arrival order give the same tree.
 */
export function buildPageTree(rows: PageListItem[]): PageNode[] {
  const byId = new Map<string, PageNode>()
  for (const row of rows) {
    byId.set(row.id, {
      id: row.id,
      title: row.title,
      parent_id: row.parent_id,
      order_index: row.order_index,
      children: [],
    })
  }
  const roots: PageNode[] = []
  for (const row of rows) {
    const node = byId.get(row.id)!
    const parent = row.parent_id === null ? undefined : byId.get(row.parent_id)
    if (parent) {
      parent.children.push(node)
    } else {
      // A parent outside the list cannot happen against a whole-project read,
      // but a row hidden behind one would otherwise vanish from the tree
      // rather than appear at the root.
      roots.push(node)
    }
  }
  sortSiblings(roots)
  return roots
}

export function pageNodeIndex(roots: PageNode[]): Map<string, PageNode> {
  const index = new Map<string, PageNode>()
  const walk = (nodes: PageNode[]) => {
    for (const node of nodes) {
      index.set(node.id, node)
      walk(node.children)
    }
  }
  walk(roots)
  return index
}
