import { describe, expect, it } from "vitest"
import {
  buildTimelineScale,
  dateToFraction,
  fractionToDayKey,
} from "../timeline"

function mem(created_at: string) {
  return { created_at }
}

const ROWS = [
  mem("2026-07-25T10:00:00"),
  mem("2026-07-25T08:00:00"),
  mem("2026-07-24T12:00:00"),
  mem("2026-03-02T09:30:00"),
  mem("2025-08-10T16:45:00"),
]

describe("buildTimelineScale", () => {
  it("returns null when there is nothing to scale", () => {
    expect(buildTimelineScale([])).toBeNull()
  })

  it("anchors the newest row at fraction 0 and the oldest at 1", () => {
    const scale = buildTimelineScale(ROWS)!
    expect(scale.newestMs).toBe(Date.parse("2026-07-25T10:00:00"))
    expect(scale.oldestMs).toBe(Date.parse("2025-08-10T16:45:00"))
    expect(dateToFraction(scale, scale.newestMs)).toBe(0)
    expect(dateToFraction(scale, scale.oldestMs)).toBe(1)
    expect(dateToFraction(scale, scale.newestMs + 999_999)).toBe(0)
  })

  it("emits one density marker per day carrying the day count", () => {
    const scale = buildTimelineScale(ROWS)!
    const keys = scale.days.map((d) => d.key)
    expect(new Set(keys).size).toBe(keys.length)
    expect(scale.days.reduce((acc, d) => acc + d.count, 0)).toBe(ROWS.length)
    const top = scale.days.find((d) => d.key === "2026-07-25")
    expect(top?.count).toBe(2)
    expect(scale.maxDayCount).toBe(2)
  })

  it("ticks every month boundary newest-first, labelling January as the year", () => {
    const scale = buildTimelineScale(ROWS)!
    expect(scale.months[0]?.key).toBe("2026-07")
    expect(scale.months[scale.months.length - 1]?.key).toBe("2025-08")
    expect(scale.months.length).toBe(12)
    const jan = scale.months.find((m) => m.key === "2026-01")
    expect(jan?.isYear).toBe(true)
    expect(jan?.label).toBe("2026")
    const fractions = scale.months.map((m) => m.fraction)
    expect([...fractions].sort((a, b) => a - b)).toEqual(fractions)
  })

  it("keeps the span finite for a single-instant corpus", () => {
    const scale = buildTimelineScale([mem("2026-07-25T10:00:00")])!
    expect(scale.spanMs).toBeGreaterThan(0)
    expect(dateToFraction(scale, scale.newestMs)).toBe(0)
  })
})

describe("fractionToDayKey", () => {
  it("round-trips the axis endpoints to their local day keys", () => {
    const scale = buildTimelineScale(ROWS)!
    expect(fractionToDayKey(scale, 0)).toBe("2026-07-25")
    expect(fractionToDayKey(scale, 1)).toBe("2025-08-10")
  })

  it("clamps out-of-range fractions", () => {
    const scale = buildTimelineScale(ROWS)!
    expect(fractionToDayKey(scale, -0.5)).toBe("2026-07-25")
    expect(fractionToDayKey(scale, 1.5)).toBe("2025-08-10")
  })
})
