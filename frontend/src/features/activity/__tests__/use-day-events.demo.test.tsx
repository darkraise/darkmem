import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/demo/flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { DAY_DRILL_DEFAULT } from "@/demo/data/activity-curated"
import { useDayEvents } from "../use-day-events"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient()
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("useDayEvents (DEMO on — standalone fixture)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("serves the curated day bucket without ever calling the network", () => {
    const { result } = renderHook(() => useDayEvents(DAY_DRILL_DEFAULT), {
      wrapper,
    })
    expect(result.current.isLoading).toBe(false)
    expect(result.current.isError).toBe(false)
    expect(result.current.events).not.toBeNull()
    expect(result.current.events!.length).toBeGreaterThan(0)
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it("returns null events for a day with no curated bucket", () => {
    const { result } = renderHook(() => useDayEvents("2020-01-01"), {
      wrapper,
    })
    expect(result.current.events).toBeNull()
    expect(result.current.total).toBe(0)
  })
})
