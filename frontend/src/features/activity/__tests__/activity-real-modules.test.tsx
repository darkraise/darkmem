import { fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { useDemoStore } from "@/demo/store"
import { FeedTab } from "../components/feed-tab"
import { DayTab } from "../components/day-tab"
import { MonitorsTab } from "../components/monitors-tab"

// This exercises the fixture-backed path deliberately (T1.45/T1.61 are
// done and this file pins their demo rendering), so it is frozen at
// DEMO: true rather than relying on the about-to-change default (T1.58).
vi.mock("@/demo/flag", () => ({ DEMO: true }))

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

describe("Buffer monitor — poison rows are actionable", () => {
  it("shows claimed, stale, and poison rows with correctly-labelled attempt counts", () => {
    render(withQuery(<MonitorsTab onOpenDigest={() => {}} />))
    expect(screen.getByText(/stale claims/)).toBeInTheDocument()
    expect(screen.getByText(/poison rows/)).toBeInTheDocument()
    // "claimed N/M times" — never "failed" or "attempts" bare, per T1.13
    // ruling 1: attempts count claims, not failures.
    expect(screen.getAllByText(/claimed \d+\/\d+ times/).length).toBeGreaterThan(0)
    expect(screen.queryByText(/failed \d+ times/)).not.toBeInTheDocument()
  })

  it("forgetting a poison row removes it and decrements the error count", () => {
    render(withQuery(<MonitorsTab onOpenDigest={() => {}} />))
    const before = useDemoStore.getState().bufferMonitor.target.error
    fireEvent.click(screen.getByText("Forget"))
    const after = useDemoStore.getState().bufferMonitor.target
    expect(after.error).toBe(before - 1)
    expect(after.poisonRows).toHaveLength(0)
    expect(screen.queryByText(/poison rows/)).not.toBeInTheDocument()
  })

  it("retrying a poison row re-buffers it to pending", () => {
    render(withQuery(<MonitorsTab onOpenDigest={() => {}} />))
    const before = useDemoStore.getState().bufferMonitor.target
    fireEvent.click(screen.getByText("Retry (re-buffer)"))
    const after = useDemoStore.getState().bufferMonitor.target
    expect(after.error).toBe(before.error - 1)
    expect(after.pending).toBe(before.pending + 1)
    expect(after.poisonRows).toHaveLength(0)
  })
})
