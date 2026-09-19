import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// The render half of T2.36. The adapter suite next to this one proves the
// row shape; every Done-when clause but "badges verbatim" is a statement
// about what the surface actually puts on screen, and that is what these
// exercise: the project scope on the wire, both sides of a disputed claim
// as text, the belief axis, paging that keeps its rows, and counters that
// are true of what was fetched.
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
import { useProjectStore } from "@/stores/project-store"
import { FactsTab } from "../components/facts-tab"

const CORROBORATED_CLAIM =
  "asserted by 3 distinct origins of kinds [memory, code], no known contradiction, as of 2026-07-27"
const DISPUTED_CLAIM =
  "disputed: 2 origins assert reranker_enabled defaults to on, 1 origin asserts reranker_enabled defaults to off, as of 2026-07-21"

function badge(overrides: Record<string, unknown> = {}) {
  return {
    verification_status: "corroborated",
    origin_count: 3,
    origin_kinds: ["memory", "code"],
    as_of: "2026-07-27T18:55:00Z",
    contradiction: false,
    human_ratified: false,
    stale: false,
    claim: CORROBORATED_CLAIM,
    ...overrides,
  }
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
    badge: badge(),
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

function page(items: object[], total: number, offset = 0) {
  return { items, total, limit: 25, offset }
}

/** A full page, so the footer sits outside the rendered window and nothing
 *  auto-pages — the state a reader is in before they scroll. */
function fullPage(total: number) {
  return page(
    Array.from({ length: 25 }, (_, i) =>
      item({ id: `f${i}`, fact: `fact number ${i}` }),
    ),
    total,
  )
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  // useMainVirtualizer scrolls #main-content, not its own overflow box.
  return (
    <div id="main-content" style={{ height: 800 }}>
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    </div>
  )
}

function urls(): string[] {
  return vi.mocked(apiFetch).mock.calls.map((call) => call[0] as string)
}

describe("FactsTab — the project scope reaches the route as the route defines it", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
    useProjectStore.setState({ activeProject: null, missingProject: null })
  })

  it("opens on every project and sends no project predicate", async () => {
    // The all-projects scope is the route's `project: None`. Sending the
    // select's sentinel as a literal filter matches a project named "all",
    // which returns nothing — and an empty list under a populated vault is
    // then rendered as a cold start. The scope must also not default to a
    // hardcoded project name, which strands every vault that does not use it.
    vi.mocked(apiFetch).mockResolvedValue(page([item()], 1))
    render(<FactsTab />, { wrapper })

    await screen.findByText("darkmem uses postgres")
    expect(urls()[0]).not.toContain("project=")
    expect(screen.getByText(/Facts — project: all projects/)).toBeInTheDocument()
  })

  it("scopes by the header switcher and offers no project select", async () => {
    useProjectStore.setState({ activeProject: "acme", missingProject: null })
    vi.mocked(apiFetch).mockResolvedValue(page([item()], 1))
    render(<FactsTab />, { wrapper })

    await screen.findByText("darkmem uses postgres")
    expect(urls()[0]).toContain("project=acme")
    expect(screen.getByText(/Facts — project: acme/)).toBeInTheDocument()
    expect(screen.queryByRole("combobox", { name: "Project scope" })).toBeNull()
  })
})

describe("FactsTab — a disputed row renders both sides, on the row", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("puts the two-sided claim on screen as text, not in a hover-only title", async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      page(
        [
          item({
            verification_status: "disputed",
            badge: badge({
              verification_status: "disputed",
              claim: DISPUTED_CLAIM,
            }),
          }),
        ],
        1,
      ),
    )
    render(<FactsTab />, { wrapper })

    // Both sides are the backend's own sentence. A title attribute is
    // invisible to touch and to a keyboard, so the row must render it.
    const claim = await screen.findByText(DISPUTED_CLAIM)
    expect(claim.tagName).toBe("P")
  })

  it("links to the detail route unconditionally now the door is wired (T2.86)", async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      page(
        [
          item({
            verification_status: "disputed",
            badge: badge({
              verification_status: "disputed",
              claim: DISPUTED_CLAIM,
            }),
          }),
        ],
        1,
      ),
    )
    render(<FactsTab />, { wrapper })

    await screen.findByText(DISPUTED_CLAIM)
    // T2.36's `detail_available` gate is retired: `GET /knowledge/facts/{id}`
    // is a real door now (T2.86), so every row links, live data included.
    expect(
      screen.getByText(/sources, ladder and windows/),
    ).toBeInTheDocument()
    expect(document.querySelectorAll("a")).toHaveLength(1)
  })
})

describe("FactsTab — the belief axis renders beside the verification axis", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("labels a closed belief window without touching the rung", async () => {
    // `LIVE_PREDICATE` is `expired_at IS NULL`, so this row is served. Doc
    // 08 §3: a closed window is retained history, not a weaker rung — and a
    // surface that renders it identically to a current fact has one axis.
    vi.mocked(apiFetch).mockResolvedValue(
      page(
        [
          item({
            belief_window: {
              valid_at: "2024-01-01T00:00:00Z",
              invalid_at: "2025-01-01T00:00:00Z",
              expired_at: null,
            },
          }),
        ],
        1,
      ),
    )
    render(<FactsTab />, { wrapper })

    await screen.findByText("darkmem uses postgres")
    expect(screen.getByText("window closed")).toBeInTheDocument()
    expect(screen.getByText("corroborated")).toBeInTheDocument()
  })

  it("says nothing about belief for a current fact", async () => {
    vi.mocked(apiFetch).mockResolvedValue(page([item()], 1))
    render(<FactsTab />, { wrapper })

    await screen.findByText("darkmem uses postgres")
    expect(screen.queryByText("window closed")).not.toBeInTheDocument()
    expect(screen.queryByText("belief withdrawn")).not.toBeInTheDocument()
  })
})

describe("FactsTab — paging keeps the rows it has, and its counters are true", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("loads the next page without unmounting the loaded rows", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(page([item()], 2))
      .mockResolvedValueOnce(page([item({ id: "f2", fact: "second fact" })], 2, 1))
    render(<FactsTab />, { wrapper })

    await screen.findByText("darkmem uses postgres")
    // The second page arrives beside the first — never through a "Loading
    // facts" state that drops the list and the reader's scroll position.
    await screen.findByText("second fact")
    expect(screen.getByText("darkmem uses postgres")).toBeInTheDocument()
    expect(screen.queryByText("Loading facts")).not.toBeInTheDocument()
    expect(urls()[1]).toContain("offset=1")
  })

  it("counts loaded rows against the server's total, never against itself", async () => {
    // 25 rows loaded of a 412-row corpus. A counter comparing the list to
    // itself always reads "N of N" and can never disclose partiality.
    vi.mocked(apiFetch).mockResolvedValue(fullPage(412))
    render(<FactsTab />, { wrapper })

    await screen.findByText("fact number 0")
    expect(screen.getByText("25 of 412 loaded")).toBeInTheDocument()
    expect(screen.queryByText("25 of 25 loaded")).not.toBeInTheDocument()
  })
})

describe("FactsTab — the free-text filter never speaks for the whole vault", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("reports the loaded count it searched, and does not drain the corpus to answer", async () => {
    const user = (await import("@testing-library/user-event")).default.setup()
    vi.mocked(apiFetch).mockResolvedValue(fullPage(412))
    render(<FactsTab />, { wrapper })
    await screen.findByText("fact number 0")

    const before = vi.mocked(apiFetch).mock.calls.length
    await user.type(
      screen.getByLabelText("Filter facts by subject or object"),
      "nothing-matches-this",
    )

    // The sentence counts what was actually searched and says the rest was
    // not read — the page presented as the corpus is invariant 14's core case.
    await screen.findByText(/No loaded fact matches/)
    expect(
      screen.getByText(/Searched the 25 facts loaded so far/),
    ).toBeInTheDocument()
    expect(screen.queryByText(/Nothing was hidden/)).not.toBeInTheDocument()

    // And it did not start paging the whole 412-row corpus in the background
    // to answer a question it can answer honestly with what it has.
    await new Promise((resolve) => setTimeout(resolve, 400))
    expect(vi.mocked(apiFetch).mock.calls.length).toBe(before)
  })

  it("says nothing was hidden only once it has the whole filtered set", async () => {
    const user = (await import("@testing-library/user-event")).default.setup()
    vi.mocked(apiFetch).mockResolvedValue(page([item()], 1))
    render(<FactsTab />, { wrapper })
    await screen.findByText("darkmem uses postgres")

    await user.type(
      screen.getByLabelText("Filter facts by subject or object"),
      "nothing-matches-this",
    )

    await screen.findByText(/No loaded fact matches/)
    expect(
      screen.getByText(/Searched all 1 facts behind the relation/),
    ).toBeInTheDocument()
  })
})

describe("FactsTab — simple mode collapses detail and keeps every honesty label", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("hides the raw triple and still renders the badge and the verbatim claim", async () => {
    useDetailLevel.setState({ level: "simple" })
    vi.mocked(apiFetch).mockResolvedValue(page([item()], 1))
    render(<FactsTab />, { wrapper })

    await screen.findByText("darkmem uses postgres")
    expect(screen.queryByText("USES")).not.toBeInTheDocument()
    expect(screen.getByText("corroborated")).toBeInTheDocument()
    expect(screen.getByText(CORROBORATED_CLAIM)).toBeInTheDocument()
  })
})

describe("FactsTab — a failed read stays a failed read", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useDetailLevel.setState({ level: "advanced" })
  })

  it("never renders an unanswered vault as a cold start, and claims no count", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    render(<FactsTab />, { wrapper })

    await screen.findByText("Could not load facts")
    expect(screen.queryByText("No corroborated facts yet")).not.toBeInTheDocument()
    expect(screen.getByText("count unavailable")).toBeInTheDocument()
  })
})
