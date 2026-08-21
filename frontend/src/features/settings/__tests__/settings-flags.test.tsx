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
vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
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

  // Job schedules are the Jobs page's, and duplicating them here meant this
  // tab fetched GET /jobs for a read-only summary of someone else's surface.
  it("summarises no job cadences — they belong to the Jobs page", () => {
    renderTab()
    expect(screen.queryByText("expired_memory_cleanup")).not.toBeInTheDocument()
    expect(screen.queryByText("job cadences")).not.toBeInTheDocument()
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

describe("FlagsTab — every badge explains itself", () => {
  // The badges are the whole explanation of a row's state, and the two words
  // most likely to be misread are "inactive" (which does not mean missing) and
  // "unmeasured" (which does not mean locked).
  it("explains what inactive means — built and wired at weight 0, not absent", () => {
    renderTab()
    const [pill] = screen.getAllByLabelText("About the inactive state")
    expect(pill).toBeInTheDocument()
  })

  it("explains what active means", () => {
    renderTab()
    expect(
      screen.getAllByLabelText("About the active state").length,
    ).toBeGreaterThan(0)
  })

  it("explains that unmeasured is about the evidence, not the control", () => {
    renderTab()
    expect(
      screen.getAllByLabelText("About the unmeasured badge"),
    ).toHaveLength(5)
  })
})

describe("FlagsTab — every section names itself", () => {
  // Four of the six group heads rendered with no `help` prop at all, so they
  // had no info icon: a heading like "rank_fusion_factor arms" is a key, not
  // an explanation.
  it("gives every group head a help tip", () => {
    renderTab()
    for (const name of [
      "rank_fusion_factor arms",
      "feature flags",
      "context match boost",
      "graph augmentation — RRF list weights + *_enabled flags",
      "pipeline & embedding tunables",
      "classification",
      "repo auto-provision allowlist",
      "corroboration promotion gate",
    ]) {
      expect(screen.getByLabelText(`About ${name}`)).toBeInTheDocument()
    }
  })

  it("gives w_context_boost a description rather than its own key", () => {
    renderTab()
    // `armFrom` falls back to the flag name when the meta table has no entry,
    // so a missing row rendered as a "description" that said nothing.
    const tip = screen.getByLabelText("About w_context_boost")
    expect(tip).toBeInTheDocument()
  })
})

describe("FlagsTab — graph augmentation is editable", () => {
  it("renders a weight input beside each channel that has one", () => {
    renderTab()
    expect(screen.getByLabelText("w_ppr")).toBeInTheDocument()
    expect(screen.getByLabelText("w_dual")).toBeInTheDocument()
    // Context augmentation produces no ranked list, so there is no weight box.
    expect(screen.queryByLabelText("w_community")).not.toBeInTheDocument()
  })

  it("committing a paired weight writes it to the store", () => {
    renderTab()
    const input = screen.getByLabelText("w_ppr")
    fireEvent.change(input, { target: { value: "0.3" } })
    fireEvent.keyDown(input, { key: "Enter" })
    const ppr = useDemoStore
      .getState()
      .flags.graph_flags.find((f) => f.key === "ppr_enabled")
    expect(ppr?.paired_arm?.value).toBe(0.3)
  })
})

describe("FlagsTab — the corroboration gate is editable and honest", () => {
  it("renders all three thresholds, not just the two origin counts", () => {
    renderTab()
    for (const name of ["n_default", "n_diverse", "time_gap_days"]) {
      expect(screen.getByText(name)).toBeInTheDocument()
    }
  })

  it("tightening a threshold is honoured", () => {
    renderTab()
    const input = screen.getByLabelText("n_default")
    fireEvent.change(input, { target: { value: "5" } })
    fireEvent.keyDown(input, { key: "Enter" })
    const param = useDemoStore
      .getState()
      .flags.corroboration.params.find((p) => p.name === "n_default")
    expect(param?.effective).toBe(5)
    expect(param?.state).toBe("honoured")
  })

  it("an unbacked loosening clamps, and the clamp is rendered rather than logged", () => {
    renderTab()
    const input = screen.getByLabelText("n_diverse")
    fireEvent.change(input, { target: { value: "1" } })
    fireEvent.keyDown(input, { key: "Enter" })

    const param = useDemoStore
      .getState()
      .flags.corroboration.params.find((p) => p.name === "n_diverse")
    expect(param?.committed).toBe(1)
    expect(param?.effective).toBe(2)
    // The point of the whole surface: an echoed 1 would state that the ladder
    // promotes at one origin, and it does not.
    expect(screen.getByText(/below the floor of 2/)).toBeInTheDocument()
    expect(screen.getAllByText("clamped").length).toBeGreaterThan(0)
  })

  it("reset to floor clears a commitment", () => {
    renderTab()
    const input = screen.getByLabelText("n_default")
    fireEvent.change(input, { target: { value: "5" } })
    fireEvent.keyDown(input, { key: "Enter" })
    fireEvent.click(screen.getAllByRole("button", { name: "reset to floor" })[0]!)

    const param = useDemoStore
      .getState()
      .flags.corroboration.params.find((p) => p.name === "n_default")
    expect(param?.committed).toBeNull()
    expect(param?.effective).toBe(3)
  })
})

describe("FlagsTab — the tunables the API served and nothing rendered", () => {
  it("renders all four pipeline/embedding knobs", () => {
    renderTab()
    for (const key of [
      "pipeline_concurrency",
      "embedding_batch_size",
      "embedding_concurrency",
      "entity_cache_ttl_minutes",
    ]) {
      expect(screen.getByLabelText(key)).toBeInTheDocument()
    }
  })

  it("committing a tunable writes it to the store", () => {
    renderTab()
    const input = screen.getByLabelText("pipeline_concurrency")
    fireEvent.change(input, { target: { value: "8" } })
    fireEvent.keyDown(input, { key: "Enter" })
    expect(
      useDemoStore
        .getState()
        .flags.tunables.find((t) => t.key === "pipeline_concurrency")?.value,
    ).toBe(8)
  })

  it("clamps a value past the API's own bound instead of sending a 422", () => {
    renderTab()
    const input = screen.getByLabelText("pipeline_concurrency")
    fireEvent.change(input, { target: { value: "99" } })
    fireEvent.keyDown(input, { key: "Enter" })
    expect(
      useDemoStore
        .getState()
        .flags.tunables.find((t) => t.key === "pipeline_concurrency")?.value,
    ).toBe(20)
  })
})

describe("FlagsTab — classification tuning", () => {
  it("renders the mode control and the area checkboxes", () => {
    renderTab()
    expect(screen.getByLabelText("classification_mode")).toBeInTheDocument()
    expect(screen.getByLabelText("technical")).toBeInTheDocument()
  })

  it("keeps general fixed on — the API forces it back server-side", () => {
    renderTab()
    expect(screen.getByLabelText("general")).toBeDisabled()
  })

  it("unchecking an area writes the remaining set", () => {
    renderTab()
    fireEvent.click(screen.getByLabelText("technical"))
    expect(
      useDemoStore.getState().flags.classification_areas,
    ).not.toContain("technical")
  })
})

describe("FlagsTab — ruling 2: repo_allowlist editing surface", () => {
  it("shows the current allowlist patterns", () => {
    renderTab()
    expect(screen.getByLabelText("repo_allowlist patterns")).toHaveValue(
      "github.com/darkraise/*",
    )
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
