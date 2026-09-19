import { useMemo } from "react"
import { useNavigate } from "@tanstack/react-router"
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
          {day.injects} inject{day.injects === 1 ? "" : "s"} — see the day
          timeline for what was pushed
        </p>
      )}
      {day.count > 0 && (
        <p className="text-muted-foreground text-xs">
          click to open this day on the Memories timeline
        </p>
      )}
    </div>
  )
}

/**
 * GitHub-style year heatmap: 53 Monday-first week columns up to today, month
 * labels across the top, Mon/Wed/Fri down the left. Cell click jumps to that
 * day on the Memories timeline via the `date` search param.
 */
export function YearHeatmap({ days }: { days: ContributionDay[] }) {
  const navigate = useNavigate()
  const weeks = useMemo(() => buildHeatmapWeeks(days), [days])
  const thresholds = useMemo(() => intensityThresholds(days), [days])
  const todayKey = localDayKey(new Date())

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <div
          aria-hidden
          className="text-muted-foreground flex shrink-0 flex-col gap-1 pt-5"
        >
          {WEEKDAY_LABELS.map((label, i) => (
            <span key={i} className="flex h-3 items-center text-xs">
              {label}
            </span>
          ))}
        </div>
        <div className="min-w-0 overflow-x-auto pb-1">
          <div className="w-max">
            <div aria-hidden className="mb-1 flex gap-1">
              {weeks.map((week, i) => (
                <div key={i} className="relative h-4 w-3">
                  {week.monthLabel && (
                    <span className="text-muted-foreground absolute left-0 text-xs whitespace-nowrap">
                      {week.monthLabel}
                    </span>
                  )}
                </div>
              ))}
            </div>
            <div className="flex gap-1">
              {weeks.map((week, wi) => (
                <div key={wi} className="flex flex-col gap-1">
                  {week.days.map((day, di) =>
                    day ? (
                      <HoverCard key={day.date} openDelay={120} closeDelay={40}>
                        <HoverCardTrigger asChild>
                          <button
                            type="button"
                            // The inject count rides the label rather than a
                            // colour alone: a coloured dot nobody can read out
                            // is not a surface a human can check push against.
                            aria-label={`${formatDayKey(day.date)} — ${day.count} memor${day.count === 1 ? "y" : "ies"}${day.injects > 0 ? `, ${day.injects} inject${day.injects === 1 ? "" : "s"}` : ""}`}
                            onClick={() =>
                              navigate({
                                to: "/memories",
                                search: { date: day.date },
                              })
                            }
                            className={cn(
                              CELL,
                              intensityClass(day.count, thresholds),
                              "hover:ring-ring focus-visible:ring-ring outline-none hover:ring-1 focus-visible:ring-1",
                              day.date === todayKey &&
                                "ring-primary/60 ring-1",
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
                    ) : (
                      <span key={di} aria-hidden className={cn(CELL, "invisible")} />
                    ),
                  )}
                </div>
              ))}
            </div>
          </div>
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
