import { localDayKey } from "./format"

const DAY_MS = 86_400_000

export interface TimelineMonthTick {
  /** YYYY-MM — stable React key. */
  key: string
  /** "Jul" for a plain month, the year ("2026") at each January boundary. */
  label: string
  isYear: boolean
  /** 0 = top of the axis (newest) … 1 = bottom (oldest). */
  fraction: number
}

export interface TimelineDayMarker {
  /** Local calendar day, YYYY-MM-DD. */
  key: string
  fraction: number
  count: number
}

export interface TimelineScale {
  /** Newest memory timestamp (top of the axis). */
  newestMs: number
  /** Oldest memory timestamp (bottom of the axis). */
  oldestMs: number
  /** Always ≥ one day so fractions stay finite. */
  spanMs: number
  /** Month boundaries, newest first. */
  months: TimelineMonthTick[]
  /** One marker per day that holds memories — density, not content. */
  days: TimelineDayMarker[]
  maxDayCount: number
}

function clamp01(f: number): number {
  return Math.min(1, Math.max(0, f))
}

/**
 * Build the vertical time-scale model for a scrubber: a linear time axis
 * from the newest row (top) to the oldest (bottom), month ticks, and
 * per-day density markers. Returns null when there is nothing to scale.
 *
 * `getTimestamp` lets a surface key on its own time column — memories date
 * from `created_at`, facts from `as_of`.
 */
export function buildTimelineScale<T extends object>(
  rows: T[],
  getTimestamp: (row: T) => string = (row) =>
    (row as { created_at: string }).created_at,
): TimelineScale | null {
  if (rows.length === 0) return null

  let newestMs = -Infinity
  let oldestMs = Infinity
  const counts = new Map<string, { ms: number; count: number }>()
  for (const row of rows) {
    const t = Date.parse(getTimestamp(row))
    if (Number.isNaN(t)) continue
    if (t > newestMs) newestMs = t
    if (t < oldestMs) oldestMs = t
    const key = localDayKey(new Date(t))
    const entry = counts.get(key)
    if (entry) {
      entry.count += 1
      if (t < entry.ms) entry.ms = t
    } else {
      counts.set(key, { ms: t, count: 1 })
    }
  }
  if (!Number.isFinite(newestMs)) return null

  const spanMs = Math.max(newestMs - oldestMs, DAY_MS)
  const fraction = (t: number) => clamp01((newestMs - t) / spanMs)

  const days: TimelineDayMarker[] = []
  let maxDayCount = 0
  for (const [key, { ms, count }] of counts) {
    days.push({ key, fraction: fraction(ms), count })
    if (count > maxDayCount) maxDayCount = count
  }
  days.sort((a, b) => a.fraction - b.fraction)

  const months: TimelineMonthTick[] = []
  const cursor = new Date(newestMs)
  cursor.setDate(1)
  cursor.setHours(0, 0, 0, 0)
  const oldestMonthStart = new Date(oldestMs)
  oldestMonthStart.setDate(1)
  oldestMonthStart.setHours(0, 0, 0, 0)
  while (cursor.getTime() >= oldestMonthStart.getTime()) {
    const isYear = cursor.getMonth() === 0
    const tickFraction = fraction(cursor.getTime())
    const previous = months[months.length - 1]
    // A partial bottom month clamps onto the previous tick — skip the
    // collision rather than render two labels on top of each other.
    if (!previous || tickFraction - previous.fraction >= 0.02) {
      months.push({
        key: `${cursor.getFullYear()}-${String(cursor.getMonth() + 1).padStart(2, "0")}`,
        label: isYear
          ? String(cursor.getFullYear())
          : cursor.toLocaleDateString(undefined, { month: "short" }),
        isYear,
        fraction: tickFraction,
      })
    }
    cursor.setMonth(cursor.getMonth() - 1)
  }

  return { newestMs, oldestMs, spanMs, months, days, maxDayCount }
}

/** Axis fraction (0 top / 1 bottom) of an absolute timestamp. */
export function dateToFraction(scale: TimelineScale, ms: number): number {
  return clamp01((scale.newestMs - ms) / scale.spanMs)
}

/** Local calendar day under an axis fraction. */
export function fractionToDayKey(
  scale: TimelineScale,
  fraction: number,
): string {
  const ms = scale.newestMs - clamp01(fraction) * scale.spanMs
  return localDayKey(new Date(ms))
}
