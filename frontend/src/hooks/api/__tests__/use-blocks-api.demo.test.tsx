import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useBlockUpdate } from "../use-blocks-api"

describe("the block hooks in demo mode", () => {
  beforeEach(() => vi.clearAllMocks())

  it("takes no read of its own, since one 401 signs the demo out", async () => {
    vi.mocked(apiFetch).mockResolvedValue(undefined as never)
    const qc = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    )
    const { result } = renderHook(() => useBlockUpdate("doc-demo"), { wrapper })

    act(() => {
      result.current.mutate({ blockId: "b1", text: "one" })
    })
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    // The blocks query is disabled here, so the queue has no seed and would
    // otherwise re-read: the one call made is the write itself.
    expect(vi.mocked(apiFetch)).toHaveBeenCalledTimes(1)
    const [path, init] = vi.mocked(apiFetch).mock.calls[0]!
    expect(path).toContain("/documents/doc-demo/blocks/b1")
    expect(init!.method).toBe("PATCH")
    expect(JSON.parse(String(init!.body))).not.toHaveProperty("expected_hash")
  })
})
