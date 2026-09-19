import { render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { Timestamp } from "../timestamp"

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date("2026-09-18T12:00:00Z"))
})
afterEach(() => vi.useRealTimers())

describe("Timestamp", () => {
  it("reads relative and carries the absolute time on hover", () => {
    const { container } = render(<Timestamp iso="2026-09-18T09:00:00Z" />)
    const time = container.querySelector("time")!
    expect(time).toHaveTextContent("3h ago")
    expect(time).toHaveAttribute("datetime", "2026-09-18T09:00:00Z")
    expect(time.getAttribute("title")).toBe(new Date("2026-09-18T09:00:00Z").toLocaleString())
  })

  it("shows a value that is not a date as written, and a missing one as a dash", () => {
    const { rerender } = render(<Timestamp iso="14:10 UTC" />)
    expect(screen.getByText("14:10 UTC")).toBeInTheDocument()
    rerender(<Timestamp iso={null} />)
    expect(screen.getByText("—")).toBeInTheDocument()
  })
})
