import { useRef, useState } from "react"
import { cn } from "darkraise-ui/lib"
import { dayKeyToMs, formatDayKey, localDayKey } from "@/lib/format"
import { fractionToDayKey, type TimelineScale } from "@/lib/timeline"

const DAY_MS = 86_400_000

/**
 * Immich-style vertical time scrubber: a thin linear time axis (newest at
 * the top), month/year ticks, per-day density markers, and a draggable
 * position indicator. It never lists memory content — it is a line of time.
 */
export function TimelineScrubber({
  scale,
  position,
  onSeek,
  className,
}: {
  scale: TimelineScale
  /** 0 = newest (top) … 1 = oldest (bottom) — tracks the results scroll. */
  position: number
  onSeek: (dayKey: string) => void
  className?: string
}) {
  const railRef = useRef<HTMLDivElement | null>(null)
  const [dragFraction, setDragFraction] = useState<number | null>(null)
  const [hoverFraction, setHoverFraction] = useState<number | null>(null)

  const fractionAt = (clientY: number): number => {
    const rect = railRef.current?.getBoundingClientRect()
    if (!rect || rect.height === 0) return 0
    return Math.min(1, Math.max(0, (clientY - rect.top) / rect.height))
  }

  const displayed = dragFraction ?? position
  const bubbleFraction = dragFraction ?? hoverFraction
  const bubbleLabel =
    bubbleFraction != null
      ? formatDayKey(fractionToDayKey(scale, bubbleFraction))
      : null

  const seekByDays = (deltaDays: number) => {
    const currentMs = dayKeyToMs(fractionToDayKey(scale, displayed))
    const nextMs = Math.min(
      scale.newestMs,
      Math.max(scale.oldestMs, currentMs + deltaDays * DAY_MS),
    )
    onSeek(localDayKey(new Date(nextMs)))
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case "ArrowUp":
      case "ArrowRight":
        seekByDays(1)
        break
      case "ArrowDown":
      case "ArrowLeft":
        seekByDays(-1)
        break
      case "PageUp":
        seekByDays(30)
        break
      case "PageDown":
        seekByDays(-30)
        break
      case "Home":
        onSeek(fractionToDayKey(scale, 0))
        break
      case "End":
        onSeek(fractionToDayKey(scale, 1))
        break
      default:
        return
    }
    e.preventDefault()
  }

  return (
    <div
      ref={railRef}
      className={cn(
        "relative h-full w-full cursor-pointer touch-none select-none",
        className,
      )}
      onPointerDown={(e) => {
        try {
          e.currentTarget.setPointerCapture(e.pointerId)
        } catch {
          // Untracked pointer (synthetic events) — dragging still works,
          // it just loses capture outside the rail.
        }
        setDragFraction(fractionAt(e.clientY))
      }}
      onPointerMove={(e) => {
        if (dragFraction != null) setDragFraction(fractionAt(e.clientY))
        else setHoverFraction(fractionAt(e.clientY))
      }}
      onPointerUp={(e) => {
        if (dragFraction == null) return
        const f = fractionAt(e.clientY)
        setDragFraction(null)
        setHoverFraction(null)
        onSeek(fractionToDayKey(scale, f))
      }}
      onPointerCancel={() => setDragFraction(null)}
      onPointerLeave={() => setHoverFraction(null)}
    >
      {/* the axis */}
      <div aria-hidden className="bg-border absolute top-0 bottom-0 right-2 w-px" />

      {/* month / year ticks */}
      {scale.months.map((m) => (
        <div key={m.key} aria-hidden>
          <div
            className={cn(
              "absolute right-1 h-px w-3",
              m.isYear ? "bg-muted-foreground/70" : "bg-muted-foreground/35",
            )}
            style={{ top: `${m.fraction * 100}%` }}
          />
          <span
            className={cn(
              "absolute right-6 -translate-y-1/2 font-mono text-[10px]",
              m.isYear
                ? "text-foreground/80 font-semibold"
                : "text-muted-foreground",
            )}
            style={{ top: `${m.fraction * 100}%` }}
          >
            {m.label}
          </span>
        </div>
      ))}

      {/* per-day density markers — where memories exist, not what they say */}
      {scale.days.map((d) => (
        <div
          key={d.key}
          aria-hidden
          className="bg-primary absolute right-[3px] h-[2px] w-[11px] -translate-y-1/2 rounded-full"
          style={{
            top: `${d.fraction * 100}%`,
            opacity: 0.25 + 0.65 * (d.count / Math.max(1, scale.maxDayCount)),
          }}
        />
      ))}

      {/* hover ghost line */}
      {hoverFraction != null && dragFraction == null && (
        <div
          aria-hidden
          className="bg-foreground/25 absolute inset-x-0 h-px"
          style={{ top: `${hoverFraction * 100}%` }}
        />
      )}

      {/* position indicator — draggable, keyboard-operable */}
      <div
        role="slider"
        tabIndex={0}
        aria-label="Timeline position"
        aria-orientation="vertical"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round((1 - displayed) * 100)}
        aria-valuetext={formatDayKey(fractionToDayKey(scale, displayed))}
        onKeyDown={onKeyDown}
        className="focus-visible:ring-ring absolute inset-x-0 -translate-y-1/2 rounded-sm py-1 outline-none focus-visible:ring-1"
        style={{ top: `${displayed * 100}%` }}
      >
        <div className="bg-primary h-[2px] w-full rounded-full" />
        <div className="bg-primary border-background absolute top-1/2 right-[5px] h-2 w-2 -translate-y-1/2 rounded-full border" />
      </div>

      {/* date bubble while dragging or hovering */}
      {bubbleFraction != null && bubbleLabel && (
        <span
          className="border-border bg-popover text-popover-foreground absolute left-full z-10 ml-2 -translate-y-1/2 rounded border px-2 py-0.5 font-mono text-[10px] whitespace-nowrap shadow-md"
          style={{ top: `${bubbleFraction * 100}%` }}
        >
          {bubbleLabel}
        </span>
      )}
    </div>
  )
}
