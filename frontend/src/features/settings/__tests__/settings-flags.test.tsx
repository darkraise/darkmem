import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { useDemoStore } from "@/demo/store"
import { FlagsTab } from "../components/flags-tab"

// This exercises the fixture-backed path deliberately (T1.45/T1.57 are done
// and this file pins their demo rendering), so it is frozen at DEMO: true
// rather than relying on the about-to-change default (T1.58). `useFlagsTab
// Binding` still calls `useFeatureFlags`/`useJobs`/`useRepoAllowlist`
// unconditionally (rules of hooks) with `enabled: false` in demo mode — the
// queries never fire, but `useQuery` still needs a provider in the tree or
// it throws.
vi.mock("@/demo/flag", () => ({ DEMO: true }))
function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const renderTab = () => render(<FlagsTab />, { wrapper })

afterEach(() => {
  useDemoStore.getState().resetSettings()
})

describe("FlagsTab — invariant 23 honesty (demo mode)", () => {
  it("renders every dormant arm as inactive, never omitted", () => {
    renderTab()
    // 4 dormant (w_importance, w_heat, w_recency, w_ppr) vs 3 active
    // (w_conf, w_context_boost, w_dual).
    expect(screen.getAllByText("inactive")).toHaveLength(4)
    expect(screen.getAllByText("active")).toHaveLength(3)
  })

  it("labels coded defaults distinctly from written overrides", () => {
    renderTab()
    expect(screen.getAllByText("(coded default)").length).toBeGreaterThan(0)
    expect(screen.getAllByText("(override)").length).toBeGreaterThan(0)
  })

  it("shows the no-weight note for community injection", () => {
    renderTab()
    expect(screen.getByText(/no paired RRF weight/)).toBeInTheDocument()
  })

  it("summarises all seven job cadences with a pointer to the Jobs tab", () => {
    renderTab()
    expect(screen.getByText("expired_memory_cleanup")).toBeInTheDocument()
    expect(
      screen.getByText(/edited in the dedicated Settings → Jobs tab/),
    ).toBeInTheDocument()
  })
})

describe("FlagsTab — ruling 1: activation ids named, not just inactive", () => {
  it("names T2.30 for w_importance and T2.31 for w_heat/w_recency", () => {
    renderTab()
    expect(screen.getByText("T2.30")).toBeInTheDocument()
    expect(screen.getAllByText("T2.31")).toHaveLength(2)
  })
})

describe("FlagsTab — ruling 3: visibly unmeasured", () => {
  it("badges every measurable-but-unmeasured arm and flag as unmeasured", () => {
    renderTab()
    // w_importance, w_heat, w_recency, w_context_boost, reranker_enabled.
    expect(screen.getAllByText("unmeasured")).toHaveLength(5)
  })

  it("does not badge already-shipped flags with no measurement requirement", () => {
    renderTab()
    const hybridRow = screen.getByText("hybrid_search_enabled").closest("div")
    expect(hybridRow?.textContent).not.toMatch(/unmeasured/)
  })

  it("flipping reranker_enabled stays possible despite being unmeasured", () => {
    renderTab()
    const toggle = screen.getByLabelText("reranker_enabled")
    expect(toggle).not.toBeDisabled()
    fireEvent.click(toggle)
    expect(
      useDemoStore
        .getState()
        .flags.behavioral_flags.find((f) => f.key === "reranker_enabled")
        ?.enabled,
    ).toBe(true)
  })
})

describe("FlagsTab — behavioral feature flags", () => {
  it("renders hybrid_search_enabled, reranker_enabled, and relation_rescue", () => {
    renderTab()
    for (const key of [
      "hybrid_search_enabled",
      "reranker_enabled",
      "relation_rescue",
    ]) {
      expect(screen.getByText(key)).toBeInTheDocument()
    }
  })
})

describe("FlagsTab — ruling 2: repo_allowlist editing surface", () => {
  it("shows the current allowlist patterns", () => {
    renderTab()
    expect(
      screen.getByLabelText("repo_allowlist patterns"),
    ).toHaveValue("github.com/darkraise/*")
  })

  it("saving a new pattern writes it to the store", () => {
    renderTab()
    const textarea = screen.getByLabelText("repo_allowlist patterns")
    fireEvent.change(textarea, {
      target: { value: "github.com/darkraise/*\n*.forge.internal.example" },
    })
    fireEvent.click(screen.getByRole("button", { name: "Save allowlist" }))
    expect(useDemoStore.getState().flags.repo_allowlist.patterns).toEqual([
      "github.com/darkraise/*",
      "*.forge.internal.example",
    ])
  })

  it("names the empty-allowlist-refuses-everything honesty when cleared", () => {
    renderTab()
    const textarea = screen.getByLabelText("repo_allowlist patterns")
    fireEvent.change(textarea, { target: { value: "" } })
    fireEvent.click(screen.getByRole("button", { name: "Save allowlist" }))
    expect(
      screen.getByText(/every repo hint is refused until at least one/),
    ).toBeInTheDocument()
  })
})
