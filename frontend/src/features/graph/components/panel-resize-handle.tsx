import { useCallback, useEffect, useRef } from "react"
import { GripVertical } from "lucide-react"
import { cn } from "darkraise-ui/lib"

export interface PanelResizeHandleProps {
  /** Current panel width, px. */
  width: number
  /** Live width during a drag; commit happens on release. */
  onResize: (width: number) => void
  onCommit: (width: number) => void
  /** Maps a pointer position to a width, both floors already applied. */
  widthAt: (clientX: number) => number
  /** How far one arrow-key press moves the edge, px. */
  step?: number
  min: number
  max: number
}

const DEFAULT_STEP = 24

/**
 * The drag edge between the canvas and the detail panel.
 *
 * Local rather than `darkraise-ui`'s `ResizableHandle` for the reason recorded
 * in `lib/panel-resize.ts`: that handle only drives a percentage group, and the
 * group cannot reopen a panel at a remembered width. The affordances are
 * modelled on it — a 1px rule with a widened hit area, a grip, arrow keys and a
 * separator role — so the two read the same to anyone using both.
 */
export function PanelResizeHandle({
  width,
  onResize,
  onCommit,
  widthAt,
  step = DEFAULT_STEP,
  min,
  max,
}: PanelResizeHandleProps) {
  const draggingRef = useRef(false)
  // A plain click is a pointerdown/pointerup with no pointermove between
  // them; committing on that would rewrite the stored width to whatever the
  // last clamp happened to produce, even though the user never dragged.
  const movedRef = useRef(false)
  const latestRef = useRef(width)
  latestRef.current = width

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      event.preventDefault()
      draggingRef.current = true
      movedRef.current = false
      event.currentTarget.setPointerCapture(event.pointerId)
      // The canvas swallows pointer events and the cursor would flicker back
      // to `default` the moment the drag crosses it.
      document.body.style.cursor = "col-resize"
      document.body.style.userSelect = "none"
    },
    [],
  )

  const handlePointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!draggingRef.current) return
      movedRef.current = true
      onResize(widthAt(event.clientX))
    },
    [onResize, widthAt],
  )

  const endDrag = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!draggingRef.current) return
      draggingRef.current = false
      event.currentTarget.releasePointerCapture(event.pointerId)
      document.body.style.cursor = ""
      document.body.style.userSelect = ""
      if (movedRef.current) onCommit(latestRef.current)
    },
    [onCommit],
  )

  // A drag interrupted by an unmount must not leave the page stuck in
  // col-resize with text unselectable.
  useEffect(
    () => () => {
      document.body.style.cursor = ""
      document.body.style.userSelect = ""
    },
    [],
  )

  const nudge = useCallback(
    (delta: number) => {
      const next = Math.max(min, Math.min(max, latestRef.current + delta))
      onResize(next)
      onCommit(next)
    },
    [min, max, onResize, onCommit],
  )

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize the detail panel"
      aria-valuenow={Math.round(width)}
      aria-valuemin={min}
      aria-valuemax={max}
      tabIndex={0}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onKeyDown={(event) => {
        // Left widens: the panel is on the right, so the edge moving left is
        // the panel growing.
        if (event.key === "ArrowLeft") {
          event.preventDefault()
          nudge(step)
        } else if (event.key === "ArrowRight") {
          event.preventDefault()
          nudge(-step)
        }
      }}
      className={cn(
        "bg-border hover:bg-primary/40 focus-visible:bg-primary/60",
        "relative flex w-px shrink-0 cursor-col-resize items-center justify-center",
        "transition-colors focus-visible:outline-none",
        // The rule stays 1px; the grabbable area is four times that.
        "after:absolute after:inset-y-0 after:left-1/2 after:w-2 after:-translate-x-1/2",
      )}
    >
      <div className="bg-border text-muted-foreground z-10 flex h-5 w-2.5 items-center justify-center rounded-sm border">
        <GripVertical className="h-3 w-3" aria-hidden />
      </div>
    </div>
  )
}
