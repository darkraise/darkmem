import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// The render half of T2.39. The adapter suite beside this one proves the row
// shape; these exercise what the surface actually puts on screen — the four
// report states said apart, the cross-run status, both decision verbs
// round-tripping, and the detail-level preference honoured.
vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useDetailLevel } from "@/components/darkmem"
import { TopicsForProject } from "../components/topics-tab"

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

function serve(topics: unknown[], pinsBody: Record<string, unknown> = {}) {
  vi.mocked(apiFetch).mockImplementation(((path: string) => {
    if (path.startsWith("/knowledge/topics/pin-suggestions")) {
      return Promise.resolve({
        diff: [],
        suggestions: [],
        pinned_subject_keys: [],
        dismissed_subject_keys: [],
        ...pinsBody,
      })
    }
    return Promise.resolve({ items: topics })
  }) as never)
}

function renderTab() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
  return render(<TopicsForProject project="darkmem" />, { wrapper: Wrapper })
}

describe("TopicsTab (live doors)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("renders a pending report as pending, not as an empty report", async () => {
    serve([topic({ report_status: "pending", report: null })])
    renderTab()

    expect(await screen.findByText(/not generated yet/i)).toBeInTheDocument()
    expect(screen.queryByText(/a report about/i)).not.toBeInTheDocument()
  })

  it("says skipped and pending differently — one resolves later, one never will", async () => {
    serve([
      topic({ report_status: "pending", report: null }),
      topic({ label: "tiny topic", report_status: "skipped", report: null }),
    ])
    renderTab()

    expect(await screen.findByText(/not generated yet/i)).toBeInTheDocument()
    expect(
      screen.getByText(/too small for a report — this one will not get one/i),
    ).toBeInTheDocument()
  })

  it("renders a ready report as its text", async () => {
    serve([topic()])
    renderTab()

    expect(
      await screen.findByText("a report about postgres tuning"),
    ).toBeInTheDocument()
  })

  it("shows what changed between runs on the topic it belongs to", async () => {
    serve([topic()], {
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
      ],
    })
    renderTab()

    expect(await screen.findByText("grown")).toBeInTheDocument()
    expect(screen.getByText(/previous run: 3 members/i)).toBeInTheDocument()
  })

  it("honours the simple detail level by dropping the cross-run arithmetic", async () => {
    useDetailLevel.setState({ level: "simple" })
    serve([topic()], {
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
      ],
    })
    renderTab()

    // The status itself is the honest signal and stays in every level; only
    // the counts it was derived from are advanced-only.
    expect(await screen.findByText("grown")).toBeInTheDocument()
    expect(screen.queryByText(/previous run:/i)).not.toBeInTheDocument()
  })

  it("hides the raw subject key at the simple level and shows it at advanced", async () => {
    serve([], { suggestions: [suggestion()] })
    const { unmount } = renderTab()
    expect(await screen.findByText(/subject key: postgres::tool/i)).toBeInTheDocument()
    unmount()

    useDetailLevel.setState({ level: "simple" })
    serve([], { suggestions: [suggestion()] })
    renderTab()
    await screen.findByText(/anchors 3 verified facts/i)
    expect(screen.queryByText(/subject key:/i)).not.toBeInTheDocument()
  })

  it("round-trips accept through the door, keyed on the subject key", async () => {
    serve([], { suggestions: [suggestion()] })
    renderTab()

    await userEvent.click(await screen.findByRole("button", { name: /accept/i }))

    await waitFor(() => {
      const call = vi
        .mocked(apiFetch)
        .mock.calls.find(([path]) => String(path).includes("/accept"))
      expect(call).toBeDefined()
      expect(JSON.parse(String((call?.[1] as RequestInit).body))).toEqual({
        project: "darkmem",
        subject_key: "postgres::tool",
      })
    })
  })

  it("round-trips dismiss through its own door", async () => {
    serve([], { suggestions: [suggestion()] })
    renderTab()

    await userEvent.click(await screen.findByRole("button", { name: /dismiss/i }))

    await waitFor(() =>
      expect(
        vi
          .mocked(apiFetch)
          .mock.calls.some(([path]) => String(path).includes("/dismiss")),
      ).toBe(true),
    )
  })

  it("renders an already-decided suggestion as decided rather than re-offering it", async () => {
    serve([], {
      suggestions: [suggestion()],
      pinned_subject_keys: ["postgres::tool"],
    })
    renderTab()

    expect(await screen.findByText(/pinned —/i)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /accept/i })).not.toBeInTheDocument()
  })

  it("says the last detection run is not reported rather than inventing a time", async () => {
    serve([topic()])
    renderTab()

    expect(
      await screen.findByText(/last detection run: not reported/i),
    ).toBeInTheDocument()
  })
})
