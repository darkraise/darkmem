import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within } from "@testing-library/react"
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

const NARROW_WIDTH = 300

/**
 * jsdom's ResizeObserver (stubbed as a no-op in setup.ts) never invokes its
 * callback, so `splitWidth` never leaves its initial 0 and the page always
 * falls back to `Number.POSITIVE_INFINITY` -- every other page-level test
 * therefore only ever exercises the non-floating split. Fire the callback
 * synchronously, narrower than `GRAPH_MIN_WIDTH + DETAIL_PANEL_MIN_WIDTH`, so
 * this file can reach the floating branch at all.
 */
class NarrowResizeObserver {
  constructor(private cb: ResizeObserverCallback) {}
  observe(target: Element) {
    this.cb(
      [
        {
          target,
          contentRect: { width: NARROW_WIDTH, height: 600 } as DOMRectReadOnly,
        } as ResizeObserverEntry,
      ],
      this as unknown as ResizeObserver,
    )
  }
  unobserve() {}
  disconnect() {}
}

describe("RealMemoryGraphPage: floating detail panel", () => {
  beforeEach(() => {
    mockUseUnifiedGraph.mockReset()
    mockUseUnifiedGraph.mockReturnValue({ data: ONE_MEMORY, isLoading: false })
    window.ResizeObserver =
      NarrowResizeObserver as unknown as typeof ResizeObserver
  })

  it("floats the panel over the canvas and keeps the close button reachable", async () => {
    const user = userEvent.setup()
    render(<RealMemoryGraphPage />, { wrapper })

    await user.click(
      screen.getByRole("button", { name: /show details panel/i }),
    )

    const panel = screen.getByTestId("graph-detail-panel")
    expect(panel).toHaveAttribute("data-floating", "true")

    // GraphSummary's own collapsible sections are buttons too, so scope to
    // the header's position rather than assuming the close button is the
    // only one -- it is the first button painted inside the panel, and
    // scoping to the panel at all proves it is reachable inside the
    // floating overlay rather than merely present somewhere on the page.
    // getAllByRole throws if the panel painted no buttons at all, so a
    // successful call here always has at least one element.
    const closeButton = within(panel).getAllByRole("button")[0]!
    await user.click(closeButton)

    expect(screen.queryByTestId("graph-detail-panel")).not.toBeInTheDocument()
  })

  it("hides the resize handle while floating", async () => {
    const user = userEvent.setup()
    render(<RealMemoryGraphPage />, { wrapper })

    await user.click(
      screen.getByRole("button", { name: /show details panel/i }),
    )

    expect(
      screen.queryByRole("separator", { name: /resize the detail panel/i }),
    ).not.toBeInTheDocument()
  })
})
