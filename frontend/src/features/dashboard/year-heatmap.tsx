import { Fragment, useMemo, useRef, useState } from "react"
import type { KeyboardEvent } from "react"
import { Link, useNavigate } from "@tanstack/react-router"
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "darkraise-ui/components/hover-card"
import { cn } from "darkraise-ui/lib"
import type { ContributionDay } from "@/features/dashboard/types"
import { formatDayKey, localDayKey } from "@/lib/format"
import {
  buildHeatmapWeeks,
  intensityClass,
  intensityThresholds,
} from "./heatmap"
import { DEMO } from "@/lib/demo-flag"

const CELL = "h-3 w-3 rounded-sm"
const WEEKDAY_LABELS = ["Mon", "", "Wed", "", "Fri", "", ""] as const

function CellPopover({ day }: { day: ContributionDay }) {
  return (
    <div className="space-y-1.5">
      <p className="text-sm font-semibold">{formatDayKey(day.date)}</p>
      <p className="text-muted-foreground text-sm">
        {day.count === 0
          ? "no memories captured"
          : `${day.count} memor${day.count === 1 ? "y" : "ies"} captured`}
      </p>
      {day.types.length > 0 && (
        <ul className="space-y-0.5">
          {day.types.slice(0, 4).map((t) => (
            <li
              key={t.label}
              className="text-muted-foreground flex items-center justify-between gap-3 text-sm"
            >
              <span>{t.label}</span>
              <span className="font-mono">{t.count}</span>
            </li>
          ))}
        </ul>
      )}
      {day.verified > 0 && (
        <p className="text-success-text text-sm">{day.verified} verified</p>
      )}
      {day.injects > 0 && (
        <p className="text-info-text text-sm">
          {day.injects} inject{day.injects === 1 ? "" : "s"}
        </p>
      )}
      {DEMO ? (
        <>
          {day.count > 0 && (
            <p className="text-muted-foreground text-xs">
              click to open this day on the Memories timeline
            </p>
          )}
          {/* The Day drill's "Dashboard" link lands here; this is the way back. */}
          <Link
            to="/activity"
            search={{ tab: "day", day: day.date }}
            className="text-primary-text inline-block text-xs underline-offset-2 hover:underline"
          >
            Open in Activity › Day drill
          </Link>
        </>
      ) : (
        <p className="text-muted-foreground text-xs">
          click to open this day in Activity › Day drill
        </p>
      )}
    </div>
  )
}

/**
 * GitHub-style year heatmap: 53 Monday-first week columns up to today, month
 * labels across the top, Mon/Wed/Fri down the left. Cell click opens that day:
 * on the demo's Memories timeline (`date` search param), or in Activity's Day
 * drill on a real instance.
 */
export function YearHeatmap({ days }: { days: ContributionDay[] }) {
  const navigate = useNavigate()
  const weeks = useMemo(() => buildHeatmapWeeks(days), [days])
  const thresholds = useMemo(() => intensityThresholds(days), [days])
  const todayKey = localDayKey(new Date())

  // Roving tabindex: the 365 cells are one tab stop, and the arrow keys walk
  // the grid (left/right a week, up/down a day, Home/End the ends), so a
  // keyboard user is not made to press Tab once per day to get past it.
  const indexByDate = useMemo(
    () => new Map(days.map((d, i) => [d.date, i])),
    [days],
  )
  const [activeDate, setActiveDate] = useState<string | null>(null)
  const cellRefs = useRef(new Map<string, HTMLButtonElement>())
  const fallbackDate =
    (indexByDate.has(todayKey) ? todayKey : days[days.length - 1]?.date) ?? null
  const focusDate =
    activeDate && indexByDate.has(activeDate) ? activeDate : fallbackDate

  const onGridKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const from = focusDate ? indexByDate.get(focusDate) : undefined
    if (from === undefined) return
    const step: Record<string, number> = {
      ArrowLeft: -7,
      ArrowRight: 7,
      ArrowUp: -1,
      ArrowDown: 1,
    }
    let to: number
    if (e.key in step) to = from + (step[e.key] ?? 0)
    else if (e.key === "Home") to = 0
    else if (e.key === "End") to = days.length - 1
    else return
    e.preventDefault()
    const target = days[Math.max(0, Math.min(days.length - 1, to))]
    if (!target) return
    setActiveDate(target.date)
    cellRefs.current.get(target.date)?.focus()
  }

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto p-px pb-1">
        {/* One grid: a label column, then one fluid column per week, so the
            cells take the card's width instead of a fixed 12px. From `sm` up
            a cell may shrink below 10px: 53 columns at 10px plus gaps are
            wider than the card at common laptop widths, and the overflow cut
            the newest weeks off the right edge. Below `sm` the grid keeps its
            floor and scrolls instead. */}
        <div
          data-testid="heatmap-grid"
          role="group"
          aria-label="Contribution calendar. Arrow keys move between days; Enter opens a day."
          onKeyDown={onGridKeyDown}
          className="grid min-w-max gap-[3px] [--cell-min:10px] sm:min-w-0 sm:[--cell-min:0px] xl:gap-1"
          style={{
            gridTemplateColumns: `auto repeat(${weeks.length}, minmax(var(--cell-min), 1fr))`,
          }}
        >
          <span aria-hidden />
          {weeks.map((week, i) => (
            <span
              key={`month-${i}`}
              aria-hidden
              className="text-muted-foreground relative h-4 text-xs whitespace-nowrap"
            >
              {week.monthLabel && (
                <span className="absolute left-0">{week.monthLabel}</span>
              )}
            </span>
          ))}
          {WEEKDAY_LABELS.map((label, di) => (
            <Fragment key={`row-${di}`}>
              <span
                aria-hidden
                // Zero-height so a label row is exactly as tall as a cell
                // row; the text overflows into the unlabelled rows beside it.
                className="text-muted-foreground flex h-0 items-center self-center pr-1 text-xs"
              >
                {label}
              </span>
              {weeks.map((week, wi) => {
                const day = week.days[di]
                if (!day) {
                  return (
                    <span
                      key={`empty-${wi}`}
                      aria-hidden
                      className="aspect-square w-full"
                    />
                  )
                }
                return (
                  <HoverCard key={day.date} openDelay={120} closeDelay={40}>
                    <HoverCardTrigger asChild>
                      <button
                        type="button"
                        ref={(el) => {
                          if (el) cellRefs.current.set(day.date, el)
                          else cellRefs.current.delete(day.date)
                        }}
                        tabIndex={day.date === focusDate ? 0 : -1}
                        onFocus={() => setActiveDate(day.date)}
                        // The inject count rides the label rather than a
                        // colour alone: a coloured dot nobody can read out
                        // is not a surface a human can check push against.
                        aria-label={`${formatDayKey(day.date)} — ${day.count} memor${day.count === 1 ? "y" : "ies"}${day.injects > 0 ? `, ${day.injects} inject${day.injects === 1 ? "" : "s"}` : ""}`}
                        onClick={() =>
                          // The real Memories page has no timeline to land
                          // a date on (only the demo's does), so a day opens
                          // where one day's activity is listed.
                          DEMO
                            ? navigate({
                                to: "/memories",
                                search: { date: day.date },
                              })
                            : navigate({
                                to: "/activity",
                                search: { tab: "day", day: day.date },
                              })
                        }
                        className={cn(
                          "aspect-square w-full rounded-sm",
                          intensityClass(day.count, thresholds),
                          "hover:ring-ring focus-visible:ring-ring outline-none hover:ring-1 focus-visible:ring-1",
                          day.date === todayKey && "ring-primary/60 ring-1",
                          day.injects > 0 &&
                            "ring-info/70 ring-1 ring-offset-0",
                        )}
                      />
                    </HoverCardTrigger>
                    <HoverCardContent
                      side="top"
                      className="w-60 p-3"
                      collisionPadding={12}
                    >
                      <CellPopover day={day} />
                    </HoverCardContent>
                  </HoverCard>
                )
              })}
            </Fragment>
          ))}
        </div>
      </div>
      <div className="text-muted-foreground flex items-center gap-1.5 text-sm">
        <span>Less</span>
        {[
          "bg-muted",
          "bg-primary/25",
          "bg-primary/50",
          "bg-primary/75",
          "bg-primary",
        ].map((cls) => (
          <span key={cls} className={cn(CELL, cls)} />
        ))}
        <span>More</span>
      </div>
    </div>
  )
}
