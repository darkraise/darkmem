import { describe, expect, it } from "vitest"
import { buildContributions } from "../dashboard"
import { dayKeyToMs } from "@/lib/format"

const NOW = new Date("2026-07-25T12:00:00").getTime()

function row(
  created_at: string,
  memory_type = "fact",
  verification_status: string | null = null,
) {
  return { created_at, memory_type, verification_status }
}

describe("buildContributions", () => {
  it("covers a Monday-aligned rolling year ending today", () => {
    const days = buildContributions([], NOW)
    const first = days[0]!
    const last = days[days.length - 1]!
    expect(new Date(dayKeyToMs(first.date)).getDay()).toBe(1)
    expect(last.date).toBe("2026-07-25")
    expect(days.length).toBeGreaterThanOrEqual(365)
    expect(days.length).toBeLessThanOrEqual(371)
    expect(days.every((d) => d.count === 0)).toBe(true)
  })

  it("derives per-day counts and breakdowns from the memory set", () => {
    const days = buildContributions(
      [
        row("2026-07-20T09:00:00", "fact", "corroborated"),
        row("2026-07-20T11:30:00", "decision"),
        row("2026-07-20T15:00:00", "fact"),
        row("2026-07-25T08:00:00", "preference", "confirmed"),
      ],
      NOW,
    )
    const monday = days.find((d) => d.date === "2026-07-20")!
    expect(monday.count).toBe(3)
    expect(monday.types).toEqual([
      { label: "fact", count: 2 },
      { label: "decision", count: 1 },
    ])
    expect(monday.verified).toBe(1)
    const today = days.find((d) => d.date === "2026-07-25")!
    expect(today.count).toBe(1)
    expect(today.verified).toBe(1)
    expect(days.filter((d) => d.count > 0)).toHaveLength(2)
  })

  it("ignores rows outside the rolling year without failing", () => {
    const days = buildContributions([row("2020-01-01T00:00:00")], NOW)
    expect(days.every((d) => d.count === 0)).toBe(true)
  })

  it("is deterministic for a fixed now", () => {
    const rows = [row("2026-07-20T09:00:00"), row("2026-02-14T10:00:00")]
    expect(buildContributions(rows, NOW)).toEqual(
      buildContributions(rows, NOW),
    )
  })
})
