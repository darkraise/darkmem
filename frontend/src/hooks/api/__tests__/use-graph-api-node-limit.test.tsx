import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useUnifiedGraph } from "../use-graph-api"
import { useProjectStore, DEFAULT_PROJECT } from "@/stores/project-store"
import { projectScopedKey } from "@/lib/query-keys"

const EMPTY = { memories: [], clusters: {}, cluster_names: {}, similarity_edges: [] }

function setup() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
  return { queryClient, wrapper }
}

describe("useUnifiedGraph: node budget", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useProjectStore.setState({ activeProject: DEFAULT_PROJECT })
    vi.mocked(apiFetch).mockResolvedValue(EMPTY)
  })

  it("sends the node limit when All is off", async () => {
    const { wrapper } = setup()
    renderHook(() => useUnifiedGraph(0.75, 3, false, 500, false), { wrapper })
    await waitFor(() => expect(apiFetch).toHaveBeenCalled())
    const url = vi.mocked(apiFetch).mock.calls[0]![0] as string
    expect(url).toContain("limit=500")
    expect(url).not.toContain("all=true")
  })

  it("sends all=true and no limit when All is on", async () => {
    const { wrapper } = setup()
    renderHook(() => useUnifiedGraph(0.75, 3, false, 500, true), { wrapper })
    await waitFor(() => expect(apiFetch).toHaveBeenCalled())
    const url = vi.mocked(apiFetch).mock.calls[0]![0] as string
    expect(url).toContain("all=true")
    expect(url).not.toContain("limit=")
  })

  it("keys the cache on the budget", async () => {
    const { queryClient, wrapper } = setup()
    const { result } = renderHook(() => useUnifiedGraph(0.75, 3, false, 500, true), { wrapper })
    await waitFor(() => expect(result.current.data).toEqual(EMPTY))
    expect(queryClient.getQueryData(projectScopedKey("unifiedGraph", 0.75, 3, false, "all"))).toEqual(EMPTY)
    expect(queryClient.getQueryData(projectScopedKey("unifiedGraph", 0.75, 3, false, 500))).toBeUndefined()
  })
})
