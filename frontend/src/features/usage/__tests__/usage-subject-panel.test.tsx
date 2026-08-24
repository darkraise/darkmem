import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import type { UsageSubject } from "@/hooks/api"
import { UsageSubjectPanel } from "../components/usage-subject-panel"

const CALL = {
  id: "c1",
  occurred_at: "2026-08-23T10:00:00Z",
  purpose: "extraction",
  model: "deepseek-v4-flash",
  provider: "deepseek",
  api_kind: "deepseek",
  subject_type: "memory",
  subject_id: "m1",
  project: "default",
  prompt_tokens: 900,
  cached_tokens: 100,
  completion_tokens: 120,
  reasoning_tokens: 0,
  tokens_measured: true,
  cost_micros: 350,
  ok: true,
  error_kind: null,
  duration_ms: 812,
  merged_classification: false,
}

const BASE: UsageSubject = {
  subject_type: "memory",
  subject_id: "m1",
  total_cost_micros: 350,
  total_calls: 1,
  batched_embedding: true,
  calls: [CALL],
}

describe("UsageSubjectPanel", () => {
  it("says the embedding was batched rather than showing zero for it", () => {
    render(<UsageSubjectPanel data={BASE} />)
    expect(screen.getByText(/embedding batched/i)).toBeInTheDocument()
  })

  it("distinguishes an unmeasured call from a free one", () => {
    render(
      <UsageSubjectPanel
        data={{
          ...BASE,
          calls: [{ ...CALL, tokens_measured: false, cost_micros: null }],
        }}
      />,
    )
    expect(screen.getByText(/not measured/i)).toBeInTheDocument()
  })

  it("distinguishes an unpriced call from an unmeasured one", () => {
    render(
      <UsageSubjectPanel
        data={{
          ...BASE,
          calls: [{ ...CALL, tokens_measured: true, cost_micros: null }],
        }}
      />,
    )
    expect(screen.getByText(/not priced/i)).toBeInTheDocument()
  })

  it("marks a merged call so its cost is not read as extraction alone", () => {
    render(
      <UsageSubjectPanel
        data={{ ...BASE, calls: [{ ...CALL, merged_classification: true }] }}
      />,
    )
    expect(screen.getByText(/\+classification/i)).toBeInTheDocument()
  })

  it("shows a failed call with its error rather than hiding it", () => {
    render(
      <UsageSubjectPanel
        data={{
          ...BASE,
          calls: [{ ...CALL, ok: false, error_kind: "ReadTimeout" }],
        }}
      />,
    )
    expect(screen.getByText("ReadTimeout")).toBeInTheDocument()
  })
})
