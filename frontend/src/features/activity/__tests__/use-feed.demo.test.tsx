import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useFeed } from "../use-feed"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient()
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("useFeed (DEMO on — standalone fixture)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("serves the demo fixture without ever calling the network", () => {
    const { result } = renderHook(() => useFeed(), { wrapper })
    expect(result.current.isLoading).toBe(false)
    expect(result.current.isError).toBe(false)
    expect(result.current.events.length).toBeGreaterThan(0)
    expect(apiFetch).not.toHaveBeenCalled()
  })
})
