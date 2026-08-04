import { describe, it, expect, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useUndoDreamCycle } from "../use-dream-digest-api"

function wrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

// F9: a hygiene bulk action's undo and the dream-digest surface's undo are
// the exact same door (`POST /dream-digest/cycles/{id}/undo`) — a hygiene
// bulk action mints its own cycle through it (doc 08 §7's unification).
// Before this fix, hygiene-queue.tsx owned a near-duplicate hook
// (`useUndoCycle`) that invalidated only `hygieneQueue`, and this hook
// invalidated only `dreamDigest`: undoing from one surface left the other
// surface's cache stale. There is now exactly one mutation hook for either
// door, and this proves it settles both caches.
describe("useUndoDreamCycle: invalidates both surfaces' caches, not just its own", () => {
  it("marks a hygieneQueue-keyed and a dreamDigest-keyed cache entry stale after undo", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    queryClient.setQueryData(["hygieneQueue", "duplicates", ""], { items: [], total: 0 })
    queryClient.setQueryData(["dreamDigest", "cycles", ""], { items: [], total: 0 })

    vi.mocked(apiFetch).mockResolvedValue({ undo_batch_id: "u1", undone: [] })

    const { result } = renderHook(() => useUndoDreamCycle(), {
      wrapper: wrapper(queryClient),
    })
    result.current.mutate({ cycleId: "cyc-1" })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    await waitFor(() => {
      expect(
        queryClient.getQueryState(["hygieneQueue", "duplicates", ""])?.isInvalidated,
      ).toBe(true)
      expect(
        queryClient.getQueryState(["dreamDigest", "cycles", ""])?.isInvalidated,
      ).toBe(true)
    })
  })
})
