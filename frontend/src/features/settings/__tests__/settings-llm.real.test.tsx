import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

import { toast } from "darkraise-ui/components/sonner"
import { apiFetch } from "@/lib/api"
import { useLLMTabBinding } from "../use-llm-tab-binding"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("useLLMTabBinding (DEMO off — real /config/llm)", () => {
  afterEach(() => vi.clearAllMocks())

  it("maps the six-purpose wire response into purpose cards and never calls the demo store", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      embedding: {
        base_url: "http://localhost:11434/v1",
        model: "qwen3-embedding:0.6b",
        api_key: null,
        dimensions: 1024,
        reasoning: false,
        api_kind: "ollama",
        params: {},
      },
      classification: {
        base_url: "http://localhost:11434/v1",
        model: "qwen2.5:3b",
        api_key: null,
        dimensions: null,
        reasoning: false,
        api_kind: "ollama",
        params: { temperature: 0 },
      },
    })

    const { result } = renderHook(() => useLLMTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(apiFetch).toHaveBeenCalledWith("/config/llm")
    const embedding = result.current.purposes.find(
      (p) => p.purpose === "embedding",
    )
    expect(embedding?.model).toBe("qwen3-embedding:0.6b")
    expect(embedding?.dimensions).toBe(1024)
    // No classifier_kind on the wire yet — defaults to "llm", never a crash.
    expect(result.current.classifierKind).toBe("llm")
    // No backend table for the code-summarization sub-buckets yet.
    expect(result.current.buckets).toBeNull()
    expect(result.current.saveCodeBucket).toBeNull()
  })

  it("reports a refused save as a failure and never as saved", async () => {
    vi.mocked(apiFetch).mockImplementation(async (_path, options) => {
      if (options?.method === "POST") {
        throw new Error("verification-judge serves the verification purpose only")
      }
      return {}
    })
    const { result } = renderHook(() => useLLMTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.savePurpose("reasoning", { provider_name: "verification-judge" })

    await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1))
    expect(vi.mocked(toast.error).mock.calls[0]?.[1]).toEqual({
      description: "verification-judge serves the verification purpose only",
    })
    expect(toast.success).not.toHaveBeenCalled()
  })

  it("announces a save only once the server has accepted it", async () => {
    vi.mocked(apiFetch).mockResolvedValue({})
    const { result } = renderHook(() => useLLMTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.setClassifierKind("llm")

    await waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1))
    expect(toast.error).not.toHaveBeenCalled()
  })

  it("save posts a wire patch to /config/llm, not to the demo store", async () => {
    vi.mocked(apiFetch).mockResolvedValue({})
    const { result } = renderHook(() => useLLMTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.savePurpose("extraction", {
      model: "gpt-4o-mini",
      params: '{"temperature": 0}',
    })

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/config/llm",
        expect.objectContaining({ method: "POST" }),
      ),
    )
    const call = vi
      .mocked(apiFetch)
      .mock.calls.find(([, init]) => (init as RequestInit | undefined)?.method === "POST")
    expect(call).toBeDefined()
    const body = JSON.parse((call![1] as RequestInit).body as string)
    expect(body.extraction.model).toBe("gpt-4o-mini")
    expect(body.extraction.params).toEqual({ temperature: 0 })
  })

  // T2.106: this is the live-wire proof, not just the demo fixture — the
  // real /config/llm response drives which array `synthesis` lands in.
  it("maps synthesis into the editable purposes, not tierCPurposes, over the real wire", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      synthesis: {
        base_url: "http://localhost:11434/v1",
        model: "qwen2.5:3b",
        api_key: null,
        dimensions: null,
        reasoning: false,
        api_kind: "ollama",
        params: { temperature: 0.3 },
      },
      verification: {
        base_url: "http://localhost:11434/v1",
        model: "qwen2.5:3b",
        api_key: null,
        dimensions: null,
        reasoning: false,
        api_kind: "ollama",
        params: {},
      },
    })

    const { result } = renderHook(() => useLLMTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    const synthesis = result.current.purposes.find((p) => p.purpose === "synthesis")
    expect(synthesis).toBeDefined()
    expect(synthesis?.model).toBe("qwen2.5:3b")

    expect(result.current.tierCPurposes.map((p) => p.purpose)).toEqual([
      "verification",
    ])
  })

  it("synthesis saves through the same wire as any live purpose, over the real wire", async () => {
    vi.mocked(apiFetch).mockResolvedValue({})
    const { result } = renderHook(() => useLLMTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.savePurpose("synthesis", { model: "qwen2.5:7b" })

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/config/llm",
        expect.objectContaining({ method: "POST" }),
      ),
    )
    const call = vi
      .mocked(apiFetch)
      .mock.calls.find(([, init]) => (init as RequestInit | undefined)?.method === "POST")
    expect(call).toBeDefined()
    const body = JSON.parse((call![1] as RequestInit).body as string)
    expect(body.synthesis.model).toBe("qwen2.5:7b")
    // savePurpose's type signature does not admit "verification" — proven
    // at compile time (LLMPurposeName), not re-proven here at runtime.
  })

  it("carries provider_name through the binding instead of connection fields", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      extraction: {
        provider_name: "ollama-local",
        base_url: "http://localhost:11434/v1",
        model: "qwen2.5:3b",
        api_key: null,
        dimensions: null,
        reasoning: false,
        api_kind: "openai",
        params: {},
      },
    })
    const { result } = renderHook(() => useLLMTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    const extraction = result.current.purposes.find((p) => p.purpose === "extraction")
    expect(extraction?.provider_name).toBe("ollama-local")
  })

  it("saves a provider change and never sends a connection field", async () => {
    vi.mocked(apiFetch).mockResolvedValue({})
    const { result } = renderHook(() => useLLMTabBinding(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    result.current.savePurpose("extraction", { provider_name: "my-ds", model: "m" })

    // The save's own onSuccess invalidates and refetches this same query, so
    // the mock's most recent call can be that refetch GET rather than the
    // save's POST — find the POST explicitly instead of assuming call order.
    await waitFor(() => {
      const call = vi
        .mocked(apiFetch)
        .mock.calls.find(([, init]) => (init as RequestInit | undefined)?.method === "POST")
      expect(call).toBeDefined()
      const body = JSON.parse((call![1] as RequestInit).body as string)
      expect(body.extraction).toEqual({ provider_name: "my-ds", model: "m" })
      expect(body.extraction).not.toHaveProperty("base_url")
      expect(body.extraction).not.toHaveProperty("api_kind")
      expect(body.extraction).not.toHaveProperty("api_key")
    })
  })
})
