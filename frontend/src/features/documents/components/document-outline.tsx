import { ListTree } from "lucide-react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import {
  Timeline,
  TimelineConnector,
  TimelineContent,
  TimelineIndicator,
  TimelineItem,
} from "darkraise-ui/components/timeline"
import { useDocumentOutline } from "@/hooks/api"

/** Indent per heading level, in pixels. Applied to the TITLE rather than to
 *  the item, because the rail is the timeline's own grid column and moving
 *  that per level would bend the line the rail exists to draw. */
const LEVEL_INDENT_PX = 10

/** The open document's heading tree, as a timeline.
 *
 * A timeline rather than a scrolling list: the rail already says "these are
 * ordered positions in one document", which is what an outline claims, and it
 * lets the whole thing render at its natural height. The previous list was
 * capped at `70vh` with `overflow-y-auto`, which put a SECOND scrollbar
 * directly beside the reader's own -- two bars a few pixels apart, each
 * scrolling something different. The cost of dropping the cap is that a
 * document with dozens of headings makes the rail taller than the viewport
 * and its tail is only reachable by scrolling the document; that is the
 * trade, not an oversight.
 *
 * Navigation is a callback carrying the block id, never an `#id` anchor. Two
 * readers can be mounted at once (the artifacts pane and the ledger) and block
 * ids are unique per document, not per page -- so `href="#block"` is ambiguous
 * exactly when both are open. The caller resolves it inside its own reader,
 * which is also what puts the focus ring on the row the reader landed on.
 */
export function DocumentOutline({
  documentId,
  activeBlockId = null,
  onNavigate,
}: {
  documentId: string
  /** The block the reader is currently focused on, if any. */
  activeBlockId?: string | null
  onNavigate: (blockId: string) => void
}) {
  const outline = useDocumentOutline(documentId)
  const items = outline.data?.items ?? []

  if (outline.isLoading) {
    return (
      <div className="space-y-1.5">
        <Skeleton className="h-3 w-2/3" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-3 w-3/4" />
      </div>
    )
  }
  // A document with no headings has no outline to show, and an empty rail
  // taking a column's width says less than nothing.
  if (items.length === 0) return null

  return (
    <nav aria-label="document outline">
      <p className="text-muted-foreground flex items-center gap-1.5 pb-2 font-mono text-[10px] tracking-wide uppercase">
        <ListTree aria-hidden className="size-3.5" />
        outline
      </p>
      {/* The library's own dot and gap are sized for an event log of a few
          entries; an outline is a dense column of twenty, so both are dialled
          down here rather than in the component. */}
      <Timeline
        style={
          {
            "--timeline-dot-size": "0.5rem",
            "--timeline-gap": "0.375rem",
            "--timeline-column-gap": "0.5rem",
          } as React.CSSProperties
        }
      >
        {items.map((node) => {
          const active = node.block_id === activeBlockId
          return (
            <TimelineItem key={node.block_id}>
              <TimelineIndicator
                data-status={active ? "current" : "upcoming"}
              />
              <TimelineConnector />
              <TimelineContent>
                <button
                  type="button"
                  onClick={() => onNavigate(node.block_id)}
                  style={{
                    paddingLeft: `${Math.max(0, node.level - 1) * LEVEL_INDENT_PX}px`,
                  }}
                  className={`hover:bg-muted/60 focus-visible:ring-primary/40 block w-full truncate rounded-sm py-0.5 pr-1.5 text-left text-sm transition-colors focus-visible:ring-2 focus-visible:outline-none ${
                    active
                      ? "text-foreground font-medium"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                  title={node.text}
                >
                  {node.text}
                </button>
              </TimelineContent>
            </TimelineItem>
          )
        })}
      </Timeline>
    </nav>
  )
}
