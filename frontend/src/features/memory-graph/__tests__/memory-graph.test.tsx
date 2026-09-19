import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, it, expect } from "vitest"
import { useProjectStore } from "@/stores/project-store"
import { MemoryGraphExplorer } from "../components/memory-graph-explorer"

describe("MemoryGraphExplorer", () => {
  beforeEach(() => {
    useProjectStore.setState({ activeProject: "darkmem", missingProject: null })
  })

  it("renders the project-scoped entity graph with topics", () => {
    render(<MemoryGraphExplorer />)
    expect(
      screen.getByRole("img", { name: /Entity graph for project darkmem/ }),
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
})
