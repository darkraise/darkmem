import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// The demo store seeds CURATED_ARTICLES unconditionally, and those fixtures
// carry `confirmed` statuses, claim sentences and invented coverage ratios.
// Rendering them outside DEMO would put fabricated verified claims in front of
// a real reader under chrome promising every claim links to a verified fact.
// T3.06 gave real mode its own door, so this file now asserts two things at
// once: the live rows render, and the fixture is still unreachable.
vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
// A row links to its article, and `Link` needs a router this suite has no
// reason to build — the href it produces is asserted directly instead.
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({
    to,
    params,
    children,
    ...rest
  }: {
    to: string
    params?: Record<string, string>
    children?: ReactNode
    [key: string]: unknown
  }) => (
    <a href={params?.articleId ? to.replace("$articleId", params.articleId) : to} {...rest}>
      {children}
    </a>
  ),
}))

import { apiFetch } from "@/lib/api"
import { ArticlesTab } from "../components/articles-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const ROW = {
  id: "11111111-1111-4111-8111-111111111111",
  subject_key: "postgres::concept",
  project: "darkmem",
  title: "postgres",
  status: "candidate",
  label_suppressed: "verification_unmeasured",
  unverified: true,
  coverage: 0.97,
  review_state: null,
  fact_set_hash: "abc",
  stale: false,
  superseded_by: null,
  applies_when: null,
  learned_in: [],
  synthesized_at: "2026-08-11T00:00:00Z",
  created_at: "2026-08-11T00:00:00Z",
  excerpt: "Postgres is a database.",
}

function serve(items: unknown[]) {
  vi.mocked(apiFetch).mockResolvedValue({
    items,
    total: items.length,
    limit: 50,
    offset: 0,
  } as never)
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("ArticlesTab on live data", () => {
  it("renders the door's rows", async () => {
    serve([ROW])

    render(<ArticlesTab />, { wrapper })

    expect(await screen.findByText("postgres")).toBeInTheDocument()
    expect(screen.getByText("Postgres is a database.")).toBeInTheDocument()
  })

  it("shows the coverage number as claim-support coverage", async () => {
    serve([ROW])

    render(<ArticlesTab />, { wrapper })

    expect(
      await screen.findByText(/claim-support coverage 0\.97/i),
    ).toBeInTheDocument()
  })

  it("says an unmeasured article is unmeasured rather than showing zero", async () => {
    // With the groundedness gate open this is every article, and 0.00 would
    // read as "measured, and ungrounded" — the opposite of what is true.
    serve([{ ...ROW, coverage: null }])

    render(<ArticlesTab />, { wrapper })

    expect(
      await screen.findByText(/claim-support coverage not measured/i),
    ).toBeInTheDocument()
    expect(screen.queryByText(/coverage 0\.00/i)).not.toBeInTheDocument()
  })

  it("labels a stale article and still serves it", async () => {
    serve([{ ...ROW, stale: true }])

    render(<ArticlesTab />, { wrapper })

    expect(await screen.findByText("postgres")).toBeInTheDocument()
    expect(
      screen.getByText(/synthesised before the latest verified change/i),
    ).toBeInTheDocument()
  })

  it("serves the rung the door served, never one it recomputed", async () => {
    // The backend gates the label; a surface that upgraded `candidate` to
    // `corroborated` because coverage looked high would assert a claim no
    // evidence backs.
    serve([{ ...ROW, coverage: 1 }])

    render(<ArticlesTab />, { wrapper })

    expect(await screen.findByText("candidate")).toBeInTheDocument()
    expect(screen.queryByText("corroborated")).not.toBeInTheDocument()
  })

  it("counts an open-review article as withheld rather than listing it", async () => {
    serve([ROW, { ...ROW, id: "22222222-2222-4222-8222-222222222222", review_state: "open" }])

    render(<ArticlesTab />, { wrapper })

    await screen.findByText("postgres")
    expect(screen.getByText(/1 article/i)).toBeInTheDocument()
    expect(screen.getByText(/routed to Knowledge → Review/i)).toBeInTheDocument()
  })

  it("does not default a real install to the demo fixture's project", async () => {
    // "darkmem" is the demo project. Defaulting to it showed an empty tab to
    // anyone whose articles live in `default` — a library reading as empty
    // when it is not.
    serve([ROW])

    render(<ArticlesTab />, { wrapper })

    await screen.findByText("postgres")
    const url = vi.mocked(apiFetch).mock.calls[0]?.[0] as string
    expect(url).not.toContain("project=darkmem")
  })

  it("does not say nothing is withheld while counting withheld articles", async () => {
    // The strip and the empty state contradicted each other in exactly the
    // standing case: every article in review, which is what an open
    // groundedness gate produces.
    serve([{ ...ROW, review_state: "open" }])

    render(<ArticlesTab />, { wrapper })

    expect(await screen.findByText(/1 article/i)).toBeInTheDocument()
    expect(
      screen.queryByText(/nothing is being withheld from you here/i),
    ).not.toBeInTheDocument()
    expect(
      screen.getByText(/Every article for this scope is in review/i),
    ).toBeInTheDocument()
  })

  it("says the corpus is empty rather than claiming the feature is unshipped", async () => {
    serve([])

    render(<ArticlesTab />, { wrapper })

    expect(await screen.findByText("No articles yet")).toBeInTheDocument()
    expect(
      screen.getByText(/nothing is being withheld from you here/i),
    ).toBeInTheDocument()
  })

  it("never reaches the demo fixture", async () => {
    serve([])

    render(<ArticlesTab />, { wrapper })

    await waitFor(() => expect(apiFetch).toHaveBeenCalled())
    for (const rung of ["corroborated", "confirmed", "disputed"]) {
      expect(screen.queryByText(rung)).not.toBeInTheDocument()
    }
  })
})
