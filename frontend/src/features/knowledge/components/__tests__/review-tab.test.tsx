import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// T2.37 — the Review / Hygiene triage shell, wired to live data.
// Adapter tests (use-review-queue.test.tsx / use-hygiene-queue.test.tsx)
// prove the data layer; this file proves what the previous round's review
// found adapter tests cannot see: the render itself. Every Done-when clause
// phrased as "the user sees X" is asserted here, at the component tree,
// never only at the hook.

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
import { useDetailLevel } from "@/components/darkmem"
import { ReviewTab } from "../review-tab"

function withQuery(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
}

const CONSEQUENCE = {
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

const FACT_ITEM = {
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
  consequence: CONSEQUENCE,
  created_at: "2026-08-01T00:00:00Z",
}

const DUPLICATE_ITEM = {
  id: "rel1",
  source_memory_id: "m1",
  target_memory_id: "m2",
  rel_type: "near_duplicate",
  project: "darkmem",
  score: 0.91,
  verdict: "likely_duplicate",
  hygiene_state: "open",
  detected_at: "2026-07-30T00:00:00Z",
  created_at: "2026-07-30T00:00:00Z",
}

function emptyList() {
  return { items: [], total: 0, limit: 10, offset: 0 }
}

function mockApi(overrides: Record<string, unknown> = {}) {
  vi.mocked(apiFetch).mockImplementation(async (url: string) => {
    if (url.startsWith("/review-queue/counts")) {
      return overrides.reviewCounts ?? { facts: 1, articles: 0 }
    }
    if (url.startsWith("/review-queue/facts")) {
      return overrides.facts ?? { items: [FACT_ITEM], total: 1, limit: 10, offset: 0 }
    }
    if (url.startsWith("/review-queue/articles")) {
      return overrides.articles ?? emptyList()
    }
    if (url.startsWith("/hygiene-queue/counts")) {
      return (
        overrides.hygieneCounts ?? {
          duplicates: 1,
          low_confidence: 0,
          expiring_soon: 0,
          superseded: 0,
        }
      )
    }
    if (url.startsWith("/hygiene-queue/duplicates")) {
      return overrides.duplicates ?? { items: [DUPLICATE_ITEM], total: 1, limit: 10, offset: 0 }
    }
    if (url.startsWith("/hygiene-queue/low-confidence")) return emptyList()
    if (url.startsWith("/hygiene-queue/expiring-soon")) return emptyList()
    if (url.startsWith("/hygiene-queue/superseded")) return emptyList()
    if (url.startsWith("/hygiene-queue/bulk/confirm-dedup")) {
      return {
        cycle_id: "cyc-1",
        results: [{ id: "rel1", applied: true, event_id: 42, reason: null }],
      }
    }
    if (url.startsWith("/dream-digest/cycles/")) {
      return {
        undo_batch_id: "undo-1",
        undone: [
          { event_id: 42, action: "associate", object_id: "m1", restored: ["hygiene_state"], not_restored: [] },
        ],
      }
    }
    throw new Error(`unexpected apiFetch call in test: ${url}`)
  })
}

async function switchToHygiene() {
  fireEvent.click(screen.getByText("Hygiene — housekeeping"))
  await screen.findByText("Superseded lineage")
}

describe("ReviewTab: the two queues are visibly distinct surfaces", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("Review shows fact/article queues; Hygiene shows housekeeping arms — never both at once", async () => {
    mockApi()
    render(withQuery(<ReviewTab />))

    expect(await screen.findByText(/why ranked here:/)).toBeInTheDocument()
    expect(screen.getByText("Ungrounded articles")).toBeInTheDocument()
    expect(screen.queryByText("Candidate duplicates")).not.toBeInTheDocument()

    await switchToHygiene()

    expect(screen.getByText("Superseded lineage")).toBeInTheDocument()
    expect(screen.queryByText("Disputed / under-sourced facts")).not.toBeInTheDocument()
  })
})

describe("ReviewTab: ranking rationale is shown per item", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("renders the consequence-derived rank_note on the fact row", async () => {
    mockApi()
    render(withQuery(<ReviewTab />))

    await screen.findByText(/why ranked here:/)
    expect(screen.getByText(/score 0\.42/)).toBeInTheDocument()
  })
})

describe("ReviewTab: honesty labels survive Simple mode; technical detail collapses", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("keeps the verification badge and queued-reason chip in simple mode, drops the consequence breakdown", async () => {
    mockApi()
    useDetailLevel.setState({ level: "simple" })
    render(withQuery(<ReviewTab />))
    await screen.findByText(/why ranked here:/)

    // Never collapsed: the honesty labels.
    expect(screen.getByText("disputed")).toBeInTheDocument()
    expect(screen.getByText(/queued: disputed/)).toBeInTheDocument()
    // Always shown regardless of level (it is the Done-when clause itself,
    // not a technical breakdown item).
    expect(screen.getByText(/why ranked here:/)).toBeInTheDocument()

    // Collapsed: the per-arm numeric breakdown.
    expect(screen.queryByText(/retrieval_frequency:/)).not.toBeInTheDocument()
  })

  it("shows the consequence breakdown only in advanced mode", async () => {
    mockApi()
    useDetailLevel.setState({ level: "advanced" })
    render(withQuery(<ReviewTab />))
    await screen.findByText(/why ranked here:/)

    expect(screen.getByText(/retrieval_frequency:/)).toBeInTheDocument()
  })
})

describe("ReviewTab: a failed read renders as an error, never an empty queue", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows the failed-read message on the fact arm when the fetch rejects", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/facts")) throw new Error("boom")
      if (url.startsWith("/review-queue/counts")) return { facts: 0, articles: 0 }
      if (url.startsWith("/review-queue/articles")) return emptyList()
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))

    expect(await screen.findByText("Could not load the fact queue")).toBeInTheDocument()
    expect(screen.queryByText("No disputed or under-sourced facts")).not.toBeInTheDocument()
  })
})

describe("ReviewTab: bulk hygiene actions confirm before applying, and are undoable", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("requires a confirm click before POSTing, then offers Undo after success", async () => {
    mockApi()
    render(withQuery(<ReviewTab />))
    await switchToHygiene()

    const checkbox = await screen.findByLabelText("Select duplicate pair rel1")
    fireEvent.click(checkbox)
    fireEvent.click(screen.getByText("Confirm dedup"))

    // The dialog is open and the mutation has NOT fired yet.
    expect(
      await screen.findByText(/Confirm 1 duplicate pair\?/),
    ).toBeInTheDocument()
    expect(
      vi.mocked(apiFetch).mock.calls.some(
        (call) => (call[0] as string) === "/hygiene-queue/bulk/confirm-dedup",
      ),
    ).toBe(false)

    fireEvent.click(screen.getByText("Apply"))

    await waitFor(() =>
      expect(
        vi.mocked(apiFetch).mock.calls.some(
          (call) => (call[0] as string) === "/hygiene-queue/bulk/confirm-dedup",
        ),
      ).toBe(true),
    )

    const undoButton = await screen.findByText("Undo this batch")
    fireEvent.click(undoButton)

    await waitFor(() =>
      expect(
        vi.mocked(apiFetch).mock.calls.some((call) =>
          (call[0] as string).startsWith("/dream-digest/cycles/cyc-1/undo"),
        ),
      ).toBe(true),
    )
    expect(await screen.findByText("undone")).toBeInTheDocument()
  })
})
