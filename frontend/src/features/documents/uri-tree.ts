import type { DocumentListItem } from "@/hooks/api"

/** Documents with no uri collect here rather than being dropped. */
export const NO_PATH = "(no path)"

export interface UriTreeNode {
  /** Last path segment -- what the row renders. */
  name: string
  /** Full path prefix, "/"-joined; unique within the tree. */
  path: string
  /** The document filed exactly at this path, when one is. A node can be
   *  both a document and a folder: `a/b.md` and `a/b.md/c.md` coexist --
   *  uris are opaque keys, not a filesystem. */
  document: DocumentListItem | null
  children: UriTreeNode[]
}

function child(parent: UriTreeNode[], name: string, path: string): UriTreeNode {
  const found = parent.find((n) => n.name === name)
  if (found) return found
  const node: UriTreeNode = { name, path, document: null, children: [] }
  parent.push(node)
  return node
}

/** Folders first, then name -- a flat alphabetical sort buries a directory
 *  among the files that sit beside it. */
function sortTree(nodes: UriTreeNode[]): void {
  nodes.sort((a, b) => {
    const aFolder = a.children.length > 0
    const bFolder = b.children.length > 0
    if (aFolder !== bFolder) return aFolder ? -1 : 1
    return a.name.localeCompare(b.name)
  })
  for (const node of nodes) sortTree(node.children)
}

/** Group documents by uri "/" segments. */
export function buildUriTree(items: DocumentListItem[]): UriTreeNode[] {
  const roots: UriTreeNode[] = []
  const orphans: UriTreeNode = {
    name: NO_PATH, path: NO_PATH, document: null, children: [],
  }

  for (const item of items) {
    if (!item.uri) {
      orphans.children.push({
        name: item.title ?? item.id,
        path: `${NO_PATH}/${item.id}`,
        document: item,
        children: [],
      })
      continue
    }
    const segments = item.uri.split("/").filter(Boolean)
    let level = roots
    let prefix = ""
    let node: UriTreeNode | null = null
    for (const segment of segments) {
      prefix = prefix ? `${prefix}/${segment}` : segment
      node = child(level, segment, prefix)
      level = node.children
    }
    // The leaf carries the document. A node already holding children keeps
    // them: `a/b.md` and `a/b.md/c.md` are both legitimate uris.
    if (node) node.document = item
  }

  sortTree(roots)
  if (orphans.children.length > 0) {
    orphans.children.sort((a, b) => a.name.localeCompare(b.name))
    roots.push(orphans)   // last, after the sort, so it stays at the bottom
  }
  return roots
}
