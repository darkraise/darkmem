import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { renderHook, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

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
})
