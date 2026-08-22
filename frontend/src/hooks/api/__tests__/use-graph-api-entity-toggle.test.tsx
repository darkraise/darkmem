import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useUnifiedGraph } from "../use-graph-api"
import { useProjectStore, DEFAULT_PROJECT } from "@/stores/project-store"

const WITHOUT = {
  memories: [{ id: "m1" }],
  clusters: {},
  cluster_names: {},
  similarity_edges: [],
}
const WITH_ENTITIES = { ...WITHOUT, entities: [{ id: "e1" }] }

function wrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
  }
}

// `includeEntities` is part of the query key, so toggling the entity layer
// addresses a different cache entry. Without held-over data the hook reports
// `isLoading`, and the page swaps the whole graph for a skeleton to add an
// overlay to a graph already on screen.
describe("useUnifiedGraph: toggling the entity layer", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useProjectStore.setState({ activeProject: DEFAULT_PROJECT })
  })

  it("keeps the graph on screen while the new shape is fetched", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    vi.mocked(apiFetch).mockResolvedValueOnce(WITHOUT)

    const { result, rerender } = renderHook(
      ({ entities }: { entities: boolean }) =>
        useUnifiedGraph(0.75, 3, entities),
      { wrapper: wrapper(queryClient), initialProps: { entities: false } },
    )
    await waitFor(() => expect(result.current.data).toEqual(WITHOUT))

    let resolveSecond: (v: unknown) => void = () => {}
    vi.mocked(apiFetch).mockReturnValueOnce(
      new Promise((res) => {
        resolveSecond = res
      }) as Promise<unknown>,
    )
    rerender({ entities: true })

    // The moment that matters: mid-flight, the previous graph is still served
    // and the hook is not reporting a cold load.
    expect(result.current.isLoading).toBe(false)
    expect(result.current.data).toEqual(WITHOUT)

    resolveSecond(WITH_ENTITIES)
    await waitFor(() => expect(result.current.data).toEqual(WITH_ENTITIES))
  })
})
