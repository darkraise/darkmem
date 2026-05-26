import { describe, it, expect, vi, afterEach } from "vitest"
import { relativeTime } from "../format"

const NOW = new Date("2025-01-15T12:00:00Z").getTime()

afterEach(() => {
  vi.restoreAllMocks()
})

function setNow(ms: number) {
  vi.spyOn(Date, "now").mockReturnValue(ms)
}

describe("relativeTime", () => {
  it("returns empty string for empty input", () => {
    setNow(NOW)
    expect(relativeTime("")).toBe("")
  })

  it('returns "just now" for less than 1 minute ago', () => {
    setNow(NOW)
    const iso = new Date(NOW - 30_000).toISOString()
    expect(relativeTime(iso)).toBe("just now")
  })

  it("returns Xm ago for minutes ago", () => {
    setNow(NOW)
    const iso = new Date(NOW - 15 * 60_000).toISOString()
    expect(relativeTime(iso)).toBe("15m ago")
  })

  it("returns Xh ago for hours ago", () => {
    setNow(NOW)
    const iso = new Date(NOW - 3 * 3600_000).toISOString()
    expect(relativeTime(iso)).toBe("3h ago")
  })

  it("returns Xd ago for days ago", () => {
    setNow(NOW)
    const iso = new Date(NOW - 2 * 86400_000).toISOString()
    expect(relativeTime(iso)).toBe("2d ago")
  })
})
