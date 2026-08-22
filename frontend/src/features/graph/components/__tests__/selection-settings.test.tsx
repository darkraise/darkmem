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
