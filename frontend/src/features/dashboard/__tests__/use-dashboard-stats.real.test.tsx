import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useDashboardStats } from "../use-dashboard-stats"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

/** Routes each dashboard query to its own fixture by URL. */
function route(overrides: Record<string, unknown> = {}) {
  vi.mocked(apiFetch).mockImplementation(async (path: string) => {
    if (path.startsWith("/analytics/stats"))
      return overrides.stats ?? { memories: 0, tags: 0, entities: 0, relationships: 0, sources: [] }
    if (path.includes("verification_status=corroborated"))
      return overrides.corroborated ?? { items: [], total: 0, limit: 1, offset: 0 }
    if (path.includes("verification_status=confirmed"))
      return overrides.confirmed ?? { items: [], total: 0, limit: 1, offset: 0 }
    if (path.includes("verification_status=disputed"))
      return overrides.disputed ?? { items: [], total: 0, limit: 1, offset: 0 }
    if (path.startsWith("/knowledge/articles"))
      return overrides.articles ?? { items: [], total: 0, limit: 1, offset: 0 }
    if (path.startsWith("/review-queue/counts"))
      return overrides.review ?? { facts: 0, articles: 0 }
    throw new Error(`unexpected path ${path}`)
  })
}

describe("useDashboardStats (DEMO off — real API)", () => {
  beforeEach(() => vi.clearAllMocks())

  // The bug this hook exists to close: the dashboard read the 5010-row demo
  // store unconditionally, so an empty vault still advertised 5010 memories
  // while the memories page correctly showed none.
  it("reports zero against an empty vault instead of the fixture count", async () => {
    route()
    const { result } = renderHook(() => useDashboardStats(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.stats.totalMemories).toBe(0)
    expect(result.current.stats.verifiedFacts).toBe(0)
    expect(result.current.stats.liveArticles).toBe(0)
    expect(result.current.stats.pendingReview).toBe(0)
    expect(result.current.stats.disputedFacts).toBe(0)
  })

  it("takes the memory count from /analytics/stats", async () => {
    route({ stats: { memories: 42, tags: 0, entities: 0, relationships: 0, sources: [] } })
    const { result } = renderHook(() => useDashboardStats(), { wrapper })

    await waitFor(() => expect(result.current.stats.totalMemories).toBe(42))
  })

  it("counts a verified fact as corroborated plus confirmed", async () => {
    route({
      corroborated: { items: [], total: 5, limit: 1, offset: 0 },
      confirmed: { items: [], total: 3, limit: 1, offset: 0 },
      disputed: { items: [], total: 2, limit: 1, offset: 0 },
    })
    const { result } = renderHook(() => useDashboardStats(), { wrapper })

    await waitFor(() => expect(result.current.stats.verifiedFacts).toBe(8))
    // Disputed is its own tile caption and must not be folded into verified.
    expect(result.current.stats.disputedFacts).toBe(2)
  })

  it("sums the review queue's two arms into pending review", async () => {
    route({ review: { facts: 4, articles: 3 } })
    const { result } = renderHook(() => useDashboardStats(), { wrapper })

    await waitFor(() => expect(result.current.stats.pendingReview).toBe(7))
  })

  it("takes live articles from the article list total", async () => {
    route({ articles: { items: [], total: 9, limit: 1, offset: 0 } })
    const { result } = renderHook(() => useDashboardStats(), { wrapper })

    await waitFor(() => expect(result.current.stats.liveArticles).toBe(9))
  })

  it("surfaces a failed load as isError rather than a fabricated zero", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    const { result } = renderHook(() => useDashboardStats(), { wrapper })

    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})
