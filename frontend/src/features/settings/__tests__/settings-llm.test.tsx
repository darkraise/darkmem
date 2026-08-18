import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, within } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { useDemoStore } from "@/demo/store"
import { LLMTab } from "../components/llm-tab"

// This exercises the fixture-backed path deliberately (T1.55 is done and
// this file pins its demo rendering), so it is frozen at DEMO: true rather
// than relying on the about-to-change default (T1.58). `useLLMTabBinding`
// still calls `useLlmConfig` unconditionally (rules of hooks) with
// `enabled: false` in demo mode — the query never fires, but `useQuery`
// still needs a provider in the tree or it throws.
vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const renderTab = () => render(<LLMTab />, { wrapper })

afterEach(() => {
  useDemoStore.getState().resetSettings()
})

describe("LLMTab", () => {
  it("renders the seven writable purpose cards and no provider/profile chrome", () => {
    renderTab()
    for (const purpose of [
      "embedding",
      "extraction",
      "classification",
      "summarization",
      "reranker",
      "reasoning",
      // Seeded inert (no consumer until T3.02) but writable since T2.106 —
      // rendered as a normal editable card, not a Tier-C read-only one.
      "synthesis",
    ]) {
      expect(screen.getAllByText(purpose).length).toBeGreaterThan(0)
    }
    // The removed chrome is shown struck-through, not silently omitted.
    expect(screen.getByText("llm-providers tab")).toBeInTheDocument()
    expect(screen.getByText(/removed with the flattening/)).toBeInTheDocument()
  })

  it("renders the one remaining Tier-C purpose, clearly labelled and never omitted", () => {
    renderTab()
    expect(screen.getAllByText("verification").length).toBeGreaterThan(0)
    // verification is live and dispatched (T2.26) and stays read-only here
    // by deliberate T2.106 ruling, not a pending write-wire gap.
    expect(screen.getByText("tier c · live")).toBeInTheDocument()
    expect(screen.getByText(/qualification record is G-D's gate evidence/)).toBeInTheDocument()
    expect(screen.queryByText("tier c · inert")).not.toBeInTheDocument()
  })

  it("does not render synthesis as a Tier-C read-only card", () => {
    renderTab()
    // Only one Tier-C card left (verification); synthesis has its own
    // full editable card among the seven live purposes above.
    expect(screen.queryByText(/no consumer yet — activates with/)).not.toBeInTheDocument()
  })

  it("synthesis is a fully editable card that saves through the normal wire", () => {
    renderTab()
    const input = screen.getByLabelText("synthesis model")
    expect(input).not.toBeDisabled()
    fireEvent.change(input, { target: { value: "qwen2.5:7b" } })
    const saves = screen.getAllByRole("button", { name: "Save" })
    const enabled = saves.find((b) => !(b as HTMLButtonElement).disabled)
    expect(enabled).toBeDefined()
    fireEvent.click(enabled!)
    expect(
      screen.getByText(/Saved — synthesis purpose updated/),
    ).toBeInTheDocument()
  })

  it("verification carries no editable inputs and no Save button", () => {
    renderTab()
    // `verification` has no `${purpose} model`-style aria-label because
    // TierCPurposeCard never wires one — only the editable PurposeCard does.
    expect(screen.queryByLabelText("verification model")).not.toBeInTheDocument()

    const card = screen.getByText("verification").closest(".border-dashed")
    expect(card).not.toBeNull()
    const inputs = within(card as HTMLElement).getAllByRole("textbox")
    expect(inputs.length).toBeGreaterThan(0)
    for (const input of inputs) {
      expect(input).toBeDisabled()
    }
    expect(
      within(card as HTMLElement).queryByRole("button", { name: "Save" }),
    ).not.toBeInTheDocument()
  })

  it("carries dimensions only on embedding", () => {
    renderTab()
    expect(screen.getAllByText("dimensions")).toHaveLength(1)
  })

  it("save shows the live-reload confirmation with the trace", () => {
    renderTab()
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
    renderTab()
    const params = screen.getByLabelText("extraction params")
    fireEvent.change(params, { target: { value: "{broken" } })
    expect(screen.getByText("invalid JSON")).toBeInTheDocument()
  })

  it("carries the classifier_kind toggle on the classification card", () => {
    renderTab()
    expect(screen.getByText("classifier_kind")).toBeInTheDocument()
    // The segments are icon-only now, so their accessible names are the only
    // handle on them — which is exactly what has to keep working.
    expect(
      screen.getByRole("radio", { name: "LLM-backed classifier" }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("radio", { name: "In-process classifier" }),
    ).toBeInTheDocument()
  })

  it("renders the code-summarization buckets as their own cards in demo mode", () => {
    renderTab()
    expect(screen.getByText("code-summarization buckets")).toBeInTheDocument()
    for (const bucket of ["symbol", "module", "overview"]) {
      expect(screen.getByText(bucket)).toBeInTheDocument()
    }
  })
})
