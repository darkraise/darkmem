import { fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { useDemoStore } from "@/demo/store"
import { FeedTab } from "../components/feed-tab"
import { DayTab } from "../components/day-tab"

// This exercises the fixture-backed path deliberately (T1.45/T1.61 are
// done and this file pins their demo rendering), so it is frozen at
// DEMO: true rather than relying on the about-to-change default (T1.58).
vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))

// DayTab renders a <Link> back to the calendar; stub it so the test needs
// no RouterProvider (matching calendar-card.test.tsx's convention).
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({ children }: { children: ReactNode }) => <a href="#">{children}</a>,
}))

function withQuery(children: ReactNode) {
  const qc = new QueryClient()
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

afterEach(() => {
  useDemoStore.getState().resetActivity()
})

describe("FeedTab reads /events (demo-bound)", () => {
  it("renders the fetched feed rows, no client-side count claimed", () => {
    render(withQuery(<FeedTab />))
    expect(screen.getByText("Activity — live feed")).toBeInTheDocument()
    expect(screen.getAllByText(/memory\.created|pipeline\.completed/).length)
      .toBeGreaterThan(0)
  })

  it("filters by category without losing the underlying fetch", () => {
    render(withQuery(<FeedTab />))
    fireEvent.click(screen.getByText("verification"))
    expect(screen.getAllByText("fact.verified").length).toBeGreaterThan(0)
    expect(screen.queryByText("repo.indexing_completed")).not.toBeInTheDocument()
  })
})

describe("DayTab reads the UTC day bucket (demo-bound)", () => {
  it("renders the day's events and labels the bucket as UTC", () => {
    render(withQuery(<DayTab day="2026-07-20" onDayChange={() => {}} />))
    expect(screen.getByText(/Days are UTC/)).toBeInTheDocument()
    expect(screen.getAllByText("created").length).toBeGreaterThan(0)
  })

  it("shows an honest empty state for a day with no events", () => {
    render(withQuery(<DayTab day="2020-01-01" onDayChange={() => {}} />))
    expect(screen.getByText("No activity on this day")).toBeInTheDocument()
  })
})
