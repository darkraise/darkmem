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
  ],
  measured_flags: [],
}

function mockApiFetch() {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path === "/config/feature-flags") return Promise.resolve(FEATURE_FLAGS_FIXTURE)
    if (path === "/jobs") return Promise.resolve({ jobs: [] })
    if (path === "/config/repo-allowlist") {
      return Promise.resolve({ patterns: ["github.com/darkraise/*"] })
    }
    return Promise.reject(new Error(`unexpected apiFetch(${path})`))
  })
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
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    const reranker = result.current.behavioralFlags.find(
      (f) => f.key === "reranker_enabled",
    )
    expect(reranker?.unmeasured).toBe(false)
  })

  it("reports graph augmentation and corroboration as unavailable — no backend row exists", async () => {
    mockApiFetch()
    const { result } = renderHook(() => useFlagsTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(result.current.graphAugmentationAvailable).toBe(false)
    expect(result.current.corroborationAvailable).toBe(false)
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
