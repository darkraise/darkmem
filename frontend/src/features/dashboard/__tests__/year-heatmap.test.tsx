import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"

vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  useNavigate: () => vi.fn(),
}))

import { YearHeatmap } from "../year-heatmap"

describe("YearHeatmap", () => {
  it("lays the weeks out as fluid grid columns that fill the card", () => {
    render(
      <YearHeatmap
        days={[{ date: "2026-07-24", count: 3, types: [], verified: 0, injects: 0 }]}
      />,
    )
    const grid = screen.getByTestId("heatmap-grid")
    expect(grid.style.gridTemplateColumns).toMatch(
      /^auto repeat\(\d+, minmax\(var\(--cell-min\), 1fr\)\)$/,
    )
    // A 10px floor only below `sm`: above it the floor overflowed the card.
    expect(grid).toHaveClass("[--cell-min:10px]", "sm:[--cell-min:0px]")
    const cell = screen.getByRole("button", { name: /3 memories/ })
    expect(cell).toHaveClass("aspect-square", "w-full")
  })
})
