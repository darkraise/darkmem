import { describe, expect, it, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { ApiError, apiFetch } from "@/lib/api"
import { useBoardRecords, useRegisterRowEdit } from "../use-board-api"

function setup() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
  return { qc, wrapper }
}

describe("the board hooks", () => {
  it("reads records for the named project", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      project: "darkmem",
      registers: [],
      plans: [],
    })
    const { wrapper } = setup()
    const { result } = renderHook(() => useBoardRecords("darkmem"), { wrapper })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe(
      "/board/records?project=darkmem",
    )
  })

  it("two quick edits to one register both land", async () => {
    vi.mocked(apiFetch).mockReset()
    let stored = "h1"
    let next = 1
    vi.mocked(apiFetch).mockImplementation(async (_path: string, init?: RequestInit) => {
      const { expected_hash } = JSON.parse(String(init?.body))
      if (expected_hash !== stored) {
        throw new ApiError("changed", 409, undefined, "hash_conflict")
      }
      stored = `h${++next}`
      return { document_id: "d", content_hash: stored, row: {} }
    })
    const { wrapper } = setup()
    const { result } = renderHook(() => useRegisterRowEdit("darkmem"), {
      wrapper,
    })
    const edit = (note: string) =>
      result.current.mutateAsync({
        documentId: "d",
        number: 7,
        expectedHash: "h1",
        note,
      })
    await expect(Promise.all([edit("first"), edit("second")])).resolves.toHaveLength(2)
    const sent = vi
      .mocked(apiFetch)
      .mock.calls.map(([, init]) => JSON.parse(String(init?.body)))
    expect(sent).toEqual([
      { expected_hash: "h1", note: "first" },
      { expected_hash: "h2", note: "second" },
    ])
  })

  it("sends the row edit with its expected hash and re-reads the records", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      document_id: "d",
      content_hash: "h2",
      row: {},
    })
    const { qc, wrapper } = setup()
    const invalidate = vi.spyOn(qc, "invalidateQueries")
    const { result } = renderHook(() => useRegisterRowEdit("darkmem"), {
      wrapper,
    })
    await result.current.mutateAsync({
      documentId: "d",
      number: 7,
      expectedHash: "h1",
      state: "verify",
      note: "why",
    })
    expect(vi.mocked(apiFetch)).toHaveBeenCalledWith(
      "/board/registers/d/rows/7",
      {
        method: "PATCH",
        body: JSON.stringify({
          expected_hash: "h1",
          state: "verify",
          note: "why",
        }),
      },
    )
    expect(invalidate).toHaveBeenCalledWith({
      queryKey: ["boardRecords", "darkmem"],
    })
  })
})
