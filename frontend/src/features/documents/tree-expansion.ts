import type { UriTreeNode } from "./uri-tree"

/** Per-project, so opening one project does not inherit another's tree. */
export function expansionStorageKey(project: string): string {
  return `darkmem:artifacts:expanded:${project}`
}

/** Folder paths on the route from a root to `documentId`, excluding the
 *  document's own node. Empty when nothing is selected or the id is unknown —
 *  "expand nothing" is the honest answer to "expand the path to nowhere". */
export function pathsToDocument(
  roots: UriTreeNode[],
  documentId: string | null,
): string[] {
  if (!documentId) return []
  const trail: string[] = []
  const walk = (nodes: UriTreeNode[], ancestors: string[]): boolean => {
    for (const n of nodes) {
      if (n.document?.id === documentId) {
        trail.push(...ancestors)
        return true
      }
      if (n.children.length > 0 && walk(n.children, [...ancestors, n.path])) {
        return true
      }
    }
    return false
  }
  walk(roots, [])
  return trail
}

/** The no-selection default: top-level folders only. */
export function rootFolderPaths(roots: UriTreeNode[]): string[] {
  return roots.filter((n) => n.children.length > 0).map((n) => n.path)
}
