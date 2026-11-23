import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

const flag = vi.hoisted(() => ({ demo: false }))
vi.mock("@/lib/demo-flag", () => ({
  get DEMO() {
    return flag.demo
  },
}))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { LLMTab } from "./llm-tab"

const NOTICE = "Local classifier unavailable, using the LLM classifier"

const CONFIG = {
  classification: {
    provider_name: "deepseek-primary",
    base_url: "https://api.deepseek.com/v1",
    model: "deepseek-v4-flash",
    api_key: "***",
    dimensions: null,
    reasoning: false,
    api_kind: "deepseek",
    params: {},
    classifier_kind: "local",
  },
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function serveHealth(classifierUnavailable: boolean, pipelineState = "ok") {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    if (String(input) === "/health") {
      return new Response(
        JSON.stringify({
          status: "ok",
          pipeline: pipelineState === "ok",
          services: { pgvector: true, llm: true },
          classifier_unavailable: classifierUnavailable,
          pipeline_state: pipelineState,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      )
    }
    return new Response("{}", { status: 404 })
  })
}

function healthCalls(fetchSpy: ReturnType<typeof serveHealth>) {
  return fetchSpy.mock.calls.filter((c) => String(c[0]) === "/health")
}

afterEach(() => {
  flag.demo = false
  vi.restoreAllMocks()
  vi.mocked(apiFetch).mockReset()
})

describe("the classification purpose's classifier notice", () => {
  it("shows the unavailable line", async () => {
    vi.mocked(apiFetch).mockImplementation(async (path: string) =>
      path.endsWith("/probe-models")
        ? { models: [], fetched_via: "", error: null }
        : CONFIG,
    )
    let fetchSpy = serveHealth(true)
    const { unmount } = render(<LLMTab />, { wrapper })
    expect(await screen.findByText(NOTICE)).toBeInTheDocument()
    unmount()
    fetchSpy.mockRestore()

    fetchSpy = serveHealth(false)
    const second = render(<LLMTab />, { wrapper })
    await waitFor(() => expect(healthCalls(fetchSpy).length).toBeGreaterThan(0))
    await waitFor(() =>
      expect(screen.getAllByText("deepseek-v4-flash").length).toBeGreaterThan(0),
    )
    expect(screen.queryByText(NOTICE)).not.toBeInTheDocument()
    second.unmount()
    fetchSpy.mockRestore()

    flag.demo = true
    fetchSpy = serveHealth(true)
    render(<LLMTab />, { wrapper })
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(healthCalls(fetchSpy)).toHaveLength(0)
    expect(screen.queryByText(NOTICE)).not.toBeInTheDocument()
  })
})

const STOPPED =
  "Processing is stopped: the model setup failed at startup. Captures are still queued. Save a working model configuration to start it."

describe("the stopped-processing banner", () => {
  function serveConfig() {
    vi.mocked(apiFetch).mockImplementation(async (path: string) =>
      path.endsWith("/probe-models")
        ? { models: [], fetched_via: "", error: null }
        : CONFIG,
    )
  }

  it("shows the stopped-processing banner while the boot setup failed", async () => {
    serveConfig()
    serveHealth(false, "failed_at_boot")
    render(<LLMTab />, { wrapper })
    expect(await screen.findByText(STOPPED)).toBeInTheDocument()
  })

  it.each(["ok", "not_configured", "read_only", "unknown"])(
    "shows no banner while pipeline_state is %s",
    async (state) => {
      serveConfig()
      const fetchSpy = serveHealth(false, state)
      render(<LLMTab />, { wrapper })
      await waitFor(() => expect(healthCalls(fetchSpy).length).toBeGreaterThan(0))
      await waitFor(() =>
        expect(screen.getAllByText("deepseek-v4-flash").length).toBeGreaterThan(0),
      )
      expect(screen.queryByText(STOPPED)).not.toBeInTheDocument()
    },
  )

  it("makes no health request in demo mode", async () => {
    flag.demo = true
    const fetchSpy = serveHealth(false, "failed_at_boot")
    render(<LLMTab />, { wrapper })
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(healthCalls(fetchSpy)).toHaveLength(0)
    expect(screen.queryByText(STOPPED)).not.toBeInTheDocument()
  })
})
