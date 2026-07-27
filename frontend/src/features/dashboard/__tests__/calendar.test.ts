import { describe, expect, it } from "vitest"
import {
  calendarWindow,
  fillCalendarDays,
  utcDayKey,
} from "../calendar"

// Fixed instant so weekday math and the day count are deterministic.
// 2026-07-25 is a Saturday (UTC).
const NOW = new Date("2026-07-25T18:00:00Z").getTime()

describe("utcDayKey", () => {
  it("keys by the UTC calendar day, not the local one", () => {
    // 23:30 UTC on the 1st is still the 2nd in UTC+something ahead, but
    // getUTCDate must read the UTC day regardless of host TZ.
    expect(utcDayKey(new Date("2026-01-01T23:30:00Z"))).toBe("2026-01-01")
    expect(utcDayKey(new Date("2026-03-05T00:00:00Z"))).toBe("2026-03-05")
  })
})

describe("calendarWindow", () => {
  it("ends today (UTC midnight) and starts on a Monday", () => {
    const { start, end } = calendarWindow(NOW)
    expect(end.toISOString()).toBe("2026-07-25T00:00:00.000Z")
    expect(start.getUTCDay()).toBe(1)
    expect(start.getTime()).toBeLessThan(end.getTime())
  })

  it("spans roughly 52-53 weeks", () => {
    const { start, end } = calendarWindow(NOW)
    const days = Math.round((end.getTime() - start.getTime()) / 86_400_000)
    expect(days).toBeGreaterThanOrEqual(364)
    expect(days).toBeLessThanOrEqual(370)
  })
})

describe("fillCalendarDays", () => {
  it("zero-fills every day the sparse bucket list omits", () => {
    const days = fillCalendarDays(
      [
        { day: "2026-07-20", count: 3 },
        { day: "2026-07-25", count: 1 },
      ],
      NOW,
    )
    const { start, end } = calendarWindow(NOW)
    const expectedCount =
      Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1
    expect(days).toHaveLength(expectedCount)
    expect(days.every((d) => d.count >= 0)).toBe(true)

    const byDate = new Map(days.map((d) => [d.date, d.count]))
    expect(byDate.get("2026-07-20")).toBe(3)
    expect(byDate.get("2026-07-25")).toBe(1)
    expect(byDate.get("2026-07-24")).toBe(0)
  })

  it("never fabricates a types breakdown or verified count", () => {
    const days = fillCalendarDays([{ day: "2026-07-25", count: 5 }], NOW)
    const today = days.find((d) => d.date === "2026-07-25")!
    expect(today.types).toEqual([])
    expect(today.verified).toBe(0)
  })

  it("reports an honest all-zero grid when there are no buckets at all", () => {
    const days = fillCalendarDays([], NOW)
    expect(days.some((d) => d.count > 0)).toBe(false)
  })

  it("keeps days in chronological order ending on `now`'s UTC day", () => {
    const days = fillCalendarDays([], NOW)
    expect(days[days.length - 1]!.date).toBe("2026-07-25")
    for (let i = 1; i < days.length; i++) {
      expect(days[i]!.date > days[i - 1]!.date).toBe(true)
    }
  })
})
