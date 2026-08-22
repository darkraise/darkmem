import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import type { UnifiedGraphData } from "@/hooks/api"

vi.mock("@/features/chat/components/chat-overlay", () => ({
  ChatOverlay: () => null,
}))
vi.mock("@/features/graph/components/graph-2d-renderer", () => ({
  Graph2DRenderer: () => null,
}))
vi.mock("@/features/graph/components/graph-3d-renderer", () => ({
  Graph3DRenderer: () => null,
}))
vi.mock("@/features/graph/components/mini-graph", () => ({ MiniGraph: () => null }))

const mockUseUnifiedGraph = vi.fn()
vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useUnifiedGraph: () => mockUseUnifiedGraph(),
}))

import { RealMemoryGraphPage } from "../real-memory-graph-page"

const DATA: UnifiedGraphData = {
  memories: [
    {
      id: "m1",
      content: "hello",
      source: "api",
      tags: [],
      memory_type: null,
      importance: 0.5,
      cluster: 0,
    },
  ],
  clusters: {},
  cluster_names: {},
  similarity_edges: [],
}

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

describe("graph loading affordance", () => {
  beforeEach(() => mockUseUnifiedGraph.mockReset())

  it("shows the skeleton on the first load, when there is nothing to keep", () => {
    mockUseUnifiedGraph.mockReturnValue({
      data: undefined,
      isLoading: true,
      isFetching: true,
    })
    render(<RealMemoryGraphPage />, { wrapper })
    expect(screen.getByText("Loading graph")).toBeInTheDocument()
  })

  // The defect: keepPreviousData holds the graph on screen when the entity
  // toggle changes the query key, so isLoading stays false and the fetch used
  // to be completely invisible.
  it("reports a refetch that isLoading cannot see", () => {
    mockUseUnifiedGraph.mockReturnValue({
      data: DATA,
      isLoading: false,
      isFetching: true,
    })
    render(<RealMemoryGraphPage />, { wrapper })
    // By text, not by role: the Spinner carries its own role="status" for
    // screen readers, so the role alone is ambiguous here.
    expect(screen.getByText(/Updating graph|Loading entities/)).toBeInTheDocument()
  })

  it("does not swap the canvas for a skeleton during that refetch", () => {
    mockUseUnifiedGraph.mockReturnValue({
      data: DATA,
      isLoading: false,
      isFetching: true,
    })
    render(<RealMemoryGraphPage />, { wrapper })
    // The renderer itself cannot be asserted here -- it mounts only once a
    // ResizeObserver measurement arrives, which jsdom never supplies. The
    // absence of the skeleton is the claim that matters and is observable:
    // the canvas, its camera and its layout are left alone.
    expect(screen.queryByText("Loading graph")).not.toBeInTheDocument()
  })

  it("says nothing once the fetch settles", () => {
    mockUseUnifiedGraph.mockReturnValue({
      data: DATA,
      isLoading: false,
      isFetching: false,
    })
    render(<RealMemoryGraphPage />, { wrapper })
    expect(
      screen.queryByText(/Updating graph|Loading entities/),
    ).not.toBeInTheDocument()
  })
})
