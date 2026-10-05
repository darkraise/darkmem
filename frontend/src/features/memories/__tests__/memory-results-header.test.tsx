import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { MemoryResultsHeader } from "../components/memory-results-header"

describe("MemoryResultsHeader", () => {
  it("shows the count", () => {
    render(<MemoryResultsHeader shown={3} total={10} />)
    expect(screen.getByText("3 of 10 shown")).toBeInTheDocument()
    expect(screen.queryByText("populated")).toBeNull()
  })

  it("is a slim caption without controls and a band with them", () => {
    const { rerender } = render(<MemoryResultsHeader shown={3} total={10} />)
    expect(screen.getByTestId("memory-results-header")).not.toHaveClass(
      "border-b",
    )
    rerender(
      <MemoryResultsHeader shown={3} total={10}>
        <button type="button">Active</button>
      </MemoryResultsHeader>,
    )
    expect(screen.getByTestId("memory-results-header")).toHaveClass("border-b")
    expect(screen.getByRole("button", { name: "Active" })).toBeInTheDocument()
  })
})
