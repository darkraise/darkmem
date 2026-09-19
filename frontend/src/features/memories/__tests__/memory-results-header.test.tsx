import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { useDetailLevel } from "@/components/darkmem"
import { MemoryResultsHeader } from "../components/memory-results-header"

describe("MemoryResultsHeader", () => {
  it("names the scope and the count in both modes", () => {
    useDetailLevel.setState({ level: "simple" })
    render(<MemoryResultsHeader scopeLabel="darkmem" shown={3} total={10} />)
    expect(screen.getByText("Results — project: darkmem")).toBeInTheDocument()
    expect(screen.getByText("3 of 10 shown")).toBeInTheDocument()
    expect(screen.queryByText("populated")).toBeNull()
  })

  it("says populated in Advanced and empty in both", () => {
    useDetailLevel.setState({ level: "advanced" })
    const { rerender } = render(
      <MemoryResultsHeader scopeLabel="all projects" shown={3} total={10} />,
    )
    expect(screen.getByText("populated")).toBeInTheDocument()
    useDetailLevel.setState({ level: "simple" })
    rerender(<MemoryResultsHeader scopeLabel="all projects" shown={0} total={0} />)
    expect(screen.getByText("empty")).toBeInTheDocument()
  })
})
