import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/demo/flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useFeed } from "../use-feed"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("useFeed (DEMO off — real /events)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("hits /events with no aggregation — items pass through verbatim", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [
        {
          id: 1,
          created_at: "2026-07-27T18:55:00Z",
          event_type: "superseded",
          object_type: "memory",
          object_id: "11111111-2222-3333-4444-555555555555",
          project: "darkmem",
          actor: null,
          api_key_id: null,
          source: null,
          payload: {},
        },
      ],
      total: 1,
    })
    const { result } = renderHook(() => useFeed(), { wrapper })
    expect(result.current.isLoading).toBe(true)

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(apiFetch).toHaveBeenCalledWith(expect.stringContaining("/events"))
    expect(result.current.isError).toBe(false)
    expect(result.current.events).toHaveLength(1)
    expect(result.current.events[0]!.type).toBe("superseded")
    expect(result.current.events[0]!.badge).toBe("superseded")
  })

  it("surfaces a failed load as isError, not as an empty feed", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    const { result } = renderHook(() => useFeed(), { wrapper })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.events).toEqual([])
  })
})
