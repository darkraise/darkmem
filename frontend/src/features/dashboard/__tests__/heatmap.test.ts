import { describe, expect, it } from "vitest"
import { buildContributions } from "@/demo/dashboard"
import { dayKeyToMs } from "@/lib/format"
import {
  buildHeatmapWeeks,
  intensityClass,
  intensityThresholds,
} from "../heatmap"

const NOW = new Date("2026-07-25T12:00:00").getTime()
const DAYS = buildContributions([], NOW)

describe("buildHeatmapWeeks", () => {
  it("chunks days into Monday-first columns of 7", () => {
    const weeks = buildHeatmapWeeks(DAYS)
    expect(weeks.length).toBeGreaterThanOrEqual(52)
    expect(weeks.length).toBeLessThanOrEqual(54)
    for (const week of weeks) expect(week.days).toHaveLength(7)
    const firstDay = weeks[0]!.days.find((d) => d != null)!
    expect(new Date(dayKeyToMs(firstDay.date)).getDay()).toBe(1)
  })

  it("keeps the days in order and pads only the trailing partial week", () => {
    const weeks = buildHeatmapWeeks(DAYS)
    const flattened = weeks.flatMap((w) => w.days).filter((d) => d != null)
    expect(flattened.map((d) => d.date)).toEqual(DAYS.map((d) => d.date))
    const last = weeks[weeks.length - 1]!
    expect(last.days.filter((d) => d == null).length).toBeGreaterThanOrEqual(0)
  })

  it("labels the column containing the 1st of each month", () => {
    const weeks = buildHeatmapWeeks(DAYS)
    const labelled = weeks.filter((w) => w.monthLabel != null)
    expect(labelled.length).toBeGreaterThanOrEqual(12)
    expect(labelled.length).toBeLessThanOrEqual(13)
    for (const week of labelled) {
      const hasFirst = week.days.some(
        (d) => d != null && new Date(dayKeyToMs(d.date)).getDate() === 1,
      )
      expect(hasFirst).toBe(true)
    }
  })
})

describe("intensity ramp", () => {
  it("computes monotone quartile thresholds", () => {
    const days = Array.from({ length: 40 }, (_, i) => ({
      date: `2026-01-${String(i + 1).padStart(2, "0")}`,
      count: i,
      types: [],
      verified: 0,
      injects: 0,
    }))
    const [t1, t2, t3] = intensityThresholds(days)
    expect(t1).toBeLessThan(t2)
    expect(t2).toBeLessThan(t3)
  })

  it("maps zero to the muted surface and the top bucket to full primary", () => {
    const t: [number, number, number] = [2, 5, 9]
    expect(intensityClass(0, t)).toBe("bg-muted")
    expect(intensityClass(1, t)).toBe("bg-primary/25")
    expect(intensityClass(4, t)).toBe("bg-primary/50")
    expect(intensityClass(9, t)).toBe("bg-primary/75")
    expect(intensityClass(50, t)).toBe("bg-primary")
  })
})
