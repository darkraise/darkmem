import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import {
  useHygieneCountsRows,
  useHygieneDuplicateRows,
  useHygieneLowConfidenceRows,
  useHygieneSupersededRows,
} from "../use-hygiene-queue"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const QUERY = { limit: 10, offset: 0 }

describe("useHygieneDuplicateRows (DEMO off — real /hygiene-queue/duplicates)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("carries only what the backend actually returns — no fabricated content preview", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [
        {
          id: "rel1",
          source_memory_id: "m1",
          target_memory_id: "m2",
          rel_type: "near_duplicate",
          project: "darkmem",
          score: 0.91,
          verdict: "likely_duplicate",
          hygiene_state: "open",
          detected_at: "2026-07-30T00:00:00Z",
          created_at: "2026-07-30T00:00:00Z",
        },
      ],
      total: 4,
      limit: 10,
      offset: 0,
    })
    const { result } = renderHook(() => useHygieneDuplicateRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.total).toBe(4)
    const row = result.current.rows[0]!
    expect(row.source_memory_id).toBe("m1")
    expect(row.target_memory_id).toBe("m2")
    expect(row.score).toBe(0.91)
    expect(Object.keys(row)).not.toContain("content_preview")
  })

  it("reports a failed read as an error, never as an empty queue", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    const { result } = renderHook(() => useHygieneDuplicateRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.error).toBe(true))

    expect(result.current.rows).toEqual([])
    expect(result.current.total).toBe(0)
  })

  it("sends project as a server-side predicate", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [], total: 0, limit: 10, offset: 0 })
    renderHook(() => useHygieneDuplicateRows({ ...QUERY, project: "darkmem" }), { wrapper })
    await waitFor(() => expect(apiFetch).toHaveBeenCalled())

    const url = vi.mocked(apiFetch).mock.calls[0]![0] as string
    expect(url).toContain("project=darkmem")
  })
})

describe("useHygieneLowConfidenceRows / useHygieneSupersededRows", () => {
  beforeEach(() => vi.clearAllMocks())

  it("reports the server's total for low-confidence memories, not the page length", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [
        {
          id: "m3",
          project: "darkmem",
          content_preview: "a low-confidence capture",
          confidence: 0.2,
          expires_at: null,
          status: "active",
          superseded_by: null,
          reason: "low_confidence",
          created_at: "2026-07-01T00:00:00Z",
        },
      ],
      total: 57,
      limit: 10,
      offset: 0,
    })
    const { result } = renderHook(() => useHygieneLowConfidenceRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.rows).toHaveLength(1)
    expect(result.current.total).toBe(57)
  })

  it("carries the superseded arm's own status and reason verbatim", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [
        {
          id: "m4",
          project: "darkmem",
          content_preview: "a retired capture",
          confidence: 0.6,
          expires_at: null,
          status: "superseded",
          superseded_by: "m5",
          reason: "superseded_lineage",
          created_at: "2026-06-01T00:00:00Z",
        },
      ],
      total: 1,
      limit: 10,
      offset: 0,
    })
    const { result } = renderHook(() => useHygieneSupersededRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.rows[0]!.status).toBe("superseded")
    expect(result.current.rows[0]!.superseded_by).toBe("m5")
  })
})

describe("useHygieneCountsRows", () => {
  beforeEach(() => vi.clearAllMocks())

  it("passes the project filter through to the counts door — unlike the review queue's, this one accepts it", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      duplicates: 2,
      low_confidence: 5,
      expiring_soon: 1,
      superseded: 9,
    })
    const { result } = renderHook(() => useHygieneCountsRows({ project: "darkmem" }), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.duplicates).toBe(2)
    expect(result.current.superseded).toBe(9)
    const url = vi.mocked(apiFetch).mock.calls[0]![0] as string
    expect(url).toContain("project=darkmem")
  })

  it("reports a failed read as an error", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    const { result } = renderHook(() => useHygieneCountsRows({}), { wrapper })
    await waitFor(() => expect(result.current.error).toBe(true))
  })
})
