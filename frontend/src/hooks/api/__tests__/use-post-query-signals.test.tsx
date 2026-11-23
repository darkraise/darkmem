import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { usePaginatedSearch } from "../use-memory-api"
import { useSubjectTotals } from "../use-usage-api"
import { useSetupProviderModels } from "../use-setup-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const never = () => new Promise<never>(() => {})

function signalOf(init: unknown): AbortSignal | undefined {
  return (init as RequestInit | undefined)?.signal ?? undefined
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetch).mockImplementation(never)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("POST-backed queries pass their abort signal", () => {
  it("the paginated memory search passes its abort signal", async () => {
    const { rerender } = renderHook(
      ({ query }) => usePaginatedSearch({ query }),
      { wrapper, initialProps: { query: "redis" } },
    )
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1))
    const first = signalOf(vi.mocked(apiFetch).mock.calls[0]![1])
    expect(first).toBeInstanceOf(AbortSignal)
    expect(first!.aborted).toBe(false)

    rerender({ query: "redis cache" })
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(first!.aborted).toBe(true))
  })

  it("the subject totals read passes its abort signal", async () => {
    const { rerender } = renderHook(
      ({ ids }) => useSubjectTotals("document", ids),
      { wrapper, initialProps: { ids: ["d1"] } },
    )
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1))
    const first = signalOf(vi.mocked(apiFetch).mock.calls[0]![1])
    expect(first).toBeInstanceOf(AbortSignal)

    rerender({ ids: ["d2"] })
    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(first!.aborted).toBe(true))
  })

  it("the setup model probe passes its abort signal", async () => {
    const fetchMock = vi.fn((_input: RequestInfo | URL, _init?: RequestInit) => never())
    vi.stubGlobal("fetch", fetchMock)
    const { rerender } = renderHook(
      ({ base_url }) =>
        useSetupProviderModels({ api_kind: "ollama", base_url, api_key: null }),
      { wrapper, initialProps: { base_url: "http://a:11434" } },
    )
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
    const first = signalOf(fetchMock.mock.calls[0]![1])
    expect(first).toBeInstanceOf(AbortSignal)

    rerender({ base_url: "http://b:11434" })
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(first!.aborted).toBe(true))
  })
})
