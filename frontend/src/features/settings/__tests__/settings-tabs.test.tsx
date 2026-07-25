import { fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { useDemoStore } from "@/demo/store"
import { FlagsTab } from "../components/flags-tab"
import { LLMTab } from "../components/llm-tab"
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

describe("FlagsTab — invariant 23 honesty", () => {
  it("renders every dormant arm as inactive, never omitted", () => {
    render(<FlagsTab />)
    // 4 dormant (w_importance, w_heat, w_recency, w_ppr) vs 3 active.
    expect(screen.getAllByText("inactive")).toHaveLength(4)
    expect(screen.getAllByText("active")).toHaveLength(3)
  })

  it("labels coded defaults distinctly from written overrides", () => {
    render(<FlagsTab />)
    expect(screen.getAllByText("(coded default)").length).toBeGreaterThan(0)
    expect(screen.getAllByText("(override)").length).toBeGreaterThan(0)
  })

  it("shows the no-weight note for community injection", () => {
    render(<FlagsTab />)
    expect(
      screen.getByText(/no paired RRF weight/),
    ).toBeInTheDocument()
  })

  it("summarises all seven job cadences with a pointer to the Jobs tab", () => {
    render(<FlagsTab />)
    expect(screen.getByText("expired_memory_cleanup")).toBeInTheDocument()
    expect(
      screen.getByText(/edited in the dedicated Settings → Jobs tab/),
    ).toBeInTheDocument()
  })
})

describe("LLMTab", () => {
  it("renders the six purpose cards and no provider/profile chrome", () => {
    render(<LLMTab />)
    for (const purpose of [
      "embedding",
      "extraction",
      "classification",
      "summarization",
      "reranker",
      "reasoning",
    ]) {
      expect(screen.getAllByText(purpose).length).toBeGreaterThan(0)
    }
    // The removed chrome is shown struck-through, not silently omitted.
    expect(screen.getByText("llm-providers tab")).toBeInTheDocument()
    expect(screen.getByText(/removed with the flattening/)).toBeInTheDocument()
  })

  it("carries dimensions only on embedding", () => {
    render(<LLMTab />)
    expect(screen.getAllByText("dimensions")).toHaveLength(1)
  })

  it("save shows the live-reload confirmation with the trace", () => {
    render(<LLMTab />)
    const input = screen.getByLabelText("reasoning base_url")
    fireEvent.change(input, { target: { value: "api.openai.com/v2" } })
    const saves = screen.getAllByRole("button", { name: "Save" })
    const enabled = saves.find((b) => !(b as HTMLButtonElement).disabled)
    expect(enabled).toBeDefined()
    fireEvent.click(enabled!)
    expect(
      screen.getByText(/Saved — reasoning purpose updated/),
    ).toBeInTheDocument()
    expect(screen.getByText(/no redeploy needed/i)).toBeInTheDocument()
  })

  it("rejects malformed params JSON before save", () => {
    render(<LLMTab />)
    const params = screen.getByLabelText("extraction params")
    fireEvent.change(params, { target: { value: "{broken" } })
    expect(screen.getByText("invalid JSON")).toBeInTheDocument()
  })

  it("carries the classifier_kind toggle on the classification card", () => {
    render(<LLMTab />)
    expect(screen.getByText("classifier_kind")).toBeInTheDocument()
    expect(screen.getByText("local")).toBeInTheDocument()
  })
})

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
