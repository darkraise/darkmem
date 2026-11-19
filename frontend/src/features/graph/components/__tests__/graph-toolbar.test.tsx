import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { GraphToolbar } from "../graph-toolbar"

const base = {
  viewMode: "2d" as const,
  onViewModeChange: vi.fn(),
  colorMode: "cluster" as const,
  onColorModeChange: vi.fn(),
  hullMode: "none" as const,
  onHullModeChange: vi.fn(),
  entityLayer: false,
  onEntityLayerChange: vi.fn(),
  sharedEntitiesOnly: false,
  onSharedEntitiesOnlyChange: vi.fn(),
  sizeMode: "importance" as const,
  onSizeModeChange: vi.fn(),
  similarityThreshold: 0.5,
  onSimilarityChange: vi.fn(),
  minClusterSize: 3,
  onMinClusterSizeChange: vi.fn(),
  spacing: 50,
  onSpacingChange: vi.fn(),
  onReset: vi.fn(),
}

async function openSettings() {
  await userEvent.click(screen.getByRole("button", { name: "Toggle graph settings" }))
}

describe("GraphToolbar layout rows", () => {
  it("offers no Tightness or Spacing control in 2D", async () => {
    render(<GraphToolbar {...base} viewMode="2d" />)
    await openSettings()
    expect(screen.getByText("Edges")).toBeInTheDocument()
    expect(screen.queryByText("Tightness")).toBeNull()
    expect(screen.queryByText("Spacing")).toBeNull()
  })

  it("keeps Spacing, and only Spacing, in 3D", async () => {
    render(<GraphToolbar {...base} viewMode="3d" />)
    await openSettings()
    expect(screen.getByText("Spacing")).toBeInTheDocument()
    expect(screen.queryByText("Tightness")).toBeNull()
  })
})

describe("GraphToolbar settings panel focus", () => {
  it("Tab past the panel's last control moves to the next toolbar button and leaves the panel open", async () => {
    const user = userEvent.setup()
    render(<GraphToolbar {...base} />)
    await user.click(screen.getByRole("button", { name: "Toggle graph settings" }))
    screen.getByRole("slider", { name: "Dim unrelated nodes, percent" }).focus()
    await user.tab()
    expect(screen.getByRole("button", { name: "Reset graph view" })).toHaveFocus()
    expect(screen.getByRole("slider", { name: "Dim unrelated nodes, percent" })).toBeInTheDocument()
  })

  it("Shift+Tab from the panel's first control returns to the settings trigger", async () => {
    const user = userEvent.setup()
    render(<GraphToolbar {...base} />)
    const trigger = screen.getByRole("button", { name: "Toggle graph settings" })
    await user.click(trigger)
    screen.getByRole("radio", { name: "2D" }).focus()
    await user.tab({ shift: true })
    expect(trigger).toHaveFocus()
  })

  it("Tab between the panel's own controls stays in the panel", async () => {
    const user = userEvent.setup()
    render(<GraphToolbar {...base} />)
    const trigger = screen.getByRole("button", { name: "Toggle graph settings" })
    await user.click(trigger)
    screen.getByRole("radio", { name: "2D" }).focus()
    await user.tab()
    expect(screen.getByRole("button", { name: "Reset graph view" })).not.toHaveFocus()
    expect(trigger).not.toHaveFocus()
    expect(document.body).not.toHaveFocus()
  })
})
