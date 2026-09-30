import { describe, it, expect, vi, beforeEach } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
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
  }) => {
    const id = params?.articleId ?? params?.factId
    const href = id ? to.replace(/\$\w+/, id) : to
    return (
      <a href={href} {...rest}>
        {children}
      </a>
    )
  },
}))

import { apiFetch } from "@/lib/api"
import { useDetailLevel } from "@/components/darkmem"
import {
  ArticleDetailLive,
  segmentProse,
} from "../components/article-detail-live"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const CONTENT = "Postgres is a database. It runs in docker."

const CITATION = {
  id: "c1",
  fact_id: "aaaaaaaa-1111-4111-8111-111111111111",
  claim_span: [0, 23] as [number, number],
  fact: "postgres is a database",
  subject_name: "postgres",
  rel_type: "IS_A",
  object_name: "database",
  believed: true,
}

const ARTICLE = {
  id: "11111111-1111-4111-8111-111111111111",
  subject_key: "postgres::concept",
  project: "darkmem",
  title: "postgres",
  status: "candidate",
  label_suppressed: "verification_unmeasured",
  unverified: true,
  coverage: 0.97,
  review_state: null,
  fact_set_hash: "hash-abc",
  stale: false,
  superseded_by: null,
  applies_when: null,
  learned_in: [],
  synthesized_at: "2026-08-11T00:00:00Z",
  created_at: "2026-08-11T00:00:00Z",
  content: CONTENT,
  citations: [CITATION],
  supersedes: null,
  resynthesis_held_at: null,
  resynthesis_held_coverage: null,
}

function serve(article: unknown) {
  vi.mocked(apiFetch).mockResolvedValue(article as never)
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  useDetailLevel.setState({ level: "advanced" })
})

describe("segmentProse", () => {
  it("cuts the prose at the served span, not at sentence boundaries", () => {
    const segments = segmentProse(CONTENT, [CITATION])

    expect(segments.map((s) => s.text)).toEqual([
      "Postgres is a database.",
      " It runs in docker.",
    ])
    expect(segments[0]?.citation).toBe(CITATION)
    expect(segments[1]?.citation).toBeNull()
  })

  it("drops a span that overlaps one already taken rather than interleaving", () => {
    // Rendering both would put text under a citation that does not cover it.
    const overlapping = { ...CITATION, id: "c2", claim_span: [10, 30] as [number, number] }

    const segments = segmentProse(CONTENT, [CITATION, overlapping])

    expect(segments.filter((s) => s.citation !== null)).toHaveLength(1)
    expect(segments.map((s) => s.text).join("")).toBe(CONTENT)
  })

  it("never loses or duplicates a character of the article", () => {
    const segments = segmentProse(CONTENT, [CITATION])
    expect(segments.map((s) => s.text).join("")).toBe(CONTENT)
  })

  it("leaves the prose whole when a span is null or inverted", () => {
    const broken = { ...CITATION, claim_span: [null, null] as [null, null] }
    expect(segmentProse(CONTENT, [broken]).map((s) => s.text)).toEqual([CONTENT])
  })
})

describe("ArticleDetailLive", () => {
  it("makes a cited claim reachable in one click", async () => {
    serve(ARTICLE)

    render(<ArticleDetailLive articleId={ARTICLE.id} />, { wrapper })

    // The claim links to the citation row, and the row exists to receive it.
    const claim = await screen.findByTitle("grounded by citation 1")
    expect(claim).toHaveAttribute("href", "#cite-1")
    expect(document.getElementById("cite-1")).not.toBeNull()
  })

  it("puts the cited fact and a link to it in the citation row", async () => {
    serve(ARTICLE)

    render(<ArticleDetailLive articleId={ARTICLE.id} />, { wrapper })

    expect(await screen.findByText(/“postgres is a database”/)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /fact aaaaaaaa/ })).toHaveAttribute(
      "href",
      `/knowledge/facts/${CITATION.fact_id}`,
    )
  })

  it("flags a citation whose fact is no longer believed instead of hiding it", async () => {
    // Hiding it would leave an uncited claim on the page, which §4.3 calls a
    // permanent grounding failure.
    serve({ ...ARTICLE, citations: [{ ...CITATION, believed: false }] })

    render(<ArticleDetailLive articleId={ARTICLE.id} />, { wrapper })

    expect(await screen.findByText(/no longer believed/i)).toBeInTheDocument()
  })

  it("shows coverage in simple mode as well as advanced", async () => {
    serve(ARTICLE)
    useDetailLevel.setState({ level: "simple" })

    render(<ArticleDetailLive articleId={ARTICLE.id} />, { wrapper })

    expect(await screen.findByText("0.97")).toBeInTheDocument()
    expect(screen.getByText("Coverage")).toBeInTheDocument()
  })

  it("hides the raw fact-set hash in simple mode and shows it in advanced", async () => {
    // T1.48's distinction, kept: the stale *label* is an honesty signal simple
    // mode may never hide, and the hash behind it is a fingerprint it should.
    // The Record section starts collapsed, so it is opened first — asserting
    // against a collapsed accordion would pass for either mode.
    serve(ARTICLE)
    useDetailLevel.setState({ level: "simple" })

    const { rerender } = render(<ArticleDetailLive articleId={ARTICLE.id} />, {
      wrapper,
    })
    fireEvent.click(await screen.findByRole("button", { name: /Record/i }))
    expect(screen.queryByText("hash-abc")).not.toBeInTheDocument()

    useDetailLevel.setState({ level: "advanced" })
    rerender(<ArticleDetailLive articleId={ARTICLE.id} />)
    expect(await screen.findByText("hash-abc")).toBeInTheDocument()
  })

  it("says unmeasured rather than rendering a zero coverage", async () => {
    serve({ ...ARTICLE, coverage: null })

    render(<ArticleDetailLive articleId={ARTICLE.id} />, { wrapper })

    expect(await screen.findByText("not measured")).toBeInTheDocument()
    expect(screen.queryByText("0.00")).not.toBeInTheDocument()
  })

  it("labels a stale article and still renders its prose", async () => {
    serve({ ...ARTICLE, stale: true })

    render(<ArticleDetailLive articleId={ARTICLE.id} />, { wrapper })

    expect(
      await screen.findByText(/synthesised before the latest verified change/i),
    ).toBeInTheDocument()
    expect(screen.getByText(/It runs in docker/)).toBeInTheDocument()
  })

  it("offers both directions of the lineage", async () => {
    serve({
      ...ARTICLE,
      superseded_by: "22222222-2222-4222-8222-222222222222",
      supersedes: "33333333-3333-4333-8333-333333333333",
    })

    render(<ArticleDetailLive articleId={ARTICLE.id} />, { wrapper })

    expect(await screen.findByText(/superseded by a newer version/)).toBeInTheDocument()
    expect(screen.getByText(/view previous version/)).toBeInTheDocument()
  })

  it("shows a held re-synthesis beside the stale label, in both modes", async () => {
    // The bare stale label cannot say "we tried and could not re-ground this",
    // which is the gap doc 09 §4.4's amendment closes. Both modes, because it
    // is an honesty signal rather than a fingerprint.
    serve({ ...ARTICLE, stale: true, resynthesis_held_at: "2026-08-12T00:00:00Z", resynthesis_held_coverage: 0.42 })
    useDetailLevel.setState({ level: "simple" })

    render(<ArticleDetailLive articleId={ARTICLE.id} />, { wrapper })

    expect(
      await screen.findByText(/re-synthesis could not be grounded \(coverage 0\.42\)/i),
    ).toBeInTheDocument()
    // …and it is not withheld: the prose and the badge are still there.
    expect(screen.getByText(/It runs in docker/)).toBeInTheDocument()
    expect(screen.getByText("candidate")).toBeInTheDocument()
  })

  it("says an article with no citations has none rather than implying grounding", async () => {
    serve({ ...ARTICLE, citations: [] })

    render(<ArticleDetailLive articleId={ARTICLE.id} />, { wrapper })

    expect(
      await screen.findByText("No citations recorded for this article."),
    ).toBeInTheDocument()
  })
})
