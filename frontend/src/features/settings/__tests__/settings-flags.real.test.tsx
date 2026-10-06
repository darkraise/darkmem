import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import {
  act,
  fireEvent,
  render,
  renderHook,
  screen,
  waitFor,
  within,
} from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

import { apiFetch } from "@/lib/api"
import { toast } from "darkraise-ui/components/sonner"
import { useFlagsTabBinding } from "../use-flags-tab-binding"
import { FlagsTab } from "../components/flags-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const FEATURE_FLAGS_FIXTURE = {
  hybrid_search_enabled: true,
  reranker_enabled: false,
  pipeline_concurrency: 5,
  classification_areas: ["general"],
  classification_mode: "simple",
  embedding_batch_size: 20,
  embedding_concurrency: 1,
  entity_cache_ttl_minutes: 60,
  relation_rescue: true,
  confidence_rank_gamma: 0.4,
  w_importance: 0,
  w_heat: 0,
  w_recency: 0,
  w_context_boost: 0.25,
  ppr_enabled: false,
  w_ppr: 0,
  dual_level_enabled: true,
  w_dual: 0.15,
  community_injection_enabled: false,
  classification_labels: [
    { name: "fact", description: "neutral factual information" },
    { name: "decision", description: "explicit choices made" },
  ],
  classification_areas_apply: false,
  graph_channels: [
    {
      name: "ppr",
      flag: "ppr_enabled",
      enabled: false,
      weight_flag: "w_ppr",
      weight: 0,
      activation: "T2.50",
    },
    {
      name: "dual_level",
      flag: "dual_level_enabled",
      enabled: true,
      weight_flag: "w_dual",
      weight: 0.15,
      activation: "T2.50",
    },
    {
      name: "community_injection",
      flag: "community_injection_enabled",
      enabled: false,
      weight_flag: null,
      weight: null,
      activation: "T2.50",
    },
  ],
  rank_arms: [
    { name: "confidence", flag: "confidence_rank_gamma", value: 0.4, activation: null },
    { name: "importance", flag: "w_importance", value: 0, activation: "T2.30" },
    { name: "heat", flag: "w_heat", value: 0, activation: "T2.31" },
    { name: "recency", flag: "w_recency", value: 0, activation: "T2.31" },
  ],
  measurable_flags: [
    "w_importance",
    "w_heat",
    "w_recency",
    "w_context_boost",
    "reranker_enabled",
    "ppr_enabled",
    "w_ppr",
    "dual_level_enabled",
    "w_dual",
    "community_injection_enabled",
  ],
  measured_flags: [],
}

const LADDER_FIXTURE = {
  params: [
    {
      name: "n_default",
      committed: null,
      effective: 3,
      floor: 3,
      measured: false,
      state: "default",
      note: null,
    },
    {
      name: "n_diverse",
      committed: 1,
      effective: 2,
      floor: 2,
      measured: false,
      state: "clamped",
      note: "1 is below the minimum of 2, so 2 is used. Going lower needs a recorded measurement.",
    },
    {
      name: "time_gap_days",
      committed: 14,
      effective: 14,
      floor: 7,
      measured: false,
      state: "honoured",
      note: null,
    },
  ],
  measured: [],
  row_present: true,
  measurement_task: "T2.40",
}

const AREAS_FIXTURE = [
  { key: "general", display_name: "General", types: ["decision"], type_descriptions: {} },
  { key: "technical", display_name: "Technical", types: ["reference"], type_descriptions: {} },
]

function mockApiFetch() {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path === "/config/feature-flags") return Promise.resolve(FEATURE_FLAGS_FIXTURE)
    if (path === "/jobs") return Promise.resolve({ jobs: [] })
    if (path === "/config/repo-allowlist") {
      return Promise.resolve({ patterns: ["github.com/darkraise/*"] })
    }
    if (path === "/config/verification-ladder") {
      return Promise.resolve(LADDER_FIXTURE)
    }
    if (path === "/config/classification-areas") {
      return Promise.resolve(AREAS_FIXTURE)
    }
    return Promise.reject(new Error(`unexpected apiFetch(${path})`))
  })
}

/** The body of the most recent PUT to `path`. */
function putBody(path: string): unknown {
  const calls = vi
    .mocked(apiFetch)
    .mock.calls.filter(
      ([p, init]) =>
        p === path && (init as RequestInit | undefined)?.method === "PUT",
    )
  const call = calls[calls.length - 1]
  if (!call) throw new Error(`no PUT to ${path} yet`)
  return JSON.parse((call[1] as RequestInit).body as string)
}

describe("useFlagsTabBinding (DEMO off — real /config/feature-flags)", () => {
  afterEach(() => vi.clearAllMocks())

  it("maps the wire response into fusion arms", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(apiFetch).toHaveBeenCalledWith("/config/feature-flags")

    const importance = result.current.fusionArms.find(
      (a) => a.key === "w_importance",
    )
    expect(importance?.value).toBe(0)
    expect(importance?.source).toBe("default")

    const confidence = result.current.fusionArms.find(
      (a) => a.key === "confidence_rank_gamma",
    )
    expect(confidence?.source).toBe("override")
  })

  // The landed replacement for `reports graph augmentation and corroboration
  // as unavailable`, which pinned the pre-wiring state. Same discipline as the
  // backend's `test_the_allowlist_holds_exactly_t209s_module_now_that_it_has_
  // landed`: a marker for "not yet" must flip the moment its surface ships,
  // not stay green by accident.
  it("reports graph augmentation and corroboration as available now both doors exist", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    await waitFor(() =>
      expect(result.current.corroborationAvailable).toBe(true),
    )

    expect(result.current.graphAugmentationAvailable).toBe(true)
  })

  it("pairs each graph flag with the weight the backend named, never a guess", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.graphFlags.length).toBe(3))

    const graph = (key: string) =>
      result.current.graphFlags.find((f) => f.key === key)
    expect(graph("ppr_enabled")?.paired_arm?.key).toBe("w_ppr")
    expect(graph("dual_level_enabled")?.paired_arm?.key).toBe("w_dual")
    expect(graph("dual_level_enabled")?.paired_arm?.value).toBe(0.15)
    // Context augmentation produces no ranked list, so there is no weight —
    // rendering a 0 here would invent a knob the fusion never reads.
    expect(graph("community_injection_enabled")?.paired_arm).toBeNull()
  })

  it("reads the enabled graph flag as an override, the default one as a default", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.graphFlags.length).toBe(3))

    const graph = (key: string) =>
      result.current.graphFlags.find((f) => f.key === key)
    expect(graph("dual_level_enabled")?.source).toBe("override")
    expect(graph("ppr_enabled")?.source).toBe("default")
  })

  it("saves a whole section in one PUT to /config/feature-flags", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.saveFlags("graph", { ppr_enabled: true, w_ppr: 0.3 })

    // One request for the whole section, not one per control.
    await waitFor(() =>
      expect(putBody("/config/feature-flags")).toEqual({
        ppr_enabled: true,
        w_ppr: 0.3,
      }),
    )
    const puts = vi
      .mocked(apiFetch)
      .mock.calls.filter(
        ([path, init]) =>
          path === "/config/feature-flags" &&
          (init as RequestInit | undefined)?.method === "PUT",
      )
    expect(puts).toHaveLength(1)
  })

  it("carries the ladder's committed/effective split, not just the number typed", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() =>
      expect(result.current.corroboration.params.length).toBe(3),
    )

    const param = (name: string) =>
      result.current.corroboration.params.find((p) => p.name === name)
    // The whole reason the door answers with a report: showing 1 here would
    // tell an operator the ladder promotes at one origin. It promotes at two.
    expect(param("n_diverse")?.committed).toBe(1)
    expect(param("n_diverse")?.effective).toBe(2)
    expect(param("n_diverse")?.state).toBe("clamped")
    expect(param("n_diverse")?.note).toMatch(/recorded measurement/)

    expect(param("time_gap_days")?.state).toBe("honoured")
    expect(param("n_default")?.state).toBe("default")
    expect(result.current.corroboration.rowPresent).toBe(true)
  })

  it("saveLadder PUTs every edited threshold in one request", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.saveLadder({ n_default: 5, time_gap_days: 14 })

    await waitFor(() =>
      expect(putBody("/config/verification-ladder")).toEqual({
        n_default: 5,
        time_gap_days: 14,
      }),
    )
  })

  it("a null in the ladder patch clears that commitment back to its floor", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.saveLadder({ time_gap_days: null })

    await waitFor(() =>
      expect(putBody("/config/verification-ladder")).toEqual({
        time_gap_days: null,
      }),
    )
  })

  it("exposes the four pipeline/embedding tunables with their API bounds", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.tunables.length).toBe(4))

    const tunable = (key: string) =>
      result.current.tunables.find((t) => t.key === key)
    expect(tunable("pipeline_concurrency")?.value).toBe(5)
    expect(tunable("pipeline_concurrency")?.source).toBe("default")
    // Mirrors FeatureFlagsUpdate's Field(ge=1, le=20) so the field refuses
    // locally exactly what the API would 422 on.
    expect(tunable("pipeline_concurrency")?.min).toBe(1)
    expect(tunable("pipeline_concurrency")?.max).toBe(20)
    expect(tunable("entity_cache_ttl_minutes")?.max).toBe(1440)
  })

  it("saves every edited tunable in one request", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.saveFlags("tunables", {
      pipeline_concurrency: 8,
      embedding_batch_size: 40,
    })

    await waitFor(() =>
      expect(putBody("/config/feature-flags")).toEqual({
        pipeline_concurrency: 8,
        embedding_batch_size: 40,
      }),
    )
  })

  it("serves the live classification areas, never a hardcoded list", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.availableAreas.length).toBe(2))

    expect(apiFetch).toHaveBeenCalledWith("/config/classification-areas")
    expect(result.current.availableAreas.map((a) => a.key)).toEqual([
      "general",
      "technical",
    ])
    expect(result.current.classificationMode).toBe("simple")
  })

  it("serves the label space the backend resolved, never a client re-derivation", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() =>
      expect(result.current.classificationLabels.length).toBe(2),
    )
    expect(result.current.classificationLabels.map((l) => l.name)).toEqual([
      "fact",
      "decision",
    ])
    // Simple mode: the merge function returns SIMPLE_TYPES and never reads the
    // enabled areas, so eleven checkboxes change nothing and the UI has to say
    // so rather than let the operator discover it.
    expect(result.current.classificationAreasApply).toBe(false)
  })

  it("reports a write as in flight only for the section being written", async () => {
    let release: (v: unknown) => void = () => {}
    const pending = new Promise((r) => {
      release = r
    })
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/config/feature-flags" && init?.method === "PUT") {
        return pending.then(() => FEATURE_FLAGS_FIXTURE)
      }
      if (path === "/config/feature-flags") return Promise.resolve(FEATURE_FLAGS_FIXTURE)
      if (path === "/config/repo-allowlist") return Promise.resolve({ patterns: [] })
      if (path === "/config/verification-ladder") return Promise.resolve(LADDER_FIXTURE)
      if (path === "/config/classification-areas") return Promise.resolve(AREAS_FIXTURE)
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })

    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(result.current.isSaving("arms")).toBe(false)

    act(() => result.current.saveFlags("arms", { w_heat: 0.5 }))
    await waitFor(() => expect(result.current.isSaving("arms")).toBe(true))
    // One shared mutation object serves every section, so its own isPending
    // would light up the whole tab. Only the saving section may report.
    expect(result.current.isSaving("tunables")).toBe(false)

    await act(async () => {
      release(null)
      await pending
    })
    await waitFor(() => expect(result.current.isSaving("arms")).toBe(false))
  })

  it("stops reporting in flight when the write fails", async () => {
    let reject: (e: unknown) => void = () => {}
    const failing = new Promise((_, r) => {
      reject = r
    })
    vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
      if (path === "/config/feature-flags" && init?.method === "PUT") return failing
      if (path === "/config/feature-flags") return Promise.resolve(FEATURE_FLAGS_FIXTURE)
      if (path === "/config/repo-allowlist") return Promise.resolve({ patterns: [] })
      if (path === "/config/verification-ladder") return Promise.resolve(LADDER_FIXTURE)
      if (path === "/config/classification-areas") return Promise.resolve(AREAS_FIXTURE)
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })

    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    act(() =>
      result.current.saveFlags("classification", {
        classification_mode: "expanded",
      }),
    )
    await waitFor(() =>
      expect(result.current.isSaving("classification")).toBe(true),
    )

    // A spinner that never stops is worse than no spinner: it reads as a save
    // still in progress forever.
    await act(async () => {
      reject(new Error("boom"))
      await failing.catch(() => {})
    })
    await waitFor(() =>
      expect(result.current.isSaving("classification")).toBe(false),
    )
    // The section dialog has closed by now; the refusal has to be said
    // somewhere, or the old value just reappears.
    expect(toast.error).toHaveBeenCalledWith("Not saved: boom")
  })

  it("gives w_context_boost a real description, not its own flag name", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    // The fallback in `armFrom` is the flag name, so a missing meta entry
    // renders as a "description" that says nothing. It had no entry until
    // 2026-08-21.
    expect(result.current.contextBoost.desc).not.toBe("w_context_boost")
    expect(result.current.contextBoost.desc).toMatch(/context conditions/)
  })

  it("saveFlags PUTs the section patch to /config/feature-flags, never the demo store", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.saveFlags("arms", { w_importance: 0.5, w_heat: 0.2 })

    await waitFor(() =>
      expect(putBody("/config/feature-flags")).toEqual({
        w_importance: 0.5,
        w_heat: 0.2,
      }),
    )
  })

  it("saveAllowlist PUTs to /config/repo-allowlist", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.saveAllowlist(["github.com/darkraise/*", "*.forge.internal.example"])

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/config/repo-allowlist",
        expect.objectContaining({ method: "PUT" }),
      ),
    )
    const call = vi
      .mocked(apiFetch)
      .mock.calls.find(
        ([path, init]) =>
          path === "/config/repo-allowlist" &&
          (init as RequestInit | undefined)?.method === "PUT",
      )
    const body = JSON.parse((call![1] as RequestInit).body as string)
    expect(body).toEqual({
      patterns: ["github.com/darkraise/*", "*.forge.internal.example"],
    })
  })
})

describe("FlagsTab — the ranking dialog enforces the server's ranges", () => {
  afterEach(() => vi.clearAllMocks())

  it("shows each arm's range, and refuses a value outside it before saving", async () => {
    const bounds = { min: 0, max: 5 }
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/config/feature-flags")
        return Promise.resolve({
          ...FEATURE_FLAGS_FIXTURE,
          numeric_bounds: {
            confidence_rank_gamma: bounds,
            w_importance: bounds,
            w_heat: bounds,
            w_recency: bounds,
            w_context_boost: bounds,
          },
        })
      if (path === "/config/verification-ladder")
        return Promise.resolve(LADDER_FIXTURE)
      if (path === "/config/classification-areas")
        return Promise.resolve(AREAS_FIXTURE)
      if (path === "/config/repo-allowlist")
        return Promise.resolve({ patterns: [] })
      return Promise.resolve({ jobs: [] })
    })
    render(<FlagsTab />, { wrapper })
    const heading = await waitFor(() => {
      const h = screen
        .getAllByRole("heading", { level: 3 })
        .find((el) => el.textContent === "ranking arms")
      if (!h) throw new Error("no ranking arms card yet")
      return h
    })
    fireEvent.click(
      within(heading.closest(".dr-card-header") as HTMLElement).getByRole(
        "button",
        { name: /Edit/ },
      ),
    )
    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getAllByText("0 to 5").length).toBe(4)

    const field = within(dialog).getByLabelText("confidence_rank_gamma")
    fireEvent.change(field, { target: { value: "10" } })
    fireEvent.blur(field)

    expect(
      await within(dialog).findByText("Enter a value from 0 to 5."),
    ).toBeInTheDocument()
    expect(within(dialog).getByRole("button", { name: "Save" })).toBeDisabled()
    // The row no longer claims an effect the save cannot have.
    expect(within(dialog).getAllByText("inactive").length).toBe(3)
    expect(within(dialog).queryByText("active")).not.toBeInTheDocument()
  })
})
