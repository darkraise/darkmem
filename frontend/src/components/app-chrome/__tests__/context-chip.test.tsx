import { describe, it, expect, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ContextChip } from "../context-chip"
import { useContextStore } from "@/stores/context-store"
import { useProjectStore, DEFAULT_PROJECT } from "@/stores/project-store"

describe("ContextChip", () => {
  beforeEach(() => {
    useContextStore.setState({ declared: null })
    useProjectStore.setState({
      activeProject: DEFAULT_PROJECT,
    })
  })

  // Ruling 4: an undeclared context renders as undeclared, literally —
  // never a default axis value standing in for "nothing chosen".
  it("renders 'not declared' when nothing is declared, with no default value shown", () => {
    render(<ContextChip />)
    const chip = screen.getByRole("button", { name: /session context/i })
    expect(chip).toHaveTextContent("context: not declared")
    expect(chip.textContent).not.toMatch(/env=|situation=|version=/)
  })

  it("declaring an axis makes it visible on the chip itself", async () => {
    const user = userEvent.setup()
    render(<ContextChip />)

    await user.click(screen.getByRole("button", { name: /session context/i }))
    const envInput = await screen.findByLabelText("env", { selector: "input" })
    await user.type(envInput, "prod")
    await user.click(screen.getByRole("button", { name: /^declare$/i }))

    expect(screen.getByRole("button", { name: /session context/i })).toHaveTextContent(
      "context: env=prod",
    )
    expect(useContextStore.getState().declared).toEqual({ axes: { env: "prod" } })
  })

  it("clearing returns the chip to 'not declared'", async () => {
    useContextStore.getState().declareContext({ env: "prod" })
    const user = userEvent.setup()
    render(<ContextChip />)

    await user.click(screen.getByRole("button", { name: /session context/i }))
    await user.click(await screen.findByRole("button", { name: /^clear$/i }))

    expect(screen.getByRole("button", { name: /session context/i })).toHaveTextContent(
      "context: not declared",
    )
    expect(useContextStore.getState().declared).toBeNull()
  })

  // Declaring every field blank must not read as "declared nothing" —
  // it must stay literally undeclared (Ruling 4 again, from the UI side).
  it("declaring with every field left blank stays undeclared", async () => {
    const user = userEvent.setup()
    render(<ContextChip />)

    await user.click(screen.getByRole("button", { name: /session context/i }))
    await user.click(await screen.findByRole("button", { name: /^declare$/i }))

    expect(useContextStore.getState().declared).toBeNull()
    expect(screen.getByRole("button", { name: /session context/i })).toHaveTextContent(
      "context: not declared",
    )
  })

  // Ruling 3: declaring a context is a retrieval hint and must never
  // change the isolation scope as a side effect.
  it("never writes to projectStore when declaring context", async () => {
    const user = userEvent.setup()
    render(<ContextChip />)

    await user.click(screen.getByRole("button", { name: /session context/i }))
    const envInput = await screen.findByLabelText("env", { selector: "input" })
    await user.type(envInput, "production")
    await user.click(screen.getByRole("button", { name: /^declare$/i }))

    expect(useProjectStore.getState().activeProject).toBe(DEFAULT_PROJECT)
  })

  it("the two chrome controls carry distinct accessible labels", () => {
    render(<ContextChip />)
    expect(screen.queryByRole("button", { name: /project scope/i })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: /session context/i })).toBeInTheDocument()
  })
})
