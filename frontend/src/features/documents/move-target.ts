import { NO_PATH, type UriTreeNode } from "./uri-tree"

export type MoveTarget =
  | { kind: "document"; documentId: string; uri: string }
  | { kind: "subtree"; uriPrefix: string; newUriPrefix: string }

/** The bucket itself AND every synthesised child under it (`(no path)/<id>`)
 *  -- an orphan child's path is derived from its document's raw id, never
 *  from anything a human chose, so handing it a real uri via a move would
 *  mint a path out of a uuid. Refused, not offered as a feature. */
function isOrphan(path: string): boolean {
  return path === NO_PATH || path.startsWith(`${NO_PATH}/`)
}

/** Where a drop lands, or `null` when the drop is refused.
 *
 *  Refused rather than clamped, because every refusal here is a case the
 *  backend would otherwise have to disambiguate: a folder into its own
 *  descendant is the rename whose ordering `rename_documents` had to be
 *  taught, and the `(no path)` bucket and its children are synthesised
 *  nodes with no real uri at all, so a move against either matches nothing
 *  a human authored. */
export function moveTarget(
  dragged: UriTreeNode,
  dropTarget: UriTreeNode | null,
): MoveTarget | null {
  const targetPath = dropTarget?.path ?? ""
  if (isOrphan(dragged.path) || isOrphan(targetPath)) return null
  if (dropTarget && dropTarget.path === dragged.path) return null
  // Into its own subtree: the `/` guard stops `a` matching `ab`.
  if (targetPath === dragged.path || targetPath.startsWith(`${dragged.path}/`)) {
    return null
  }

  const leaf = dragged.path.split("/").pop()!
  const parent = dragged.path.slice(0, Math.max(0, dragged.path.length - leaf.length - 1))
  if (parent === targetPath) return null // already there

  const destination = targetPath ? `${targetPath}/${leaf}` : leaf

  // A node can be both a document and a folder (`a/b.md` above
  // `a/b.md/c.md`); moving the document alone would strand every descendant
  // under the old prefix. Children decide, not the row -- matches
  // project-workspace.tsx's rename dispatch.
  if (dragged.children.length > 0) {
    return { kind: "subtree", uriPrefix: dragged.path, newUriPrefix: destination }
  }
  if (dragged.document) {
    return { kind: "document", documentId: dragged.document.id, uri: destination }
  }
  return { kind: "subtree", uriPrefix: dragged.path, newUriPrefix: destination }
}
