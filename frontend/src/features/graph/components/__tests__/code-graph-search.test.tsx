import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import {
  CodeGraphSearch,
  type CodeGraphSearchNode,
} from "../code-graph-search"

const NODES: CodeGraphSearchNode[] = [
  { id: "n1", label: "UserService", kind: "class" },
  { id: "n2", label: "login", kind: "method" },
  { id: "n3", label: "app/main.py", kind: "file" },
]

const NODE_COLORS: Record<string, string> = {
  class: "#aabbcc",
  method: "#112233",
  file: "#445566",
}

function renderPalette(overrides: Partial<Parameters<typeof CodeGraphSearch>[0]> = {}) {
  const onPick = vi.fn()
  const onOpenChange = vi.fn()
  render(
    <CodeGraphSearch
      open
      onOpenChange={onOpenChange}
      nodes={NODES}
      nodeColors={NODE_COLORS}
      onPick={onPick}
      {...overrides}
    />,
  )
  return { onPick, onOpenChange }
}

describe("CodeGraphSearch", () => {
  it("renders every node's label and kind", () => {
    renderPalette()
    expect(screen.getByText("UserService")).toBeInTheDocument()
    expect(screen.getByText("login")).toBeInTheDocument()
    expect(screen.getByText("app/main.py")).toBeInTheDocument()
    // The muted kind label appears alongside the matching node.
    expect(screen.getByText("class")).toBeInTheDocument()
  })

  it("calls onPick with the node id and closes when an item is selected", async () => {
    const user = userEvent.setup()
    const { onPick, onOpenChange } = renderPalette()

    await user.click(screen.getByText("login"))

    expect(onPick).toHaveBeenCalledTimes(1)
    expect(onPick).toHaveBeenCalledWith("n2")
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it("shows the empty message when no node matches the typed query", async () => {
    const user = userEvent.setup()
    renderPalette()

    await user.type(
      screen.getByPlaceholderText("Jump to a graph node…"),
      "zzz-no-such-node",
    )

    expect(screen.getByText("No matching nodes.")).toBeInTheDocument()
  })

  it("exposes an accessible name and description on the dialog", () => {
    renderPalette()
    const dialog = screen.getByRole("dialog")
    expect(dialog).toHaveAccessibleName("Jump to graph node")
    expect(dialog).toHaveAccessibleDescription(
      "Search code graph nodes by name, kind, or id and jump to one.",
    )
  })

  it("caps how many nodes mount at once for large graphs", () => {
    const many: CodeGraphSearchNode[] = Array.from(
      { length: 5000 },
      (_, i) => ({ id: `n${i}`, label: `sym_${i}`, kind: "function" }),
    )
    renderPalette({ nodes: many })
    // The palette must never mount the entire node set; it renders a bounded
    // slice so opening it on a huge graph does not fire thousands of updates.
    expect(screen.getAllByRole("option").length).toBeLessThanOrEqual(50)
  })

  it("narrows the bounded slice to nodes matching the typed query", async () => {
    const user = userEvent.setup()
    const many: CodeGraphSearchNode[] = Array.from(
      { length: 5000 },
      (_, i) => ({ id: `n${i}`, label: `sym_${i}`, kind: "function" }),
    )
    renderPalette({ nodes: many })

    await user.type(
      screen.getByPlaceholderText("Jump to a graph node…"),
      "sym_4242",
    )

    expect(screen.getByText("sym_4242")).toBeInTheDocument()
    expect(screen.getAllByRole("option").length).toBeLessThanOrEqual(50)
  })
})
