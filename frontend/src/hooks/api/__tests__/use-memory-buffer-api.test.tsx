import { beforeEach, describe, expect, it, vi } from "vitest"
import { act, renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import {
  useDiscardBufferItem,
  useMemoryBufferItems,
  useRequeueBufferItem,
} from "../use-memory-buffer-api"

const ROW = {
  id: "b1",
  memory_id: "m1",
  memory_exists: true,
  project: "default",
  source: "api",
  status: "error",
  is_stale: false,
  attempts: 5,
  max_attempts: 5,
  last_error: "value too long",
  created_at: "2026-11-20T10:00:00Z",
  claimed_at: null,
  claimed_by: null,
  token_size: null,
  content_preview: "a capture",
  content_length: 9,
}

function setup() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
  return { qc, wrapper }
}

beforeEach(() => vi.mocked(apiFetch).mockReset())

describe("the memory buffer hooks", () => {
  it("lists poison rows", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [ROW], total: 1, limit: 200, offset: 0,
    })
    const { wrapper } = setup()
    const { result } = renderHook(() => useMemoryBufferItems(), { wrapper })

    await waitFor(() => expect(result.current.items).toHaveLength(1))
    expect(result.current.total).toBe(1)
    expect(apiFetch).toHaveBeenCalledTimes(1)
    expect(vi.mocked(apiFetch).mock.calls[0]![0]).toBe(
      "/memory-buffer?state=poison&limit=200",
    )
  })

  it("discard and requeue invalidate the list", async () => {
    vi.mocked(apiFetch).mockResolvedValue(undefined)
    const { qc, wrapper } = setup()
    const invalidate = vi.spyOn(qc, "invalidateQueries")
    const discard = renderHook(() => useDiscardBufferItem(), { wrapper })
    const requeue = renderHook(() => useRequeueBufferItem(), { wrapper })

    await act(() => discard.result.current.mutateAsync("b1"))
    expect(apiFetch).toHaveBeenCalledTimes(1)
    expect(apiFetch).toHaveBeenLastCalledWith("/memory-buffer/b1", {
      method: "DELETE",
    })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["memoryBuffer"] })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["memories"] })

    invalidate.mockClear()
    await act(() => requeue.result.current.mutateAsync("b2"))
    expect(apiFetch).toHaveBeenCalledTimes(2)
    expect(apiFetch).toHaveBeenLastCalledWith("/memory-buffer/b2/requeue", {
      method: "POST",
    })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["memoryBuffer"] })
    expect(invalidate).not.toHaveBeenCalledWith({ queryKey: ["memories"] })
  })
})
