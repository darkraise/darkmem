import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, within } from "@testing-library/react"
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
    ladder_total: 1,
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

  // T2.86 fix round (F6): the path param is a UUID, so a malformed id 422s
  // before any lookup runs — no retry could ever turn that into success. It
  // used to fold into "failed", which offered a Retry button that could
  // never succeed and copy that called it "a fetch problem", both wrong.
  it("renders a malformed id as a distinct, non-retryable state", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new ApiError("Unprocessable", 422))
    render(<FactDetail factId="not-a-uuid" />, { wrapper })

    await screen.findByText("Not a valid fact id")
    expect(screen.queryByText("Fact not found")).not.toBeInTheDocument()
    expect(screen.queryByText("Couldn't load this fact")).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument()
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

  // T2.86 fix round (F1): a ladder truncated by the backend's LADDER_LIMIT
  // must say so, not present a partial list as the whole history —
  // invariant 14's shape. `ladder.length !== ladder_total` is the signal;
  // reusing the loaded/total idiom already established for the Facts tab's
  // footer (T2.36) and the dream digest's cycle picker (T2.38).
  it("discloses a truncated ladder instead of presenting it as complete", async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      detailItem({
        ladder: [
          {
            id: 6,
            created_at: "2026-06-06T00:00:00Z",
            event_type: "sources_changed",
            actor: null,
            payload: { seq: 5 },
          },
        ],
        ladder_total: 55,
      }),
    )
    render(<FactDetail factId="f1" />, { wrapper })

    await screen.findByText(BADGE.claim)
    expect(screen.getByText("1 of 55 loaded")).toBeInTheDocument()
    fireEvent.click(screen.getByText("Verification ladder"))
    expect(
      screen.getByText(/the 1 most recent of 55 .* not loaded here/),
    ).toBeInTheDocument()
  })

  it("an untruncated ladder reports a plain count, not a fraction", async () => {
    vi.mocked(apiFetch).mockResolvedValue(detailItem())
    render(<FactDetail factId="f1" />, { wrapper })

    await screen.findByText(BADGE.claim)
    expect(screen.getByText("1 event")).toBeInTheDocument()
    expect(screen.queryByText(/of 1 loaded/)).not.toBeInTheDocument()
  })

  // T2.86 fix round (F7): the only fixture anywhere exercised the
  // verification_status rung transition. These three rows cover the ladder's
  // other reachable shapes: no before/after at all, a non-rung field's
  // generic "field: from → to" line, and the `to === null → "candidate"`
  // fallback a blocked promotion can produce on real data
  // (`knowledge_triples.py` can write `after.verification_status: null`).
  it("renders the ladder's non-rung transition shapes", async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      detailItem({
        ladder: [
          {
            id: 1,
            created_at: "2026-06-01T00:00:00Z",
            event_type: "sources_changed",
            actor: null,
            payload: { outcome: "corroborated" },
          },
          {
            id: 2,
            created_at: "2026-06-03T00:00:00Z",
            event_type: "invalidated",
            actor: null,
            payload: {
              before: { invalid_at: null },
              after: { invalid_at: "2026-06-03T00:00:00Z" },
            },
          },
          {
            id: 3,
            created_at: "2026-06-04T00:00:00Z",
            event_type: "verified",
            actor: null,
            payload: {
              before: { verification_status: "corroborated" },
              after: { verification_status: null },
            },
          },
        ],
        ladder_total: 3,
      }),
    )
    render(<FactDetail factId="f1" />, { wrapper })
    await screen.findByText(BADGE.claim)
    fireEvent.click(screen.getByText("Verification ladder"))

    // No before/after at all: the badge and nothing else — no stray arrow.
    const noTransitionRow = screen.getByText("2026-06-01T00:00:00Z").parentElement
    expect(noTransitionRow).not.toBeNull()
    expect(within(noTransitionRow!).getByText("sources_changed")).toBeInTheDocument()
    expect(within(noTransitionRow!).queryByText(/→/)).not.toBeInTheDocument()

    // A non-rung field: the generic "field: from → to" line.
    const genericRow = screen.getByText("2026-06-03T00:00:00Z").parentElement
    expect(genericRow).not.toBeNull()
    expect(
      within(genericRow!).getByText(/invalid_at: — → 2026-06-03T00:00:00Z/),
    ).toBeInTheDocument()

    // `after.verification_status: null` — a blocked promotion — falls back
    // to the weakest rung, never a blank pill.
    const fallbackRow = screen.getByText("2026-06-04T00:00:00Z").parentElement
    expect(fallbackRow).not.toBeNull()
    expect(within(fallbackRow!).getByText("corroborated")).toBeInTheDocument()
    expect(within(fallbackRow!).getByText("candidate")).toBeInTheDocument()
  })

  it("renders the sources door's grouping, auditable against origin_count", async () => {
    vi.mocked(apiFetch).mockResolvedValue(detailItem())
    render(<FactDetail factId="f1" />, { wrapper })

    await screen.findByText(BADGE.claim)
    expect(screen.getByText("origin_key: session-a")).toBeInTheDocument()
  })

  // T2.86, T2.48's rescope: `FactSourceGroup.stale` is served (once the
  // backend schema declares it) but was read nowhere — a broken code
  // citation looked identical to a live one. Doc 10 §6: this is a
  // downgrade of corroboration, never a contradiction, so the label must
  // not read as a dispute.
  it("a stale code citation renders as stale, not as disputed", async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      detailItem({
        sources: [
          {
            origin_key: "repo-b",
            unknown_origin: false,
            stale: true,
            source_kinds: ["code"],
            first_seen: "2026-06-01T09:00:00Z",
            last_seen: "2026-06-01T09:00:00Z",
            sources: [
              {
                id: "s2",
                source_kind: "code",
                source_ref: "code@def6789",
                detail: { symbol_key: "main" },
                created_at: "2026-06-01T09:00:00Z",
              },
            ],
          },
        ],
      }),
    )
    render(<FactDetail factId="f1" />, { wrapper })

    await screen.findByText(BADGE.claim)
    expect(screen.getByText("stale")).toBeInTheDocument()
    expect(screen.queryByText("disputed")).not.toBeInTheDocument()
  })

  it("a live-only source group renders no stale label", async () => {
    vi.mocked(apiFetch).mockResolvedValue(detailItem())
    render(<FactDetail factId="f1" />, { wrapper })

    await screen.findByText(BADGE.claim)
    expect(screen.queryByText("stale")).not.toBeInTheDocument()
  })

  // T2.86 fix round (F3): the earlier "not as disputed" assertion held
  // trivially, because that fixture's `verification_status` was not
  // `disputed` — the string could not have rendered regardless of the
  // stale treatment. This fixture *is* disputed (proven by asserting the
  // dispute claim renders first), so a global `queryByText("disputed")`
  // would now find it legitimately elsewhere on the page. The scoped
  // assertion is what actually tests the doc 10 §6 claim: the stale
  // group's own markup — badge plus inline note — never picks up a
  // dispute-styled "disputed" treatment just because the fact it belongs
  // to happens to be disputed.
  it("a stale source group inside a disputed fact still reads as stale, not disputed", async () => {
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
        sources: [
          {
            origin_key: "repo-b",
            unknown_origin: false,
            stale: true,
            source_kinds: ["code"],
            first_seen: "2026-06-01T09:00:00Z",
            last_seen: "2026-06-01T09:00:00Z",
            sources: [
              {
                id: "s2",
                source_kind: "code",
                source_ref: "code@def6789",
                detail: { symbol_key: "main" },
                created_at: "2026-06-01T09:00:00Z",
              },
            ],
          },
        ],
      }),
    )
    render(<FactDetail factId="f1" />, { wrapper })

    // Confirms the fixture is genuinely disputed — the word legitimately
    // appears on the page, so the scoped check below is non-vacuous.
    await screen.findByText(DISPUTED_CLAIM)
    fireEvent.click(screen.getByText("Sources"))

    const staleGroup = screen
      .getByText("origin_key: repo-b")
      .closest<HTMLDivElement>("div.rounded-md")
    expect(staleGroup).not.toBeNull()
    expect(within(staleGroup!).getByText("stale")).toBeInTheDocument()
    expect(within(staleGroup!).queryByText(/disputed/i)).not.toBeInTheDocument()
  })

  // T2.86 fix round (F8): the belief window section's `meta` used to read
  // `fact.project` — every other section's meta is a count or a state, and
  // this one read like a stray copy from the Record section below it. It
  // now reports the window's own open/closed state.
  it("the belief window section's meta reports the window's own state, not the project", async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      detailItem({
        project: "darkmem",
        belief_window: {
          valid_at: "2026-01-01T00:00:00Z",
          invalid_at: "2026-02-01T00:00:00Z",
          expired_at: null,
        },
      }),
    )
    render(<FactDetail factId="f1" />, { wrapper })

    await screen.findByText(BADGE.claim)
    // Scoped to the section's own header: the Record section below it also
    // (correctly, by design) shows `fact.project` as its meta, so a
    // page-wide query for "darkmem" would pass for the wrong reason.
    const windowHeader = screen.getByText("Belief window").parentElement
    expect(windowHeader).not.toBeNull()
    expect(within(windowHeader!).getByText("closed")).toBeInTheDocument()
    expect(within(windowHeader!).queryByText("darkmem")).not.toBeInTheDocument()
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

  // T2.86 fix round (F5): `dispute.enumeration` rode the wire, asserted by a
  // backend test, and was never rendered — the 17-row table had no row for
  // it either. Advanced-mode only, alongside `rule`/`witness_origin`, which
  // already carry the same "structured detail behind the sentence" role.
  it("renders the dispute's enumeration alongside rule and witness_origin", async () => {
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

    await screen.findByText(DISPUTED_CLAIM)
    expect(screen.getByText("enumeration")).toBeInTheDocument()
    expect(screen.getByText("first_finding")).toBeInTheDocument()
  })
})
