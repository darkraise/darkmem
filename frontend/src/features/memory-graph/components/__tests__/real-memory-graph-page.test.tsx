import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
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
vi.mock("@/features/graph/components/mini-graph", () => ({
  MiniGraph: () => null,
}))

const mockUseUnifiedGraph = vi.fn()
vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useUnifiedGraph: () => mockUseUnifiedGraph(),
}))

import { RealMemoryGraphPage } from "../real-memory-graph-page"

const ONE_MEMORY: UnifiedGraphData = {
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
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

// T1.60 Step 4 (closes F8/I1's "surface it" bar and F10's UI half): the
// entity-layer toggle carries two distinct captions — a permanent one
// (entities are globally scoped, a standing fact, not a per-request
// signal) and a conditional one (entities_truncated, visible only when
// the under-return is actually happening).
describe("RealMemoryGraphPage: entity-overlay honesty captions", () => {
  beforeEach(() => {
    mockUseUnifiedGraph.mockReset()
  })

  it("shows no entity-scope caption while the entity layer is off", () => {
    mockUseUnifiedGraph.mockReturnValue({ data: ONE_MEMORY, isLoading: false })
    render(<RealMemoryGraphPage />, { wrapper })
    expect(
      screen.queryByText(/shared across every project/),
    ).not.toBeInTheDocument()
  })

  it("shows the permanent scope caption once the entity layer is toggled on, with no truncation", async () => {
    const user = userEvent.setup()
    mockUseUnifiedGraph.mockReturnValue({
      data: { ...ONE_MEMORY, entities_truncated: false },
      isLoading: false,
    })
    render(<RealMemoryGraphPage />, { wrapper })

    await user.click(screen.getByRole("button", { name: "Entities" }))

    expect(
      screen.getByText(/shared across every project/),
    ).toBeInTheDocument()
    expect(screen.queryByText(/truncated/)).not.toBeInTheDocument()
  })

  it("also shows the truncation banner when entities_truncated is true", async () => {
    const user = userEvent.setup()
    mockUseUnifiedGraph.mockReturnValue({
      data: { ...ONE_MEMORY, entities_truncated: true },
      isLoading: false,
    })
    render(<RealMemoryGraphPage />, { wrapper })

    await user.click(screen.getByRole("button", { name: "Entities" }))

    expect(
      screen.getByText(/shared across every project/),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Entity overlay truncated/),
    ).toBeInTheDocument()
  })
})
