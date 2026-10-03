import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useUnifiedGraph } from "../use-graph-api"
import { useProjectStore, DEFAULT_PROJECT } from "@/stores/project-store"
import { projectScopedKey } from "@/lib/query-keys"

// Mirrors use-memory-api-project-scope.test.tsx (T1.65): a hand-written
// key list is not proof the cache behaves, so this seeds a real cache
// entry under one project, switches the store, and asserts the previous
// project's rows are not what a fresh mount reads.
describe("useUnifiedGraph: switching the active project never serves the previous project's rows", () => {
  it("does not retain a mounted observer's rows while another project loads", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const previous = { memories: [{ id: "private-alpha" }], clusters: {}, cluster_names: {}, similarity_edges: [] }
    vi.mocked(apiFetch).mockResolvedValueOnce(previous)
    const { result } = renderHook(() => useUnifiedGraph(), { wrapper: wrapper(queryClient) })
    await waitFor(() => expect(result.current.data).toEqual(previous))
    vi.mocked(apiFetch).mockImplementationOnce(() => new Promise(() => {}))
    act(() => useProjectStore.getState().setProject("beta"))
    expect(result.current.data).toBeUndefined()
  })
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

    const DATA_A = { memories: [{ id: "alpha-mem" }], clusters: {}, cluster_names: {}, similarity_edges: [] }
    vi.mocked(apiFetch).mockResolvedValueOnce(DATA_A)

    const { result, unmount } = renderHook(() => useUnifiedGraph(), {
      wrapper: wrapper(queryClient),
    })
    await waitFor(() => expect(result.current.data).toEqual(DATA_A))

    const keyAlpha = projectScopedKey("unifiedGraph", 0.75, 3, false, 200)
    expect(queryClient.getQueryData(keyAlpha)).toEqual(DATA_A)
    unmount()

    useProjectStore.getState().setProject("beta")
    const keyBeta = projectScopedKey("unifiedGraph", 0.75, 3, false, 200)
    expect(keyBeta).not.toEqual(keyAlpha)

    // The critical assertion: project alpha's rows are not readable under
    // project beta's key.
    expect(queryClient.getQueryData(keyBeta)).toBeUndefined()
    expect(queryClient.getQueryData(keyAlpha)).toEqual(DATA_A)

    const DATA_B = { memories: [{ id: "beta-mem" }], clusters: {}, cluster_names: {}, similarity_edges: [] }
    vi.mocked(apiFetch).mockResolvedValueOnce(DATA_B)

    const second = renderHook(() => useUnifiedGraph(), { wrapper: wrapper(queryClient) })
    await waitFor(() => expect(second.result.current.data).toEqual(DATA_B))
    expect(second.result.current.data).not.toEqual(DATA_A)
  })

  it("sends the active project on the fetch URL, not just the cache key", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    vi.mocked(apiFetch).mockResolvedValueOnce({
      memories: [],
      clusters: {},
      cluster_names: {},
      similarity_edges: [],
    })
    useProjectStore.getState().setProject("acme")

    renderHook(() => useUnifiedGraph(), { wrapper: wrapper(queryClient) })
    await waitFor(() => expect(apiFetch).toHaveBeenCalled())

    const url = vi.mocked(apiFetch).mock.calls[0]![0] as string
    expect(url).toContain(`project=${encodeURIComponent("acme")}`)
  })
})
