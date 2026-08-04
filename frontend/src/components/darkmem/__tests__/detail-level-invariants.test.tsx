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
import { LiveDreamDigest } from "@/features/activity/components/dream-tab"
import { ReviewQueue } from "@/features/knowledge/components/review-queue"
import { FactRow } from "@/features/knowledge/components/facts-tab"
import { FactDetail } from "@/features/knowledge/components/fact-detail"
import type { FactRowData } from "@/features/knowledge/use-facts"

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

const DREAM_CYCLE_ID = "20260803-01"
const DREAM_OBJECT_ID = "33333333-3333-3333-3333-333333333333"

function dreamCyclesFixture() {
  return {
    items: [
      {
        cycle_id: DREAM_CYCLE_ID,
        started_at: "2026-08-03T02:00:00Z",
        ended_at: "2026-08-03T02:05:00Z",
        projects: ["darkmem"],
        total: 1,
        counts: { subsume: 1, associate: 0, refine: 0 },
        undone_count: 0,
        origin: null,
      },
    ],
    total: 1,
    limit: 20,
    offset: 0,
  }
}

function dreamDigestFixture() {
  return {
    cycle_id: DREAM_CYCLE_ID,
    started_at: "2026-08-03T02:00:00Z",
    ended_at: "2026-08-03T02:05:00Z",
    counts: { subsume: 1, associate: 0, refine: 0 },
    undone_count: 0,
    objects: [
      {
        object_id: DREAM_OBJECT_ID,
        project: "darkmem",
        actions: [
          {
            event_id: 201,
            created_at: "2026-08-03T02:01:00Z",
            action: "subsume",
            object_id: DREAM_OBJECT_ID,
            project: "darkmem",
            detector: "dedup",
            origin: null,
            actor: null,
            before: { status: "active" },
            after: { status: "superseded" },
            detail: { verdict: "dup", score: 0.9 },
            undone: false,
            undone_at: null,
            undone_by: null,
            undo_batch_id: null,
            restored: [],
            not_restored: [],
            undoable: true,
            undo_blocked_reason: null,
          },
        ],
      },
    ],
  }
}

describe("detail level: dream digest honesty labels render in both modes", () => {
  function queryWrapper({ children }: { children: ReactNode }) {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }

  beforeEach(() => {
    useDetailLevel.setState({ level: "advanced" })
    vi.mocked(apiFetch).mockImplementation((path: unknown) => {
      const p = String(path)
      if (p.startsWith("/dream-digest/cycles/")) {
        return Promise.resolve(dreamDigestFixture())
      }
      return Promise.resolve(dreamCyclesFixture())
    })
  })

  it.each(["simple", "advanced"] as const)(
    "the undo control and the before/after diff both render in %s mode",
    async (level) => {
      useDetailLevel.setState({ level })
      render(<LiveDreamDigest />, { wrapper: queryWrapper })
      await screen.findByText(`object ${DREAM_OBJECT_ID.slice(0, 8)}`)

      // Honesty: reachable undo and what-changed are never collapsed.
      expect(screen.getByRole("button", { name: /^undo$/i })).toBeInTheDocument()
      expect(screen.getByText(/status:/)).toBeInTheDocument()
      expect(screen.getByText(/active/)).toBeInTheDocument()
      expect(screen.getByText(/superseded/)).toBeInTheDocument()
    },
  )

  it("collapses only the technical event id / detail line in simple mode", async () => {
    useDetailLevel.setState({ level: "simple" })
    render(<LiveDreamDigest />, { wrapper: queryWrapper })
    await screen.findByText(`object ${DREAM_OBJECT_ID.slice(0, 8)}`)

    expect(screen.queryByText(/event #201/)).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^undo$/i })).toBeInTheDocument()
  })
})

const FACT_CLAIM =
  "asserted by 3 distinct origins of kinds [memory, code], no known contradiction, as of 2026-07-27"

const FACT_ROW: FactRowData = {
  id: "f1",
  project: "darkmem",
  subject_name: "darkmem",
  rel_type: "USES",
  object_name: "postgres",
  fact_text: "darkmem uses postgres",
  verification_status: "corroborated",
  claim: FACT_CLAIM,
  origin_count: 3,
  origin_kinds: ["memory", "code"],
  review_state: "open",
  as_of: "2026-07-27T18:55:00Z",
  under_sourced: true,
  window_closed: true,
  invalid_at: "2025-01-01T00:00:00Z",
  expired: false,
  created_at: "2026-07-01T00:00:00Z",
  applies_when: [],
}

describe("detail level: the Facts tab's honesty labels render in both modes", () => {
  beforeEach(() => {
    useDetailLevel.setState({ level: "advanced" })
  })

  it.each(["simple", "advanced"] as const)(
    "rung badge, verbatim claim, under-sourced, belief window and review state all render in %s mode",
    (level) => {
      useDetailLevel.setState({ level })
      render(<FactRow fact={FACT_ROW} focused={false} />)
      expect(screen.getByText("L2 · fact")).toBeInTheDocument()
      expect(screen.getByText("corroborated")).toBeInTheDocument()
      // Doc 12 §4: the claim is shown verbatim or not at all. Simple mode is
      // not an exception — and for a disputed fact this line is both sides.
      expect(screen.getByText(FACT_CLAIM)).toBeInTheDocument()
      expect(screen.getByText("under-sourced")).toBeInTheDocument()
      expect(screen.getByText("window closed")).toBeInTheDocument()
      expect(screen.getByText("in review")).toBeInTheDocument()
      expect(screen.getByText(/3 origins/)).toBeInTheDocument()
      expect(screen.getByText("no context restriction")).toBeInTheDocument()
    },
  )

  it("collapses only the raw triple and the window's timestamp in simple mode", () => {
    useDetailLevel.setState({ level: "simple" })
    render(<FactRow fact={FACT_ROW} focused={false} />)
    // Collapsed: the taxonomy form of the same statement the sentence below
    // it already carries, and the closed window's raw timestamp.
    expect(screen.queryByText("USES")).not.toBeInTheDocument()
    expect(screen.queryByText("2025-01-01T00:00:00Z")).not.toBeInTheDocument()
    // Never collapsed: the row's own honesty labels and its claim.
    expect(screen.getByText("window closed")).toBeInTheDocument()
    expect(screen.getByText(FACT_CLAIM)).toBeInTheDocument()
    expect(screen.getByText("darkmem uses postgres")).toBeInTheDocument()
  })

  it("shows the raw triple and the window's timestamp in advanced mode", () => {
    useDetailLevel.setState({ level: "advanced" })
    render(<FactRow fact={FACT_ROW} focused={false} />)
    expect(screen.getByText("USES")).toBeInTheDocument()
    expect(screen.getByText("2025-01-01T00:00:00Z")).toBeInTheDocument()
  })
})

// T2.86 — the fact detail route on live data. The Facts *tab*'s own
// Simple/Advanced coverage lived here already (above); the detail *page* is
// new surface, so it gets its own block here rather than only in
// `routes/_authenticated/__tests__/fact-detail.test.tsx` — the review-queue
// block's own comment records why an own-file-only clause reads as vacuous.
const DETAIL_CLAIM =
  "asserted by 2 distinct origins of kinds [memory], no known contradiction, as of 2026-07-27"

function factDetailFixture() {
  return {
    id: "f1",
    id_kind: "fact",
    subject_name: "darkmem",
    object_name: "postgres",
    rel_type: "USES",
    fact: "darkmem uses postgres",
    project: "darkmem",
    verification_status: "corroborated",
    lifecycle: null,
    badge: {
      verification_status: "corroborated",
      origin_count: 2,
      origin_kinds: ["memory"],
      as_of: "2026-07-27T18:55:00Z",
      contradiction: false,
      human_ratified: false,
      stale: false,
      claim: DETAIL_CLAIM,
    },
    confidence: 0.8,
    review_state: null,
    demotion_pending_since: null,
    belief_window: { valid_at: "2026-01-01T00:00:00Z", invalid_at: null, expired_at: null },
    applies_when: null,
    applies_when_labels: [],
    created_at: "2026-07-01T00:00:00Z",
    sources: [],
    triple_key: "darkmem:USES:postgres",
    learned_in: null,
    source_file: null,
    reference_time: null,
    ladder: [],
    ladder_total: 0,
    dispute: null,
  }
}

describe("detail level: the fact detail page's honesty labels render in both modes", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
    vi.mocked(apiFetch).mockResolvedValue(factDetailFixture())
  })

  function detailWrapper({ children }: { children: ReactNode }) {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }

  it.each(["simple", "advanced"] as const)(
    "the rung badge and the verbatim claim render in %s mode",
    async (level) => {
      useDetailLevel.setState({ level })
      render(<FactDetail factId="f1" />, { wrapper: detailWrapper })
      await screen.findByText(DETAIL_CLAIM)
      expect(screen.getByText("corroborated")).toBeInTheDocument()
    },
  )

  it("collapses the raw triple in simple mode, never the claim", async () => {
    useDetailLevel.setState({ level: "simple" })
    render(<FactDetail factId="f1" />, { wrapper: detailWrapper })
    await screen.findByText(DETAIL_CLAIM)
    expect(screen.queryByText("USES")).not.toBeInTheDocument()
    expect(screen.getByText(DETAIL_CLAIM)).toBeInTheDocument()
  })

  it("shows the raw triple in advanced mode", async () => {
    useDetailLevel.setState({ level: "advanced" })
    render(<FactDetail factId="f1" />, { wrapper: detailWrapper })
    await screen.findByText(DETAIL_CLAIM)
    expect(screen.getByText("USES")).toBeInTheDocument()
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
