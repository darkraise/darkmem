import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import type { UsageOverview as UsageOverviewData } from "@/hooks/api"
import { UsageOverview } from "../components/usage-overview"
import { costCell, formatUsd } from "../format"

const BASE: UsageOverviewData = {
  window_start: "2026-07-24T00:00:00Z",
  window_end: "2026-08-23T00:00:00Z",
  total_cost_micros: 3_410_000,
  total_calls: 120,
  prompt_tokens: 10_000,
  cached_tokens: 4_200,
  completion_tokens: 2_000,
  reasoning_tokens: 0,
  unmeasured_calls: 0,
  unpriced_calls: 0,
  unpriced_models: [],
  merged_classification_present: false,
  cache_hit_ratio: 0.42,
  failed_calls: 0,
  failed_cost_micros: 0,
  by_purpose: [
    {
      key: "extraction",
      cost_micros: 2_100_000,
      calls: 60,
      prompt_tokens: 8_000,
      cached_tokens: 4_000,
      completion_tokens: 1_500,
      unmeasured_calls: 0,
      unpriced_calls: 0,
    },
  ],
  by_model: [],
  by_subject_type: [],
}

describe("UsageOverview", () => {
  it("renders spend as currency, not micros", () => {
    render(<UsageOverview data={BASE} />)
    expect(screen.getByText("$3.41")).toBeInTheDocument()
  })

  it("says when classification is folded into extraction", () => {
    // Under the default config classification reads near zero. Unflagged, an
    // operator optimises a purpose that only looks free.
    render(
      <UsageOverview data={{ ...BASE, merged_classification_present: true }} />,
    )
    expect(
      screen.getByText(/includes folded classification/i),
    ).toBeInTheDocument()
  })

  it("never renders an unmeasured call as free", () => {
    render(<UsageOverview data={{ ...BASE, unmeasured_calls: 7 }} />)
    expect(screen.getByText(/7 calls not measured/i)).toBeInTheDocument()
  })

  it("names unpriced models rather than counting them as zero", () => {
    render(
      <UsageOverview
        data={{
          ...BASE,
          unpriced_calls: 3,
          unpriced_models: ["mystery-model-9"],
        }}
      />,
    )
    expect(screen.getByText(/3 calls not priced/i)).toBeInTheDocument()
    expect(screen.getByText(/mystery-model-9/)).toBeInTheDocument()
  })

  it("reports what failed calls cost", () => {
    // A vendor bills for work that errored after it started, and a failed call
    // is exactly the waste this surface exists to find.
    render(
      <UsageOverview
        data={{ ...BASE, failed_calls: 4, failed_cost_micros: 120_000 }}
      />,
    )
    expect(screen.getByText(/4 calls failed/i)).toBeInTheDocument()
    expect(screen.getByText(/\$0\.12/)).toBeInTheDocument()
  })

  it("raises no caveats when every call is measured and priced", () => {
    render(<UsageOverview data={BASE} />)
    expect(screen.queryByText(/not measured/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/not priced/i)).not.toBeInTheDocument()
  })

  it("shows an unknown cache ratio as unknown, not as zero", () => {
    render(<UsageOverview data={{ ...BASE, cache_hit_ratio: null }} />)
    expect(screen.getByText("—")).toBeInTheDocument()
  })
})

describe("formatUsd", () => {
  it("keeps sub-cent spend distinguishable from free", () => {
    // $0.00 would tell an operator a call cost nothing when it was merely
    // cheap, which is the same class of error as reporting an unmeasured call
    // as zero.
    expect(formatUsd(1_200)).toBe("$0.0012")
    expect(formatUsd(0)).toBe("$0.00")
  })
})


describe("costCell", () => {
  const row = {
    cost_micros: 0,
    calls: 3,
    unmeasured_calls: 0,
    unpriced_calls: 0,
  }

  it("never renders an all-unpriced group as free", () => {
    // SUM(cost_micros) is 0 when every call in the group priced to NULL, so
    // the arithmetic and "this model is free" are indistinguishable without
    // this. Caught by looking at the rendered page, not by a test.
    expect(costCell({ ...row, unpriced_calls: 3 })).toBe("not priced")
  })

  it("never renders an all-unmeasured group as free", () => {
    expect(costCell({ ...row, unmeasured_calls: 3 })).toBe("not measured")
  })

  it("keeps the number for a mixed group, which is a real floor", () => {
    expect(
      costCell({ ...row, cost_micros: 2_000_000, unpriced_calls: 1 }),
    ).toBe("$2.00")
  })

  it("reports a measured zero as zero", () => {
    // The local embedders bill nothing and say so; that is not "unpriced".
    expect(costCell(row)).toBe("$0.00")
  })
})
