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
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>()
  return { ...actual, apiFetch: vi.fn() }
})
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))
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

import { apiFetch, ApiError } from "@/lib/api"
import { toast } from "darkraise-ui/components/sonner"
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
  // m1 (source) is the older endpoint, m2 (target) the newer one — the
  // fixed direction the T2.87 fix-round-1 F3 tests below assert both the
  // confirm dialog and the POST body agree on.
  source_content_preview: "uses postgres 14",
  source_created_at: "2026-07-20T00:00:00Z",
  target_content_preview: "uses postgres 14 as well",
  target_created_at: "2026-07-30T00:00:00Z",
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

// T2.37 fix round 1 — findings F1-F4, F6. Each test below asserts what the
// adapter tests structurally cannot see: F1-F4 are all "the UI stays silent
// when it should speak" defects, so the guard is the DOM the user would
// actually be looking at, not a hook return value.

function factItem(id: string) {
  return { ...FACT_ITEM, id }
}

describe("ReviewTab: a stranded page shows a way back, never a false caught-up message (F1)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("offers 'Back to the first page' instead of claiming the queue is empty", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 11, articles: 0 }
      if (url.startsWith("/review-queue/articles")) return emptyList()
      if (url.startsWith("/review-queue/facts")) {
        // Simulates the shape the finding names: the offset-10 page reads
        // back empty (a page-2 ratify/reject already removed its rows)
        // while the backend's own total still says 10 remain.
        if (url.includes("offset=10")) {
          return { items: [], total: 10, limit: 10, offset: 10 }
        }
        return {
          items: Array.from({ length: 10 }, (_, i) => factItem(`f${i}`)),
          total: 11,
          limit: 10,
          offset: 0,
        }
      }
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))
    await screen.findAllByText(/why ranked here:/)

    fireEvent.click(screen.getByLabelText("Next page"))

    expect(await screen.findByText("This page emptied out")).toBeInTheDocument()
    expect(
      screen.queryByText("No disputed or under-sourced facts"),
    ).not.toBeInTheDocument()
    expect(screen.getByText(/10 facts still remain/)).toBeInTheDocument()

    fireEvent.click(screen.getByText("Back to the first page"))
    expect((await screen.findAllByText(/why ranked here:/)).length).toBeGreaterThan(0)
  })
})

describe("ReviewTab: a confirmed action that fails to apply is reported, not silent (F2)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows an error toast when the confirm-dedup POST fails", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 0, articles: 0 }
      if (url.startsWith("/review-queue/facts")) return emptyList()
      if (url.startsWith("/review-queue/articles")) return emptyList()
      if (url.startsWith("/hygiene-queue/counts")) {
        return { duplicates: 1, low_confidence: 0, expiring_soon: 0, superseded: 0 }
      }
      if (url.startsWith("/hygiene-queue/duplicates")) {
        return { items: [DUPLICATE_ITEM], total: 1, limit: 10, offset: 0 }
      }
      if (url.startsWith("/hygiene-queue/low-confidence")) return emptyList()
      if (url.startsWith("/hygiene-queue/expiring-soon")) return emptyList()
      if (url.startsWith("/hygiene-queue/superseded")) return emptyList()
      if (url === "/hygiene-queue/bulk/confirm-dedup") {
        throw new ApiError("Internal Server Error", 500)
      }
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))
    await switchToHygiene()

    const checkbox = await screen.findByLabelText("Select duplicate pair rel1")
    fireEvent.click(checkbox)
    fireEvent.click(screen.getByText("Confirm dedup"))
    fireEvent.click(await screen.findByText("Apply"))

    await waitFor(() => expect(toast.error).toHaveBeenCalled())
    const [title] = vi.mocked(toast.error).mock.calls[0]!
    expect(String(title)).toMatch(/action failed/i)
    // No notice renders for a request that never came back with a result.
    expect(screen.queryByText(/applied/)).not.toBeInTheDocument()
  })
})

describe("ReviewTab: a refused undo (409) is shown, never a silently reset spinner (F3)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows the refusal reason and leaves the undo button retryable", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 0, articles: 0 }
      if (url.startsWith("/review-queue/facts")) return emptyList()
      if (url.startsWith("/review-queue/articles")) return emptyList()
      if (url.startsWith("/hygiene-queue/counts")) {
        return { duplicates: 1, low_confidence: 0, expiring_soon: 0, superseded: 0 }
      }
      if (url.startsWith("/hygiene-queue/duplicates")) {
        return { items: [DUPLICATE_ITEM], total: 1, limit: 10, offset: 0 }
      }
      if (url.startsWith("/hygiene-queue/low-confidence")) return emptyList()
      if (url.startsWith("/hygiene-queue/expiring-soon")) return emptyList()
      if (url.startsWith("/hygiene-queue/superseded")) return emptyList()
      if (url === "/hygiene-queue/bulk/confirm-dedup") {
        return {
          cycle_id: "cyc-1",
          results: [{ id: "rel1", applied: true, event_id: 42, reason: null }],
        }
      }
      if (url.startsWith("/dream-digest/cycles/")) {
        throw new ApiError("conflict", 409, [
          { event_id: 42, action: "associate", reason: "state_changed" },
        ])
      }
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))
    await switchToHygiene()

    const checkbox = await screen.findByLabelText("Select duplicate pair rel1")
    fireEvent.click(checkbox)
    fireEvent.click(screen.getByText("Confirm dedup"))
    fireEvent.click(await screen.findByText("Apply"))

    fireEvent.click(await screen.findByText("Undo this batch"))

    await waitFor(() => expect(toast.error).toHaveBeenCalled())
    const [title, opts] = vi.mocked(toast.error).mock.calls[0]!
    expect(String(title)).toMatch(/refused/i)
    expect(String((opts as { description?: string })?.description)).toMatch(
      /changed since this action ran/i,
    )
    // Never silently marked undone — the button is still there to retry.
    expect(screen.queryByText("undone")).not.toBeInTheDocument()
    expect(await screen.findByText("Undo this batch")).toBeInTheDocument()
  })
})

describe("ReviewTab: the counts header never fabricates a zero while loading (F4)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows a loading line until the counts door actually answers", async () => {
    let resolveCounts: (value: { facts: number; articles: number }) => void = () => {}
    const countsPromise = new Promise<{ facts: number; articles: number }>((resolve) => {
      resolveCounts = resolve
    })
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/counts")) return countsPromise
      if (url.startsWith("/review-queue/facts")) {
        return { items: [FACT_ITEM], total: 1, limit: 10, offset: 0 }
      }
      if (url.startsWith("/review-queue/articles")) return emptyList()
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))
    await screen.findByText(/why ranked here:/)

    expect(screen.getByText(/counts loading…/)).toBeInTheDocument()
    expect(screen.queryByText(/0 facts?/)).not.toBeInTheDocument()

    resolveCounts({ facts: 1, articles: 0 })
    await waitFor(() => expect(screen.getByText(/1 fact/)).toBeInTheDocument())
  })
})

describe("ReviewTab: per-item refusal reasons reach the DOM (F6)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("names the refused item's reason, not just an applied/refused count", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 0, articles: 0 }
      if (url.startsWith("/review-queue/facts")) return emptyList()
      if (url.startsWith("/review-queue/articles")) return emptyList()
      if (url.startsWith("/hygiene-queue/counts")) {
        return { duplicates: 1, low_confidence: 0, expiring_soon: 0, superseded: 0 }
      }
      if (url.startsWith("/hygiene-queue/duplicates")) {
        return { items: [DUPLICATE_ITEM], total: 1, limit: 10, offset: 0 }
      }
      if (url.startsWith("/hygiene-queue/low-confidence")) return emptyList()
      if (url.startsWith("/hygiene-queue/expiring-soon")) return emptyList()
      if (url.startsWith("/hygiene-queue/superseded")) return emptyList()
      if (url === "/hygiene-queue/bulk/confirm-dedup") {
        return {
          cycle_id: "cyc-2",
          results: [{ id: "rel1", applied: false, event_id: null, reason: "stale" }],
        }
      }
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))
    await switchToHygiene()

    const checkbox = await screen.findByLabelText("Select duplicate pair rel1")
    fireEvent.click(checkbox)
    fireEvent.click(screen.getByText("Confirm dedup"))
    fireEvent.click(await screen.findByText("Apply"))

    expect(await screen.findByText(/0 applied, 1 refused/)).toBeInTheDocument()
    expect(screen.getByText(/no longer active/)).toBeInTheDocument()
  })
})

describe("HygieneQueue: every arm states its ordering honestly, in both detail modes (F5 / clause 2)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it.each(["simple", "advanced"] as const)(
    "shows an honest ordering line per arm and never claims consequence ranking, in %s mode",
    async (level) => {
      useDetailLevel.setState({ level })
      mockApi()
      render(withQuery(<ReviewTab />))
      await switchToHygiene()

      expect(screen.getByText(/^newest first —/)).toBeInTheDocument()
      expect(screen.getByText(/lowest confidence first/)).toBeInTheDocument()
      expect(screen.getByText(/soonest expires_at first/)).toBeInTheDocument()
      expect(screen.getByText(/newest first, read-only/)).toBeInTheDocument()
      // The one honest claim this epic allows on this surface is the
      // absence of ranking, never its presence — doc 08 §6's
      // "consequence-ranked, not FIFO" belongs to the Review queue's facts
      // arm alone (T2.23's reported gap), and no hygiene arm may borrow it.
      expect(
        screen.queryByText("consequence-ranked, not FIFO"),
      ).not.toBeInTheDocument()
    },
  )
})

// T2.37 fix round 2 — N3. The round-1 guards for F1 and F4 each covered one
// representative site (review-queue's facts arm) and left the hygiene side's
// four independently-computed branches unguarded; a mutant reverting any one
// of them stayed green against the full suite. These widen the guard to
// every hygiene site rather than narrowing the finding to the one already
// covered.

const LOW_CONF_ITEM = {
  id: "m-low-1",
  project: "darkmem",
  content_preview: "a low confidence capture",
  confidence: 0.2,
  expires_at: null,
  status: "active",
  superseded_by: null,
  reason: "low_confidence",
  created_at: "2026-07-01T00:00:00Z",
}

const EXPIRING_ITEM = {
  id: "m-exp-1",
  project: "darkmem",
  content_preview: "a memory about to expire",
  confidence: 0.6,
  expires_at: "2026-08-10T00:00:00Z",
  status: "active",
  superseded_by: null,
  reason: "expiring_soon",
  created_at: "2026-07-01T00:00:00Z",
}

describe("HygieneQueue: a stranded page shows a way back on every arm, not just one (N3)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("renders the stranded recovery message independently on all four hygiene arms", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 0, articles: 0 }
      if (url.startsWith("/review-queue/facts")) return emptyList()
      if (url.startsWith("/review-queue/articles")) return emptyList()
      if (url.startsWith("/hygiene-queue/counts")) {
        return { duplicates: 5, low_confidence: 6, expiring_soon: 7, superseded: 8 }
      }
      // Each arm's own query returns rows.length === 0 while total > 0 — the
      // exact shape a stale offset produces (F1's finding), isolated per arm
      // with a distinct total so each arm's own message is independently
      // verifiable, not one shared assertion that could pass on a single arm.
      if (url.startsWith("/hygiene-queue/duplicates")) return { items: [], total: 5, limit: 10, offset: 0 }
      if (url.startsWith("/hygiene-queue/low-confidence")) return { items: [], total: 6, limit: 10, offset: 0 }
      if (url.startsWith("/hygiene-queue/expiring-soon")) return { items: [], total: 7, limit: 10, offset: 0 }
      if (url.startsWith("/hygiene-queue/superseded")) return { items: [], total: 8, limit: 10, offset: 0 }
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))
    await switchToHygiene()

    expect(await screen.findByText(/5 rows still remain/)).toBeInTheDocument()
    expect(screen.getByText(/6 rows still remain/)).toBeInTheDocument()
    expect(screen.getByText(/7 rows still remain/)).toBeInTheDocument()
    expect(screen.getByText(/8 rows still remain/)).toBeInTheDocument()
    expect(screen.getAllByText("Back to the first page")).toHaveLength(4)
    // Never the caught-up phrasing for a queue the backend still says is
    // non-empty (invariant 14) — the defect this whole finding guards.
    // Widened to all four arms (D3): each arm's own `emptyLine` prop must
    // stay suppressed independently, not just the duplicates arm's.
    expect(
      screen.queryByText("Candidate duplicates — none flagged by the last dream cycle"),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByText("Low-confidence memories — none below the review threshold"),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByText("Expiring soon — no rows with expires_at inside the lookahead window"),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByText("Superseded lineage — nothing flagged for cleanup"),
    ).not.toBeInTheDocument()
  })
})

describe("HygieneQueue: the counts header never fabricates a zero while loading (N3)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows a loading line until the hygiene counts door actually answers", async () => {
    let resolveCounts: (value: {
      duplicates: number
      low_confidence: number
      expiring_soon: number
      superseded: number
    }) => void = () => {}
    const countsPromise = new Promise<{
      duplicates: number
      low_confidence: number
      expiring_soon: number
      superseded: number
    }>((resolve) => {
      resolveCounts = resolve
    })
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 0, articles: 0 }
      if (url.startsWith("/review-queue/facts")) return emptyList()
      if (url.startsWith("/review-queue/articles")) return emptyList()
      if (url.startsWith("/hygiene-queue/counts")) return countsPromise
      if (url.startsWith("/hygiene-queue/duplicates")) {
        return { items: [DUPLICATE_ITEM], total: 1, limit: 10, offset: 0 }
      }
      if (url.startsWith("/hygiene-queue/low-confidence")) return emptyList()
      if (url.startsWith("/hygiene-queue/expiring-soon")) return emptyList()
      if (url.startsWith("/hygiene-queue/superseded")) return emptyList()
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))
    await switchToHygiene()

    expect(screen.getByText(/counts loading…/)).toBeInTheDocument()
    expect(screen.queryByText(/0 duplicate/)).not.toBeInTheDocument()

    resolveCounts({ duplicates: 1, low_confidence: 0, expiring_soon: 0, superseded: 0 })
    await waitFor(() =>
      expect(screen.getByText(/1 duplicate pair/)).toBeInTheDocument(),
    )
  })
})

// T2.37 fix round 2 — N3, widening F2. Round 1's guard covered only
// confirm-dedup; prune-low, prune-expiring, ratify and reject each had their
// own `onError` deleted entirely by a mutant and the full suite stayed
// green. Each test below fails specifically when *that* site's error
// handling is removed — it does not, and is not meant to, catch a
// regression on a sibling site.

describe("HygieneQueue: the prune (low-confidence) door reports a failed apply (N3 / F2)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows an error toast naming the low-confidence arm when the prune POST fails", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 0, articles: 0 }
      if (url.startsWith("/review-queue/facts")) return emptyList()
      if (url.startsWith("/review-queue/articles")) return emptyList()
      if (url.startsWith("/hygiene-queue/counts")) {
        return { duplicates: 0, low_confidence: 1, expiring_soon: 0, superseded: 0 }
      }
      if (url.startsWith("/hygiene-queue/duplicates")) return emptyList()
      if (url.startsWith("/hygiene-queue/low-confidence")) {
        return { items: [LOW_CONF_ITEM], total: 1, limit: 10, offset: 0 }
      }
      if (url.startsWith("/hygiene-queue/expiring-soon")) return emptyList()
      if (url.startsWith("/hygiene-queue/superseded")) return emptyList()
      if (url === "/hygiene-queue/bulk/prune") throw new ApiError("Internal Server Error", 500)
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))
    await switchToHygiene()

    fireEvent.click(await screen.findByLabelText("Select a low confidence capture"))
    fireEvent.click(screen.getByText("Prune"))
    fireEvent.click(await screen.findByText("Apply"))

    await waitFor(() => expect(toast.error).toHaveBeenCalled())
    const [title] = vi.mocked(toast.error).mock.calls[0]!
    expect(String(title)).toMatch(/Prune \(low-confidence\).*action failed/i)
  })
})

describe("HygieneQueue: the prune (expiring-soon) door reports a failed apply (N3 / F2)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows an error toast naming the expiring-soon arm when the prune POST fails", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 0, articles: 0 }
      if (url.startsWith("/review-queue/facts")) return emptyList()
      if (url.startsWith("/review-queue/articles")) return emptyList()
      if (url.startsWith("/hygiene-queue/counts")) {
        return { duplicates: 0, low_confidence: 0, expiring_soon: 1, superseded: 0 }
      }
      if (url.startsWith("/hygiene-queue/duplicates")) return emptyList()
      if (url.startsWith("/hygiene-queue/low-confidence")) return emptyList()
      if (url.startsWith("/hygiene-queue/expiring-soon")) {
        return { items: [EXPIRING_ITEM], total: 1, limit: 10, offset: 0 }
      }
      if (url.startsWith("/hygiene-queue/superseded")) return emptyList()
      if (url === "/hygiene-queue/bulk/prune") throw new ApiError("Internal Server Error", 500)
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))
    await switchToHygiene()

    fireEvent.click(await screen.findByLabelText("Select a memory about to expire"))
    fireEvent.click(screen.getByText("Prune now"))
    fireEvent.click(await screen.findByText("Apply"))

    await waitFor(() => expect(toast.error).toHaveBeenCalled())
    const [title] = vi.mocked(toast.error).mock.calls[0]!
    expect(String(title)).toMatch(/Prune \(expiring soon\).*action failed/i)
  })
})

describe("ReviewTab: the ratify door reports a failed apply, not silence (N3 / F2)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows an error toast when the ratify POST fails", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 1, articles: 0 }
      if (url.startsWith("/review-queue/facts")) {
        return { items: [FACT_ITEM], total: 1, limit: 10, offset: 0 }
      }
      if (url.startsWith("/review-queue/articles")) return emptyList()
      if (url.startsWith("/knowledge/facts/") && init?.method === "POST") {
        throw new ApiError("Internal Server Error", 500)
      }
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))

    await screen.findByText(/why ranked here:/)
    fireEvent.click(screen.getByText("Ratify → confirmed"))
    fireEvent.click(await screen.findByText("Ratify as confirmed"))

    await waitFor(() => expect(toast.error).toHaveBeenCalled())
    const [title] = vi.mocked(toast.error).mock.calls[0]!
    expect(String(title)).toMatch(/Ratify failed/i)
  })
})

describe("ReviewTab: the reject door reports a failed apply, not silence (N3 / F2)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows an error toast when the reject POST fails", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string, init?: RequestInit) => {
      // The reject-POST check must run before the facts-list GET check:
      // "/review-queue/facts/f1/reject" also starts with "/review-queue/facts",
      // so a looser ordering would let the list branch swallow it.
      if (url.startsWith("/review-queue/facts/") && init?.method === "POST") {
        throw new ApiError("Internal Server Error", 500)
      }
      if (url.startsWith("/review-queue/counts")) return { facts: 1, articles: 0 }
      if (url.startsWith("/review-queue/facts")) {
        return { items: [FACT_ITEM], total: 1, limit: 10, offset: 0 }
      }
      if (url.startsWith("/review-queue/articles")) return emptyList()
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))

    await screen.findByText(/why ranked here:/)
    fireEvent.click(screen.getByText("Reject"))
    // The row's own action button and the confirm dialog's action button are
    // both literally labelled "Reject" — the dialog's copy is the second to
    // appear once it opens.
    await waitFor(() => expect(screen.getAllByText("Reject")).toHaveLength(2))
    const rejectButtons = screen.getAllByText("Reject")
    fireEvent.click(rejectButtons[rejectButtons.length - 1]!)

    await waitFor(() => expect(toast.error).toHaveBeenCalled())
    const [title] = vi.mocked(toast.error).mock.calls[0]!
    expect(String(title)).toMatch(/Reject failed/i)
  })
})

// T2.37 fix round 3 — N1. Every test above that exercises an onError branch
// rejects with `new ApiError(...)`, which only ever proves the "nothing was
// applied" wording. The unknown-outcome branch alongside it — reached when
// the mutation rejects with anything that is not an `ApiError` (a dropped
// connection, `fetch` itself throwing) — had no test anywhere, so a mutant
// collapsing it into the known wording at all four sites left the full
// suite green. These four pin the "state unknown" wording independently at
// each site: the shared bulk helper, ratify, reject, and runUndo's non-409
// branch.

describe("HygieneQueue: a non-HTTP bulk failure reports state unknown, not applied (N1)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows the state-unknown toast when the confirm-dedup POST rejects without an HTTP response", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 0, articles: 0 }
      if (url.startsWith("/review-queue/facts")) return emptyList()
      if (url.startsWith("/review-queue/articles")) return emptyList()
      if (url.startsWith("/hygiene-queue/counts")) {
        return { duplicates: 1, low_confidence: 0, expiring_soon: 0, superseded: 0 }
      }
      if (url.startsWith("/hygiene-queue/duplicates")) {
        return { items: [DUPLICATE_ITEM], total: 1, limit: 10, offset: 0 }
      }
      if (url.startsWith("/hygiene-queue/low-confidence")) return emptyList()
      if (url.startsWith("/hygiene-queue/expiring-soon")) return emptyList()
      if (url.startsWith("/hygiene-queue/superseded")) return emptyList()
      if (url === "/hygiene-queue/bulk/confirm-dedup") {
        // The shape a dropped connection actually produces: `fetch` itself
        // rejects with a TypeError, never reaching apiFetch's ApiError path.
        throw new TypeError("Failed to fetch")
      }
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))
    await switchToHygiene()

    const checkbox = await screen.findByLabelText("Select duplicate pair rel1")
    fireEvent.click(checkbox)
    fireEvent.click(screen.getByText("Confirm dedup"))
    fireEvent.click(await screen.findByText("Apply"))

    await waitFor(() => expect(toast.error).toHaveBeenCalled())
    const [title, opts] = vi.mocked(toast.error).mock.calls[0]!
    expect(String(title)).toMatch(/state unknown/i)
    expect(String(title)).not.toMatch(/nothing was applied/i)
    expect(String((opts as { description?: string })?.description)).toMatch(
      /Failed to fetch/,
    )
  })
})

describe("ReviewTab: a non-HTTP ratify failure reports state unknown, not applied (N1)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows the state-unknown toast when the ratify POST rejects without an HTTP response", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string, init?: RequestInit) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 1, articles: 0 }
      if (url.startsWith("/review-queue/facts")) {
        return { items: [FACT_ITEM], total: 1, limit: 10, offset: 0 }
      }
      if (url.startsWith("/review-queue/articles")) return emptyList()
      if (url.startsWith("/knowledge/facts/") && init?.method === "POST") {
        throw new TypeError("Failed to fetch")
      }
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))

    await screen.findByText(/why ranked here:/)
    fireEvent.click(screen.getByText("Ratify → confirmed"))
    fireEvent.click(await screen.findByText("Ratify as confirmed"))

    await waitFor(() => expect(toast.error).toHaveBeenCalled())
    const [title] = vi.mocked(toast.error).mock.calls[0]!
    expect(String(title)).toMatch(/Ratify failed — state unknown/i)
    expect(String(title)).not.toMatch(/was not changed/i)
  })
})

describe("ReviewTab: a non-HTTP reject failure reports state unknown, not applied (N1)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows the state-unknown toast when the reject POST rejects without an HTTP response", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string, init?: RequestInit) => {
      // Same ordering footgun as the reject-ApiError test above: the reject
      // POST url also starts with "/review-queue/facts", so it must be
      // checked before the facts-list GET branch.
      if (url.startsWith("/review-queue/facts/") && init?.method === "POST") {
        throw new Error("network error")
      }
      if (url.startsWith("/review-queue/counts")) return { facts: 1, articles: 0 }
      if (url.startsWith("/review-queue/facts")) {
        return { items: [FACT_ITEM], total: 1, limit: 10, offset: 0 }
      }
      if (url.startsWith("/review-queue/articles")) return emptyList()
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))

    await screen.findByText(/why ranked here:/)
    fireEvent.click(screen.getByText("Reject"))
    await waitFor(() => expect(screen.getAllByText("Reject")).toHaveLength(2))
    const rejectButtons = screen.getAllByText("Reject")
    fireEvent.click(rejectButtons[rejectButtons.length - 1]!)

    await waitFor(() => expect(toast.error).toHaveBeenCalled())
    const [title] = vi.mocked(toast.error).mock.calls[0]!
    expect(String(title)).toMatch(/Reject failed — state unknown/i)
    expect(String(title)).not.toMatch(/was not changed/i)
  })
})

describe("ReviewTab: a non-409 undo failure reports state unknown, not refused (N1)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows the state-unknown toast when the undo POST rejects without an HTTP response", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 0, articles: 0 }
      if (url.startsWith("/review-queue/facts")) return emptyList()
      if (url.startsWith("/review-queue/articles")) return emptyList()
      if (url.startsWith("/hygiene-queue/counts")) {
        return { duplicates: 1, low_confidence: 0, expiring_soon: 0, superseded: 0 }
      }
      if (url.startsWith("/hygiene-queue/duplicates")) {
        return { items: [DUPLICATE_ITEM], total: 1, limit: 10, offset: 0 }
      }
      if (url.startsWith("/hygiene-queue/low-confidence")) return emptyList()
      if (url.startsWith("/hygiene-queue/expiring-soon")) return emptyList()
      if (url.startsWith("/hygiene-queue/superseded")) return emptyList()
      if (url === "/hygiene-queue/bulk/confirm-dedup") {
        return {
          cycle_id: "cyc-1",
          results: [{ id: "rel1", applied: true, event_id: 42, reason: null }],
        }
      }
      if (url.startsWith("/dream-digest/cycles/")) {
        throw new TypeError("Failed to fetch")
      }
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))
    await switchToHygiene()

    const checkbox = await screen.findByLabelText("Select duplicate pair rel1")
    fireEvent.click(checkbox)
    fireEvent.click(screen.getByText("Confirm dedup"))
    fireEvent.click(await screen.findByText("Apply"))

    fireEvent.click(await screen.findByText("Undo this batch"))

    await waitFor(() => expect(toast.error).toHaveBeenCalled())
    const [title] = vi.mocked(toast.error).mock.calls[0]!
    expect(String(title)).toMatch(/Undo failed — state unknown/i)
    expect(String(title)).not.toMatch(/refused/i)
    // Never silently marked undone — the button is still there to retry.
    expect(screen.queryByText("undone")).not.toBeInTheDocument()
    expect(await screen.findByText("Undo this batch")).toBeInTheDocument()
  })
})

// T2.87 fix round 1 — F3. The payload mapping in `applyPending`'s
// "supersede-dup" branch (`memory_id: item.olderId, superseded_by:
// item.newerId`) is the one place the client's `duplicateDirection` guess
// becomes a write, and nothing rendered the "Supersede instead" flow or
// asserted its request body before this round: flipping the mapping passed
// typecheck and every test that existed. This test fails if that mapping
// is flipped.

describe("HygieneQueue: 'Supersede instead' states a direction and applies that same direction (T2.87 fix round 1, F3)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows older→newer in the confirm dialog, then POSTs memory_id/superseded_by in that order", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 0, articles: 0 }
      if (url.startsWith("/review-queue/facts")) return emptyList()
      if (url.startsWith("/review-queue/articles")) return emptyList()
      if (url.startsWith("/hygiene-queue/counts")) {
        return { duplicates: 1, low_confidence: 0, expiring_soon: 0, superseded: 0 }
      }
      if (url.startsWith("/hygiene-queue/duplicates")) {
        return { items: [DUPLICATE_ITEM], total: 1, limit: 10, offset: 0 }
      }
      if (url.startsWith("/hygiene-queue/low-confidence")) return emptyList()
      if (url.startsWith("/hygiene-queue/expiring-soon")) return emptyList()
      if (url.startsWith("/hygiene-queue/superseded")) return emptyList()
      if (url === "/hygiene-queue/bulk/supersede") {
        return {
          cycle_id: "cyc-2",
          results: [{ id: "rel1", applied: true, event_id: 43, reason: null }],
        }
      }
      throw new Error(`unexpected: ${url}`)
    })
    render(withQuery(<ReviewTab />))
    await switchToHygiene()

    const checkbox = await screen.findByLabelText("Select duplicate pair rel1")
    fireEvent.click(checkbox)
    fireEvent.click(screen.getByText("Supersede instead"))

    // The dialog states the direction — m1 is the older endpoint
    // (source_created_at 2026-07-20, before m2's 2026-07-30) — before
    // anything is applied.
    expect(await screen.findByText(/Supersede 1 duplicate pair\?/)).toBeInTheDocument()
    expect(screen.getByText(/m1 → superseded by → m2/)).toBeInTheDocument()
    expect(
      vi.mocked(apiFetch).mock.calls.some(
        (call) => (call[0] as string) === "/hygiene-queue/bulk/supersede",
      ),
    ).toBe(false)

    fireEvent.click(screen.getByText("Apply"))

    await waitFor(() =>
      expect(
        vi.mocked(apiFetch).mock.calls.some(
          (call) => (call[0] as string) === "/hygiene-queue/bulk/supersede",
        ),
      ).toBe(true),
    )
    const [, init] = vi
      .mocked(apiFetch)
      .mock.calls.find((call) => (call[0] as string) === "/hygiene-queue/bulk/supersede")!
    const body = JSON.parse((init as RequestInit).body as string)
    expect(body).toEqual({ items: [{ memory_id: "m1", superseded_by: "m2" }] })
  })
})
