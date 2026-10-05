import { describe, expect, it } from "vitest"
import { describeCron } from "../cron-describe"

describe("describeCron", () => {
  it.each([
    ["* * * * *", "Every minute"],
    ["*/3 * * * *", "Every 3 minutes"],
    ["0 * * * *", "Every hour, on the hour"],
    ["30 * * * *", "Every hour at :30"],
    ["0 5 * * *", "At 5:00 AM every day"],
    ["30 17 * * *", "At 5:30 PM every day"],
    ["0 0 * * *", "At 12:00 AM every day"],
    ["0 */6 * * *", "Every 6 hours"],
    ["0 3 * * 1", "At 3:00 AM every Monday"],
    ["0 3 1 * *", "At 3:00 AM on day 1 of the month"],
  ])("describes %s", (expr, expected) => {
    expect(describeCron(expr)).toBe(expected)
  })

  // Six-field expressions put seconds first, Quartz-style (CLAUDE.md).
  it("reads a six-field expression as seconds-first", () => {
    expect(describeCron("0 0 5 * * *")).toBe("At 5:00 AM every day")
    expect(describeCron("*/30 * * * * *")).toBe("Every 30 seconds")
  })

  // Never invent a reading for something it cannot parse — the raw
  // expression is the honest fallback, and the caller still shows it.
  it("returns null rather than guessing at what it cannot read", () => {
    expect(describeCron("nonsense")).toBeNull()
    expect(describeCron("1 2 3 4 5 6 7")).toBeNull()
    expect(describeCron("0 1-5/2,7 * * *")).toBeNull()
  })
})

describe("withZone", () => {
  it("names UTC for a clock time and leaves intervals alone", async () => {
    const { withZone } = await import("../components/job-schedule-state")
    expect(withZone("At 4:30 AM every day")).toBe("At 4:30 AM every day UTC")
    expect(withZone("Every 30 seconds")).toBe("Every 30 seconds")
    expect(withZone("Every hour at :20")).toBe("Every hour at :20")
  })
})
