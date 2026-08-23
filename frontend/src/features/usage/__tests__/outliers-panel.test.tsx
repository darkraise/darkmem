import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

import type { UsageTopRow } from "@/hooks/api"
import { OutliersPanel } from "../components/outliers-panel"

const ROW: UsageTopRow = {
  subject_type: "job_run",
  subject_id: "memory_dream@2026-08-23T04:00:00+00:00",
  project: null,
  cost_micros: 400_000,
  calls: 40,
  duration_ms: 92_000,
  unmeasured_calls: 0,
}

const BASE = {
  axis: "cost" as const,
  onAxisChange: vi.fn(),
  windowTotal: 1_000_000,
  windowCalls: 100,
  selectedKey: null,
  onSelect: vi.fn(),
  isLoading: false,
  isError: false,
  typeFilter: null,
  onTypeFilterChange: vi.fn(),
  availableTypes: ["job_run", "memory"],
}

describe("OutliersPanel", () => {
  it("names the job instead of showing its composite run id", () => {
    render(<OutliersPanel {...BASE} rows={[ROW]} />)
    expect(screen.getByText("memory_dream")).toBeInTheDocument()
  })

  it("says how concentrated the spend is, not just who is on top", () => {
    // A ranked list without this reads as "these are the big ones" whether
    // they are 90% of the bill or 3% of it.
    render(<OutliersPanel {...BASE} rows={[ROW]} />)
    expect(screen.getByText(/40% of \$1\.00/)).toBeInTheDocument()
    expect(screen.getByText(/40 of 100 calls/)).toBeInTheDocument()
  })

  it("shows a share only when the ranking is in the total's units", () => {
    // The window total this page holds is money. Ranking by calls and showing
    // "% of window" would be a percentage of the wrong denominator.
    const { rerender } = render(<OutliersPanel {...BASE} rows={[ROW]} />)
    expect(screen.getByText(/% of window/)).toBeInTheDocument()
    rerender(<OutliersPanel {...BASE} axis="calls" rows={[ROW]} />)
    expect(screen.queryByText(/% of window/)).not.toBeInTheDocument()
  })

  it("renders the ranked value in the active axis's own units", () => {
    const { rerender } = render(<OutliersPanel {...BASE} rows={[ROW]} />)
    expect(screen.getByText("$0.40")).toBeInTheDocument()
    rerender(<OutliersPanel {...BASE} axis="duration" rows={[ROW]} />)
    expect(screen.getAllByText("1m 32s").length).toBeGreaterThan(0)
  })

  it("marks a row that is a floor rather than a total", () => {
    render(
      <OutliersPanel {...BASE} rows={[{ ...ROW, unmeasured_calls: 6 }]} />,
    )
    expect(screen.getByText(/6 unmeasured/)).toBeInTheDocument()
  })

  it("reports a failed read as failed, never as an empty list", () => {
    render(<OutliersPanel {...BASE} isError rows={[]} />)
    expect(screen.getByText(/could not read the outlier list/i)).toBeInTheDocument()
  })

  it("says which filter emptied the list", () => {
    render(
      <OutliersPanel {...BASE} rows={[]} typeFilter="chat" />,
    )
    expect(screen.getByText(/No Chat turn calls in this window/i)).toBeInTheDocument()
  })

  it("marks the selected row for assistive tech, not only by colour", () => {
    render(
      <OutliersPanel
        {...BASE}
        rows={[ROW]}
        selectedKey={`${ROW.subject_type}:${ROW.subject_id}`}
      />,
    )
    expect(screen.getByRole("button", { pressed: true })).toBeInTheDocument()
  })

  it("does not mark every unattributed row as the open one", () => {
    // Every unattributed row shares subject_id null, so comparing ids alone
    // rendered all of them selected at once. Caught by looking at the page.
    const anon: UsageTopRow = { ...ROW, subject_type: "unattributed", subject_id: null }
    render(<OutliersPanel {...BASE} rows={[anon]} selectedKey={null} />)
    expect(screen.queryByRole("button", { pressed: true })).not.toBeInTheDocument()
  })

  it("does not offer to open a row that has no subject id", () => {
    const anon: UsageTopRow = { ...ROW, subject_type: "unattributed", subject_id: null }
    render(<OutliersPanel {...BASE} rows={[anon]} />)
    expect(screen.getByRole("button", { name: /unattributed/i })).toBeDisabled()
  })
})
