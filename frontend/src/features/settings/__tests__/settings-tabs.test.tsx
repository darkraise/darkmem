import { fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { useDemoStore } from "@/demo/store"
import { SecurityTab } from "../components/security-tab"
import { MaintenanceTab } from "../components/maintenance-tab"
import { DistributionTab } from "../components/distribution-tab"
import { ConfirmGate } from "../components/confirm-gate"

// MaintenanceTab links into /activity; stub the router Link.
vi.mock("@tanstack/react-router", () => ({
  Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
}))

afterEach(() => {
  useDemoStore.getState().resetSettings()
})

// FlagsTab's own tests live in settings-flags.test.tsx / .real.test.tsx.

describe("SecurityTab — dormant ApiKey honesty", () => {
  it("renders the Phase-4 card with every control disabled", () => {
    render(<SecurityTab />)
    expect(screen.getByText(/Phase-4 · designed, not wired/)).toBeInTheDocument()
    expect(screen.getByLabelText("Key label")).toBeDisabled()
    expect(
      screen.getByRole("button", { name: /Create key — unavailable/ }),
    ).toBeDisabled()
    expect(
      screen.getByText(/ratify — never a scope, human cookie session only/),
    ).toBeInTheDocument()
  })

  it("renders the three LAN doors and the TOFU claim", () => {
    render(<SecurityTab />)
    expect(screen.getByText("/mcp")).toBeInTheDocument()
    expect(screen.getByText("/api/v1 + /ws")).toBeInTheDocument()
    expect(screen.getByText("/setup")).toBeInTheDocument()
    expect(screen.getAllByText("claimed").length).toBeGreaterThan(0)
  })
})

describe("MaintenanceTab — confirmation gates", () => {
  it("never runs a destructive op from a bare click", () => {
    render(<MaintenanceTab />)
    fireEvent.click(screen.getByRole("button", { name: /Run sweep now/ }))
    // Armed, not run: the count is untouched until Confirm.
    expect(
      useDemoStore.getState().maintenance.cleanup.expired,
    ).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole("button", { name: /Confirm — delete now/ }))
    expect(useDemoStore.getState().maintenance.cleanup.expired).toBe(0)
  })

  it("marks endpoint-less DB ops as illustrative, not shipped", () => {
    render(<MaintenanceTab />)
    expect(screen.getAllByText("no dedicated endpoint yet")).toHaveLength(2)
    expect(screen.getByText(/use Repositories → Reindex/)).toBeInTheDocument()
  })
})

describe("DistributionTab", () => {
  it("labels injected context with layer + verification, unrelabelled", () => {
    render(<DistributionTab />)
    expect(screen.getByText(/Labels survive injection/)).toBeInTheDocument()
    expect(screen.getAllByText("corroborated").length).toBeGreaterThan(0)
    expect(screen.getAllByText("superseded").length).toBeGreaterThan(0)
  })

  it("curbing a client appends an inject_curbed log row", () => {
    render(<DistributionTab />)
    const before = useDemoStore.getState().distribution.log.length
    fireEvent.click(screen.getByLabelText("Cursor push"))
    expect(useDemoStore.getState().distribution.log.length).toBe(before + 1)
    expect(
      useDemoStore.getState().distribution.clients.find(
        (c) => c.id === "cursor",
      )?.status,
    ).toBe("curbed")
  })

  it("shows the not-connected client with its onboarding CTA inline", () => {
    render(<DistributionTab />)
    expect(screen.getByText("not connected")).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: /darkmem connect cline/ }),
    ).toBeInTheDocument()
  })
})

describe("ConfirmGate", () => {
  it("arms on trigger, cancels without firing, confirms once", () => {
    const onConfirm = vi.fn()
    render(
      <ConfirmGate
        trigger={<button type="button">Do it</button>}
        headline="Sure?"
        desc="d"
        confirmLabel="Confirm"
        tone="danger"
        onConfirm={onConfirm}
      />,
    )
    fireEvent.click(screen.getByText("Do it"))
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }))
    expect(onConfirm).not.toHaveBeenCalled()
    fireEvent.click(screen.getByText("Do it"))
    fireEvent.click(screen.getByRole("button", { name: "Confirm" }))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })
})
