import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { useFlagsTabBinding } from "../use-flags-tab-binding"

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
      note: "1 is below the floor of 2 and no T2.40 measurement names this parameter, so the ladder is running at 2.",
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

  it("maps the wire response into fusion arms with the backend's own activation ids", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(apiFetch).toHaveBeenCalledWith("/config/feature-flags")

    const importance = result.current.fusionArms.find(
      (a) => a.key === "w_importance",
    )
    expect(importance?.activatesWith).toBe("T2.30")
    expect(importance?.value).toBe(0)
    expect(importance?.source).toBe("default")

    const heat = result.current.fusionArms.find((a) => a.key === "w_heat")
    expect(heat?.activatesWith).toBe("T2.31")

    const confidence = result.current.fusionArms.find(
      (a) => a.key === "confidence_rank_gamma",
    )
    // Already live — no activation id, but non-default so it reads "override".
    expect(confidence?.activatesWith).toBeUndefined()
    expect(confidence?.source).toBe("override")
  })

  it("marks every measurable-but-unmeasured flag from measured_flags, never a hardcoded list", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    const importance = result.current.fusionArms.find(
      (a) => a.key === "w_importance",
    )
    expect(importance?.unmeasured).toBe(true)
    expect(result.current.contextBoost.unmeasured).toBe(true)

    const reranker = result.current.behavioralFlags.find(
      (f) => f.key === "reranker_enabled",
    )
    expect(reranker?.unmeasured).toBe(true)

    const hybrid = result.current.behavioralFlags.find(
      (f) => f.key === "hybrid_search_enabled",
    )
    expect(hybrid?.unmeasured).toBe(false)
  })

  it("clears the unmeasured badge once a flag is in measured_flags", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/config/feature-flags") {
        return Promise.resolve({
          ...FEATURE_FLAGS_FIXTURE,
          measured_flags: ["reranker_enabled"],
        })
      }
      if (path === "/jobs") return Promise.resolve({ jobs: [] })
      if (path === "/config/repo-allowlist") return Promise.resolve({ patterns: [] })
      if (path === "/config/verification-ladder") return Promise.resolve(LADDER_FIXTURE)
      if (path === "/config/classification-areas") return Promise.resolve(AREAS_FIXTURE)
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    const reranker = result.current.behavioralFlags.find(
      (f) => f.key === "reranker_enabled",
    )
    expect(reranker?.unmeasured).toBe(false)
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
    expect(graph("community_injection_enabled")?.no_weight_note).toMatch(
      /no paired RRF weight/,
    )
  })

  it("carries the graph channels' activation id and unmeasured badge", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.graphFlags.length).toBe(3))

    for (const flag of result.current.graphFlags) {
      expect(flag.activatesWith).toBe("T2.50")
      expect(flag.unmeasured).toBe(true)
    }
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

  it("setGraphFlag PUTs to /config/feature-flags, never the demo store", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.setGraphFlag("ppr_enabled", true)

    await waitFor(() => expect(putBody("/config/feature-flags")).toEqual({
      ppr_enabled: true,
    }))
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
    expect(param("n_diverse")?.note).toMatch(/T2\.40/)

    expect(param("time_gap_days")?.state).toBe("honoured")
    expect(param("n_default")?.state).toBe("default")
    expect(result.current.corroboration.rowPresent).toBe(true)
    expect(result.current.corroboration.measurementTask).toBe("T2.40")
  })

  it("saveCorroboration PUTs one threshold to /config/verification-ladder", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.saveCorroboration("n_default", 5)

    await waitFor(() =>
      expect(putBody("/config/verification-ladder")).toEqual({ n_default: 5 }),
    )
  })

  it("saveCorroboration(null) clears a commitment back to its floor", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.saveCorroboration("time_gap_days", null)

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

  it("saveTunable PUTs a single-key patch to /config/feature-flags", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.saveTunable("pipeline_concurrency", 8)

    await waitFor(() =>
      expect(putBody("/config/feature-flags")).toEqual({
        pipeline_concurrency: 8,
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

  it("gives w_context_boost a real description, not its own flag name", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    // The fallback in `armFrom` is the flag name, so a missing meta entry
    // renders as a "description" that says nothing. It had no entry until
    // 2026-08-21.
    expect(result.current.contextBoost.desc).not.toBe("w_context_boost")
    expect(result.current.contextBoost.desc).toMatch(/MATCH/)
  })

  it("saveArm PUTs a single-key patch to /config/feature-flags, never the demo store", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.saveArm("w_importance", 0.5)

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/config/feature-flags",
        expect.objectContaining({ method: "PUT" }),
      ),
    )
    const call = vi
      .mocked(apiFetch)
      .mock.calls.find(([, init]) => (init as RequestInit | undefined)?.method === "PUT")
    const body = JSON.parse((call![1] as RequestInit).body as string)
    expect(body).toEqual({ w_importance: 0.5 })
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
