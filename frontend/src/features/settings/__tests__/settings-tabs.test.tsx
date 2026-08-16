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

// T4.04 rewrote this block rather than deleting it. It used to assert the
// dormancy claim — "Phase-4 · designed, not wired", every control disabled —
// which was true until T4.01 wired the credential and T4.02 stamped the
// columns, and afterwards was a test pinning a false statement about the
// system. What it protects is unchanged: that this card says what is actually
// true of the box, in whichever direction that runs.
describe("SecurityTab — ApiKey honesty", () => {
  it("renders the credential path as live, with its controls usable", () => {
    render(<SecurityTab />, { wrapper })
    expect(screen.queryByText(/designed, not wired/)).not.toBeInTheDocument()
    expect(screen.queryByText(/not available in this deployment/)).not.toBeInTheDocument()
    expect(screen.getByLabelText("Key label")).not.toBeDisabled()
    expect(
      screen.getByText(/ratify — never a scope, human cookie session only/),
    ).toBeInTheDocument()
  })

  it("cannot create a key without a label — the mint is never a bare click", () => {
    render(<SecurityTab />, { wrapper })
    expect(screen.getByRole("button", { name: /Create key/ })).toBeDisabled()
  })

  it("renders the three LAN doors and the TOFU claim", () => {
    render(<SecurityTab />, { wrapper })
    expect(screen.getByText("/mcp")).toBeInTheDocument()
    expect(screen.getByText("/api/v1 + /ws")).toBeInTheDocument()
    expect(screen.getByText("/setup")).toBeInTheDocument()
    expect(screen.getAllByText("claimed").length).toBeGreaterThan(0)
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

  it("marks endpoint-less DB ops as illustrative, not shipped", () => {
    render(<MaintenanceTab />, { wrapper })
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
