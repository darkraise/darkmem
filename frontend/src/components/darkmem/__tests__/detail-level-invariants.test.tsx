import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// T1.48 — the detail-level preference honoured across advanced surfaces.
// Invariant 14: `simple` collapses technical detail (per-modality/fused
// scores, arm breakdowns, fingerprints, origin-row detail) to one plain
// line, and NEVER hides an honesty signal (verification badges, layer
// labels, superseded/stale labels, exclusion counts). This suite asserts
// that rule across every surface the flag already reaches, and proves the
// preference only changes rendering, never the request.

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({
    children,
    to: _to,
    params: _params,
    ...rest
  }: {
    children?: ReactNode
    to?: string
    params?: unknown
    [key: string]: unknown
  }) => <a {...rest}>{children}</a>,
}))

import { apiFetch } from "@/lib/api"
import { useDetailLevel } from "../use-detail-level"
import { MemoryRow } from "@/features/memories/components/memory-row"
import { RealMemoriesView } from "@/features/memories/components/real-memories-view"
import { FactSourcesGroups } from "@/features/knowledge/components/fact-sources"
import { ReviewQueue } from "@/features/knowledge/components/review-queue"

// FactSource stays in @/demo/types: T1.68 (the type-relocation task T1.67's
// falsification opened) found no real Knowledge-vault binding anywhere in
// the codebase, so nothing outside fact-sources.tsx's demo-only consumer
// ever needs it. This file defines its own structurally-equivalent shape
// rather than importing it anyway, so it never depended on that move
// either way (T1.64 plan §5.4).
interface TestFactSource {
  origin_key: string
  kind: "memory" | "code" | "block" | "human"
  ref: string
  detail: string
  at: string
}

const TRACE = {
  channels: [
    { name: "semantic", fraction: 0.81 },
    { name: "keyword", fraction: 0.4 },
  ],
  rrfScore: 0.0271,
  summary: "semantic 0.81, keyword 0.40 — fused into rrf_score 0.0271.",
}

const SUPERSEDED_ROW = {
  id: "m1",
  content: "the superseded row",
  tags: [],
  source: "mcp",
  created_at: new Date().toISOString(),
  layer: 0 as const,
  status: "superseded" as const,
  verification_status: "corroborated" as const,
  verification_detail: "asserted by 3 distinct origins, no known contradiction",
}

describe("detail level: MemoryRow honesty labels render in both modes", () => {
  beforeEach(() => {
    useDetailLevel.setState({ level: "advanced" })
  })

  it.each(["simple", "advanced"] as const)(
    "layer chip, lifecycle badge, and verification badge all render in %s mode",
    (level) => {
      useDetailLevel.setState({ level })
      render(
        <MemoryRow
          memory={SUPERSEDED_ROW}
          trace={TRACE}
          expanded
          onToggleTrace={vi.fn()}
        />,
      )
      expect(screen.getByText("L0 · memory")).toBeInTheDocument()
      expect(screen.getByText("superseded")).toBeInTheDocument()
      expect(screen.getByText("corroborated")).toBeInTheDocument()
    },
  )

  it("collapses only the score breakdown in simple mode — never the row's own badges", () => {
    useDetailLevel.setState({ level: "simple" })
    render(
      <MemoryRow
        memory={SUPERSEDED_ROW}
        trace={TRACE}
        expanded
        onToggleTrace={vi.fn()}
      />,
    )
    // Collapsed: the technical breakdown is gone.
    expect(screen.queryByText("rrf_score")).not.toBeInTheDocument()
    expect(screen.queryByText("semantic")).not.toBeInTheDocument()
    // Never collapsed: the row's own honesty labels.
    expect(screen.getByText("L0 · memory")).toBeInTheDocument()
    expect(screen.getByText("superseded")).toBeInTheDocument()
    expect(screen.getByText("corroborated")).toBeInTheDocument()
    expect(screen.getByText(/Why it ranked:/)).toBeInTheDocument()
  })
})

const SOURCES: TestFactSource[] = [
  {
    origin_key: "session-a",
    kind: "memory",
    ref: "memory abc12345",
    detail: "captured this fact first",
    at: "2026-06-01 09:00",
  },
  {
    origin_key: "session-b",
    kind: "code",
    ref: "code@def6789",
    detail: "parsed from source",
    at: "2026-06-02 10:00",
  },
]

describe("detail level: fact-sources honesty count renders in both modes", () => {
  beforeEach(() => {
    useDetailLevel.setState({ level: "advanced" })
  })

  it.each(["simple", "advanced"] as const)(
    "origin kind, origin_key, and the distinct-origin count all render in %s mode",
    (level) => {
      useDetailLevel.setState({ level })
      render(<FactSourcesGroups sources={SOURCES} />)
      expect(screen.getByText("origin_key: session-a")).toBeInTheDocument()
      expect(screen.getByText("origin_key: session-b")).toBeInTheDocument()
      expect(
        screen.getByText(/COUNT\(DISTINCT origin_key\)/),
      ).toBeInTheDocument()
      expect(screen.getByText("2")).toBeInTheDocument()
    },
  )

  it("hides the raw per-source rows in simple mode, never the origin count", () => {
    useDetailLevel.setState({ level: "simple" })
    render(<FactSourcesGroups sources={SOURCES} />)
    expect(screen.queryByText("memory abc12345")).not.toBeInTheDocument()
    expect(screen.getByText("origin_key: session-a")).toBeInTheDocument()
  })
})

describe("detail level: preference persists in localStorage and never touches the request", () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("persists the chosen level under the darkmem-detail-level key", () => {
    useDetailLevel.getState().setLevel("simple")
    const stored = JSON.parse(
      localStorage.getItem("darkmem-detail-level") ?? "{}",
    )
    expect(stored.state.level).toBe("simple")
  })

  it("never sends detail level as a search request parameter, and toggling fires no new request", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
      envelope: {
        query: "",
        channels: {},
        reranked: false,
        weights: {},
        excluded: {},
      },
    })

    function wrapper({ children }: { children: ReactNode }) {
      const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
      return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    }

    render(<RealMemoriesView />, { wrapper })
    await screen.findByText(/no memories captured yet/i)

    const callsBeforeToggle = vi.mocked(apiFetch).mock.calls.length
    useDetailLevel.setState({ level: "simple" })
    useDetailLevel.setState({ level: "advanced" })

    // Toggling the client-only rendering preference must not issue a new
    // request — the fetch call count is unchanged, and every call made so
    // far carries no detail-level key of any kind.
    expect(vi.mocked(apiFetch).mock.calls.length).toBe(callsBeforeToggle)
    for (const call of vi.mocked(apiFetch).mock.calls) {
      const init = call[1] as { body?: string } | undefined
      if (init?.body) {
        expect(init.body).not.toMatch(/detail.?level/i)
      }
    }
  })
})

// T2.37 — the review queue is a new surface this flag must reach. Unlike
// the Facts tab (which the reviewer found sits entirely outside this file's
// coverage, making its own Simple/Advanced Done-when clause vacuous), the
// review queue's honesty labels are asserted here at the render, gated by
// an actual `useDetailLevel` read in `review-queue.tsx` — not a bare `<p>`
// that happens to always render.
const REVIEW_CONSEQUENCE = {
  score: 0.42,
  tier: 1,
  retrieval_frequency: {
    source_memories: 3,
    peak_access_count: 12,
    last_accessed: "2026-07-01T00:00:00Z",
    decayed_access: 0.41,
    half_life_days: 30,
    weight: 0.5,
    component: 0.2,
  },
  subject_salience: { neighbour_count: 4, weight: 0.5, component: 0.15 },
  staleness: {
    stale: false,
    label: "fresh",
    dispute_opened_at: null,
    dispute_age_days: null,
    threshold_days: 14,
  },
}

function reviewQueueWrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("detail level: the review queue's honesty labels survive Simple mode", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 1, articles: 0 }
      if (url.startsWith("/review-queue/facts")) {
        return {
          items: [
            {
              id: "f1",
              subject_name: "darkmem",
              object_name: "postgres",
              rel_type: "USES",
              fact: "darkmem uses postgres",
              project: "darkmem",
              valid_at: null,
              invalid_at: null,
              expired_at: null,
              verification_status: "disputed",
              confidence: 0.4,
              review_state: "open",
              demotion_pending_since: null,
              reason: "disputed",
              evidence: null,
              consequence: REVIEW_CONSEQUENCE,
              created_at: "2026-08-01T00:00:00Z",
            },
          ],
          total: 1,
          limit: 10,
          offset: 0,
        }
      }
      if (url.startsWith("/review-queue/articles")) {
        return { items: [], total: 0, limit: 10, offset: 0 }
      }
      throw new Error(`unexpected apiFetch call: ${url}`)
    })
  })

  it.each(["simple", "advanced"] as const)(
    "the verification badge, queued-reason chip, and rank_note all render in %s mode",
    async (level) => {
      useDetailLevel.setState({ level })
      render(<ReviewQueue />, { wrapper: reviewQueueWrapper })

      expect(await screen.findByText(/why ranked here:/)).toBeInTheDocument()
      expect(screen.getByText("disputed")).toBeInTheDocument()
      expect(screen.getByText(/queued: disputed/)).toBeInTheDocument()
    },
  )

  it("collapses only the consequence breakdown in simple mode — never the row's own badges", async () => {
    useDetailLevel.setState({ level: "simple" })
    render(<ReviewQueue />, { wrapper: reviewQueueWrapper })

    await screen.findByText(/why ranked here:/)
    // Collapsed: the technical per-arm breakdown.
    expect(screen.queryByText(/retrieval_frequency:/)).not.toBeInTheDocument()
    // Never collapsed: the row's own honesty labels.
    expect(screen.getByText("disputed")).toBeInTheDocument()
    expect(screen.getByText(/queued: disputed/)).toBeInTheDocument()
  })

  it("shows the consequence breakdown in advanced mode", async () => {
    useDetailLevel.setState({ level: "advanced" })
    render(<ReviewQueue />, { wrapper: reviewQueueWrapper })

    await screen.findByText(/why ranked here:/)
    expect(screen.getByText(/retrieval_frequency:/)).toBeInTheDocument()
  })
})
