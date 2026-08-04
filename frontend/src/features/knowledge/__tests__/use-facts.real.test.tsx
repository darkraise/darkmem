import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { ALL_PROJECTS, ANY, useFactRows } from "../use-facts"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const BADGE = {
  verification_status: "corroborated",
  origin_count: 3,
  origin_kinds: ["memory", "code"],
  as_of: "2026-07-27T18:55:00Z",
  contradiction: false,
  human_ratified: false,
  stale: false,
  claim:
    "asserted by 3 distinct origins of kinds [memory, code], no known contradiction, as of 2026-07-27",
}

function item(overrides: Record<string, unknown> = {}) {
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
    belief_window: { valid_at: null, invalid_at: null, expired_at: null },
    applies_when: null,
    applies_when_labels: [],
    created_at: "2026-07-01T00:00:00Z",
    ...overrides,
  }
}

const QUERY = {
  project: ALL_PROJECTS,
  relation: ANY,
  status: ANY,
  subject: "",
}

describe("useFactRows (DEMO off — real /knowledge/facts)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("carries the badge claim verbatim and never composes one", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [item()],
      total: 1,
      limit: 25,
      offset: 0,
    })
    const { result } = renderHook(() => useFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    // Doc 12 §4: the claim is the contract. Byte-for-byte, not reworded.
    expect(result.current.rows[0]!.claim).toBe(BADGE.claim)
  })

  it("renders no claim rather than an invented one when the badge is absent", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [item({ badge: null })],
      total: 1,
      limit: 25,
      offset: 0,
    })
    const { result } = renderHook(() => useFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    // No badge means no claim and no parts to lay out — never a substitute
    // sentence assembled from whatever happened to be present.
    expect(result.current.rows[0]!.claim).toBe("")
    expect(result.current.rows[0]!.origin_count).toBeNull()
    expect(result.current.rows[0]!.origin_kinds).toEqual([])
  })

  it("carries the badge's parts as values, never as a second sentence", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [item()],
      total: 1,
      limit: 25,
      offset: 0,
    })
    const { result } = renderHook(() => useFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    const row = result.current.rows[0]!
    expect(row.origin_count).toBe(3)
    expect(row.origin_kinds).toEqual(["memory", "code"])
    // Every string on the row that speaks to its standing is the badge's own.
    for (const value of Object.values(row)) {
      if (typeof value !== "string" || value === row.claim) continue
      expect(value.toLowerCase()).not.toContain("asserted by")
      expect(value.toLowerCase()).not.toContain("distinct origin")
    }
  })

  it("reports the server's total, not the page length", async () => {
    // The page is one row; the corpus behind the filter is 412. A surface
    // that counts `rows` tells the user the vault is 1 fact deep.
    vi.mocked(apiFetch).mockResolvedValue({
      items: [item()],
      total: 412,
      limit: 25,
      offset: 0,
    })
    const { result } = renderHook(() => useFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.rows).toHaveLength(1)
    expect(result.current.total).toBe(412)
    // `loaded` is the other half of the same honesty: the count the surface
    // must use for anything it says about the rows it actually holds.
    expect(result.current.loaded).toBe(1)
    expect(result.current.hasMore).toBe(true)
  })

  it("keeps the belief axis distinct from the verification axis", async () => {
    // Doc 08 §3: a fact can be well-verified and no longer current. A window
    // closing must not downgrade the rung. `list_live`'s predicate is
    // `expired_at IS NULL`, so a closed window on a non-expired row is
    // exactly the state this route serves — and the one the row must carry.
    vi.mocked(apiFetch).mockResolvedValue({
      items: [
        item({
          belief_window: {
            valid_at: "2024-01-01T00:00:00Z",
            invalid_at: "2025-01-01T00:00:00Z",
            expired_at: null,
          },
        }),
      ],
      total: 1,
      limit: 25,
      offset: 0,
    })
    const { result } = renderHook(() => useFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    const row = result.current.rows[0]!
    expect(row.verification_status).toBe("corroborated")
    expect(row.window_closed).toBe(true)
    expect(row.invalid_at).toBe("2025-01-01T00:00:00Z")
    expect(row.expired).toBe(false)
  })

  it("carries the under-sourced overlay and still serves the row", async () => {
    // T2.46: the marker is served, never withheld. A corroborated fact with a
    // pending demotion stays in the list wearing the caution.
    vi.mocked(apiFetch).mockResolvedValue({
      items: [item({ demotion_pending_since: "2026-07-20T00:00:00Z" })],
      total: 1,
      limit: 25,
      offset: 0,
    })
    const { result } = renderHook(() => useFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.rows).toHaveLength(1)
    expect(result.current.rows[0]!.under_sourced).toBe(true)
    expect(result.current.rows[0]!.verification_status).toBe("corroborated")
  })

  it("under-claims an unrecognised status rather than passing it through", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [item({ verification_status: "gilded" })],
      total: 1,
      limit: 25,
      offset: 0,
    })
    const { result } = renderHook(() => useFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.rows[0]!.verification_status).toBe("candidate")
  })

  it("sends the filters as server predicates, on the path apiFetch expects", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [],
      total: 0,
      limit: 25,
      offset: 0,
    })
    renderHook(
      () =>
        useFactRows({
          project: "darkmem",
          relation: "USES",
          status: "disputed",
          subject: "",
        }),
      { wrapper },
    )
    await waitFor(() => expect(apiFetch).toHaveBeenCalled())

    // The whole path, not three substrings of it. `apiFetch` prepends
    // `/api/v1` itself, so a caller that spells the prefix produces
    // `/api/v1/api/v1/...` and 404s on every request — invisible to any
    // assertion that only looks for the query parameters it expects.
    const url = vi.mocked(apiFetch).mock.calls[0]![0] as string
    expect(url).toBe(
      "/knowledge/facts?project=darkmem&rel_type=USES" +
        "&verification_status=disputed&limit=25&offset=0",
    )
  })

  it("drops the project predicate for the all-projects scope", async () => {
    // The route's own all-projects capability is `project: None`. Sending the
    // sentinel as a literal filter matches a project literally named "all" —
    // nothing — and the surface then renders a populated vault as an empty one.
    vi.mocked(apiFetch).mockResolvedValue({
      items: [],
      total: 0,
      limit: 25,
      offset: 0,
    })
    renderHook(() => useFactRows(QUERY), { wrapper })
    await waitFor(() => expect(apiFetch).toHaveBeenCalled())

    const url = vi.mocked(apiFetch).mock.calls[0]![0] as string
    expect(url).toBe("/knowledge/facts?limit=25&offset=0")
    expect(url).not.toContain(ALL_PROJECTS)
  })

  it("matches the free-text needle against subject and object, over loaded rows only", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [
        item(),
        item({ id: "f2", subject_name: "hybrid_search", object_name: "rrf" }),
      ],
      total: 40,
      limit: 25,
      offset: 0,
    })
    const { result } = renderHook(
      () => useFactRows({ ...QUERY, subject: "postgres" }),
      { wrapper },
    )
    await waitFor(() => expect(result.current.loading).toBe(false))

    // "postgres" is f1's object, not its subject.
    expect(result.current.rows.map((r) => r.id)).toEqual(["f1"])
    // The needle narrowed the rows; it narrowed neither what was loaded nor
    // the server's own count, and both stay available to say so.
    expect(result.current.loaded).toBe(2)
    expect(result.current.total).toBe(40)
  })

  it("accumulates pages instead of re-keying on a growing limit", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({
        items: [item()],
        total: 2,
        limit: 25,
        offset: 0,
      })
      .mockResolvedValueOnce({
        items: [item({ id: "f2" })],
        total: 2,
        limit: 25,
        offset: 1,
      })
    const { result } = renderHook(() => useFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.hasMore).toBe(true)

    result.current.fetchMore()
    await waitFor(() => expect(result.current.rows).toHaveLength(2))

    // Page one is still here — the second fetch added to it rather than
    // re-keying the query, dropping its data and unmounting the list.
    expect(result.current.rows.map((r) => r.id)).toEqual(["f1", "f2"])
    expect(result.current.hasMore).toBe(false)
    const second = vi.mocked(apiFetch).mock.calls[1]![0] as string
    expect(second).toBe("/knowledge/facts?limit=25&offset=1")
  })

  it("reports a failed read as an error, never as an empty vault", async () => {
    // Invariant 14. "No facts" and "we could not tell you" are different
    // sentences, and a surface that collapses them looks healthy while broken.
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    const { result } = renderHook(() => useFactRows(QUERY), { wrapper })
    await waitFor(() => expect(result.current.error).toBe(true))

    expect(result.current.rows).toEqual([])
    expect(result.current.total).toBe(0)
  })
})
