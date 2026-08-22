import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useMemories } from "../use-memory-api"
import { useProjectStore, DEFAULT_PROJECT } from "@/stores/project-store"
import { projectScopedKey } from "@/lib/query-keys"

// Ruling 2: a hand-written list of keys asserting today's shape is not
// proof the cache behaves. This seeds real cache entries under one
// project, switches the global store, and asserts the previous project's
// rows are not what a fresh mount of the SAME hook reads.
describe("useMemories: switching the active project never serves the previous project's rows", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useProjectStore.setState({
      activeProject: DEFAULT_PROJECT,
    })
  })

  function wrapper(queryClient: QueryClient) {
    return function Wrapper({ children }: { children: ReactNode }) {
      return (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      )
    }
  }

  it("addresses a distinct, empty cache entry after a project switch", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })

    const ROWS_A = [{ id: "a-memory", content: "belongs to project alpha" }]
    vi.mocked(apiFetch).mockResolvedValueOnce(ROWS_A)

    const { result, unmount } = renderHook(() => useMemories(), {
      wrapper: wrapper(queryClient),
    })
    await waitFor(() => expect(result.current.data).toEqual(ROWS_A))

    const keyAlpha = projectScopedKey("memories")
    expect(queryClient.getQueryData(keyAlpha)).toEqual(ROWS_A)
    unmount()

    // Switch scope — a distinct mount of the same hook, same cache, no refetch yet.
    useProjectStore.getState().setProject("beta")
    const keyBeta = projectScopedKey("memories")
    expect(keyBeta).not.toEqual(keyAlpha)

    // The critical assertion: project alpha's rows are not readable under
    // project beta's key. A cache keyed only on "memories" (no project)
    // would return ROWS_A here instead of undefined.
    expect(queryClient.getQueryData(keyBeta)).toBeUndefined()

    // Alpha's own entry survives untouched — switching scope doesn't erase
    // history, it changes which entry the view reads.
    expect(queryClient.getQueryData(keyAlpha)).toEqual(ROWS_A)

    const ROWS_B = [{ id: "b-memory", content: "belongs to project beta" }]
    vi.mocked(apiFetch).mockResolvedValueOnce(ROWS_B)

    const second = renderHook(() => useMemories(), { wrapper: wrapper(queryClient) })
    await waitFor(() => expect(second.result.current.data).toEqual(ROWS_B))
    expect(second.result.current.data).not.toEqual(ROWS_A)
  })

  it("sends the active project in the request body, not just the cache key", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    vi.mocked(apiFetch).mockResolvedValueOnce([])
    useProjectStore.getState().setProject("acme")

    renderHook(() => useMemories(), { wrapper: wrapper(queryClient) })
    await waitFor(() => expect(apiFetch).toHaveBeenCalled())

    const call = vi.mocked(apiFetch).mock.calls[0]
    if (!call) throw new Error("apiFetch was never called")
    const [, init] = call
    const body = JSON.parse((init as { body: string }).body)
    expect(body.project).toBe("acme")
  })
})
