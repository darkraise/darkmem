import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import {
  useReviewArticleRows,
  useReviewCounts,
  useReviewFactRows,
} from "../use-review-queue"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const CONSEQUENCE = {
  score: 0.42,
  tier: 1,
  retrieval_frequency: {
    source_memories: 3,
    peak_access_count: 12,
    last_accessed: "2026-07-01T00:00:00Z",
    decayed_access: 0.41,
    half_life_days: 30,
    weight: 0.5,
    component: 0.2,
  },
  subject_salience: { neighbour_count: 4, weight: 0.5, component: 0.15 },
  staleness: {
    stale: false,
    label: "fresh",
    dispute_opened_at: null,
    dispute_age_days: null,
    threshold_days: 14,
  },
}

function factItem(overrides: Record<string, unknown> = {}) {
  return {
    id: "f1",
    subject_name: "darkmem",
    object_name: "postgres",
    rel_type: "USES",
    fact: "darkmem uses postgres",
    project: "darkmem",
    valid_at: null,
    invalid_at: null,
    expired_at: null,
    verification_status: "disputed",
    confidence: 0.4,
    review_state: "open",
    demotion_pending_since: null,
    reason: "disputed",
    evidence: null,
    consequence: CONSEQUENCE,
    created_at: "2026-08-01T00:00:00Z",
    ...overrides,
  }
}

const QUERY = { limit: 10, offset: 0 }

describe("useReviewFactRows (DEMO off — real /review-queue/facts)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("reports the server's total, not the page length", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [factItem()],
      total: 231,
      limit: 10,
      offset: 0,
    })
    const { result } = renderHook(() => useReviewFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.rows).toHaveLength(1)
    expect(result.current.total).toBe(231)
  })

  it("carries the backend's own `reason` verbatim, never re-derives it", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [factItem({ reason: "under-sourced", demotion_pending_since: "2026-07-20T00:00:00Z" })],
      total: 1,
      limit: 10,
      offset: 0,
    })
    const { result } = renderHook(() => useReviewFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.rows[0]!.reason).toBe("under-sourced")
    expect(result.current.rows[0]!.under_sourced).toBe(true)
  })

  it("under-claims an unrecognised verification_status rather than passing it through", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [factItem({ verification_status: "gilded" })],
      total: 1,
      limit: 10,
      offset: 0,
    })
    const { result } = renderHook(() => useReviewFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.rows[0]!.verification_status).toBe("candidate")
  })

  it("composes rank_note from the consequence breakdown and carries the breakdown itself", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [factItem()],
      total: 1,
      limit: 10,
      offset: 0,
    })
    const { result } = renderHook(() => useReviewFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    const row = result.current.rows[0]!
    expect(row.rank_note).toContain("score 0.42")
    expect(row.rank_note).toContain("tier 1")
    expect(row.consequence).toEqual(CONSEQUENCE)
  })

  it("names the absence of a ranking signal honestly rather than inventing a score", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [factItem({ consequence: null })],
      total: 1,
      limit: 10,
      offset: 0,
    })
    const { result } = renderHook(() => useReviewFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.rows[0]!.rank_note).toMatch(/arrival order/)
    expect(result.current.rows[0]!.consequence).toBeNull()
  })

  it("carries the contradiction evidence block verbatim when present", async () => {
    const evidence = {
      payload: {
        outcome: "dispute",
        origin_count: 2,
        contradiction: {
          counterpart_id: "f2",
          counterpart_subject: "darkmem",
          counterpart_rel_type: "USES",
          counterpart_object: "mysql",
          rule: "mutex_technology",
          witness_origin: "session-b",
          enumeration: "first_finding",
        },
      },
      recorded_at: "2026-08-01T00:00:00Z",
    }
    vi.mocked(apiFetch).mockResolvedValue({
      items: [factItem({ evidence })],
      total: 1,
      limit: 10,
      offset: 0,
    })
    const { result } = renderHook(() => useReviewFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.rows[0]!.evidence).toEqual(evidence)
  })

  it("sends project as a server-side predicate", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [], total: 0, limit: 10, offset: 0 })
    renderHook(() => useReviewFactRows({ ...QUERY, project: "darkmem" }), { wrapper })
    await waitFor(() => expect(apiFetch).toHaveBeenCalled())

    const url = vi.mocked(apiFetch).mock.calls[0]![0] as string
    expect(url).toContain("project=darkmem")
  })

  it("reports a failed read as an error, never as an empty queue", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    const { result } = renderHook(() => useReviewFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.error).toBe(true))

    expect(result.current.rows).toEqual([])
    expect(result.current.total).toBe(0)
  })
})

describe("useReviewArticleRows (DEMO off — real /review-queue/articles)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("maps the article shape and reports the server total", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [
        {
          id: "a1",
          subject_key: "darkmem:pipeline",
          project: "darkmem",
          title: "Pipeline overview",
          status: "low_confidence",
          confidence: 0.3,
          fact_set_hash: "abc",
          review_state: "open",
          reason: "unspecified",
          content_preview: "The pipeline runs in five phases…",
          synthesized_at: "2026-07-15T00:00:00Z",
          created_at: "2026-07-15T00:00:00Z",
        },
      ],
      total: 9,
      limit: 10,
      offset: 0,
    })
    const { result } = renderHook(() => useReviewArticleRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.total).toBe(9)
    expect(result.current.rows[0]!.title).toBe("Pipeline overview")
    expect(result.current.rows[0]!.reason).toBe("unspecified")
  })

  it("reports a failed read as an error, never as an empty queue", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    const { result } = renderHook(() => useReviewArticleRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.error).toBe(true))

    expect(result.current.rows).toEqual([])
  })
})

describe("useReviewCounts", () => {
  beforeEach(() => vi.clearAllMocks())

  it("flags itself unscoped when a project filter is active — the counts door takes no project param", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ facts: 12, articles: 3 })
    const { result } = renderHook(() => useReviewCounts({ project: "darkmem" }), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.facts).toBe(12)
    expect(result.current.unscoped).toBe(true)
  })

  it("is not unscoped when no project filter is active", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ facts: 12, articles: 3 })
    const { result } = renderHook(() => useReviewCounts({}), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.unscoped).toBe(false)
  })
})
