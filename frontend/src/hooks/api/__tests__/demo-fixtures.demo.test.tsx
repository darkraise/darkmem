import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useProjects, useUsageOverview, useUsageSeries } from "@/hooks/api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

afterEach(() => vi.clearAllMocks())

describe("demo fixtures reach the hooks without a request", () => {
  it("serves the project catalogue", () => {
    const { result } = renderHook(() => useProjects(), { wrapper })
    expect(result.current.isSuccess).toBe(true)
    expect(result.current.data?.map((p) => p.name)).toEqual([
      "default",
      "darkmem",
      "acme-storefront",
      "notes",
    ])
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it("serves a usage overview and series for every window", () => {
    for (const window of ["24h", "7d", "30d", "all"] as const) {
      const overview = renderHook(() => useUsageOverview(window), { wrapper })
      const series = renderHook(() => useUsageSeries(window), { wrapper })
      expect(overview.result.current.data?.total_calls).toBeGreaterThan(0)
      expect(series.result.current.data?.buckets.length).toBeGreaterThan(0)
    }
    expect(apiFetch).not.toHaveBeenCalled()
  })
})
