import { describe, it, expect, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

// F7: the demo-side counterpart to use-hygiene-queue.test.tsx — every
// existing test for this adapter mocked DEMO: false, so the demo branch's
// own project filter and offset/limit slicing were true by reading only.

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import {
  useHygieneCountsRows,
  useHygieneDuplicateRows,
  useHygieneExpiringRows,
  useHygieneLowConfidenceRows,
  useHygieneSupersededRows,
} from "../use-hygiene-queue"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("useHygieneDuplicateRows (DEMO on — the curated fixture)", () => {
  it("never reaches the network", () => {
    renderHook(() => useHygieneDuplicateRows({ limit: 10, offset: 0 }), { wrapper })
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it("honours the project filter — the fixture's own project matches, any other excludes everything", () => {
    const { result: matched } = renderHook(
      () => useHygieneDuplicateRows({ project: "darkmem", limit: 10, offset: 0 }),
      { wrapper },
    )
    expect(matched.current.rows.length).toBeGreaterThan(0)
    for (const row of matched.current.rows) expect(row.project).toBe("darkmem")

    const { result: unmatched } = renderHook(
      () => useHygieneDuplicateRows({ project: "no-such-project", limit: 10, offset: 0 }),
      { wrapper },
    )
    expect(unmatched.current.rows).toHaveLength(0)
    expect(unmatched.current.total).toBe(0)
  })

  it("applies offset/limit paging over the fixture, reporting the corpus total", () => {
    const { result: all } = renderHook(
      () => useHygieneDuplicateRows({ limit: 100, offset: 0 }),
      { wrapper },
    )
    const total = all.current.total
    expect(total).toBeGreaterThanOrEqual(2)

    const { result: page1 } = renderHook(
      () => useHygieneDuplicateRows({ limit: 1, offset: 0 }),
      { wrapper },
    )
    const { result: page2 } = renderHook(
      () => useHygieneDuplicateRows({ limit: 1, offset: 1 }),
      { wrapper },
    )
    expect(page1.current.rows).toHaveLength(1)
    expect(page2.current.rows).toHaveLength(1)
    expect(page2.current.rows[0]!.id).not.toBe(page1.current.rows[0]!.id)
    expect(page1.current.total).toBe(total)
    expect(page2.current.total).toBe(total)
  })
})

describe("useHygieneLowConfidenceRows / useHygieneExpiringRows (DEMO on)", () => {
  it("honours the project filter for both memory-row arms", () => {
    const { result: lowUnmatched } = renderHook(
      () => useHygieneLowConfidenceRows({ project: "no-such-project", limit: 10, offset: 0 }),
      { wrapper },
    )
    expect(lowUnmatched.current.rows).toHaveLength(0)

    const { result: expUnmatched } = renderHook(
      () => useHygieneExpiringRows({ project: "no-such-project", limit: 10, offset: 0 }),
      { wrapper },
    )
    expect(expUnmatched.current.rows).toHaveLength(0)
  })

  it("slices past the end of the fixture, still reporting the true total", () => {
    const { result: page0 } = renderHook(
      () => useHygieneLowConfidenceRows({ limit: 1, offset: 0 }),
      { wrapper },
    )
    expect(page0.current.rows.length).toBeGreaterThan(0)
    const total = page0.current.total

    const { result: pastEnd } = renderHook(
      () => useHygieneLowConfidenceRows({ limit: 1, offset: total }),
      { wrapper },
    )
    expect(pastEnd.current.rows).toHaveLength(0)
    expect(pastEnd.current.total).toBe(total)
  })
})

describe("useHygieneSupersededRows (DEMO on — flattened lineage)", () => {
  it("returns only the links the fixture itself marks superseded", () => {
    const { result } = renderHook(
      () => useHygieneSupersededRows({ limit: 10, offset: 0 }),
      { wrapper },
    )
    expect(result.current.rows.length).toBeGreaterThan(0)
    for (const row of result.current.rows) expect(row.status).toBe("superseded")
  })

  it("honours the project filter", () => {
    const { result } = renderHook(
      () => useHygieneSupersededRows({ project: "no-such-project", limit: 10, offset: 0 }),
      { wrapper },
    )
    expect(result.current.rows).toHaveLength(0)
    expect(result.current.total).toBe(0)
  })
})

describe("useHygieneCountsRows (DEMO on)", () => {
  it("counts the fixture directly, and honours the project filter the same way the list arms do", () => {
    const { result: matched } = renderHook(() => useHygieneCountsRows({}), { wrapper })
    expect(matched.current.duplicates).toBeGreaterThan(0)

    const { result: unmatched } = renderHook(
      () => useHygieneCountsRows({ project: "no-such-project" }),
      { wrapper },
    )
    expect(unmatched.current.duplicates).toBe(0)
    expect(unmatched.current.low_confidence).toBe(0)
    expect(unmatched.current.expiring_soon).toBe(0)
    expect(unmatched.current.superseded).toBe(0)
  })
})
