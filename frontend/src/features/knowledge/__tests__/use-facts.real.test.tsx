import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useFactRows } from "../use-facts"

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

const QUERY = { limit: 25, offset: 0 }

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

    expect(result.current.rows[0]!.claim).toBe("")
    expect(result.current.rows[0]!.meta).toBe("")
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
  })

  it("keeps the belief axis distinct from the verification axis", async () => {
    // Doc 08 §3: a fact can be well-verified and no longer current. A window
    // closing must not downgrade the rung, and an expiry must not either.
    vi.mocked(apiFetch).mockResolvedValue({
      items: [
        item({
          belief_window: {
            valid_at: "2024-01-01T00:00:00Z",
            invalid_at: "2025-01-01T00:00:00Z",
            expired_at: "2025-06-01T00:00:00Z",
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
    expect(row.expired).toBe(true)
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
          ...QUERY,
          project: "darkmem",
          rel_type: "USES",
          verification_status: "disputed",
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
