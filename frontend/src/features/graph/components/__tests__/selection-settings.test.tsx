import { describe, it, expect, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { SelectionSettings } from "../selection-settings"
import {
  useGraphPrefs,
  DEFAULT_SELECTION_COLOR,
  DEFAULT_DIM,
} from "@/features/graph/lib/graph-prefs"

describe("SelectionSettings", () => {
  beforeEach(() => {
    localStorage.clear()
    useGraphPrefs.setState({
      selectionColor: DEFAULT_SELECTION_COLOR,
      dimUnrelated: DEFAULT_DIM,
    })
  })

  it("offers both halo colours", () => {
    render(<SelectionSettings />)
    expect(screen.getByRole("radio", { name: /accent/i })).toBeInTheDocument()
    expect(screen.getByRole("radio", { name: /inverted/i })).toBeInTheDocument()
  })

  it("shows which colour is active", () => {
    useGraphPrefs.setState({ selectionColor: "inverted" })
    render(<SelectionSettings />)
    expect(screen.getByRole("radio", { name: /inverted/i })).toBeChecked()
  })

  it("writes the chosen colour to the store", async () => {
    const user = userEvent.setup()
    render(<SelectionSettings />)

    await user.click(screen.getByRole("radio", { name: /inverted/i }))

    expect(useGraphPrefs.getState().selectionColor).toBe("inverted")
  })

  it("reports the dim level in the units the reader thinks in", () => {
    useGraphPrefs.setState({ dimUnrelated: 25 })
    render(<SelectionSettings />)
    expect(screen.getByText("25%")).toBeInTheDocument()
  })

  // Both surfaces render this one component against one store, so the
  // Appearance section and the graph popover cannot drift apart.
  it("reflects a change made by another instance of itself", () => {
    const first = render(<SelectionSettings />)
    useGraphPrefs.getState().setSelectionColor("inverted")
    first.unmount()

    render(<SelectionSettings />)
    expect(screen.getByRole("radio", { name: /inverted/i })).toBeChecked()
  })
})

// The popover is narrow and asks for the small segments; Settings >
// Appearance has the room for full-size ones. Both render the same component
// over the same store, so the size is the only thing that may differ.
describe("SelectionSettings row size", () => {
  const itemClass = (el: HTMLElement) =>
    el.querySelector(".dr-segment-group-item")!.className

  it("uses compact segments inside the graph popover", () => {
    const { container } = render(<SelectionSettings compact />)
    expect(itemClass(container)).toContain("px-2")
    expect(itemClass(container)).toContain("text-xs")
  })

  it("leaves them full size on the settings page", () => {
    const { container } = render(<SelectionSettings />)
    expect(itemClass(container)).not.toContain("px-2")
    expect(itemClass(container)).not.toContain("text-xs")
  })
})
