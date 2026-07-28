import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/features/memory-graph/components/memory-graph-explorer", () => ({
  MemoryGraphExplorer: () => <div>demo-memory-graph-explorer</div>,
}))
vi.mock("@/features/memory-graph/components/real-memory-graph-page", () => ({
  RealMemoryGraphPage: () => <div>real-memory-graph-page</div>,
}))

import { Route } from "../memory-graph"

// T1.60 Step 1's confirmed nav bug: the sidebar already links to
// /memory-graph, so this DEMO=false branch is what a real user's click
// actually reaches. Mutation proof: hard-coding the route component to
// always render MemoryGraphExplorer (ignoring DEMO) makes this test fail
// while memory-graph-route.demo.test.tsx keeps passing — proving the
// assertion is live, not vacuous.
describe("/memory-graph route (DEMO off)", () => {
  it("renders the real Memory Graph page, not the demo explorer", () => {
    const Component = Route.options.component!
    render(<Component />)
    expect(screen.getByText("real-memory-graph-page")).toBeInTheDocument()
    expect(screen.queryByText("demo-memory-graph-explorer")).not.toBeInTheDocument()
  })
})
