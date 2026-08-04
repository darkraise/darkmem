import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// T2.86 — the fact detail route on live data. `knowledge_.facts_.$factId.tsx`
// called `useDemoFact` unconditionally; with DEMO off (the default since
// T1.58) any real fact id rendered "This fact does not exist in the demo
// store." `FactDetail` (features/knowledge/components/fact-detail.tsx) takes
// `factId` as a prop rather than reading `Route.useParams()`, so this file
// renders and drives it directly, no router context required — the same
// testability shape `ReviewQueue`/`FactRow` already use.

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>()
  return { ...actual, apiFetch: vi.fn() }
})
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
import { useDetailLevel } from "@/components/darkmem"
import { FactDetail } from "@/features/knowledge/components/fact-detail"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const BADGE = {
  verification_status: "corroborated",
  origin_count: 2,
  origin_kinds: ["memory"],
  as_of: "2026-07-27T18:55:00Z",
  contradiction: false,
  human_ratified: false,
  stale: false,
  claim: "asserted by 2 distinct origins of kinds [memory], no known contradiction, as of 2026-07-27",
}

const DISPUTED_CLAIM =
  "disputed: 2 origins assert reranker_enabled defaults to on, 1 origin asserts reranker_enabled defaults to off, as of 2026-07-21"

function detailItem(overrides: Record<string, unknown> = {}) {
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
    badge: BADGE,
    confidence: 0.8,
    review_state: null,
    demotion_pending_since: null,
    belief_window: { valid_at: "2026-01-01T00:00:00Z", invalid_at: null, expired_at: null },
    applies_when: null,
    applies_when_labels: [],
    created_at: "2026-07-01T00:00:00Z",
    sources: [
      {
        origin_key: "session-a",
        unknown_origin: false,
        source_kinds: ["memory"],
        first_seen: "2026-06-01T09:00:00Z",
        last_seen: "2026-06-01T09:00:00Z",
        sources: [
          {
            id: "s1",
            source_kind: "memory",
            source_ref: "mem-abc123",
            detail: { excerpt: "captured this fact first" },
            created_at: "2026-06-01T09:00:00Z",
          },
        ],
      },
    ],
    triple_key: "darkmem:USES:postgres",
    learned_in: ["repo-x"],
    source_file: null,
    reference_time: null,
    ladder: [
      {
        id: 1,
        created_at: "2026-06-02T00:00:00Z",
        event_type: "verified",
        actor: null,
        payload: {
          before: { verification_status: "candidate" },
          after: { verification_status: "corroborated" },
        },
      },
    ],
    dispute: null,
    ...overrides,
  }
}

describe("FactDetail (DEMO off — GET /knowledge/facts/{id})", () => {
  beforeEach(() => vi.clearAllMocks())

  it("renders a loading state before the fetch resolves", () => {
    vi.mocked(apiFetch).mockReturnValue(new Promise(() => {}))
    render(<FactDetail factId="f1" />, { wrapper })
    expect(document.querySelector(".animate-spin")).not.toBeNull()
  })

  it("renders a genuine 404 as distinguishable from a failed read", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new ApiError("Fact not found", 404))
    render(<FactDetail factId="does-not-exist" />, { wrapper })

    await screen.findByText("Fact not found")
    expect(screen.getByText("No fact exists with this id.")).toBeInTheDocument()
    // Distinct copy from the failed-read state below — a reader must not
    // confuse "nothing here" with "the read broke".
    expect(screen.queryByText(/Couldn't load/)).not.toBeInTheDocument()
  })

  it("renders a failed read as a failed read, distinct from a missing fact", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new ApiError("boom", 500))
    render(<FactDetail factId="f1" />, { wrapper })

    await screen.findByText("Couldn't load this fact")
    expect(screen.queryByText("Fact not found")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument()
  })

  it("a non-ApiError rejection is also a failed read, never silently a 404", async () => {
    // Mutation-relevant: the 404 check requires `instanceof ApiError`
    // specifically — a bare thrown Error must not be misread as "missing".
    vi.mocked(apiFetch).mockRejectedValue(new Error("network down"))
    render(<FactDetail factId="f1" />, { wrapper })

    await screen.findByText("Couldn't load this fact")
    expect(screen.queryByText("Fact not found")).not.toBeInTheDocument()
  })

  it("renders the fact on a successful read", async () => {
    vi.mocked(apiFetch).mockResolvedValue(detailItem())
    render(<FactDetail factId="f1" />, { wrapper })

    await screen.findByText(BADGE.claim)
    expect(screen.getByText("darkmem uses postgres")).toBeInTheDocument()
    expect(screen.getByText("corroborated")).toBeInTheDocument()
  })

  it("a disputed fact renders the backend's two-sided claim verbatim", async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      detailItem({
        verification_status: "disputed",
        review_state: "open",
        badge: { ...BADGE, verification_status: "disputed", claim: DISPUTED_CLAIM },
        dispute: {
          review_state: "open",
          claim: { subject: "darkmem", rel_type: "USES", object: "postgres", id: "f1" },
          counterpart: {
            subject: "darkmem",
            rel_type: "AVOIDS",
            object: "postgres",
            id: "f2",
          },
          counterpart_absent: null,
          rule: "functional_object_conflict",
          witness_origin: "origin-7",
          enumeration: "first_finding",
        },
      }),
    )
    render(<FactDetail factId="f1" />, { wrapper })

    // The sentence itself, shown verbatim — never recomposed on this page.
    const claim = await screen.findByText(DISPUTED_CLAIM)
    expect(claim).toBeInTheDocument()
    // The structured counterpart triple, laid out as parts, not prose.
    expect(screen.getByText("AVOIDS")).toBeInTheDocument()
  })

  it("a disputed fact with no recorded counterpart says so, not silently", async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      detailItem({
        verification_status: "disputed",
        review_state: "open",
        badge: { ...BADGE, verification_status: "disputed", claim: DISPUTED_CLAIM },
        dispute: {
          review_state: "open",
          claim: { subject: "darkmem", rel_type: "USES", object: "postgres", id: "f1" },
          counterpart: null,
          counterpart_absent: "no_finding_recorded",
          rule: null,
          witness_origin: null,
          enumeration: null,
        },
      }),
    )
    render(<FactDetail factId="f1" />, { wrapper })

    await screen.findByText(DISPUTED_CLAIM)
    expect(screen.getByText("no_finding_recorded")).toBeInTheDocument()
  })

  it("renders the raw journal ladder, oldest event visible", async () => {
    vi.mocked(apiFetch).mockResolvedValue(detailItem())
    render(<FactDetail factId="f1" />, { wrapper })

    await screen.findByText(BADGE.claim)
    // Collapsed by default (the sources section opens first) — open it.
    fireEvent.click(screen.getByText("Verification ladder"))
    expect(screen.getByText("verified")).toBeInTheDocument()
    expect(screen.getByText("2026-06-02T00:00:00Z")).toBeInTheDocument()
  })

  it("renders the sources door's grouping, auditable against origin_count", async () => {
    vi.mocked(apiFetch).mockResolvedValue(detailItem())
    render(<FactDetail factId="f1" />, { wrapper })

    await screen.findByText(BADGE.claim)
    expect(screen.getByText("origin_key: session-a")).toBeInTheDocument()
  })
})

describe("FactDetail — Simple/Advanced (T2.86, own file)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("shows the raw triple and technical record fields in advanced mode", async () => {
    vi.mocked(apiFetch).mockResolvedValue(detailItem())
    render(<FactDetail factId="f1" />, { wrapper })
    await screen.findByText(BADGE.claim)

    // The hero triple is always in the DOM (advanced mode); the record
    // section's technical fields are behind the accordion — open it.
    expect(screen.getByText("USES")).toBeInTheDocument()
    fireEvent.click(screen.getByText("Record & provenance"))
    expect(screen.getByText("darkmem:USES:postgres")).toBeInTheDocument()
  })

  it("collapses the raw triple and technical record fields in simple mode, never the claim", async () => {
    useDetailLevel.setState({ level: "simple" })
    vi.mocked(apiFetch).mockResolvedValue(detailItem())
    render(<FactDetail factId="f1" />, { wrapper })
    await screen.findByText(BADGE.claim)

    expect(screen.queryByText("USES")).not.toBeInTheDocument()
    fireEvent.click(screen.getByText("Record & provenance"))
    expect(screen.queryByText("darkmem:USES:postgres")).not.toBeInTheDocument()
    // Never collapsed: the honesty labels.
    expect(screen.getByText("corroborated")).toBeInTheDocument()
    expect(screen.getByText(BADGE.claim)).toBeInTheDocument()
  })
})
