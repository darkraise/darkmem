import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { useDemoStore } from "@/demo/store"
import { SecurityTab } from "../components/security-tab"
import { MaintenanceTab } from "../components/maintenance-tab"
import { DistributionTab } from "../components/distribution-tab"
import { ConfirmGate } from "../components/confirm-gate"

// This exercises the fixture-backed path deliberately (pins SecurityTab's
// and MaintenanceTab's demo rendering), so it is frozen at DEMO: true rather
// than relying on the real default (T1.58) — see settings-security.real
// .test.tsx / settings-maintenance.real.test.tsx for the real-mode bindings.
vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))

// MaintenanceTab links into /activity; stub the router Link.
vi.mock("@tanstack/react-router", () => ({
  Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
}))

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

afterEach(() => {
  useDemoStore.getState().resetSettings()
})

// FlagsTab's own tests live in settings-flags.test.tsx / .real.test.tsx.

describe("SecurityTab", () => {
  it("renders the MCP host allowlist", () => {
    render(<SecurityTab />, { wrapper })
    expect(screen.getByText("192.168.0.195:8000")).toBeInTheDocument()
  })
})

describe("MaintenanceTab — confirmation gates", () => {
  it("never runs a destructive op from a bare click", () => {
    render(<MaintenanceTab />, { wrapper })
    fireEvent.click(screen.getByRole("button", { name: /Run sweep now/ }))
    // Armed, not run: the count is untouched until Confirm.
    expect(
      useDemoStore.getState().maintenance.cleanup.expired,
    ).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole("button", { name: /Confirm — delete now/ }))
    expect(useDemoStore.getState().maintenance.cleanup.expired).toBe(0)
  })
})

describe("DistributionTab — keys for apps and agents", () => {
  it("offers a usable New key control", () => {
    render(<DistributionTab />, { wrapper })
    expect(screen.getByRole("button", { name: /New key/ })).not.toBeDisabled()
  })

  it("cannot create a key without a label — the mint is never a bare click", async () => {
    render(<DistributionTab />, { wrapper })
    fireEvent.click(screen.getByRole("button", { name: /New key/ }))
    const create = await screen.findByRole("button", { name: /Create key/ })
    expect(create).toBeDisabled()

    fireEvent.change(screen.getByLabelText(/What is this key for/), {
      target: { value: "a name" },
    })
    expect(screen.getByRole("button", { name: /Create key/ })).not.toBeDisabled()
  })
})

describe("DistributionTab", () => {
  it("shows the MCP connect card and no fixture-backed push panel in demo", () => {
    render(<DistributionTab />, { wrapper })
    expect(screen.getByText("Connect an MCP client")).toBeInTheDocument()
    expect(screen.queryByText(/Labels survive injection/)).not.toBeInTheDocument()
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
