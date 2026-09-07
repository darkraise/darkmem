import { NO_PATH, type UriTreeNode } from "./uri-tree"

export type MoveTarget =
  | { kind: "document"; documentId: string; uri: string }
  | { kind: "subtree"; uriPrefix: string; newUriPrefix: string }

/** Where a drop lands, or `null` when the drop is refused.
 *
 *  Refused rather than clamped, because every refusal here is a case the
 *  backend would otherwise have to disambiguate: a folder into its own
 *  descendant is the rename whose ordering `rename_documents` had to be
 *  taught, and the `(no path)` bucket is a synthesised node with no uri at
 *  all, so a subtree verb against it matches nothing. */
export function moveTarget(
  dragged: UriTreeNode,
  dropTarget: UriTreeNode | null,
): MoveTarget | null {
  const targetPath = dropTarget?.path ?? ""
  if (dragged.path === NO_PATH || targetPath === NO_PATH) return null
  if (dropTarget && dropTarget.path === dragged.path) return null
  // Into its own subtree: the `/` guard stops `a` matching `ab`.
  if (targetPath === dragged.path || targetPath.startsWith(`${dragged.path}/`)) {
    return null
  }

  const leaf = dragged.path.split("/").pop()!
  const parent = dragged.path.slice(0, Math.max(0, dragged.path.length - leaf.length - 1))
  if (parent === targetPath) return null // already there

  const destination = targetPath ? `${targetPath}/${leaf}` : leaf

  if (dragged.document) {
    return { kind: "document", documentId: dragged.document.id, uri: destination }
  }
  return { kind: "subtree", uriPrefix: dragged.path, newUriPrefix: destination }
}
