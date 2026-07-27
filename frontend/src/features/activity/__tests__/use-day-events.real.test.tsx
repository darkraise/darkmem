import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/demo/flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useDayEvents } from "../use-day-events"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("useDayEvents (DEMO off — real /events, UTC day window)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("windows /events to the UTC day boundary, never re-bucketing locally", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [], total: 0 })
    const { result } = renderHook(() => useDayEvents("2026-07-20"), {
      wrapper,
    })
    await waitFor(() => expect(result.current.events).not.toBeNull())

    const url = vi.mocked(apiFetch).mock.calls[0]![0] as string
    expect(url).toContain("since=2026-07-20T00%3A00%3A00.000Z")
    expect(url).toContain("until=2026-07-21T00%3A00%3A00.000Z")
  })

  it("reports total from the server, and flags truncation honestly", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [
        {
          id: 1,
          created_at: "2026-07-20T09:41:00Z",
          event_type: "verified",
          object_type: "fact",
          object_id: null,
          project: "darkmem",
          actor: null,
          api_key_id: null,
          source: null,
          payload: {},
        },
      ],
      total: 250,
    })
    const { result } = renderHook(() => useDayEvents("2026-07-20"), {
      wrapper,
    })
    await waitFor(() => expect(result.current.events).not.toBeNull())
    expect(result.current.total).toBe(250)
    expect(result.current.truncated).toBe(true)
  })

  it("surfaces a failed load as isError, not as an empty day", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    const { result } = renderHook(() => useDayEvents("2026-07-20"), {
      wrapper,
    })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.events).toBeNull()
  })
})
