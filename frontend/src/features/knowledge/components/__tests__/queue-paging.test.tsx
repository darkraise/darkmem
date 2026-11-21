import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { readFileSync } from "node:fs"
import path from "node:path"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({ children, to: _to, params: _params, ...rest }: { children?: ReactNode; [key: string]: unknown }) => (
    <a {...rest}>{children}</a>
  ),
}))
vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useBulkPrune: () => ({ mutate: vi.fn() }),
  useBulkSupersede: () => ({ mutate: vi.fn() }),
  useBulkConfirmDedup: () => ({ mutate: vi.fn() }),
  useUndoDreamCycle: () => ({ mutate: vi.fn() }),
  useRatifyFact: () => ({ mutate: vi.fn(), isPending: false }),
  useRejectFact: () => ({ mutate: vi.fn(), isPending: false }),
  useDismissSuspicion: () => ({ mutate: vi.fn(), isPending: false }),
}))

interface Page {
  limit: number
  offset: number
}
const seen: Record<string, number[]> = { facts: [], low: [] }
const empty = { rows: [], total: 0, loading: false, error: false }
const range = ({ limit, offset }: Page, total: number) =>
  Array.from({ length: Math.max(0, Math.min(limit, total - offset)) }, (_, i) => offset + i)

vi.mock("../../use-review-queue", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../use-review-queue")>()),
  useReviewFactRows: (q: Page) => {
    seen.facts!.push(q.offset)
    return {
      rows: range(q, 25).map((n) => ({
        id: `f${n}`,
        queue_id: `f${n}`,
        project: "p",
        subject_name: `subject ${n}`,
        rel_type: "USES",
        object_name: "postgres",
        fact_text: `fact ${n}`,
        verification_status: "disputed",
        reason: "disputed",
        under_sourced: false,
        label_suppressed: null,
        suspected_contradiction: null,
        evidence: null,
        created_at: "2026-07-01T00:00:00Z",
      })),
      total: 25,
      loading: false,
      error: false,
    }
  },
  useReviewArticleRows: () => empty,
}))
vi.mock("../../use-hygiene-queue", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../../use-hygiene-queue")>()),
  useHygieneLowConfidenceRows: (q: Page) => {
    seen.low!.push(q.offset)
    return {
      rows: range(q, 25).map((n) => ({
        id: `m${n}`,
        project: "p",
        content_preview: `memory ${n}`,
        confidence: 0.2,
        expires_at: null,
        status: "active",
        superseded_by: null,
        reason: "low confidence",
        created_at: "2026-07-01T00:00:00Z",
      })),
      total: 25,
      loading: false,
      error: false,
    }
  },
  useHygieneDuplicateRows: () => empty,
  useHygieneExpiringRows: () => empty,
  useHygieneSupersededRows: () => empty,
}))

import { HygieneQueue } from "../hygiene-queue"
import { ReviewQueue } from "../review-queue"

beforeEach(() => {
  seen.facts = []
  seen.low = []
})

describe("queue paging", () => {
  it.each([
    ["review", () => <ReviewQueue project="p" />, "facts"],
    ["hygiene", () => <HygieneQueue project="p" />, "low"],
  ] as const)("both queues page with the library pagination (%s)", async (_name, ui, key) => {
    render(ui())
    const pager = screen.getByRole("navigation", { name: "pagination" })
    expect(within(pager).getByRole("link", { name: /previous page/i })).toHaveAttribute(
      "aria-disabled",
      "true",
    )
    await userEvent.click(within(pager).getByRole("link", { name: /next page/i }))
    expect(seen[key]![seen[key]!.length - 1]).toBe(10)
    await userEvent.click(
      within(screen.getByRole("navigation", { name: "pagination" })).getByRole("link", {
        name: /previous page/i,
      }),
    )
    expect(seen[key]![seen[key]!.length - 1]).toBe(0)
  })

  it("no hand-written pager is left in either queue", () => {
    for (const file of ["review-queue.tsx", "hygiene-queue.tsx"]) {
      const source = readFileSync(path.resolve(__dirname, "..", file), "utf8")
      expect(source, file).toContain("<QueuePager")
      expect(source, file).not.toMatch(/function PageControls|ChevronLeft|ChevronRight|aria-label="Next page"/)
    }
  })
})
