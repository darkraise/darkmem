import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
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

  it("counts memory captures only, not every journal row", async () => {
    // Every cell reads "N memories captured"; an unscoped count took in
    // logins and maintenance runs and showed captures on an empty install.
    vi.mocked(apiFetch).mockResolvedValue({ buckets: [] } as never)
    const { result } = renderHook(() => useContributionCalendar(NOW), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    const paths = vi.mocked(apiFetch).mock.calls.map(([path]) => path as string)
    const main = paths.find((p) => !p.includes("event_type=inject"))
    expect(main).toContain("event_type=created")
    expect(main).toContain("object_type=memory")
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

describe("the inject overlay (T3.20, doc 13 §6.5)", () => {
  beforeEach(() => vi.clearAllMocks())

  function routeCalendar(all: unknown[], injects: unknown[]) {
    vi.mocked(apiFetch).mockImplementation(async (path: string) =>
      (path.includes("event_type=inject")
        ? { buckets: injects }
        : { buckets: all }) as never,
    )
  }

  it("asks the server for the inject series rather than splitting the total", async () => {
    // The endpoint returns counts, not rows — there is nothing client-side to
    // slice, and a subtraction would be inventing a breakdown.
    routeCalendar([{ day: "2026-07-25", count: 4 }], [{ day: "2026-07-25", count: 2 }])
    const { result } = renderHook(() => useContributionCalendar(NOW), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    await waitFor(() =>
      expect(result.current.days[result.current.days.length - 1]!.count).toBe(4),
    )
    expect(
      vi.mocked(apiFetch).mock.calls.some(([path]) =>
        (path as string).includes("event_type=inject"),
      ),
    ).toBe(true)
  })

  it("marks the days that hold an inject, and only those", async () => {
    routeCalendar(
      [
        { day: "2026-07-24", count: 3 },
        { day: "2026-07-25", count: 4 },
      ],
      [{ day: "2026-07-25", count: 2 }],
    )
    const { result } = renderHook(() => useContributionCalendar(NOW), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    await waitFor(() =>
      expect(
        result.current.days.find((d) => d.date === "2026-07-25")!.injects,
      ).toBe(2),
    )

    expect(result.current.days.find((d) => d.date === "2026-07-24")!.injects).toBe(0)
  })

  it("draws the calendar it does have when only the overlay fails", async () => {
    // A calendar that refused to render because the inject series was
    // unavailable would hide the activity it does know about.
    vi.mocked(apiFetch).mockImplementation(async (path: string) => {
      if (path.includes("event_type=inject")) throw new Error("overlay down")
      return { buckets: [{ day: "2026-07-25", count: 4 }] } as never
    })
    const { result } = renderHook(() => useContributionCalendar(NOW), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.isError).toBe(false)
    expect(result.current.days[result.current.days.length - 1]!.count).toBe(4)
    expect(result.current.days[result.current.days.length - 1]!.injects).toBe(0)
  })
})
