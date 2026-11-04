import { memo, useEffect, useMemo, useRef } from "react"
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

/** A table block's data rows, keyed by the table's id, plus the set of row
 *  ids the table has adopted so the body does not render them twice.
 *
 *  `table_row` blocks carry the table as their `parent_id`, so this is exact
 *  rather than an adjacency guess. A row whose table is not in this result --
 *  a `block_ids` drill-down can return one -- is left in the body and renders
 *  standalone, because dropping it would silently lose content.
 */
export function adoptTableRows(rows: BlockRow[]): {
  rowsByTable: Map<string, BlockRow[]>
  adopted: Set<string>
} {
  const tables = new Set(
    rows.filter((r) => r.type === "table").map((r) => r.block_id),
  )
  const rowsByTable = new Map<string, BlockRow[]>()
  const adopted = new Set<string>()
  for (const row of rows) {
    if (row.type !== "table_row") continue
    if (row.parent_id === null || !tables.has(row.parent_id)) continue
    const bucket = rowsByTable.get(row.parent_id)
    if (bucket) bucket.push(row)
    else rowsByTable.set(row.parent_id, [row])
    adopted.add(row.block_id)
  }
  return { rowsByTable, adopted }
}

/** Vertical rhythm, which a uniform gap cannot express.
 *
 * The body used to be `space-y-2.5`: the same gap between two list items as
 * between a paragraph and the heading of the next section, so nothing on the
 * page grouped and a document read as one flat column. Prose needs a heading
 * to own the space above it, and a run of list items to sit tighter than the
 * paragraphs around them.
 *
 * Returned as a class per row rather than a `space-y` on the parent, because
 * the gap depends on which two block types meet.
 */
export function blockSpacing(
  block: BlockRow,
  previous: BlockRow | undefined,
  index: number,
): string {
  if (index === 0) return ""
  // A heading opens a section: the space belongs above it, and more of it the
  // higher the level.
  if (block.type === "heading") {
    const level = Number(block.properties?.level)
    return level === 1 || level === 2 ? "mt-6" : "mt-5"
  }
  // The first row after a heading stays close to it -- it is that heading's
  // content, not a new thing.
  if (previous?.type === "heading") return "mt-1.5"
  // Consecutive list items are one list.
  if (block.type === "list" && previous?.type === "list") return "mt-1"
  if (block.type === "table_row") return "mt-0"
  if (block.type === "divider") return "mt-5"
  if (previous?.type === "divider") return "mt-5"
  return "mt-3"
}

/** Memoised, because the artifacts workspace holds the reader's *reported*
 *  heading as its own state and renders the rail beside it.
 *
 * Every heading the body scrolls past is a `setState` in that parent, so
 * without this the reader re-rendered its whole block list once per crossing
 * -- measured on a 120-heading, 1200-block document as a ~1.4s frozen frame
 * per heading, which is the rail visibly lagging the scroll. Its props are
 * stable across that state change by construction: the callback is the
 * workspace's own `useCallback`, and nothing else about the reader depends on
 * where the reader currently is. */
export const DocumentReader = memo(function DocumentReader({
  documentId,
  focusBlockId = null,
  showOutline = true,
  onActiveHeadingChange,
}: {
  documentId: string
  /** Scroll to and mark this block once the body has rendered. A section
   *  search that only opened the document would drop the reader at the top,
   *  losing the section they matched. */
  focusBlockId?: string | null
  /** The inline outline rail. Off for a caller that mounts `DocumentOutline`
   *  itself -- the artifacts workspace parks it in a sticky right column, and
   *  two rails for one document would be two jump lists disagreeing about
   *  where the reader is. */
  showOutline?: boolean
  /** The heading the reader is currently under, reported as the body scrolls.
   *  Lives here rather than in the outline because only this component knows
   *  which rows are headings and which element scrolls them. */
  onActiveHeadingChange?: (blockId: string | null) => void
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

  // Which heading the body is currently under, recomputed as it scrolls.
  //
  // A geometry read on scroll rather than an IntersectionObserver: the
  // question is "which heading did we last pass", and that has an answer even
  // when NO heading is on screen -- a long section scrolls its own heading out
  // of view, and an observer watching for intersections reports nothing there
  // and leaves the rail pointing at whatever was last seen entering. The last
  // heading above the fold is the section you are in, by definition.
  //
  // The scroller is the ScrollArea's viewport, not the window, so it is found
  // from the body rather than assumed.
  useEffect(() => {
    if (!ready || !onActiveHeadingChange) return
    const body = bodyRef.current
    const root = body?.closest<HTMLElement>("[data-darkraise-scroll-viewport]")
    if (!body || !root) return

    let frame = 0
    let last: string | null = null
    const measure = () => {
      frame = 0
      const headings = body.querySelectorAll<HTMLElement>("[data-heading]")
      // Reported, not skipped: a document with no headings has no current
      // section, and returning early would leave the rail marking a heading
      // from the document that was open before this one.
      if (headings.length === 0) {
        if (last !== null) {
          last = null
          onActiveHeadingChange(null)
        }
        return
      }
      // Matches the block rows' own `scroll-mt-16`: a heading parked under the
      // sticky header is one the reader cannot see, so it must not count as
      // the current one.
      const line = root.getBoundingClientRect().top + 64
      let current = headings[0]!.dataset.blockId ?? null
      for (const heading of headings) {
        if (heading.getBoundingClientRect().top > line) break
        current = heading.dataset.blockId ?? current
      }
      if (current !== last) {
        last = current
        onActiveHeadingChange(current)
      }
    }
    const onScroll = () => {
      // Coalesced to one read per frame: the handler is pure geometry and a
      // scroll fires far more often than the rail can usefully move.
      if (frame === 0) frame = requestAnimationFrame(measure)
    }

    measure()
    root.addEventListener("scroll", onScroll, { passive: true })
    return () => {
      root.removeEventListener("scroll", onScroll)
      if (frame !== 0) cancelAnimationFrame(frame)
    }
  }, [ready, documentId, onActiveHeadingChange])

  const rows = blocks.data?.blocks ?? []
  // Three full passes over the block list, and none of them depends on
  // anything but the list itself -- so they run once per document rather than
  // once per render.
  const { depths, rowsByTable, body } = useMemo(() => {
    const { rowsByTable: byTable, adopted } = adoptTableRows(rows)
    return {
      depths: listDepths(rows),
      rowsByTable: byTable,
      body: rows.filter((block) => !adopted.has(block.block_id)),
    }
  }, [rows])

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
      <p className="text-destructive-text text-sm">
        This document could not be read.
      </p>
    )
  }

  if (rows.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">
        This document is empty.
      </p>
    )
  }

  return (
    <div className="flex gap-5">
      {showOutline && (outline.data?.items.length ?? 0) > 0 ? (
        <nav className="hidden w-52 shrink-0 lg:block">
          <p className="text-muted-foreground pb-1.5 font-mono text-xs tracking-wide uppercase">
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

      <div ref={bodyRef} className="min-w-0 flex-1">
        {body.map((block, i) => {
          const depth = depths[block.block_id] ?? 0
          const previous = body[i - 1]
          return (
            <div
              key={block.block_id}
              id={block.block_id}
              data-block-id={block.block_id}
              data-depth={depth}
              // The scrollspy's selector. A data attribute rather than a
              // class so a styling change cannot silently unhook it.
              data-heading={block.type === "heading" ? "" : undefined}
              style={depth > 0 ? { paddingLeft: `${depth * 18}px` } : undefined}
              className={[
                // The reader's own header bar is sticky over this column, so
                // a block scrolled to by the outline or a search hit must
                // stop below it rather than under it.
                "scroll-mt-16",
                blockSpacing(block, previous, i),
                block.block_id === focusBlockId
                  ? "ring-primary/40 rounded-sm ring-2 ring-offset-2 ring-offset-transparent"
                  : "",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              <BlockView
                block={block}
                rows={rowsByTable.get(block.block_id) ?? []}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
})
