import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { MemoryResultsHeader } from "../components/memory-results-header"

describe("MemoryResultsHeader", () => {
  it("shows the count", () => {
    render(<MemoryResultsHeader shown={3} total={10} />)
    expect(screen.getByText("3 of 10 shown")).toBeInTheDocument()
    expect(screen.queryByText("populated")).toBeNull()
  })
})
