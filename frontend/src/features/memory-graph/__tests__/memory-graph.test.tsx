import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, it, expect } from "vitest"
import { AppPageHeader } from "@/components/app-chrome"
import { useProjectStore } from "@/stores/project-store"
import { MemoryGraphExplorer } from "../components/memory-graph-explorer"

describe("MemoryGraphExplorer", () => {
  beforeEach(() => {
    useProjectStore.setState({ activeProject: "darkmem", missingProject: null })
  })

  it("renders the project-scoped entity graph with topics", () => {
    render(<MemoryGraphExplorer />)
    expect(
      screen.getByRole("group", { name: /Entity graph for project darkmem/ }),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/12 entities · 14 relations · 3 topics/),
    ).toBeInTheDocument()
    expect(screen.getByText("Community navigator")).toBeInTheDocument()
    expect(screen.getByText("Retrieval & ranking")).toBeInTheDocument()
    // read-only honesty note: browsing does not feed ranking
    expect(
      screen.getByText(/browsing them here does not feed ranking/),
    ).toBeInTheDocument()
  })

  it("click-to-inspect shows the entity's relations, no verification rung", () => {
    render(<MemoryGraphExplorer />)
    fireEvent.click(
      screen.getByRole("button", { name: "postgres (database)" }),
    )
    expect(
      screen.getByText(/L1 carries no verification rung/),
    ).toBeInTheDocument()
    expect(screen.getByText(/relations \(2\)/)).toBeInTheDocument()
  })

  it("reads the header scope and offers no project select", () => {
    render(<MemoryGraphExplorer />)
    expect(screen.queryByRole("combobox", { name: "Project scope" })).toBeNull()
  })

  it("shows a hidden label while its node has focus", () => {
    // Every project at once, in the Community layout: the fixture overlaps
    // labels in that layout only (Force and Tree place all sixteen clear).
    useProjectStore.setState({ activeProject: null, missingProject: null })
    render(<MemoryGraphExplorer />)
    fireEvent.click(screen.getByRole("radio", { name: /Community/ }))
    const nodes = screen.getAllByRole("button").filter((b) => b.tagName.toLowerCase() === "g")
    const hidden = nodes.find((n) => n.querySelector("text") === null)
    expect(hidden, "the fixture places at least one overlapping label").toBeDefined()
    fireEvent.focus(hidden!)
    expect(hidden!.querySelector("text")).not.toBeNull()
    fireEvent.blur(hidden!)
    expect(hidden!.querySelector("text")).toBeNull()
  })

  it("is not an image around its node buttons", () => {
    render(<MemoryGraphExplorer />)
    expect(screen.queryByRole("img")).toBeNull()
  })

  it("shows a theme-coloured ring on the node that has keyboard focus", () => {
    render(<MemoryGraphExplorer />)
    const node = screen.getByRole("button", { name: "postgres (database)" })
    expect(node.getAttribute("class")).not.toMatch(/(^|\s)outline-none(\s|$)/)
    const ring = node.querySelector('[data-focus-ring]')!
    expect(ring.getAttribute("class")).toMatch(/stroke-ring/)
    expect(ring.getAttribute("class")).toMatch(/group-focus-visible:opacity-100/)
  })

  it("publishes the page chrome the real page does", () => {
    render(
      <>
        <MemoryGraphExplorer />
        <AppPageHeader />
      </>,
    )
    expect(screen.getByRole("heading", { name: "Memory Graph" })).toBeInTheDocument()
  })
})
