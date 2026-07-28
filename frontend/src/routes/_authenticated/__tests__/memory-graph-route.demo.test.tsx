import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/features/memory-graph/components/memory-graph-explorer", () => ({
  MemoryGraphExplorer: () => <div>demo-memory-graph-explorer</div>,
}))
vi.mock("@/features/memory-graph/components/real-memory-graph-page", () => ({
  RealMemoryGraphPage: () => <div>real-memory-graph-page</div>,
}))

import { Route } from "../memory-graph"

// T1.60 Step 1: /memory-graph used to serve MemoryGraphExplorer
// unconditionally, with no DEMO gate at all, while the real implementation
// sat unreachable at /unified-graph. This pins the DEMO=true branch so a
// regression toward "always demo" or "always real" is caught alongside its
// DEMO=false sibling in memory-graph-route.real.test.tsx.
describe("/memory-graph route (DEMO on)", () => {
  it("renders MemoryGraphExplorer, not the real page", () => {
    const Component = Route.options.component!
    render(<Component />)
    expect(screen.getByText("demo-memory-graph-explorer")).toBeInTheDocument()
    expect(screen.queryByText("real-memory-graph-page")).not.toBeInTheDocument()
  })
})
