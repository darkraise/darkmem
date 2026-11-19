import { describe, it, expect, vi, beforeEach } from "vitest"
import { act, render, screen } from "@testing-library/react"
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
  useUnifiedGraph: (...args: unknown[]) => mockUseUnifiedGraph(...args),
}))

import { RealMemoryGraphPage } from "../real-memory-graph-page"
import { useGraphPrefs } from "@/features/graph/lib/graph-prefs"

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
/** The entity layer moved off the canvas and into the graph settings panel,
 *  so reaching it now means opening that panel first. */
async function enableEntityLayer(user: ReturnType<typeof userEvent.setup>) {
  await user.click(
    screen.getByRole("button", { name: /toggle graph settings/i }),
  )
  await user.click(await screen.findByRole("switch", { name: /entity layer/i }))
}

describe("RealMemoryGraphPage: entity-overlay truncation banner", () => {
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

  it("also shows the truncation banner when entities_truncated is true", async () => {
    const user = userEvent.setup()
    mockUseUnifiedGraph.mockReturnValue({
      data: { ...ONE_MEMORY, entities_truncated: true },
      isLoading: false,
    })
    render(<RealMemoryGraphPage />, { wrapper })

    await enableEntityLayer(user)

    // The standing scope caption was removed on the owner's instruction; the
    // truncation banner is a different signal and stays, because nothing else
    // on the page reports that the view is missing data.
    expect(
      screen.queryByText(/shared across every project/),
    ).not.toBeInTheDocument()
    expect(
      screen.getByText(/Entity overlay truncated/),
    ).toBeInTheDocument()
  })
})

describe("RealMemoryGraphPage: node budget", () => {
  beforeEach(() => {
    mockUseUnifiedGraph.mockReset()
    useGraphPrefs.setState({ nodeLimit: 200, allNodes: false })
  })

  it("asks for the stored node limit", () => {
    mockUseUnifiedGraph.mockReturnValue({ data: ONE_MEMORY, isLoading: false })
    useGraphPrefs.setState({ nodeLimit: 750, allNodes: false })
    render(<RealMemoryGraphPage />, { wrapper })
    const calls = mockUseUnifiedGraph.mock.calls
    expect(calls[calls.length - 1]!.slice(3)).toEqual([750, false])
  })

  it("asks for every memory when All is stored", () => {
    mockUseUnifiedGraph.mockReturnValue({ data: ONE_MEMORY, isLoading: false })
    useGraphPrefs.setState({ allNodes: true })
    render(<RealMemoryGraphPage />, { wrapper })
    const calls = mockUseUnifiedGraph.mock.calls
    expect(calls[calls.length - 1]!.slice(3)).toEqual([200, true])
  })

  it("waits for the node limit to settle before asking for it", () => {
    vi.useFakeTimers()
    try {
      mockUseUnifiedGraph.mockReturnValue({ data: ONE_MEMORY, isLoading: false })
      render(<RealMemoryGraphPage />, { wrapper })
      const lastLimit = () => {
        const calls = mockUseUnifiedGraph.mock.calls
        return calls[calls.length - 1]![3]
      }

      act(() => useGraphPrefs.setState({ nodeLimit: 900 }))
      act(() => vi.advanceTimersByTime(499))
      expect(lastLimit()).toBe(200)

      act(() => vi.advanceTimersByTime(1))
      expect(lastLimit()).toBe(900)
    } finally {
      vi.useRealTimers()
    }
  })

  it("shows how many memories are plotted in the settings panel", async () => {
    const user = userEvent.setup()
    mockUseUnifiedGraph.mockReturnValue({
      data: { ...ONE_MEMORY, total_memories: 4580, memories_truncated: true },
      isLoading: false,
    })
    render(<RealMemoryGraphPage />, { wrapper })
    await user.click(screen.getByRole("button", { name: /toggle graph settings/i }))
    expect(await screen.findByTestId("node-count-summary")).toHaveTextContent("Showing 1 of 4,580")
  })
})

describe("RealMemoryGraphPage: filter panel", () => {
  beforeEach(() => {
    mockUseUnifiedGraph.mockReset()
    mockUseUnifiedGraph.mockReturnValue({ data: ONE_MEMORY, isLoading: false })
  })

  it("keeps the collapsed panel's controls out of the tab order until Filters opens it", async () => {
    const user = userEvent.setup()
    render(<RealMemoryGraphPage />, { wrapper })
    const contentFilter = screen.getByPlaceholderText(/filter by content/i)
    expect(contentFilter.closest("[inert]")).not.toBeNull()

    await user.click(screen.getByRole("button", { name: "Filters" }))
    expect(contentFilter.closest("[inert]")).toBeNull()
  })
})
