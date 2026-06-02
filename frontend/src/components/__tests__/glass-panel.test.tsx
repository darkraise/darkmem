import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { GlassPanel } from "../glass-panel"

describe("GlassPanel", () => {
  it("renders children and forwards className", () => {
    render(
      <GlassPanel className="max-w-sm" data-testid="panel">
        <span>hello</span>
      </GlassPanel>,
    )
    expect(screen.getByText("hello")).toBeInTheDocument()
    const panel = screen.getByTestId("panel")
    expect(panel.className).toContain("max-w-sm")
    expect(panel.className).toContain("backdrop-blur-[16px]")
  })
})
