import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen } from "@testing-library/react"
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
  it("renders the six live purpose cards and no provider/profile chrome", () => {
    renderTab()
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

  it("renders the two inert Tier-C purposes, clearly labelled and never omitted", () => {
    renderTab()
    for (const purpose of ["synthesis", "verification"]) {
      expect(screen.getAllByText(purpose).length).toBeGreaterThan(0)
    }
    expect(screen.getAllByText("inert").length).toBe(2)
    expect(screen.getByText(/T3\.02/)).toBeInTheDocument()
    expect(screen.getByText(/T2\.26/)).toBeInTheDocument()
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
    expect(screen.getByText("local")).toBeInTheDocument()
  })

  it("renders the code-summarization buckets as their own cards in demo mode", () => {
    renderTab()
    expect(screen.getByText("code-summarization buckets")).toBeInTheDocument()
    for (const bucket of ["symbol", "module", "overview"]) {
      expect(screen.getByText(bucket)).toBeInTheDocument()
    }
  })
})
