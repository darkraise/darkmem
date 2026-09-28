import { describe, expect, it, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { ApiError, apiFetch } from "@/lib/api"
import {
  useWorklogEntries,
  useWorklogResume,
  useWorklogSearch,
  useWorkstreamPurge,
  useWorkstreams,
  useWorkstreamUpdate,
} from "../use-worklog-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("work-log reads", () => {
  it("lists one state of a project's workstreams and pages back on next_before", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({ items: [{ id: "w1" }], next_before: "cursor-1" })
      .mockResolvedValueOnce({ items: [{ id: "w2" }], next_before: null })
    const { result } = renderHook(() => useWorkstreams("darkmem", "open"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe(
      "/worklog/workstreams?project=darkmem&state=open&limit=50",
    )
    expect(result.current.hasNextPage).toBe(true)
    await result.current.fetchNextPage()
    await waitFor(() => expect(result.current.data?.pages).toHaveLength(2))
    expect(vi.mocked(apiFetch).mock.calls[1]![0]).toBe(
      "/worklog/workstreams?project=darkmem&state=open&limit=50&before=cursor-1",
    )
    expect(result.current.hasNextPage).toBe(false)
  })

  it("reads entries forward on next_after, filtered by kind", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({ items: [{ id: "e1", seq: 4 }], next_after: 4 })
      .mockResolvedValueOnce({ items: [], next_after: null })
    const { result } = renderHook(() => useWorklogEntries("w1", "ledger", false), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe(
      "/worklog/workstreams/w1/entries?limit=200&kind=ledger",
    )
    await result.current.fetchNextPage()
    await waitFor(() => expect(vi.mocked(apiFetch)).toHaveBeenCalledTimes(2))
    expect(vi.mocked(apiFetch).mock.calls[1]![0]).toBe(
      "/worklog/workstreams/w1/entries?limit=200&kind=ledger&after=4",
    )
  })

  it("stays idle without a workstream", () => {
    const { result } = renderHook(() => useWorklogEntries(null, null, true), { wrapper })
    expect(result.current.fetchStatus).toBe("idle")
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })

  it("answers null for a workstream that does not exist", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new ApiError("No workstream", 404))
    const { result } = renderHook(() => useWorklogResume("darkmem", "nope"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(result.current.data).toBeNull()
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe(
      "/worklog/resume?project=darkmem&workstream=nope",
    )
  })

  it("reads no resume while disabled", () => {
    const { result } = renderHook(() => useWorklogResume("darkmem", "plan", false), { wrapper })
    expect(result.current.fetchStatus).toBe("idle")
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })

  it("surfaces any other resume failure as an error", async () => {
    vi.mocked(apiFetch).mockRejectedValueOnce(new ApiError("boom", 500))
    const { result } = renderHook(() => useWorklogResume("darkmem", "plan"), { wrapper })
    await waitFor(() => expect(result.current.isError).toBe(true))
  })
})

describe("work-log writes", () => {
  it("patches, purges and searches through the work-log routes", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [], semantic_ran: true })
    const update = renderHook(() => useWorkstreamUpdate(), { wrapper })
    await update.result.current.mutateAsync({ id: "w1", state: "closed" })
    expect(vi.mocked(apiFetch)).toHaveBeenLastCalledWith("/worklog/workstreams/w1", {
      method: "PATCH",
      body: JSON.stringify({ state: "closed" }),
    })

    const purge = renderHook(() => useWorkstreamPurge(), { wrapper })
    await purge.result.current.mutateAsync("w1")
    expect(vi.mocked(apiFetch)).toHaveBeenLastCalledWith("/worklog/workstreams/w1", {
      method: "DELETE",
    })

    const search = renderHook(() => useWorklogSearch(), { wrapper })
    await search.result.current.mutateAsync({ project: "darkmem", query: "retention" })
    expect(vi.mocked(apiFetch)).toHaveBeenLastCalledWith("/worklog/search", {
      method: "POST",
      body: JSON.stringify({ project: "darkmem", query: "retention" }),
    })
  })
})
