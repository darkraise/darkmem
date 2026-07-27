import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

// YearHeatmap calls useNavigate() at render; stub it so the test needs no
// RouterProvider (and no console warning).
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  useNavigate: () => vi.fn(),
}))

import type { ContributionDay } from "@/demo/types"
import { CalendarCard } from "../calendar-card"

function day(date: string, count: number): ContributionDay {
  return { date, count, types: [], verified: 0 }
}

describe("CalendarCard", () => {
  it("shows a loading skeleton, not the grid or an error, while in flight", () => {
    render(<CalendarCard days={[]} isLoading isError={false} />)
    expect(screen.getByRole("status")).toBeInTheDocument()
    expect(screen.queryByText(/couldn't load/i)).not.toBeInTheDocument()
    expect(
      screen.queryByText(/no memory activity recorded yet/i),
    ).not.toBeInTheDocument()
  })

  it("shows an explicit error, never a blank or zero-filled grid, on failure", () => {
    render(<CalendarCard days={[]} isLoading={false} isError />)
    expect(screen.getByText(/couldn't load the contribution calendar/i)).toBeInTheDocument()
    expect(screen.queryByRole("status")).not.toBeInTheDocument()
    expect(
      screen.queryByText(/no memory activity recorded yet/i),
    ).not.toBeInTheDocument()
  })

  it("renders an honest empty caption when successfully loaded with zero activity", () => {
    const days = [day("2026-07-24", 0), day("2026-07-25", 0)]
    render(<CalendarCard days={days} isLoading={false} isError={false} />)
    expect(
      screen.getByText(/no memory activity recorded yet/i),
    ).toBeInTheDocument()
    expect(screen.queryByText(/couldn't load/i)).not.toBeInTheDocument()
    expect(screen.queryByRole("status")).not.toBeInTheDocument()
  })

  it("renders the heatmap with no empty caption when there is real activity", () => {
    const days = [day("2026-07-24", 0), day("2026-07-25", 3)]
    render(<CalendarCard days={days} isLoading={false} isError={false} />)
    expect(
      screen.queryByText(/no memory activity recorded yet/i),
    ).not.toBeInTheDocument()
    expect(screen.queryByText(/couldn't load/i)).not.toBeInTheDocument()
  })
})
