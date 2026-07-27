import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/demo/flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useContributionCalendar } from "../use-contribution-calendar"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const NOW = new Date("2026-07-25T18:00:00Z").getTime()

describe("useContributionCalendar (DEMO off — real /events/calendar)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("hits /events/calendar and zero-fills the window from its buckets", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      buckets: [{ day: "2026-07-25", count: 4 }],
    })
    const { result } = renderHook(() => useContributionCalendar(NOW), {
      wrapper,
    })
    expect(result.current.isLoading).toBe(true)

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(apiFetch).toHaveBeenCalledWith(
      expect.stringContaining("/events/calendar"),
    )
    expect(result.current.isError).toBe(false)
    expect(result.current.days[result.current.days.length - 1]!.count).toBe(4)
    expect(result.current.days.some((d) => d.date === "2026-07-24")).toBe(true)
  })

  it("surfaces a failed load as isError, not as a zero-filled grid", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    const { result } = renderHook(() => useContributionCalendar(NOW), {
      wrapper,
    })

    await waitFor(() => expect(result.current.isError).toBe(true))
    // No fabricated days for a failed load — the caller renders an error,
    // not an all-muted grid indistinguishable from a genuinely quiet month.
    expect(result.current.days).toEqual([])
  })
})
