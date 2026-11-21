import { beforeEach, describe, expect, it, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { useDocumentRevision, useDocumentRevisions } from "../use-document-revisions-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("document revision reads", () => {
  it("lists newest first and pages back on next_before", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({ document_id: "d1", items: [{ id: "r2" }], next_before: "r2" })
      .mockResolvedValueOnce({ document_id: "d1", items: [{ id: "r1" }], next_before: null })
    const { result } = renderHook(() => useDocumentRevisions("d1", true), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe("/documents/d1/revisions?")
    expect(result.current.hasNextPage).toBe(true)
    await result.current.fetchNextPage()
    await waitFor(() => expect(result.current.data?.pages).toHaveLength(2))
    expect(vi.mocked(apiFetch).mock.calls[1]![0]).toBe("/documents/d1/revisions?before=r2")
  })

  it("stays idle while the sheet is closed", () => {
    const { result } = renderHook(() => useDocumentRevisions("d1", false), { wrapper })
    expect(result.current.fetchStatus).toBe("idle")
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })

  it("reads one revision with its content, and nothing without an id", async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ id: "r1", content: "a\n" })
    const none = renderHook(() => useDocumentRevision("d1", null), { wrapper })
    expect(none.result.current.fetchStatus).toBe("idle")
    const one = renderHook(() => useDocumentRevision("d1", "r1"), { wrapper })
    await waitFor(() => expect(one.result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/documents/d1/revisions/r1", expect.objectContaining({ signal: expect.any(AbortSignal) }))
    expect(one.result.current.data?.content).toBe("a\n")
  })
})
