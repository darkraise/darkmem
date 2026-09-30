import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, within } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { toast } from "darkraise-ui/components/sonner"
import { useDemoStore } from "@/demo/store"
import { LLMTab } from "../components/llm-tab"

// This exercises the fixture-backed path deliberately (T1.55 is done and
// this file pins its demo rendering), so it is frozen at DEMO: true rather
// than relying on the about-to-change default (T1.58). `useLLMTabBinding`
// still calls `useLlmConfig` unconditionally (rules of hooks) with
// `enabled: false` in demo mode — the query never fires, but `useQuery`
// still needs a provider in the tree or it throws.
vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
// A save reports through a toast now. No <Toaster /> is mounted here, so the
// call is the observable, and asserting on it also proves both doors announce
// through the same helper rather than each rendering its own banner.
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))
function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const renderTab = () => render(<LLMTab />, { wrapper })

afterEach(() => {
  useDemoStore.getState().resetSettings()
})

// Purpose editing moved behind a dialog. These tests open it and then assert
// exactly what they asserted before — which field exists, which validation
// fires, what a save puts on the wire. The properties did not change; the
// number of clicks to reach them did.
function openPurposeEditor(purpose: string) {
  fireEvent.click(screen.getByLabelText(`Edit ${purpose}`))
}

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
    // The struck-through "removed with the flattening" list is gone: a panel
    // that was never built in this app does not need a headstone in its UI.
    expect(screen.queryByText("llm-profiles tab")).not.toBeInTheDocument()
    expect(
      screen.queryByText(/removed with the flattening/),
    ).not.toBeInTheDocument()
  })

  it("renders the read-only verification purpose, never omitted", () => {
    renderTab()
    expect(screen.getAllByText("verification").length).toBeGreaterThan(0)
    expect(
      screen.getByText(/managed by the judge qualification run/),
    ).toBeInTheDocument()
  })

  it("renders exactly one read-only purpose card", () => {
    renderTab()
    // synthesis has its own editable card among the seven live purposes.
    expect(
      screen.getAllByText(/managed by the judge qualification run/),
    ).toHaveLength(1)
  })

  it("synthesis is a fully editable card that saves through the normal wire", () => {
    renderTab()
    openPurposeEditor("synthesis")
    const input = screen.getByLabelText("synthesis model")
    expect(input).not.toBeDisabled()
    fireEvent.change(input, { target: { value: "qwen2.5:7b" } })
    fireEvent.click(screen.getByRole("button", { name: "Save" }))
    expect(toast.success).toHaveBeenCalledWith(
      "Saved — synthesis purpose updated",
      expect.objectContaining({
        description: expect.stringContaining("model"),
      }),
    )
  })

  it("verification carries no editable inputs and no Save button", () => {
    renderTab()
    // The Tier-C purpose has no edit affordance at all, by owner ruling: its
    // connection is pinned to a measured qualification identity and the
    // supported way to change the judge is to re-run the harness, not a form.
    expect(screen.queryByLabelText("Edit verification")).not.toBeInTheDocument()
    expect(
      screen.queryByLabelText("verification model"),
    ).not.toBeInTheDocument()

    const card = screen.getByText("verification").closest(".border-dashed")
    expect(card).not.toBeNull()
    expect(within(card as HTMLElement).queryAllByRole("textbox")).toHaveLength(
      0,
    )
    expect(
      within(card as HTMLElement).queryByRole("button", { name: "Save" }),
    ).not.toBeInTheDocument()
  })

  it("carries dimensions only on embedding", () => {
    renderTab()
    openPurposeEditor("embedding")
    expect(screen.getAllByText("dimensions")).toHaveLength(1)
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }))
    openPurposeEditor("extraction")
    expect(screen.queryByText("dimensions")).not.toBeInTheDocument()
  })

  it("save shows the live-reload confirmation with the trace", () => {
    renderTab()
    openPurposeEditor("reasoning")
    const input = screen.getByLabelText("reasoning model")
    fireEvent.change(input, { target: { value: "gpt-5.1" } })
    fireEvent.click(screen.getByRole("button", { name: "Save" }))
    // The trace moved into the toast's description: the changed field.
    expect(toast.success).toHaveBeenCalledWith(
      "Saved — reasoning purpose updated",
      expect.objectContaining({
        description: expect.stringContaining("model"),
      }),
    )
  })

  it("rejects malformed params JSON before save", () => {
    renderTab()
    openPurposeEditor("extraction")
    const params = screen.getByLabelText("extraction params")
    fireEvent.change(params, { target: { value: "{broken" } })
    expect(screen.getByText("invalid JSON")).toBeInTheDocument()
  })

  it("carries the classifier_kind toggle on the classification card", () => {
    renderTab()
    openPurposeEditor("classification")
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
    openPurposeEditor("summarization")
    expect(screen.getByText("code-summarization buckets")).toBeInTheDocument()
    for (const bucket of ["symbol", "module", "overview"]) {
      expect(screen.getByText(bucket)).toBeInTheDocument()
    }
  })

  it("switches the purposes layout and keeps its own preference key", () => {
    renderTab()
    fireEvent.click(screen.getByRole("radio", { name: "List layout" }))
    expect(screen.getByRole("radio", { name: "List layout" })).toBeChecked()
    expect(
      JSON.parse(localStorage.getItem("darkmem-llm-purposes-layout") ?? "{}")
        .state.layout,
    ).toBe("list")
  })

  it("shows no editable field on a purpose row until its editor is opened", () => {
    renderTab()
    expect(screen.queryByLabelText("extraction model")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("extraction params")).not.toBeInTheDocument()
    openPurposeEditor("extraction")
    expect(screen.getByLabelText("extraction model")).toBeInTheDocument()
  })

  // Only four of the eight purposes have a system prompt in
  // `backend/app/services/prompt.py`; the rest would open an empty editor.
  it("offers a system-prompt CTA on exactly the purposes that have one", () => {
    renderTab()
    for (const purpose of [
      "extraction",
      "classification",
      "reasoning",
      "summarization",
    ]) {
      expect(
        screen.getByLabelText(`System prompt for ${purpose}`),
      ).toBeInTheDocument()
    }
    for (const purpose of ["embedding", "reranker", "synthesis"]) {
      expect(
        screen.queryByLabelText(`System prompt for ${purpose}`),
      ).not.toBeInTheDocument()
    }
  })

  it("opens the prompt editor for the purpose whose CTA was pressed", () => {
    renderTab()
    fireEvent.click(screen.getByLabelText("System prompt for extraction"))
    expect(
      screen.getByRole("dialog", { name: /extraction system prompt/ }),
    ).toBeInTheDocument()
  })

  // `Number(v) || 0` on the old raw input committed zero dimensions for text
  // it could not parse, which is a silently broken embedder rather than a
  // rejected edit.
  it("refuses an unparseable dimensions value instead of committing zero", () => {
    renderTab()
    openPurposeEditor("embedding")
    const field = screen.getByLabelText("embedding dimensions")

    // Positive control first, so the negative assertion below cannot pass by
    // the field simply being inert.
    fireEvent.change(field, { target: { value: "1536" } })
    fireEvent.blur(field)
    expect((field as HTMLInputElement).value).toBe("1536")

    fireEvent.change(field, { target: { value: "not-a-number" } })
    fireEvent.blur(field)
    expect((field as HTMLInputElement).value).toBe("1536")
  })
})
