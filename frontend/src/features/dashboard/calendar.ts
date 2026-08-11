import type { ContributionDay } from "@/features/dashboard/types"
import type { CalendarBucket } from "@/hooks/api"

const DAY_MS = 86_400_000
const YEAR_DAYS = 364

/** UTC calendar day key, YYYY-MM-DD — matches ix_events_day's bucket unit. */
export function utcDayKey(d: Date): string {
  const y = d.getUTCFullYear()
  const m = String(d.getUTCMonth() + 1).padStart(2, "0")
  const day = String(d.getUTCDate()).padStart(2, "0")
  return `${y}-${m}-${day}`
}

export interface CalendarWindow {
  start: Date
  end: Date
  since: string
  until: string
}

/**
 * The Monday on/before (today − 52 weeks) through today, in UTC — the same
 * window shape the demo heatmap used, but anchored to UTC days so it lines
 * up with the server's `(created_at AT TIME ZONE 'UTC')::date` bucket.
 */
export function calendarWindow(now = Date.now()): CalendarWindow {
  const end = new Date(now)
  end.setUTCHours(0, 0, 0, 0)
  const start = new Date(end.getTime() - YEAR_DAYS * DAY_MS)
  start.setUTCDate(start.getUTCDate() - ((start.getUTCDay() + 6) % 7))
  return {
    start,
    end,
    since: start.toISOString(),
    until: new Date(now).toISOString(),
  }
}

/**
 * Zero-fill the sparse `/events/calendar` buckets — the endpoint's GROUP BY
 * only emits days with at least one event — into one entry per day across
 * the window, so the heatmap's Monday-first chunking never sees a gap.
 * `types`/`verified` stay empty: the calendar endpoint carries no per-type
 * or per-verification breakdown, and rendering fabricated non-zero values
 * would misrepresent real data as richer than it is.
 */
export function fillCalendarDays(
  buckets: CalendarBucket[],
  now = Date.now(),
  injectBuckets: CalendarBucket[] = [],
): ContributionDay[] {
  const { start, end } = calendarWindow(now)
  const byDay = new Map(buckets.map((b) => [b.day, b.count]))
  // A second server-side series over the same buckets, never a share of the
  // first: `count` is every event that day, and subtracting or slicing it
  // would be inventing a breakdown the endpoint does not return.
  const injectsByDay = new Map(injectBuckets.map((b) => [b.day, b.count]))
  const days: ContributionDay[] = []
  const cursor = new Date(start)
  while (cursor.getTime() <= end.getTime()) {
    const key = utcDayKey(cursor)
    days.push({
      date: key,
      count: byDay.get(key) ?? 0,
      types: [],
      verified: 0,
      injects: injectsByDay.get(key) ?? 0,
    })
    cursor.setUTCDate(cursor.getUTCDate() + 1)
  }
  return days
}
