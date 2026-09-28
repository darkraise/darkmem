import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import type { UnifiedGraphData } from "@/hooks/api"
import { LARGE_3D_NOTICE_NODES } from "@/features/graph/lib/graph-scale"

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

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function graphOf(count: number): UnifiedGraphData {
  return {
    memories: Array.from({ length: count }, (_, i) => ({
      id: `m${i}`,
      content: `memory ${i}`,
      source: "api",
      tags: [],
      memory_type: null,
      importance: 0.5,
      cluster: 0,
    })),
    clusters: {},
    cluster_names: {},
    similarity_edges: [],
  }
}

async function switchTo3D(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /toggle graph settings/i }))
  const mode = await screen.findByRole("radiogroup", { name: "Render mode" })
  await user.click(within(mode).getByRole("radio", { name: "3D" }))
}

describe("RealMemoryGraphPage: large 3D notice", () => {
  beforeEach(() => mockUseUnifiedGraph.mockReset())

  it("recommends 2D for a large graph in 3D and can be dismissed", async () => {
    const user = userEvent.setup()
    mockUseUnifiedGraph.mockReturnValue({ data: graphOf(LARGE_3D_NOTICE_NODES), isLoading: false })
    render(<RealMemoryGraphPage />, { wrapper })
    await switchTo3D(user)

    expect(await screen.findByText(/3D is best-effort here/)).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Dismiss" }))
    expect(screen.queryByText(/3D is best-effort here/)).not.toBeInTheDocument()
  })

  it("stays quiet for a small graph", async () => {
    const user = userEvent.setup()
    mockUseUnifiedGraph.mockReturnValue({ data: graphOf(10), isLoading: false })
    render(<RealMemoryGraphPage />, { wrapper })
    await switchTo3D(user)
    expect(screen.queryByText(/3D is best-effort here/)).not.toBeInTheDocument()
  })
})
