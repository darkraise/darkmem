import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, renderHook, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import {
  useLlmProviders,
  useDeleteLlmProvider,
} from "@/hooks/api/use-llm-providers-api"
import { ProvidersPanel } from "../components/providers-panel"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const PROVIDERS = {
  providers: [
    {
      name: "ollama-local",
      api_kind: "openai",
      base_url: "http://localhost:11434/v1",
      api_key: null,
      used_by: ["embedding", "extraction"],
      serves_verification: false,
    },
    {
      name: "verification-judge",
      api_kind: "openai",
      base_url: "https://api.openai.com/v1",
      api_key: "***",
      used_by: ["verification"],
      serves_verification: true,
    },
  ],
}

describe("useLlmProviders (DEMO off — real /config/llm-providers)", () => {
  afterEach(() => vi.clearAllMocks())

  it("lists providers with the key masked and a usage count", async () => {
    vi.mocked(apiFetch).mockResolvedValue(PROVIDERS)
    const { result } = renderHook(() => useLlmProviders(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    expect(apiFetch).toHaveBeenCalledWith("/config/llm-providers")
    const local = result.current.data!.providers.find(
      (p) => p.name === "ollama-local",
    )!
    expect(local.used_by).toEqual(["embedding", "extraction"])
    const judge = result.current.data!.providers.find(
      (p) => p.name === "verification-judge",
    )!
    expect(judge.api_key).toBe("***")
    expect(judge.serves_verification).toBe(true)
  })

  it("surfaces the 409 when delete is blocked by a reference", async () => {
    vi.mocked(apiFetch).mockRejectedValue(
      new Error("409: provider is used by extraction"),
    )
    const { result } = renderHook(() => useDeleteLlmProvider(), { wrapper })

    result.current.mutate("ollama-local")
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error?.message).toContain("extraction")
  })
})

describe("ProvidersPanel (DEMO off — read-only rendering)", () => {
  afterEach(() => vi.clearAllMocks())

  it("freezes base_url and api_kind on the verification provider but not its key", async () => {
    vi.mocked(apiFetch).mockResolvedValue(PROVIDERS)
    render(<ProvidersPanel />, { wrapper })
    await waitFor(() =>
      expect(screen.getByLabelText("verification-judge base_url")).toBeDisabled(),
    )
    expect(screen.getByLabelText("verification-judge api_kind")).toBeDisabled()
    expect(screen.getByLabelText("verification-judge api_key")).toBeEnabled()
  })

  it("does not freeze base_url and api_kind on a non-verification provider", async () => {
    vi.mocked(apiFetch).mockResolvedValue(PROVIDERS)
    render(<ProvidersPanel />, { wrapper })
    await waitFor(() =>
      expect(screen.getByLabelText("ollama-local base_url")).toBeEnabled(),
    )
    expect(screen.getByLabelText("ollama-local api_kind")).toBeEnabled()
    expect(screen.getByLabelText("ollama-local api_key")).toBeEnabled()
  })

  it("disables delete while a purpose still references the provider", async () => {
    vi.mocked(apiFetch).mockResolvedValue(PROVIDERS)
    render(<ProvidersPanel />, { wrapper })
    await waitFor(() =>
      expect(screen.getByLabelText("Delete ollama-local")).toBeDisabled(),
    )
  })

  it("renders an empty state when no providers are configured", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ providers: [] })
    render(<ProvidersPanel />, { wrapper })
    await waitFor(() =>
      expect(screen.getByText(/No providers configured/i)).toBeInTheDocument(),
    )
  })

  it("renders a probe error inline instead of throwing", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/config/llm-providers") return Promise.resolve(PROVIDERS)
      if (path.endsWith("/probe-models")) {
        return Promise.resolve({
          models: [],
          fetched_via: "openai",
          error: "connection refused",
        })
      }
      return Promise.reject(new Error(`unexpected path ${path}`))
    })
    render(<ProvidersPanel />, { wrapper })
    await waitFor(() =>
      expect(
        screen.getByLabelText("Test connection ollama-local"),
      ).toBeInTheDocument(),
    )
    screen.getByLabelText("Test connection ollama-local").click()
    await waitFor(() =>
      expect(screen.getByText("connection refused")).toBeInTheDocument(),
    )
  })
})
