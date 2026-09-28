import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { NodeCountRow } from "../node-count-row"
import { useGraphPrefs, NODE_LIMIT_MAX, NODE_LIMIT_MIN } from "@/features/graph/lib/graph-prefs"

function renderRow(overrides: Partial<Parameters<typeof NodeCountRow>[0]> = {}) {
  const props = {
    nodeLimit: 200,
    onNodeLimitChange: vi.fn(),
    allNodes: false,
    onAllNodesChange: vi.fn(),
    shown: 200,
    total: 4580,
    truncated: true,
    ...overrides,
  }
  render(<NodeCountRow {...props} />)
  return props
}

describe("NodeCountRow", () => {
  it("steps the node limit", async () => {
    const user = userEvent.setup()
    const props = renderRow()
    await user.click(screen.getByRole("button", { name: "Increment" }))
    expect(props.onNodeLimitChange).toHaveBeenLastCalledWith(300)
  })

  it("toggles All and disables the number while it is on", async () => {
    const user = userEvent.setup()
    const props = renderRow()
    await user.click(screen.getByRole("checkbox", { name: "All nodes" }))
    expect(props.onAllNodesChange).toHaveBeenCalledWith(true)

    renderRow({ allNodes: true })
    expect(screen.getAllByRole("button", { name: "Increment" })[1]).toBeDisabled()
  })

  it("reports what is shown against the total", () => {
    renderRow()
    expect(screen.getByTestId("node-count-summary")).toHaveTextContent("Showing 200 of 4,580")
  })

  it("names the ceiling when All was capped", () => {
    renderRow({ allNodes: true, shown: 50000, total: 60000, truncated: true })
    expect(screen.getByTestId("node-count-summary")).toHaveTextContent("capped at 50,000")
  })

  it("hides the summary without a total", () => {
    renderRow({ total: undefined })
    expect(screen.queryByTestId("node-count-summary")).not.toBeInTheDocument()
  })
})

describe("graph prefs: node budget", () => {
  beforeEach(() => useGraphPrefs.setState({ nodeLimit: 200, allNodes: false }))

  it("clamps and rounds the node limit", () => {
    useGraphPrefs.getState().setNodeLimit(12.6)
    expect(useGraphPrefs.getState().nodeLimit).toBe(NODE_LIMIT_MIN)
    useGraphPrefs.getState().setNodeLimit(10_000_000)
    expect(useGraphPrefs.getState().nodeLimit).toBe(NODE_LIMIT_MAX)
    useGraphPrefs.getState().setNodeLimit(1234.4)
    expect(useGraphPrefs.getState().nodeLimit).toBe(1234)
    useGraphPrefs.getState().setNodeLimit(Number.NaN)
    expect(useGraphPrefs.getState().nodeLimit).toBe(1234)
  })

  it("stores All", () => {
    useGraphPrefs.getState().setAllNodes(true)
    expect(useGraphPrefs.getState().allNodes).toBe(true)
  })

  it("persists the budget under the graph prefs key", () => {
    useGraphPrefs.getState().setNodeLimit(750)
    useGraphPrefs.getState().setAllNodes(true)
    const stored = JSON.parse(localStorage.getItem("darkmem-graph-prefs") ?? "{}")
    expect(stored.state).toMatchObject({ nodeLimit: 750, allNodes: true })
  })
})
