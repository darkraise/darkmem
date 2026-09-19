import { useEffect, useRef, useState, type CSSProperties } from "react"
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

/** How a heading level reads on the rail.
 *
 * Level is the one fact the outline has that a flat list throws away, and
 * indentation alone does not survive truncation -- a long h3 and a long h1
 * both become an ellipsis at the same width, so the only thing left telling
 * them apart is a few pixels of left padding. So each level differs on four
 * axes at once: dot size, dot fill, type size and weight, and indent. A
 * reader scanning the rail can then tell a section from a subsection without
 * comparing two rows' left edges.
 *
 * `dot` sizes the disc INSIDE the indicator, never the indicator itself. Each
 * `TimelineItem` is its own grid whose rail column is as wide as its own
 * indicator, so sizing the indicator per level gave every level a different
 * rail width: the dots sat on four different x positions, the connectors
 * zig-zagged between them, and the text column moved by level on top of the
 * indent below -- which is what made the rail read as unaligned. The
 * indicator is one fixed box at every level now and only the disc inside it
 * changes.
 *
 * Levels past 4 are clamped rather than continuing to shrink: below `text-xs`
 * the label stops being readable, and a document nesting six deep is asking
 * the rail to render structure the pane has no width for.
 */
const LEVEL_STYLE: Record<number, { dot: string; text: string; indent: number }> = {
  1: { dot: "0.6rem", text: "text-sm font-semibold text-foreground", indent: 0 },
  2: { dot: "0.5rem", text: "text-sm font-medium text-foreground/90", indent: 8 },
  3: { dot: "0.375rem", text: "text-xs text-muted-foreground", indent: 18 },
  4: { dot: "0.25rem", text: "text-xs text-muted-foreground/80", indent: 26 },
}

/** One rail row's height, and the single number the dot and the text are both
 *  aligned to.
 *
 * The indicator is a grid item in row 1 with `align-self: start`, so its box
 * height -- not any alignment property -- is what decides where the disc
 * lands: the disc is centred in the box, so the box has to be exactly as tall
 * as the label's first line box for the two centres to coincide. It was the
 * dot's own diameter before, which parked every dot against the top of its
 * label instead of beside it. `leading-5` on the button then holds that line
 * box at one height across `text-sm` and `text-xs` alike, so a level-3 row
 * does not quietly re-break the alignment 2px the other way.
 */
const ROW_H = "1.5rem" // leading-5 (1.25rem) + the button's py-0.5, twice.

/** The reader's sticky path-and-toolbar bar, which the rail parks below.
 *  Mirrors the `top-12` the workspace pins the rail at. */
const STICKY_HEADER_PX = 48

function levelStyle(level: number) {
  return LEVEL_STYLE[Math.min(Math.max(level, 1), 4)] ?? LEVEL_STYLE[4]!
}

/** The open document's heading tree, as a timeline that follows the reader.
 *
 * A timeline rather than a scrolling list: the rail already says "these are
 * ordered positions in one document", which is what an outline claims. It
 * scrolls, but its scrollbar is hidden and never dragged -- the rail moves
 * itself, keeping the current heading near the middle as the document
 * scrolls, so the reader's position in the document and the marker's position
 * on the rail stay the same gesture. Two visible scrollbars a few pixels
 * apart, each scrolling something different, is what this replaced.
 *
 * Navigation is a callback carrying the block id, never an `#id` anchor. Two
 * readers can be mounted at once (the artifacts pane and the ledger) and block
 * ids are unique per document, not per page -- so `href="#block"` is ambiguous
 * exactly when both are open. The caller resolves it inside its own reader.
 */
export function DocumentOutline({
  documentId,
  activeBlockId = null,
  onNavigate,
}: {
  documentId: string
  /** The heading the reader is currently under. Drives both the marker and
   *  where the rail parks itself. */
  activeBlockId?: string | null
  onNavigate: (blockId: string) => void
}) {
  const outline = useDocumentOutline(documentId)
  const items = outline.data?.items ?? []
  const railRef = useRef<HTMLDivElement>(null)
  const navRef = useRef<HTMLElement>(null)
  const [railHeight, setRailHeight] = useState<number | null>(null)

  // How tall the rail may be, measured rather than guessed.
  //
  // The rail is `sticky` inside the reader's scroll viewport, so the space it
  // can occupy is that viewport's height minus the sticky header it parks
  // under. A percentage cannot express that -- a sticky element resolves
  // percentage heights against its PARENT, which here is as tall as the whole
  // document -- and the `100vh` expression this replaced overshot by whatever
  // page chrome sits above the pane, clipping the rail's last row against the
  // window edge. A viewport-derived number also survives a change to that
  // chrome, which a hand-tuned constant would not.
  useEffect(() => {
    const root = navRef.current?.closest<HTMLElement>(
      "[data-darkraise-scroll-viewport]",
    )
    if (!root) return
    const measure = () => setRailHeight(root.clientHeight - STICKY_HEADER_PX - 24)
    measure()
    if (typeof ResizeObserver === "undefined") return
    const observer = new ResizeObserver(measure)
    observer.observe(root)
    return () => observer.disconnect()
    // Keyed on the rendered list, not `[]`: the first mount returns the
    // loading skeleton, so `navRef` is null and a mount-only effect would
    // find no scroller and never look again -- leaving the rail on its CSS
    // floor and running past the bottom of the pane.
  }, [items.length])

  // Park the active row near the middle of the rail.
  //
  // Deliberately NOT `scrollIntoView`: that walks every scrollable ancestor,
  // and the nearest one here is the reader's own viewport -- so tracking the
  // document's scroll would scroll the document, which is a feedback loop.
  // Setting this one element's `scrollTop` moves the rail and nothing else.
  useEffect(() => {
    const rail = railRef.current
    if (!rail || !activeBlockId) return
    const row = rail.querySelector<HTMLElement>(
      `[data-outline-block="${activeBlockId}"]`,
    )
    if (!row) return
    const railBox = rail.getBoundingClientRect()
    const rowBox = row.getBoundingClientRect()
    const next =
      rail.scrollTop + (rowBox.top - railBox.top) - rail.clientHeight / 2 + rowBox.height / 2
    const clamped = Math.max(0, Math.min(next, rail.scrollHeight - rail.clientHeight))
    // A no-op guard: a heading change can arrive while the rail is already
    // where it belongs (a short section passing under the line), and
    // re-issuing a scroll there reads as a twitch.
    if (Math.abs(clamped - rail.scrollTop) < 2) return
    // Instant, NOT smooth. This is a follower, and the scrollspy fires on
    // every heading the document passes -- a fast scroll crosses dozens.
    // Each one restarts a smooth animation toward a target that has already
    // moved, so the rail falls further behind the further you scroll and
    // settles where the reader was seconds ago. Measured: a scroll to the end
    // of a 24-section document left the rail nine sections short with nothing
    // marked on screen. Tracking 1:1 is what makes it read as attached to the
    // document.
    rail.scrollTo({ top: clamped, behavior: "auto" })
  }, [activeBlockId, items.length])

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
    <nav
      ref={navRef}
      aria-label="document outline"
      className="flex min-h-0 flex-col"
      // The measured cap wins once it exists; the class on the `aside` is the
      // floor that keeps the rail bounded on the first paint and anywhere
      // ResizeObserver is missing.
      style={railHeight !== null ? { maxHeight: `${railHeight}px` } : undefined}
    >
      <p className="text-muted-foreground flex shrink-0 items-center gap-1.5 pb-2 font-mono text-[10px] tracking-wide uppercase">
        <ListTree aria-hidden className="size-3.5" />
        outline
      </p>
      {/* The scroller. Its bar is hidden on every engine rather than styled:
          the rail is driven by the document's own scroll and by clicks, so a
          bar here would be a control that never needs using, sitting beside
          the reader's bar that does. */}
      <div
        ref={railRef}
        className="min-h-0 flex-1 overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {/* The library's own dot and gap are sized for an event log of a few
            entries; an outline is a dense column of twenty, so both are
            dialled down here rather than in the component. The dot size is
            re-set per item, by level. */}
        <Timeline
          style={
            {
              "--timeline-gap": "0.375rem",
              "--timeline-column-gap": "0.5rem",
              // The rail column's width, fixed for every level so the dots
              // and the connectors form one straight line and the text
              // column starts at the same x on every row.
              "--timeline-dot-size": "0.625rem",
            } as CSSProperties
          }
        >
          {items.map((node) => {
            const active = node.block_id === activeBlockId
            const style = levelStyle(node.level)
            return (
              <TimelineItem key={node.block_id}>
                {/* Spans BOTH grid rows and hangs half a row below its own,
                    so the line runs dot-centre to dot-centre unbroken. The
                    library's connector starts under the indicator, which is
                    continuous only while the dot fills the whole row -- once
                    the dot is centred beside its label, that leaves a gap
                    above and below every marker. Drawn before the indicator
                    so the dot paints over it. */}
                <TimelineConnector
                  className="[grid-row:1_/_3]"
                  style={{
                    marginTop: `calc(${ROW_H} / 2)`,
                    marginBottom: `calc(${ROW_H} / -2)`,
                  }}
                />
                <TimelineIndicator
                  data-status={active ? "current" : "upcoming"}
                  className="relative z-10 rounded-none border-0 bg-transparent shadow-none"
                  style={{ height: ROW_H }}
                >
                  <span
                    aria-hidden
                    className={`rounded-full transition-colors ${
                      active
                        ? "bg-primary ring-primary/25 ring-2"
                        : "bg-muted-foreground/40"
                    }`}
                    style={{ width: style.dot, height: style.dot }}
                  />
                </TimelineIndicator>
                <TimelineContent>
                  <button
                    type="button"
                    data-outline-block={node.block_id}
                    onClick={() => onNavigate(node.block_id)}
                    style={{ paddingLeft: `${style.indent}px` }}
                    className={`hover:bg-muted/60 focus-visible:ring-primary/40 block w-full cursor-pointer truncate rounded-sm py-0.5 pr-1.5 text-left leading-5 transition-colors focus-visible:ring-2 focus-visible:outline-none ${
                      active
                        ? "text-primary-text text-sm font-semibold"
                        : `${style.text} hover:text-foreground`
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
      </div>
    </nav>
  )
}
