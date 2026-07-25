import { Link } from "@tanstack/react-router"
import {
  ArrowRight,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  Circle,
  Clock,
  Link2,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { VerificationBadge } from "@/components/darkmem"
import { dayBucket, shiftDay } from "@/demo/activity"
import { useDemoDayBuckets } from "@/demo/hooks"
import type { DemoDayEvent } from "@/demo/types"
import { SurfaceStateChip } from "./module-surface"

function DayEventRow({ event }: { event: DemoDayEvent }) {
  return (
    <div className="border-border flex flex-wrap items-start gap-2.5 border-t border-dashed py-2.5 first:border-t-0 first:pt-0">
      <span className="text-muted-foreground w-20 shrink-0 pt-0.5 font-mono text-sm whitespace-nowrap">
        {event.time_label}
      </span>
      <span className="border-border bg-muted text-muted-foreground inline-flex shrink-0 items-center gap-1 rounded-sm border px-2 py-0.5 font-mono text-sm whitespace-nowrap">
        <Circle aria-hidden className="h-2 w-2" />
        {event.type}
      </span>
      <div className="flex min-w-0 flex-1 basis-72 flex-col gap-1.5">
        <span className="flex items-start gap-1.5 text-sm">
          <Link2
            aria-hidden
            className="text-muted-foreground mt-0.5 h-3.5 w-3.5 shrink-0"
          />
          {event.link_label}
        </span>
        {/* The from→to rung pair — only for verification transitions,
            never for a plain lifecycle event. */}
        {event.transition && (
          <span className="inline-flex flex-wrap items-center gap-2">
            <VerificationBadge status={event.transition.from} />
            <ArrowRight
              aria-hidden
              className="text-muted-foreground h-3.5 w-3.5"
            />
            <VerificationBadge
              status={event.transition.to}
              label={event.transition.to_label}
            />
          </span>
        )}
        {event.badge && <VerificationBadge status={event.badge} />}
        {event.inject_detail && (
          <span className="text-muted-foreground flex flex-wrap gap-3 font-mono text-sm">
            {event.inject_detail.map((d) => (
              <span key={d}>{d}</span>
            ))}
          </span>
        )}
        {event.note && (
          <span className="text-muted-foreground text-sm">{event.note}</span>
        )}
      </div>
    </div>
  )
}

export function DayTab({
  day,
  onDayChange,
}: {
  day: string
  onDayChange: (day: string) => void
}) {
  const buckets = useDemoDayBuckets()
  const bucket = dayBucket(buckets, day)

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-4xl text-sm">
        A calendar-day drill into that UTC day-bucket's slice of the durable
        events substrate — the same event-row component the per-object timeline
        renders, with the from→to rung pair reserved for genuine verification
        transitions.
      </p>
      <div className="border-border flex flex-wrap items-center gap-2.5 border-b border-dashed pb-2.5">
        <Button size="sm" variant="ghost" asChild>
          <Link to="/">
            <ChevronLeft className="mr-1 size-3.5" />
            Activity calendar
          </Link>
        </Button>
        <span className="border-border bg-muted rounded-sm border px-2.5 py-1 font-mono text-sm">
          /activity · day {day}
        </span>
        <SurfaceStateChip state={bucket ? "populated" : "empty"} />
        <div className="ml-auto flex items-center gap-1.5">
          <Button
            size="sm"
            variant="outline"
            onClick={() => onDayChange(shiftDay(day, -1))}
          >
            <ChevronLeft className="mr-1 size-3.5" />
            {shiftDay(day, -1)}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onDayChange(shiftDay(day, 1))}
          >
            {shiftDay(day, 1)}
            <ChevronRight className="ml-1 size-3.5" />
          </Button>
        </div>
        <span className="text-muted-foreground flex basis-full items-center gap-1.5 text-sm">
          <Clock aria-hidden className="h-3.5 w-3.5 shrink-0" />
          <span>
            <b className="text-foreground font-semibold">Days are UTC</b> —
            this list is the UTC calendar date, not your local one.
          </span>
        </span>
      </div>
      {bucket ? (
        <div className="flex flex-col">
          {bucket.events.map((event, i) => (
            <DayEventRow key={`${event.time_label}-${i}`} event={event} />
          ))}
        </div>
      ) : (
        // Honest empty: names the UTC bucket it checked; a quiet day is an
        // ordinary outcome, not a blank.
        <EmptyState
          icon={<CalendarDays aria-hidden className="h-6 w-6" />}
          title="No activity on this day"
          description={`No events rows fall in the UTC bucket for ${day} — nothing was created, verified, injected, or synced in this project on that date. The bucket boundary is the UTC calendar date, so a late-night local capture may land on the neighbouring day here.`}
        />
      )}
    </div>
  )
}
