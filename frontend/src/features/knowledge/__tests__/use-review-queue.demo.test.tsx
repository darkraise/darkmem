import { describe, it, expect, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// F7: every existing test for this adapter mocked DEMO: false. The demo
// branch's own predicates (project match, offset/limit slicing) were true by
// reading but guarded by nothing — re-inerting them would stay green. This
// file is the demo-side counterpart to use-review-queue.test.tsx, mirroring
// the sibling `use-facts.demo.test.tsx` convention.

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import {
  useReviewArticleRows,
  useReviewFactRows,
} from "../use-review-queue"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("useReviewFactRows / useReviewArticleRows (DEMO on — the curated fixture)", () => {
  it("never reaches the network", () => {
    renderHook(() => useReviewFactRows({ limit: 10, offset: 0 }), { wrapper })
    renderHook(() => useReviewArticleRows({ limit: 10, offset: 0 }), { wrapper })
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it("honours the project filter — the fixture's own project matches, any other excludes everything", () => {
    const { result: matched } = renderHook(
      () => useReviewFactRows({ project: "darkmem", limit: 10, offset: 0 }),
      { wrapper },
    )
    expect(matched.current.rows.length).toBeGreaterThan(0)
    for (const row of matched.current.rows) expect(row.project).toBe("darkmem")

    const { result: unmatched } = renderHook(
      () => useReviewFactRows({ project: "no-such-project", limit: 10, offset: 0 }),
      { wrapper },
    )
    expect(unmatched.current.rows).toHaveLength(0)
    expect(unmatched.current.total).toBe(0)
  })

  it("applies the same offset/limit paging the live query would send, reporting the corpus total", () => {
    const { result: all } = renderHook(
      () => useReviewFactRows({ limit: 100, offset: 0 }),
      { wrapper },
    )
    const corpusTotal = all.current.total
    expect(corpusTotal).toBeGreaterThanOrEqual(2)

    const { result: page1 } = renderHook(
      () => useReviewFactRows({ limit: 1, offset: 0 }),
      { wrapper },
    )
    const { result: page2 } = renderHook(
      () => useReviewFactRows({ limit: 1, offset: 1 }),
      { wrapper },
    )
    expect(page1.current.rows).toHaveLength(1)
    expect(page1.current.total).toBe(corpusTotal)
    expect(page2.current.rows).toHaveLength(1)
    expect(page2.current.rows[0]!.id).not.toBe(page1.current.rows[0]!.id)
    expect(page2.current.total).toBe(corpusTotal)
  })

  it("slices the article arm the same way, past the end of the fixture", () => {
    const { result: page0 } = renderHook(
      () => useReviewArticleRows({ limit: 1, offset: 0 }),
      { wrapper },
    )
    expect(page0.current.rows.length).toBeGreaterThan(0)
    const total = page0.current.total

    const { result: pastEnd } = renderHook(
      () => useReviewArticleRows({ limit: 1, offset: total }),
      { wrapper },
    )
    expect(pastEnd.current.rows).toHaveLength(0)
    expect(pastEnd.current.total).toBe(total)
  })
})
