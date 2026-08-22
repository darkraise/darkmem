import { describe, it, expect, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { SelectionSettings } from "../selection-settings"
import {
  useGraphPrefs,
  DEFAULT_TREATMENT,
  DEFAULT_DIM,
} from "@/features/graph/lib/graph-prefs"

describe("SelectionSettings", () => {
  beforeEach(() => {
    localStorage.clear()
    useGraphPrefs.setState({
      selectionTreatment: DEFAULT_TREATMENT,
      dimUnrelated: DEFAULT_DIM,
    })
  })

  it("offers all three treatments", () => {
    render(<SelectionSettings />)
    expect(screen.getByRole("radio", { name: /halo/i })).toBeInTheDocument()
    expect(screen.getByRole("radio", { name: /keyline/i })).toBeInTheDocument()
    expect(screen.getByRole("radio", { name: /inverted/i })).toBeInTheDocument()
  })

  it("shows which treatment is active", () => {
    useGraphPrefs.setState({ selectionTreatment: "invert" })
    render(<SelectionSettings />)
    expect(screen.getByRole("radio", { name: /inverted/i })).toBeChecked()
  })

  it("writes the chosen treatment to the store", async () => {
    const user = userEvent.setup()
    render(<SelectionSettings />)

    await user.click(screen.getByRole("radio", { name: /keyline/i }))

    expect(useGraphPrefs.getState().selectionTreatment).toBe("keyline")
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
    useGraphPrefs.getState().setSelectionTreatment("invert")
    first.unmount()

    render(<SelectionSettings />)
    expect(screen.getByRole("radio", { name: /inverted/i })).toBeChecked()
  })
})
