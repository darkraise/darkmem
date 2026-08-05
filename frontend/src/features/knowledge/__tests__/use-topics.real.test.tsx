import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useTopics } from "../use-topics"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function topic(overrides: Record<string, unknown> = {}) {
  return {
    project: "darkmem",
    label: "postgres, tuning",
    dominant_entities: [{ name: "postgres", type: "tool", display_name: "Postgres" }],
    impact_rating: 0.8,
    member_count: 6,
    report_status: "ready",
    report: "a report about postgres tuning",
    ...overrides,
  }
}

function suggestion(overrides: Record<string, unknown> = {}) {
  return {
    project: "darkmem",
    subject_key: "postgres::tool",
    dominant_name: "postgres",
    dominant_entity_type: "tool",
    label: "postgres, tuning",
    why: "new",
    member_count: 6,
    verified_fact_count: 3,
    ...overrides,
  }
}

function pins(overrides: Record<string, unknown> = {}) {
  return {
    diff: [],
    suggestions: [],
    pinned_subject_keys: [],
    dismissed_subject_keys: [],
    ...overrides,
  }
}

function route(topics: unknown, pinsBody: unknown) {
  return (path: string) => {
    if (path.startsWith("/knowledge/topics/pin-suggestions")) {
      return Promise.resolve(pinsBody)
    }
    return Promise.resolve(topics)
  }
}

describe("useTopics (DEMO off — the live topics doors)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("carries the backend's four-value report status rather than deriving it", async () => {
    vi.mocked(apiFetch).mockImplementation(
      route(
        {
          items: [
            topic({ report_status: "pending", report: null }),
            topic({ label: "tiny", report_status: "skipped", report: null }),
            topic({ label: "broken", report_status: "failed", report: null }),
          ],
        },
        pins(),
      ) as never,
    )

    const { result } = renderHook(() => useTopics("darkmem"), { wrapper })
    await waitFor(() => expect(result.current.topics).toHaveLength(3))

    // `report == null` cannot tell these three apart, which is exactly why
    // the status is carried and not recomputed from the text.
    expect(result.current.topics.map((t) => t.reportStatus)).toEqual([
      "pending",
      "skipped",
      "failed",
    ])
  })

  it("scopes every read to the requested project", async () => {
    vi.mocked(apiFetch).mockImplementation(route({ items: [] }, pins()) as never)

    renderHook(() => useTopics("other-project"), { wrapper })

    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(2))
    for (const call of vi.mocked(apiFetch).mock.calls) {
      expect(String(call[0])).toContain("project=other-project")
    }
  })

  it("marks a suggestion decided from the durable pinned/dismissed sets", async () => {
    vi.mocked(apiFetch).mockImplementation(
      route(
        { items: [] },
        pins({
          suggestions: [
            suggestion(),
            suggestion({ subject_key: "redis::tool", dominant_name: "redis" }),
            suggestion({ subject_key: "kafka::tool", dominant_name: "kafka" }),
          ],
          pinned_subject_keys: ["postgres::tool"],
          dismissed_subject_keys: ["redis::tool"],
        }),
      ) as never,
    )

    const { result } = renderHook(() => useTopics("darkmem"), { wrapper })
    await waitFor(() => expect(result.current.suggestions).toHaveLength(3))

    expect(result.current.suggestions.map((s) => s.decision)).toEqual([
      "accepted",
      "dismissed",
      null,
    ])
  })

  it("surfaces the cross-run diff, including a decayed label", async () => {
    vi.mocked(apiFetch).mockImplementation(
      route(
        { items: [topic()] },
        pins({
          diff: [
            {
              project: "darkmem",
              label: "postgres, tuning",
              status: "grown",
              dominant_name: "postgres",
              dominant_entity_type: "tool",
              member_count: 6,
              prior_member_count: 3,
            },
            {
              project: "darkmem",
              label: "gone",
              status: "decayed",
              dominant_name: "gone",
              dominant_entity_type: "tool",
              member_count: 0,
              prior_member_count: 4,
            },
          ],
        }),
      ) as never,
    )

    const { result } = renderHook(() => useTopics("darkmem"), { wrapper })
    await waitFor(() => expect(result.current.diff).toHaveLength(2))

    expect(result.current.diff.map((d) => d.status)).toEqual(["grown", "decayed"])
    expect(result.current.diff[0]!.priorMemberCount).toBe(3)
  })

  it("posts a decision keyed on the subject key, never on a community id", async () => {
    vi.mocked(apiFetch).mockImplementation(
      route({ items: [] }, pins({ suggestions: [suggestion()] })) as never,
    )

    const { result } = renderHook(() => useTopics("darkmem"), { wrapper })
    await waitFor(() => expect(result.current.suggestions).toHaveLength(1))

    act(() => result.current.decide("postgres::tool", "accepted"))

    await waitFor(() =>
      expect(
        vi
          .mocked(apiFetch)
          .mock.calls.some(([path]) =>
            String(path).includes("pin-suggestions/accept"),
          ),
      ).toBe(true),
    )
    const call = vi
      .mocked(apiFetch)
      .mock.calls.find(([path]) => String(path).includes("/accept"))
    expect(call).toBeDefined()
    const body = JSON.parse(String((call![1] as RequestInit).body))
    expect(body).toEqual({ project: "darkmem", subject_key: "postgres::tool" })
    expect(Object.keys(body)).not.toContain("community_id")
  })

  it("routes dismiss to its own door", async () => {
    vi.mocked(apiFetch).mockImplementation(
      route({ items: [] }, pins({ suggestions: [suggestion()] })) as never,
    )

    const { result } = renderHook(() => useTopics("darkmem"), { wrapper })
    await waitFor(() => expect(result.current.suggestions).toHaveLength(1))

    act(() => result.current.decide("postgres::tool", "dismissed"))

    await waitFor(() =>
      expect(
        vi
          .mocked(apiFetch)
          .mock.calls.some(([path]) =>
            String(path).includes("pin-suggestions/dismiss"),
          ),
      ).toBe(true),
    )
  })

  it("reports no last detection run rather than inventing one", async () => {
    vi.mocked(apiFetch).mockImplementation(route({ items: [] }, pins()) as never)

    const { result } = renderHook(() => useTopics("darkmem"), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    // The live doors serve no run timestamp; a plausible-looking one would
    // be the surface asserting something the backend never said.
    expect(result.current.lastRun).toBeNull()
  })
})
