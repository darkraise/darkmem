import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import type { ContributionDay } from "@/features/dashboard/types"
import { YearHeatmap } from "./year-heatmap"

export interface CalendarCardProps {
  days: ContributionDay[]
  isLoading: boolean
  isError: boolean
}

/**
 * Honesty invariant (runbook §7 / Ruling 2): loading, error and a genuinely
 * quiet window must never render as the same thing. A failed load shows an
 * explicit message, a load-in-flight shows a skeleton, and only a
 * successfully-loaded, truly empty window renders the all-muted grid — with
 * a caption, so it never reads as a broken widget.
 */
export function CalendarCard({ days, isLoading, isError }: CalendarCardProps) {
  const hasActivity = days.some((d) => d.count > 0)

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-muted-foreground text-sm font-medium tracking-wider uppercase">
          Contribution Calendar
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isError ? (
          <p className="text-destructive text-sm">
            Couldn&apos;t load the contribution calendar. Try reloading the
            page.
          </p>
        ) : isLoading ? (
          <div
            role="status"
            aria-label="Loading contribution calendar"
            className="bg-muted h-32 animate-pulse rounded"
          />
        ) : (
          <div className="space-y-2">
            <YearHeatmap days={days} />
            {!hasActivity && (
              <p className="text-muted-foreground text-sm">
                No memory activity recorded yet — this calendar fills in as
                you capture memories.
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
