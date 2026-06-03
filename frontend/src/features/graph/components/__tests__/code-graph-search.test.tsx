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
})
