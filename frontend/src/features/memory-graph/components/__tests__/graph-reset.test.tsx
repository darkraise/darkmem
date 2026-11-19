import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import type { UnifiedGraphData } from "@/hooks/api"
import { DEFAULT_COLOR_MODE, type ColorMode } from "@/features/graph/lib/graph-colors"
import { DEFAULT_SIZE_MODE, type SizeMode } from "@/features/graph/lib/graph-utils"
import { DEFAULT_HULL_MODE, type HullMode } from "@/features/graph/lib/graph-geometry"

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

async function openGraphSettings(user: ReturnType<typeof userEvent.setup>) {
  await user.click(
    screen.getByRole("button", { name: /toggle graph settings/i }),
  )
}

const COLOR_LABELS: Record<ColorMode, string> = {
  type: "Type",
  cluster: "Cluster",
  tag: "Tag",
}
const SIZE_LABELS: Record<SizeMode, string> = {
  connections: "Links",
  importance: "Weight",
  uniform: "Equal",
}
const REGIONS_ON: Record<HullMode, string> = { none: "false", cluster: "true" }

// "Reset graph view" must land the encodings on the same defaults the page
// boots into (features/graph/hooks/__tests__/graph-defaults.test.ts pins
// those constants and the hook's initial state) -- not on a second,
// independently hardcoded set that can drift from them.
describe("RealMemoryGraphPage: reset graph view", () => {
  beforeEach(() => {
    mockUseUnifiedGraph.mockReset()
    mockUseUnifiedGraph.mockReturnValue({ data: ONE_MEMORY, isLoading: false })
  })

  it("returns colour, size and region encodings to the page's own defaults", async () => {
    const user = userEvent.setup()
    render(<RealMemoryGraphPage />, { wrapper })

    await openGraphSettings(user)

    const colourGroup = screen.getByRole("radiogroup", { name: "Colour" })
    const sizeGroup = screen.getByRole("radiogroup", { name: "Node size" })
    const regions = screen.getByRole("switch", { name: "Cluster regions" })

    // Move every encoding away from the page's own defaults first, so a
    // reset that merely leaves the current value untouched cannot pass.
    await user.click(within(colourGroup).getByRole("radio", { name: "Type" }))
    await user.click(within(sizeGroup).getByRole("radio", { name: "Links" }))
    await user.click(regions)

    expect(
      within(colourGroup).getByRole("radio", { name: "Type" }),
    ).toHaveAttribute("aria-checked", "true")
    expect(
      within(sizeGroup).getByRole("radio", { name: "Links" }),
    ).toHaveAttribute("aria-checked", "true")
    expect(regions).toHaveAttribute("aria-checked", "true")

    await user.click(
      screen.getByRole("button", { name: /reset graph view/i }),
    )

    // The reset button sits outside the popover; reopen it if the click
    // dismissed it, and reacquire the group handles either way.
    if (!screen.queryByRole("radiogroup", { name: "Colour" })) {
      await openGraphSettings(user)
    }
    const colourGroupAfter = screen.getByRole("radiogroup", { name: "Colour" })
    const sizeGroupAfter = screen.getByRole("radiogroup", { name: "Node size" })
    const regionsAfter = screen.getByRole("switch", { name: "Cluster regions" })

    expect(
      within(colourGroupAfter).getByRole("radio", {
        name: COLOR_LABELS[DEFAULT_COLOR_MODE],
      }),
    ).toHaveAttribute("aria-checked", "true")
    expect(
      within(sizeGroupAfter).getByRole("radio", {
        name: SIZE_LABELS[DEFAULT_SIZE_MODE],
      }),
    ).toHaveAttribute("aria-checked", "true")
    expect(regionsAfter).toHaveAttribute(
      "aria-checked",
      REGIONS_ON[DEFAULT_HULL_MODE],
    )
  })
})
