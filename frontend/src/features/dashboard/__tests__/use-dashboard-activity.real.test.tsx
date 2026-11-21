import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useDashboardActivity } from "../use-dashboard-activity"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const ROW = {
  id: 55,
  created_at: "2026-08-18T03:55:39.622609Z",
  event_type: "extracted",
  object_type: "memory",
  object_id: "0d2f9c11-aaaa-bbbb-cccc-1234567890ab",
  project: "default",
  actor: null,
  api_key_id: null,
  source: null,
  payload: { outcome: "completed" },
}

describe("useDashboardActivity (DEMO off — real /events)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("renders an empty feed for an empty journal rather than fixture rows", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [], total: 0 })
    const { result } = renderHook(() => useDashboardActivity(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(apiFetch).toHaveBeenCalledWith(expect.stringContaining("/events"), expect.objectContaining({ signal: expect.any(AbortSignal) }))
    expect(result.current.events).toEqual([])
  })

  it("maps a journal row onto the feed item the dashboard renders", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [ROW], total: 1 })
    const { result } = renderHook(() => useDashboardActivity(), { wrapper })

    await waitFor(() => expect(result.current.events.length).toBe(1))
    const event = result.current.events[0]!
    expect(event.id).toBe("55")
    expect(event.at).toBe(ROW.created_at)
    // Icon lookup is Record<kind, Icon> — an unmapped kind renders undefined
    // and throws in ActivityFeedItem, so every row must land on a real kind.
    expect(["memory", "fact", "article", "pipeline", "job", "review"]).toContain(
      event.kind,
    )
    expect(event.title.length).toBeGreaterThan(0)
  })

  it("titles an event with its initialisms upper-cased", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [{ ...ROW, event_type: "api_key_revoked", object_type: "system" }],
      total: 1,
    })
    const { result } = renderHook(() => useDashboardActivity(), { wrapper })

    await waitFor(() => expect(result.current.events.length).toBe(1))
    expect(result.current.events[0]!.title).toBe("API key revoked")
  })

  it("gives an unknown event type a renderable kind rather than undefined", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [{ ...ROW, event_type: "some_future_event" }],
      total: 1,
    })
    const { result } = renderHook(() => useDashboardActivity(), { wrapper })

    await waitFor(() => expect(result.current.events.length).toBe(1))
    expect(["memory", "fact", "article", "pipeline", "job", "review"]).toContain(
      result.current.events[0]!.kind,
    )
  })

  it("leaves sign-in and setup rows to their own reader", async () => {
    const logins = Array.from({ length: 10 }, (_, i) => ({
      ...ROW,
      id: 100 + i,
      event_type: i % 2 ? "auth_login_failed" : "auth_login_success",
      object_type: null,
      object_id: null,
    }))
    vi.mocked(apiFetch).mockResolvedValue({
      items: [...logins, { ...ROW, event_type: "setup_complete" }, ROW],
      total: 12,
    })
    const { result } = renderHook(() => useDashboardActivity(), { wrapper })

    await waitFor(() => expect(result.current.events.length).toBe(1))
    expect(result.current.events[0]!.id).toBe("55")
  })

  it("surfaces a failed load as isError", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    const { result } = renderHook(() => useDashboardActivity(), { wrapper })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.events).toEqual([])
  })
})
