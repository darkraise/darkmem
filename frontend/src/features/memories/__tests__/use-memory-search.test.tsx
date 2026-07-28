import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import {
  demoTraceToView,
  EXCLUSION_CAVEAT,
  traceToView,
  useMemorySearchPage,
} from "../use-memory-search"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("traceToView", () => {
  it("labels rrf_score as the fused ordering signal and each channel as its own contribution (Ruling 3)", () => {
    const view = traceToView({
      scores: { semantic: 0.82, keyword: 0.4, rrf_score: 0.031, rerank_score: null },
      rank_fusion_factor: 1.0,
      rank_fusion_breakdown: {},
    })
    expect(view.rrfScore).toBe(0.031)
    expect(view.channels).toEqual([
      { name: "semantic", fraction: 0.82 },
      { name: "keyword", fraction: 0.4 },
    ])
    // Neither per-channel score is ever labelled "the score" in the summary.
    expect(view.summary).not.toMatch(/^the score/i)
    expect(view.summary).toContain("rrf_score")
  })

  it("appends a rerank channel only when rerank_score is present", () => {
    const reranked = traceToView({
      scores: { semantic: 0.5, keyword: 0.5, rrf_score: 0.02, rerank_score: 7.4 },
      rank_fusion_factor: 1.0,
      rank_fusion_breakdown: {},
    })
    expect(reranked.channels).toHaveLength(3)
    expect(reranked.channels[2]).toEqual({
      name: "rerank",
      fraction: 0.74,
      display: "7.4 / 10",
    })

    const notReranked = traceToView({
      scores: { semantic: 0.5, keyword: 0.5, rrf_score: 0.02, rerank_score: null },
      rank_fusion_factor: 1.0,
      rank_fusion_breakdown: {},
    })
    expect(notReranked.channels).toHaveLength(2)
  })

  it("mentions the rank-fusion factor only when it differs from 1", () => {
    const flat = traceToView({
      scores: { semantic: 0.5, keyword: 0.5, rrf_score: 0.02 },
      rank_fusion_factor: 1.0,
      rank_fusion_breakdown: {},
    })
    expect(flat.summary).not.toContain("rank-fusion factor")

    const weighted = traceToView({
      scores: { semantic: 0.5, keyword: 0.5, rrf_score: 0.02 },
      rank_fusion_factor: 1.05,
      rank_fusion_breakdown: { confidence: 1.05 },
    })
    expect(weighted.summary).toContain("rank-fusion factor 1.050x")
  })
})

describe("demoTraceToView", () => {
  it("renames rrf_score to rrfScore without changing the value", () => {
    const view = demoTraceToView({
      channels: [{ name: "semantic", fraction: 0.7 }],
      rrf_score: 0.041,
      summary: "strong match",
    })
    expect(view).toEqual({
      channels: [{ name: "semantic", fraction: 0.7 }],
      rrfScore: 0.041,
      summary: "strong match",
    })
  })
})

describe("EXCLUSION_CAVEAT (Ruling 1)", () => {
  it("says an absent count is never proof nothing was filtered", () => {
    expect(EXCLUSION_CAVEAT.toLowerCase()).toContain("never")
    expect(EXCLUSION_CAVEAT.toLowerCase()).toMatch(/project|status/)
  })
})

describe("useMemorySearchPage", () => {
  beforeEach(() => vi.clearAllMocks())

  it("calls /search/paginated with with_trace: true and maps the envelope's excluded counts", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
      envelope: {
        query: "q",
        channels: { semantic: { ran: true }, keyword: { ran: true } },
        reranked: false,
        weights: { semantic_weight: 0.7 },
        excluded: { technologies: 3, not_found: 0 },
      },
    })

    const { result } = renderHook(
      () =>
        useMemorySearchPage({
          query: "q",
          project: "all",
          status: ["active", "superseded"],
          limit: 50,
        }),
      { wrapper },
    )

    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(apiFetch).toHaveBeenCalledWith(
      "/memories/search/paginated",
      expect.objectContaining({
        body: expect.stringContaining('"with_trace":true'),
      }),
    )
    // Zero-count reasons never render as a "0 excluded" row.
    expect(result.current.exclusions).toEqual([
      { count: 3, unit: "memories", reason: expect.any(String), tag: "technologies" },
    ])
  })

  it("never reports project or status as an exclusion reason, even though rows are dropped by them", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
      envelope: {
        query: "q",
        channels: {},
        reranked: false,
        weights: {},
        excluded: {},
      },
    })

    const { result } = renderHook(
      () =>
        useMemorySearchPage({
          query: "q",
          project: "scoped-project",
          status: ["active", "superseded"],
          limit: 50,
        }),
      { wrapper },
    )

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.exclusions.some((e) => e.tag === "by_project")).toBe(false)
    expect(result.current.exclusions.some((e) => e.tag === "by_status")).toBe(false)
    // The empty strip is what the caveat exists to keep honest — asserted
    // as a UI-visible string in real-memories-view.test.tsx.
    expect(result.current.exclusions).toEqual([])
  })

  it("surfaces a failed load as isError, never as a silent zero-result page", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("both channels failed"))

    const { result } = renderHook(
      () =>
        useMemorySearchPage({
          query: "q",
          project: "all",
          status: ["active", "superseded"],
          limit: 50,
        }),
      { wrapper },
    )

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.rows).toEqual([])
  })
})
