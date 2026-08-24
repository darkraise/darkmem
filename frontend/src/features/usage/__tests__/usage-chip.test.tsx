import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import type { SubjectTotalRow } from "@/hooks/api"
import { UsageChip } from "../components/usage-chip"

const TOTALS: SubjectTotalRow = {
  subject_id: "m1",
  cost_micros: 311,
  calls: 1,
  prompt_tokens: 9_885,
  cached_tokens: 0,
  completion_tokens: 121,
  unmeasured_calls: 0,
  unpriced_calls: 0,
}

describe("UsageChip", () => {
  it("sums input and output into the token figure", () => {
    render(<UsageChip totals={TOTALS} />)
    expect(screen.getByText(/10\.0k tok/)).toBeInTheDocument()
  })

  it("distinguishes an unrecorded item from a free one", () => {
    // Absent totals are not a measured zero: the item may predate metering or
    // its rows may have been pruned. "$0.00" would assert a measurement that
    // nothing took.
    render(<UsageChip totals={undefined} />)
    expect(screen.getByText(/no spend recorded/i)).toBeInTheDocument()
    expect(screen.queryByText(/\$0\.00/)).not.toBeInTheDocument()
  })

  it("marks a partly-uncosted total as a floor rather than a total", () => {
    render(<UsageChip totals={{ ...TOTALS, calls: 3, unmeasured_calls: 1 }} />)
    expect(screen.getByText(/^≥/)).toBeInTheDocument()
  })

  it("says not priced when nothing in the group had a rate", () => {
    render(<UsageChip totals={{ ...TOTALS, calls: 2, unpriced_calls: 2 }} />)
    expect(screen.getByText(/not priced/i)).toBeInTheDocument()
  })

  it("shows a pending read as pending, never as an absence", () => {
    render(<UsageChip pending totals={undefined} />)
    expect(screen.queryByText(/no spend recorded/i)).not.toBeInTheDocument()
  })
})
