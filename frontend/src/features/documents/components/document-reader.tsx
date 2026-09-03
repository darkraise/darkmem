import { useEffect, useRef } from "react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { useDocumentBlocks, useDocumentOutline } from "@/hooks/api"
import type { BlockRow } from "@/hooks/api"
import { BlockView } from "./block-view"

/** Outline rail plus the block body, in reading order.
 *
 * Reading order is what `document_blocks` serves -- a flat, `order_index`
 * sorted list -- and it stays the render order. What is reconstructed is
 * *list* nesting only, as indentation, so a nested list reads as nested
 * without the body being restructured into a tree: the flat sibling list is
 * what `focusBlockId`'s scroll query and the outline's `#id` anchors address.
 *
 * Not semantic `<ul>`/`<ol>` grouping: the parser writes no marker for a list
 * block, so an ordered list cannot be told from a bullet one on this surface
 * and every `<ol>` would be a guess. That is the deferred defect 3.
 */
/** List-nesting depth per block id, counting only `list` ancestors.
 *
 * Every block under a heading carries that heading as its `parent_id`, so
 * depth cannot simply be the length of the parent chain -- that would indent
 * a whole document body under its title. Counting list ancestors also gets
 * the case a chain length would miss: a code block inside a list item
 * indents with its item.
 *
 * Defensive against a dangling parent (a `block_ids` drill-down legitimately
 * returns a child without its parent) and against a cycle, which the schema
 * permits even though the parser cannot emit one.
 */
export function listDepths(rows: BlockRow[]): Record<string, number> {
  const byId = new Map(rows.map((r) => [r.block_id, r]))
  const depths: Record<string, number> = {}
  for (const row of rows) {
    let depth = 0
    const seen = new Set<string>([row.block_id])
    let cursor = row.parent_id
    while (cursor !== null && !seen.has(cursor)) {
      seen.add(cursor)
      const parent = byId.get(cursor)
      if (parent === undefined) break
      if (parent.type === "list") depth += 1
      cursor = parent.parent_id
    }
    depths[row.block_id] = depth
  }
  return depths
}

export function DocumentReader({
  documentId,
  focusBlockId = null,
}: {
  documentId: string
  /** Scroll to and mark this block once the body has rendered. A section
   *  search that only opened the document would drop the reader at the top,
   *  losing the section they matched. */
  focusBlockId?: string | null
}) {
  const outline = useDocumentOutline(documentId)
  const blocks = useDocumentBlocks(documentId)
  const bodyRef = useRef<HTMLDivElement>(null)

  const ready = !blocks.isLoading && !blocks.isError
  useEffect(() => {
    if (!focusBlockId || !ready) return
    // Query within this reader rather than the document: two readers can be
    // mounted (the artifacts pane and the ledger), and block ids are unique
    // per document, not per page.
    const target = bodyRef.current?.querySelector(`[data-block-id="${focusBlockId}"]`)
    target?.scrollIntoView({ behavior: "smooth", block: "start" })
  }, [focusBlockId, ready, documentId])

  if (blocks.isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-20 w-full" />
      </div>
    )
  }
  if (blocks.isError) {
    return (
      <p className="text-destructive text-sm">
        This document could not be read — a failed read, not an empty document.
      </p>
    )
  }

  const rows = blocks.data?.blocks ?? []
  const depths = listDepths(rows)
  if (rows.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">
        This document is filed but holds no blocks.
      </p>
    )
  }

  return (
    <div className="flex gap-5">
      {(outline.data?.items.length ?? 0) > 0 ? (
        <nav className="hidden w-52 shrink-0 lg:block">
          <p className="text-muted-foreground pb-1.5 font-mono text-[10px] tracking-wide uppercase">
            outline
          </p>
          <ul className="space-y-0.5">
            {outline.data!.items.map((node) => (
              <li key={node.block_id}>
                <a
                  href={`#${node.block_id}`}
                  className="text-muted-foreground hover:text-foreground block truncate text-sm"
                  style={{ paddingLeft: `${Math.max(0, node.level - 1) * 10}px` }}
                >
                  {node.text}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}

      <div ref={bodyRef} className="min-w-0 flex-1 space-y-2.5">
        {rows.map((block) => {
          const depth = depths[block.block_id] ?? 0
          return (
            <div
              key={block.block_id}
              id={block.block_id}
              data-block-id={block.block_id}
              data-depth={depth}
              style={depth > 0 ? { paddingLeft: `${depth * 18}px` } : undefined}
              className={
                block.block_id === focusBlockId
                  ? "ring-primary/40 rounded-sm ring-2 ring-offset-2 ring-offset-transparent"
                  : undefined
              }
            >
              <BlockView block={block} />
            </div>
          )
        })}
      </div>
    </div>
  )
}
