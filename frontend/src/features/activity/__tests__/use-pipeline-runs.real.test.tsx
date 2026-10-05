import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { derivedOutcome, usePipelineRuns } from "../use-pipeline-runs"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("usePipelineRuns (DEMO off — real /analytics/pipeline-logs)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("ruling 3: a partial outcome survives as partial, not folded into completed or failed", async () => {
    vi.mocked(apiFetch).mockResolvedValue([
      {
        id: 1,
        memory_id: "11111111-2222-3333-4444-555555555555",
        details: {
          embed: "ok", extract: "ok", vector: "ok", graph: "error",
          entities_count: 2, relations_count: 1,
          error: "Graph write failed: boom", outcome: "partial",
        },
        timestamp: "2026-07-27T18:55:00Z",
      },
    ])
    const { result } = renderHook(() => usePipelineRuns(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(apiFetch).toHaveBeenCalledWith(
      expect.stringContaining("/analytics/pipeline-logs"),
    )
    const [run] = result.current.runs
    expect(run!.terminal).toBe("partial")
    expect(run!.substeps).toEqual({ vector: "ok", graph: "error" })
    // The split write dot needs vector===ok / graph===error visible on the
    // step array too, not collapsed to a single pass/fail colour.
    expect(run!.steps[4]).not.toBe("ok")
    expect(run!.note).toBe("Graph write failed: boom")
  })

  it("never fabricates an in-flight row — real mode has no per-phase progress signal", async () => {
    vi.mocked(apiFetch).mockResolvedValue([
      {
        id: 2,
        memory_id: "22222222-2222-3333-4444-555555555555",
        details: {
          embed: "ok", extract: "ok", vector: "ok", graph: "ok",
          entities_count: 1, relations_count: 0, error: null, outcome: "completed",
        },
        timestamp: "2026-07-27T18:55:00Z",
      },
    ])
    const { result } = renderHook(() => usePipelineRuns(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.runs.every((r) => r.terminal !== "running")).toBe(true)
  })

  it("the batch backstop's unknown/error status reads as a hard failure, never softened", async () => {
    vi.mocked(apiFetch).mockResolvedValue([
      {
        id: 3,
        memory_id: "33333333-2222-3333-4444-555555555555",
        details: {
          embed: "unknown", extract: "unknown", vector: "error", graph: "error",
          entities_count: 0, relations_count: 0, error: "boom", outcome: "failed",
        },
        timestamp: "2026-07-27T18:55:00Z",
      },
    ])
    const { result } = renderHook(() => usePipelineRuns(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    const [run] = result.current.runs
    expect(run!.terminal).toBe("failed")
    expect(run!.steps[0]).toBe("error")
    expect(run!.steps[1]).toBe("error")
  })

  it("surfaces a failed load as isError, not as an empty run list", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    const { result } = renderHook(() => usePipelineRuns(), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.runs).toEqual([])
  })
})

describe("derivedOutcome", () => {
  it("reads a row journalled without an outcome from its steps", () => {
    // Older update and reprocess doors wrote a second `extracted` row with
    // only the step statuses; every step ok is a completed run, not a failure.
    expect(
      derivedOutcome({ embed: "ok", extract: "ok", vector: "ok", graph: "ok" }),
    ).toBe("completed")
    expect(
      derivedOutcome({ embed: "ok", extract: "ok", vector: "ok", graph: "error" }),
    ).toBe("partial")
    expect(
      derivedOutcome({ embed: "error", extract: "skipped", vector: "skipped", graph: "skipped" }),
    ).toBe("failed")
    expect(derivedOutcome({})).toBe("failed")
  })
})
