import { fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { useDemoStore } from "@/demo/store"
import { PipelineTab } from "../components/pipeline-tab"
import { TriageTab } from "../components/triage-tab"
import { DreamTab } from "../components/dream-tab"
import { CheckpointsTab } from "../components/checkpoints-tab"

// This file pins the fixture-backed rendering deliberately (T1.45 is
// done), so it is frozen at DEMO: true rather than relying on the
// about-to-change default (T1.58) — neither tab's real branch ever fires
// here, but useQuery is called unconditionally (rules of hooks) and
// throws without a QueryClient in the tree regardless of `enabled`.
vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
function withQuery(children: ReactNode) {
  const qc = new QueryClient()
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

afterEach(() => {
  useDemoStore.getState().resetActivity()
})

describe("PipelineTab honesty", () => {
  it("names the failed step on every partial/failed row — never a bare fail", () => {
    render(withQuery(<PipelineTab />))
    expect(screen.getByText("graph_write")).toBeInTheDocument()
    expect(screen.getByText("extraction_partial")).toBeInTheDocument()
    expect(screen.getByText("content_embedding")).toBeInTheDocument()
  })

  it("renders the honest terminal chips", () => {
    render(withQuery(<PipelineTab />))
    expect(screen.getByText("running")).toBeInTheDocument()
    expect(screen.getByText("completed")).toBeInTheDocument()
    expect(screen.getAllByText("partial").length).toBeGreaterThan(0)
    expect(screen.getByText("failed")).toBeInTheDocument()
  })
})

describe("TriageTab", () => {
  it("surfaces the poison row with its reason and a deliberate retry", () => {
    render(withQuery(<TriageTab />))
    expect(screen.getByText("poison")).toBeInTheDocument()
    expect(screen.getByText("Retry anyway")).toBeInTheDocument()
  })

  it("shows the healthy empty state once every row is forgotten", () => {
    const store = useDemoStore.getState()
    for (const f of store.pipelineFailures) store.forgetFailure(f.id)
    render(withQuery(<TriageTab />))
    expect(screen.getByText("No failures to triage")).toBeInTheDocument()
  })
})

describe("DreamTab undo honesty", () => {
  it("renders a disabled undo WITH its reason for a blocked action", () => {
    render(<DreamTab />)
    expect(
      screen.getByText(/a newer change rewrote this object/i),
    ).toBeInTheDocument()
    // Past-window entries live behind the "Earlier cycles" disclosure.
    fireEvent.click(screen.getByText(/Earlier cycles/))
    expect(
      screen.getAllByText(/dream_undo_retention elapsed/i).length,
    ).toBeGreaterThan(0)
  })

  it("offers per-action undo buttons and per-batch undo", () => {
    render(<DreamTab />)
    expect(screen.getAllByRole("button", { name: /^Undo(?! batch)/ }).length)
      .toBeGreaterThan(0)
    expect(
      screen.getAllByRole("button", { name: /Undo batch/ }).length,
    ).toBeGreaterThan(0)
  })
})

describe("CheckpointsTab is operational — no verification badge", () => {
  it("labels every run 'session digest · not verified knowledge'", () => {
    render(withQuery(<CheckpointsTab />))
    expect(
      screen.getAllByText("session digest · not verified knowledge").length,
    ).toBeGreaterThan(0)
  })

  it("never renders the vault's rung vocabulary", () => {
    render(withQuery(<CheckpointsTab />))
    expect(screen.queryByText("corroborated")).not.toBeInTheDocument()
    expect(screen.queryByText("candidate")).not.toBeInTheDocument()
  })

  it("shows the marker-bounded CLAUDE.md resume block", () => {
    // The writer's own sentinels (`inject_block.MARKER_BEGIN` / `MARKER_END`).
    // This asserted a `darkmem:resume:begin` pair until 2026-08-11 — markers
    // no shipped code writes, so the demo taught a block the real writer
    // would not have recognised.
    render(withQuery(<CheckpointsTab />))
    expect(screen.getByText(/<!-- darkmem:begin -->/)).toBeInTheDocument()
  })
})
