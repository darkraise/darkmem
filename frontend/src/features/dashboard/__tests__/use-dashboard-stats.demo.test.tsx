import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useDashboardStats } from "../use-dashboard-stats"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient()
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("useDashboardStats (DEMO on — standalone fixture)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("serves the demo fixture without ever calling the network", () => {
    const { result } = renderHook(() => useDashboardStats(), { wrapper })
    expect(result.current.isLoading).toBe(false)
    expect(result.current.stats.totalMemories).toBeGreaterThan(0)
    expect(apiFetch).not.toHaveBeenCalled()
  })
})
