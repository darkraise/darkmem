import type { ContributionDay } from "@/demo/types"
import { dayKeyToMs } from "@/lib/format"

export interface HeatmapWeek {
  /** Monday-first; null pads a partial leading/trailing week. */
  days: (ContributionDay | null)[]
  /** Short month label when this column contains the 1st of a month. */
  monthLabel: string | null
}

const MONTH_SHORT = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const

/**
 * Chunk chronological contribution days into Monday-first week columns and
 * mark the columns that open a new month — the GitHub heatmap layout model.
 */
export function buildHeatmapWeeks(days: ContributionDay[]): HeatmapWeek[] {
  const weeks: HeatmapWeek[] = []
  let current: (ContributionDay | null)[] = []
  let monthLabel: string | null = null

  const flush = () => {
    if (current.length === 0) return
    while (current.length < 7) current.push(null)
    weeks.push({ days: current, monthLabel })
    current = []
    monthLabel = null
  }

  for (const day of days) {
    const at = new Date(dayKeyToMs(day.date))
    const dow = (at.getDay() + 6) % 7
    if (current.length === 0 && weeks.length === 0) {
      for (let i = 0; i < dow; i++) current.push(null)
    }
    current.push(day)
    if (at.getDate() === 1) monthLabel = MONTH_SHORT[at.getMonth()] ?? null
    if (current.length === 7) flush()
  }
  flush()
  return weeks
}

/** Quartile thresholds over the nonzero counts — the 4-step intensity ramp. */
export function intensityThresholds(
  days: ContributionDay[],
): [number, number, number] {
  const nonzero = days
    .map((d) => d.count)
    .filter((c) => c > 0)
    .sort((a, b) => a - b)
  if (nonzero.length === 0) return [1, 2, 3]
  const q = (p: number): number =>
    nonzero[Math.min(nonzero.length - 1, Math.floor(p * nonzero.length))] ?? 1
  const t1 = q(0.25)
  const t2 = Math.max(q(0.5), t1 + 1)
  const t3 = Math.max(q(0.75), t2 + 1)
  return [t1, t2, t3]
}

/** Sequential single-hue ramp from theme tokens — empty stays the muted surface. */
export function intensityClass(
  count: number,
  [t1, t2, t3]: [number, number, number],
): string {
  if (count === 0) return "bg-muted"
  if (count <= t1) return "bg-primary/25"
  if (count <= t2) return "bg-primary/50"
  if (count <= t3) return "bg-primary/75"
  return "bg-primary"
}
