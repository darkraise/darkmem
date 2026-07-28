import type { VerificationStatus } from "@/components/darkmem"
import { dayBucket } from "@/demo/activity"
import { DEMO } from "@/lib/demo-flag"
import { useDemoDayBuckets } from "@/demo/hooks"
import type { DemoDayEvent } from "@/demo/types"
import { useEvents, type EventLogEntry } from "@/hooks/api"

/** The one row shape DayTab renders, whichever source fed it. `transition`
 *  stays optional — only the demo fixture models a from→to rung pair
 *  today; the real payload does not carry one for every event_type. */
export interface DayRowData {
  id: string
  timeLabel: string
  type: string
  linkLabel: string
  note?: string
  badge?: VerificationStatus
  transition?: { from: VerificationStatus; to: VerificationStatus; toLabel?: string }
}

function fromDemo(event: DemoDayEvent, index: number): DayRowData {
  return {
    id: `${event.time_label}-${index}`,
    timeLabel: event.time_label,
    type: event.type,
    linkLabel: event.link_label,
    note: event.note ?? event.inject_detail?.join(" · "),
    badge: event.badge,
    transition: event.transition
      ? {
          from: event.transition.from,
          to: event.transition.to,
          toLabel: event.transition.to_label,
        }
      : undefined,
  }
}

function shortId(id: string | null): string {
  return id ? id.slice(0, 8) : ""
}

function utcTimeLabel(iso: string): string {
  return `${iso.slice(11, 16)} UTC`
}

function fromEventLog(entry: EventLogEntry): DayRowData {
  const linkLabel = [
    entry.object_type,
    shortId(entry.object_id),
    entry.project ? `· project ${entry.project}` : null,
  ]
    .filter(Boolean)
    .join(" ")
  return {
    id: String(entry.id),
    timeLabel: utcTimeLabel(entry.created_at),
    type: entry.event_type,
    linkLabel: linkLabel || entry.event_type,
    badge: entry.event_type === "superseded" ? "superseded" : undefined,
  }
}

/** UTC day-bucket boundaries for `since`/`until`, matching `ix_events_day`'s
 *  immutable `(created_at AT TIME ZONE 'UTC')::date` cast — never re-bucket
 *  to local time client-side (doc 04 §8.1, T1.08's fix). */
function utcDayWindow(day: string): { since: string; until: string } {
  const start = new Date(`${day}T00:00:00.000Z`)
  const end = new Date(start.getTime() + 86_400_000)
  return { since: start.toISOString(), until: end.toISOString() }
}

const DAY_EVENT_LIMIT = 200

/**
 * `DEMO ? demo : real` for one UTC day-bucket, following
 * `use-contribution-calendar.ts`. The real branch reads `/events` windowed
 * to that UTC day (`since`/`until`) — the endpoint has no per-day route, so
 * this is the list endpoint with a day-sized window, still zero
 * client-side aggregation: `total` comes from the server, never a count of
 * `items.length` after a truncated page.
 */
export function useDayEvents(day: string): {
  /** null = no bucket for this day (demo) or nothing fetched yet (real, not loading/error) */
  events: DayRowData[] | null
  total: number
  isLoading: boolean
  isError: boolean
  truncated: boolean
} {
  const demoBuckets = useDemoDayBuckets()
  const demoBucket = dayBucket(demoBuckets, day)
  const window = utcDayWindow(day)
  const query = useEvents(
    { since: window.since, until: window.until, limit: DAY_EVENT_LIMIT },
    { enabled: !DEMO },
  )

  if (DEMO) {
    return {
      events: demoBucket ? demoBucket.events.map(fromDemo) : null,
      total: demoBucket?.events.length ?? 0,
      isLoading: false,
      isError: false,
      truncated: false,
    }
  }

  if (!query.data) {
    return {
      events: null,
      total: 0,
      isLoading: query.isLoading,
      isError: query.isError,
      truncated: false,
    }
  }
  return {
    events: query.data.items.map(fromEventLog),
    total: query.data.total,
    isLoading: false,
    isError: false,
    truncated: query.data.total > query.data.items.length,
  }
}
