import { describe, it, expect, vi, afterEach } from "vitest"
import * as format from "../format"
import { formatList, formatWhen, relativeTime } from "../format"

const SOURCES = import.meta.glob<string>("/src/**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
})

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

describe("formatList", () => {
  it("reads as prose", () => {
    expect(formatList([])).toBe("")
    expect(formatList(["memory"])).toBe("memory")
    expect(formatList(["code", "memory"])).toBe("code and memory")
    expect(formatList(["code", "human", "memory"])).toBe("code, human and memory")
  })
})

describe("formatWhen", () => {
  it("passes a value that is not a date through unchanged", () => {
    expect(formatWhen("14:10 UTC")).toBe("14:10 UTC")
  })
})

describe("formatDuration", () => {
  // The module's own export, read off the namespace so this file compiles
  // before the helper exists and fails on the missing function instead.
  const formatDuration = (seconds: number) =>
    (format as unknown as Record<string, (s: number) => string>).formatDuration!(seconds)

  it("formatDuration rounds across the minute", () => {
    expect(formatDuration(119.6)).toBe("2m 0s")
    expect(formatDuration(59.6)).toBe("1m 0s")
    expect(formatDuration(59.4)).toBe("59s")
  })
})

describe("shared formatters", () => {
  it("one formatDateTime and one formatDuration", () => {
    const declared = (name: string) =>
      Object.entries(SOURCES)
        .filter(([file]) => !file.includes("/__tests__/") && !/\.test\.tsx?$/.test(file))
        .filter(([, text]) =>
          new RegExp(`(function|const|let)\\s+${name}\\b`).test(text),
        )
        .map(([file]) => file)
    expect(declared("formatDateTime")).toEqual(["/src/lib/format.ts"])
    expect(declared("formatDuration")).toEqual(["/src/lib/format.ts"])
  })
})
