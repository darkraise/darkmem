import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, within } from "@testing-library/react"
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

/** Every section is read-only until its Edit button is pressed, so a test that
 *  touches a control has to open that section's editor first. Scoped to the
 *  card whose heading matches, because every card has an Edit button. */
const openEditor = (section: string) => {
  const heading = screen
    .getAllByRole("heading", { level: 3 })
    .find((h) => h.textContent === section)
  if (!heading) throw new Error(`no section card titled ${section}`)
  const header = heading.closest(".dr-card-header")
  fireEvent.click(within(header as HTMLElement).getByRole("button", { name: /Edit/ }))
}

/** The dialog's own Save — the single request for that section. */
const saveEditor = () => {
  fireEvent.click(screen.getByRole("button", { name: "Save" }))
}

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
    openEditor("feature flags")
    const toggle = screen.getByLabelText("reranker_enabled")
    expect(toggle).not.toBeDisabled()
    fireEvent.click(toggle)
    saveEditor()
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
      "graph augmentation",
      "pipeline & embedding tunables",
      "classification",
      "repo auto-provision allowlist",
      "corroboration promotion gate",
    ]) {
      expect(screen.getByLabelText(`About ${name}`)).toBeInTheDocument()
    }
  })

  it("keeps every card header on one row", () => {
    // jsdom does not lay out, so height cannot be asserted. The class that
    // decides this can: the library's `.dr-card-header` is `flex flex-col`,
    // so a header carrying only `flex-nowrap` still stacks its children into
    // a column — which is exactly the bug this pins. `flex-row` is the
    // override that matters.
    const { container } = renderTab()
    const headers = container.querySelectorAll(".dr-card-header")
    expect(headers.length).toBe(8)
    for (const header of headers) {
      expect(header.className).toContain("flex-row")
      expect(header.className).toContain("flex-nowrap")
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
    openEditor("graph augmentation")
    expect(screen.getByLabelText("w_ppr")).toBeInTheDocument()
    expect(screen.getByLabelText("w_dual")).toBeInTheDocument()
    // Context augmentation produces no ranked list, so there is no weight box.
    expect(screen.queryByLabelText("w_community")).not.toBeInTheDocument()
  })

  it("committing a paired weight writes it to the store", () => {
    renderTab()
    openEditor("graph augmentation")
    const input = screen.getByLabelText("w_ppr")
    fireEvent.change(input, { target: { value: "0.3" } })
    fireEvent.keyDown(input, { key: "Enter" })
    saveEditor()
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
    openEditor("corroboration promotion gate")
    const input = screen.getByLabelText("n_default")
    fireEvent.change(input, { target: { value: "5" } })
    fireEvent.keyDown(input, { key: "Enter" })
    saveEditor()
    const param = useDemoStore
      .getState()
      .flags.corroboration.params.find((p) => p.name === "n_default")
    expect(param?.effective).toBe(5)
    expect(param?.state).toBe("honoured")
  })

  it("an unbacked loosening clamps, and the clamp is rendered rather than logged", () => {
    renderTab()
    openEditor("corroboration promotion gate")
    const input = screen.getByLabelText("n_diverse")
    fireEvent.change(input, { target: { value: "1" } })
    fireEvent.keyDown(input, { key: "Enter" })
    saveEditor()

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

  // Found in a browser, not by a test: the input's draft was
  // initial-value-only, so after a reset the next blur committed the stale
  // number back and silently undid it — a 200 on the way out and no error
  // anywhere. Every assertion below fails against that version.
  // The dialog holds the draft, so a reset cannot be undone by a later blur
  // on a stale field — the whole class of bug the old inline editor had.
  it("reset to floor clears a commitment and survives a blur", () => {
    renderTab()
    openEditor("corroboration promotion gate")
    const input = screen.getByLabelText("n_diverse")
    fireEvent.change(input, { target: { value: "4" } })
    fireEvent.keyDown(input, { key: "Enter" })

    const resets = screen.getAllByRole("button", { name: "reset to floor" })
    fireEvent.click(resets[1]!)
    fireEvent.blur(input)
    saveEditor()

    const param = useDemoStore
      .getState()
      .flags.corroboration.params.find((p) => p.name === "n_diverse")
    expect(param?.committed).toBeNull()
    expect(param?.effective).toBe(2)
  })

  it("shows the floor in the box once a commitment is cleared", () => {
    renderTab()
    openEditor("corroboration promotion gate")
    const input = screen.getByLabelText("n_diverse")
    fireEvent.change(input, { target: { value: "4" } })
    fireEvent.keyDown(input, { key: "Enter" })
    expect(input).toHaveValue("4")

    fireEvent.click(screen.getAllByRole("button", { name: "reset to floor" })[1]!)
    // A box still reading 4 next to a floor of 2 is what made the old inline
    // editor re-commit the stale number.
    expect(input).toHaveValue("2")
  })

  it("cancelling discards the whole section's edits", () => {
    // The other half of editing in a dialog: nothing is written until Save,
    // so an abandoned edit costs no request and leaves no partial state.
    renderTab()
    openEditor("corroboration promotion gate")
    const input = screen.getByLabelText("n_default")
    fireEvent.change(input, { target: { value: "9" } })
    fireEvent.keyDown(input, { key: "Enter" })
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }))

    const param = useDemoStore
      .getState()
      .flags.corroboration.params.find((p) => p.name === "n_default")
    expect(param?.committed).toBeNull()
  })

  it("names every field one save will write", () => {
    renderTab()
    openEditor("corroboration promotion gate")
    for (const [name, value] of [
      ["n_default", "5"],
      ["time_gap_days", "14"],
    ] as const) {
      const input = screen.getByLabelText(name)
      fireEvent.change(input, { target: { value } })
      fireEvent.keyDown(input, { key: "Enter" })
    }
    expect(
      screen.getByText(/one request will write: n_default, time_gap_days/),
    ).toBeInTheDocument()
  })
})

describe("FlagsTab — the tunables the API served and nothing rendered", () => {
  it("renders all four pipeline/embedding knobs", () => {
    renderTab()
    openEditor("pipeline & embedding tunables")
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
    openEditor("pipeline & embedding tunables")
    const input = screen.getByLabelText("pipeline_concurrency")
    fireEvent.change(input, { target: { value: "8" } })
    fireEvent.keyDown(input, { key: "Enter" })
    saveEditor()
    expect(
      useDemoStore
        .getState()
        .flags.tunables.find((t) => t.key === "pipeline_concurrency")?.value,
    ).toBe(8)
  })

  it("clamps a value past the API's own bound instead of sending a 422", () => {
    renderTab()
    openEditor("pipeline & embedding tunables")
    const input = screen.getByLabelText("pipeline_concurrency")
    fireEvent.change(input, { target: { value: "99" } })
    fireEvent.keyDown(input, { key: "Enter" })
    saveEditor()
    expect(
      useDemoStore
        .getState()
        .flags.tunables.find((t) => t.key === "pipeline_concurrency")?.value,
    ).toBe(20)
  })
})

/** Demo mode starts in `simple`, where the area rows are deliberately absent.
 *  Anything asserting on them has to put the tab into the mode that has
 *  them. */
const switchToExpanded = () => {
  // By role: the word also appears in the mode explainer sentence, which
  // `getByText` matches too.
  fireEvent.click(screen.getByRole("radio", { name: "expanded" }))
}

describe("FlagsTab — the classification label space", () => {
  it("renders the labels the classifier may actually emit", () => {
    renderTab()
    expect(screen.getByText("label space")).toBeInTheDocument()
    for (const label of ["fact", "decision", "problem", "procedural"]) {
      expect(
        screen.getByLabelText(`About the ${label} label`),
      ).toBeInTheDocument()
    }
  })

  it("hides the areas in simple mode instead of listing them inert", () => {
    // They cannot change the list above them there, and eleven rows each
    // saying so made the card longest exactly when it had least to say.
    renderTab()
    expect(screen.queryByLabelText("technical")).not.toBeInTheDocument()
    expect(screen.queryByText("would add")).not.toBeInTheDocument()
  })

  it("still names the feature and where it lives, so it does not read as absent", () => {
    renderTab()
    expect(screen.getByText(/not read at\s+all/)).toBeInTheDocument()
    expect(screen.getByText(/Edit and switch to/)).toBeInTheDocument()
  })

  it("brings the areas back in expanded mode", () => {
    renderTab()
    openEditor("classification")
    switchToExpanded()
    saveEditor()
    // The read-only card now lists the enabled areas and what each contributes.
    expect(screen.getByText("Technical")).toBeInTheDocument()
  })
})

describe("FlagsTab — classification areas", () => {
  it("edits mode and areas together, in one request", () => {
    // The pair is the point: switching to expanded and choosing the areas that
    // expanded mode reads are one decision, and used to be two writes.
    renderTab()
    openEditor("classification")
    switchToExpanded()
    fireEvent.click(screen.getByLabelText("technical"))
    expect(
      screen.getByText(
        /one request will write: classification_mode, classification_areas/,
      ),
    ).toBeInTheDocument()
    saveEditor()

    const flags = useDemoStore.getState().flags
    expect(flags.classification_mode).toBe("expanded")
    expect(flags.classification_areas).not.toContain("technical")
  })

  it("keeps general fixed on — the API forces it back server-side", () => {
    renderTab()
    openEditor("classification")
    switchToExpanded()
    expect(screen.getByLabelText("general")).toBeDisabled()
  })

  it("shows and hides the area list as the drafted mode changes", () => {
    // The list follows the mode being drafted, not the one that is saved:
    // picking `simple` is picking a fixed vocabulary, so the controls that
    // shape a per-area one have nothing to say.
    renderTab()
    openEditor("classification")
    const dialog = screen.getByRole("dialog")
    expect(within(dialog).queryByLabelText("technical")).not.toBeInTheDocument()
    expect(within(dialog).getByText(/does not read/)).toBeInTheDocument()

    switchToExpanded()
    expect(within(dialog).getByLabelText("technical")).toBeInTheDocument()

    fireEvent.click(within(dialog).getByRole("radio", { name: "simple" }))
    expect(within(dialog).queryByLabelText("technical")).not.toBeInTheDocument()
  })

  it("keeps the area selection across a mode round-trip", () => {
    // Hiding the list must not discard what it held — the values are still
    // drafted, and go out with the save.
    renderTab()
    openEditor("classification")
    switchToExpanded()
    fireEvent.click(screen.getByLabelText("technical"))

    const dialog = screen.getByRole("dialog")
    fireEvent.click(within(dialog).getByRole("radio", { name: "simple" }))
    switchToExpanded()

    expect(screen.getByLabelText("technical")).not.toBeChecked()
    // The mode is dirty too (demo starts simple), so the footer names both —
    // what matters is that the area edit survived being hidden.
    expect(
      within(dialog).getByText(/one request will write:.*classification_areas/),
    ).toBeInTheDocument()
  })
})

describe("FlagsTab — ruling 2: repo_allowlist editing surface", () => {
  it("shows the current allowlist patterns", () => {
    renderTab()
    expect(screen.getByText("github.com/darkraise/*")).toBeInTheDocument()
  })

  it("saving a new pattern writes it to the store", () => {
    renderTab()
    openEditor("repo auto-provision allowlist")
    fireEvent.change(screen.getByLabelText("repo_allowlist patterns"), {
      target: { value: "github.com/darkraise/*\n*.forge.internal.example" },
    })
    saveEditor()
    expect(useDemoStore.getState().flags.repo_allowlist.patterns).toEqual([
      "github.com/darkraise/*",
      "*.forge.internal.example",
    ])
  })

  it("names the empty-allowlist-refuses-everything honesty when cleared", () => {
    renderTab()
    openEditor("repo auto-provision allowlist")
    fireEvent.change(screen.getByLabelText("repo_allowlist patterns"), {
      target: { value: "" },
    })
    saveEditor()
    expect(
      screen.getByText(/every repo hint is refused until at least one/),
    ).toBeInTheDocument()
  })
})
