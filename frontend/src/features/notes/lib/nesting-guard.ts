/** The slice of a ProseMirror node this module reads, so it needs no import
 *  of the editor's internals. */
interface DocNode {
  type: { name: string }
  attrs: Record<string, unknown>
  firstChild: DocNode | null
  childCount: number
  child(index: number): DocNode
  forEach(visit: (node: DocNode) => void): void
  descendants(visit: (node: DocNode) => boolean | void): void
}

/** The editor block types that may hold children on a page: the editor's
 *  names for `list`, `todo` and `toggle`. */
const EDITOR_CONTAINERS: ReadonlySet<string> = new Set([
  "bulletListItem",
  "numberedListItem",
  "checkListItem",
  "toggleListItem",
])

/** Every `parent>child` id pair in `doc` whose parent may not hold children
 *  on a page. */
export function nestingViolations(doc: DocNode): Set<string> {
  const out = new Set<string>()
  doc.descendants((node) => {
    if (node.type.name !== "blockContainer") return true
    const content = node.firstChild
    const group = node.childCount > 1 ? node.child(1) : null
    if (content && group && !EDITOR_CONTAINERS.has(content.type.name)) {
      group.forEach((child) => out.add(`${node.attrs.id}>${child.attrs.id}`))
    }
    return true
  })
  return out
}

/** True when `after` breaks the page nesting rule somewhere `before` did not.
 *  Comparing against the previous document lets a shape already on the page
 *  (a quote holding a code block) keep loading and taking edits, while no
 *  edit can make a new one: not an indent, a drag, a paste, nor a retype of a
 *  list item that has children. */
export function addsNestingViolation(before: DocNode, after: DocNode): boolean {
  const existing = nestingViolations(before)
  for (const pair of nestingViolations(after)) if (!existing.has(pair)) return true
  return false
}
