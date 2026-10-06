import { ApiError } from "@/lib/api"
import type { DocumentListItem } from "@/hooks/api"
import { NO_PATH, type UriTreeNode } from "./uri-tree"

/** The server's prefix predicate, unnormalised (CLAUDE.md, Documents):
 *  `uri = prefix OR left(uri, len+1) = prefix || '/'`. The subtree rename,
 *  the subtree delete and the manifest all answer by it. */
export function matchesPrefix(uri: string | null, prefix: string): boolean {
  return uri !== null && (uri === prefix || uri.startsWith(`${prefix}/`))
}

/** Every document the tree shows under `node`, the node's own included. */
export function treeDocuments(node: UriTreeNode): DocumentListItem[] {
  const out: DocumentListItem[] = []
  const walk = (n: UriTreeNode) => {
    if (n.document) out.push(n.document)
    n.children.forEach(walk)
  }
  walk(node)
  return out
}

export type SubtreeCheck =
  | { ok: true; count: number }
  | { ok: false; reason: string }

/** Whether a folder action on `node` would touch exactly what the tree shows
 *  under it.
 *
 *  The tree splits uris on "/" and drops empty segments, so `/notes/a.md`,
 *  `notes//a.md` and `file:///d/a.md` all sit in folders whose path is not a
 *  prefix the server's predicate matches them by: a leading-slash uri
 *  matches at no level, a doubled slash only above the anomaly. A rename or
 *  delete there would silently skip rows the reader can see, so it is
 *  refused and those documents are moved one at a time instead. */
export function checkSubtree(
  node: UriTreeNode,
  items: DocumentListItem[],
): SubtreeCheck {
  if (node.path === NO_PATH || node.path.startsWith(`${NO_PATH}/`)) {
    return { ok: false, reason: "Documents with no path are not a folder." }
  }
  const shown = new Set(treeDocuments(node).map((d) => d.id))
  const matched = items.filter((d) => matchesPrefix(d.uri, node.path))
  const same =
    matched.length === shown.size && matched.every((d) => shown.has(d.id))
  if (!same) {
    return {
      ok: false,
      reason:
        `Some documents under ${node.path} have irregular paths (a leading ` +
        "slash, a doubled slash or a scheme), so a folder action cannot " +
        "address them all. Move those documents one at a time.",
    }
  }
  return { ok: true, count: matched.length }
}

/** A path the SPA will file a document at or move one to. Refused shapes
 *  are the ones the prefix predicate cannot address as a folder later. */
export function uriProblem(uri: string): string | null {
  if (!uri) return "Enter a path."
  if (uri.length > 500) return "A path holds at most 500 characters."
  if (uri.startsWith("/")) return "A path cannot start with a slash."
  if (uri.endsWith("/")) return "A path cannot end with a slash."
  if (uri.includes("//")) return "A path cannot contain an empty folder (//)."
  return null
}

/** The server's refusals, in words a reader can act on. */
export function documentWriteMessage(error: unknown): string {
  if (error instanceof ApiError && error.status === 409) {
    if (error.message.includes("expected_hash")) {
      return "This document changed since you opened it. Reopen it and try again."
    }
    const taken = /already holds the uri '(.*)'/.exec(error.message)
    if (taken) {
      return `Another document in this project is already filed at ${taken[1]}.`
    }
    if (/block/i.test(error.message)) {
      return "That path holds a document edited block by block, which a new filing cannot replace."
    }
  }
  return error instanceof Error ? error.message : String(error)
}
