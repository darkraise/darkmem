import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useDashboardActivity } from "../use-dashboard-activity"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient()
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("useDashboardActivity (DEMO on — standalone fixture)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("serves the demo fixture without ever calling the network", () => {
    const { result } = renderHook(() => useDashboardActivity(), { wrapper })
    expect(result.current.events.length).toBeGreaterThan(0)
    expect(apiFetch).not.toHaveBeenCalled()
  })
})
