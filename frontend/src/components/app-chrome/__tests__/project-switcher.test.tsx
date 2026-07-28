import { describe, it, expect, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ProjectSwitcher } from "../project-switcher"
import { useProjectStore, DEFAULT_PROJECT } from "@/stores/project-store"
import { useContextStore } from "@/stores/context-store"

describe("ProjectSwitcher", () => {
  beforeEach(() => {
    useProjectStore.setState({
      activeProject: DEFAULT_PROJECT,
      knownProjects: [DEFAULT_PROJECT],
    })
    useContextStore.setState({ declared: null })
  })

  it("shows the active project, always visible without opening anything", () => {
    useProjectStore.getState().setProject("acme")
    render(<ProjectSwitcher />)
    expect(screen.getByRole("button", { name: /project scope/i })).toHaveTextContent(
      "project: acme",
    )
  })

  it("switching projects updates the store", async () => {
    const user = userEvent.setup()
    render(<ProjectSwitcher />)

    await user.click(screen.getByRole("button", { name: /project scope/i }))
    const input = await screen.findByLabelText(/new project name/i)
    await user.type(input, "acme")
    await user.click(screen.getByRole("button", { name: /^switch$/i }))

    expect(useProjectStore.getState().activeProject).toBe("acme")
  })

  it("offers known (recently used) projects to switch back to", async () => {
    useProjectStore.getState().setProject("acme")
    useProjectStore.getState().setProject("beta")
    const user = userEvent.setup()
    render(<ProjectSwitcher />)

    await user.click(screen.getByRole("button", { name: /project scope/i }))
    const acmeChip = await screen.findByRole("button", { name: "acme" })
    await user.click(acmeChip)

    expect(useProjectStore.getState().activeProject).toBe("acme")
  })

  // Ruling 3: switching the project is a scope change and must never
  // declare a context as a side effect.
  it("never writes to contextStore when switching projects", async () => {
    const user = userEvent.setup()
    render(<ProjectSwitcher />)

    await user.click(screen.getByRole("button", { name: /project scope/i }))
    const input = await screen.findByLabelText(/new project name/i)
    await user.type(input, "production")
    await user.click(screen.getByRole("button", { name: /^switch$/i }))

    expect(useProjectStore.getState().activeProject).toBe("production")
    expect(useContextStore.getState().declared).toBeNull()
  })
})
