import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

const navigateMock = vi.fn()
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  useNavigate: () => navigateMock,
}))
vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))

import { YearHeatmap } from "../year-heatmap"

describe("YearHeatmap", () => {
  it("opens a clicked day in Activity's Day drill on a real instance", () => {
    // The real Memories page has no timeline, so ?date= landed on the whole,
    // unfiltered list.
    render(
      <YearHeatmap
        days={[
          { date: "2026-07-24", count: 3, types: [], verified: 0, injects: 0 },
        ]}
      />,
    )
    fireEvent.click(screen.getByRole("button", { name: /3 captures/ }))
    expect(navigateMock).toHaveBeenCalledWith({
      to: "/activity",
      search: { tab: "day", day: "2026-07-24" },
    })
  })

  it("names its count as captures, which outlive a deleted memory", () => {
    // 24 created events against 21 memories read "24 memories captured".
    render(
      <YearHeatmap
        days={[
          { date: "2026-10-05", count: 24, types: [], verified: 0, injects: 0 },
          { date: "2026-10-04", count: 1, types: [], verified: 0, injects: 0 },
        ]}
      />,
    )
    expect(
      screen.getByRole("button", { name: /— 24 captures$/ }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: /— 1 capture$/ }),
    ).toBeInTheDocument()
    expect(screen.getByText("memory captures per day")).toBeInTheDocument()
    expect(screen.queryByText(/memories captured/)).toBeNull()
  })

  it("lays the weeks out as fluid grid columns that fill the card", () => {
    render(
      <YearHeatmap
        days={[
          { date: "2026-07-24", count: 3, types: [], verified: 0, injects: 0 },
        ]}
      />,
    )
    const grid = screen.getByTestId("heatmap-grid")
    expect(grid.style.gridTemplateColumns).toMatch(
      /^auto repeat\(\d+, minmax\(var\(--cell-min\), 1fr\)\)$/,
    )
    // A 10px floor only below `sm`: above it the floor overflowed the card.
    expect(grid).toHaveClass("[--cell-min:10px]", "sm:[--cell-min:0px]")
    const cell = screen.getByRole("button", { name: /3 captures/ })
    expect(cell).toHaveClass("aspect-square", "w-full")
  })

  it("is one tab stop, with the arrow keys moving between days", () => {
    const days = Array.from({ length: 21 }, (_, i) => ({
      date: `2026-07-${String(i + 1).padStart(2, "0")}`,
      count: i,
      types: [],
      verified: 0,
      injects: 0,
    }))
    render(<YearHeatmap days={days} />)
    const cells = screen.getAllByRole("button")
    const stops = cells.filter((c) => c.tabIndex === 0)
    expect(stops).toHaveLength(1)
    // No today in the fixture, so the newest day holds the tab stop.
    expect(stops[0]?.getAttribute("aria-label")).toMatch(/20 captures/)

    const grid = screen.getByTestId("heatmap-grid")
    stops[0]!.focus()
    fireEvent.keyDown(grid, { key: "ArrowLeft" })
    expect(document.activeElement?.getAttribute("aria-label")).toMatch(
      /— 13 captures/,
    )
    fireEvent.keyDown(grid, { key: "ArrowUp" })
    expect(document.activeElement?.getAttribute("aria-label")).toMatch(
      /— 12 captures/,
    )
    expect(cells.filter((c) => c.tabIndex === 0)).toEqual([
      document.activeElement,
    ])
    fireEvent.keyDown(grid, { key: "Home" })
    expect(document.activeElement?.getAttribute("aria-label")).toMatch(
      /— 0 captures/,
    )
  })
})
