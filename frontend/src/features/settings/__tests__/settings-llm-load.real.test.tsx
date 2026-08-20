import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import type { LlmConfigResponse } from "@/hooks/api"
import { LLMTab } from "../components/llm-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

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

// Typed as the eight-purpose `LlmConfigResponse` shape, but — mirroring the
// hook-level fixture above it — only populates the one purpose each test
// needs: every other card resolves to the empty/default fallback, has no
// provider_name, and therefore never auto-probes (so its model field stays
// silent instead of racing the one card under test for the same error text).
const PURPOSES_FIXTURE: LlmConfigResponse = {
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
}

describe("LLMTab first paint (DEMO off)", () => {
  afterEach(() => vi.clearAllMocks())

  // The cards seeded their editable draft with `useState(() => toDraft(purpose))`
  // while the query was still in flight, so they froze the empty placeholder
  // the binding builds from `query.data?.[p]` and never re-read it. The fields
  // stayed blank until the tab was unmounted and remounted, which is what
  // switching away and back does.
  it("shows the loaded values without needing a remount", async () => {
    vi.mocked(apiFetch).mockImplementation(async (path: string) =>
      path.endsWith("/probe-models") ? { models: [], fetched_via: "", error: null } : CONFIG,
    )
    render(<LLMTab />, { wrapper })

    await waitFor(() =>
      expect(screen.getByDisplayValue("deepseek-v4-flash")).toBeInTheDocument(),
    )
    expect(screen.getByText("deepseek-primary")).toBeInTheDocument()
  })

  // The control read `query.data?.classification?.classifier_kind`, which the
  // response schema did not carry, so it always resolved to the "llm" default
  // no matter what the database held.
  it("reflects the served classifier_kind rather than the fallback", async () => {
    vi.mocked(apiFetch).mockImplementation(async (path: string) =>
      path.endsWith("/probe-models") ? { models: [], fetched_via: "", error: null } : CONFIG,
    )
    render(<LLMTab />, { wrapper })

    await waitFor(() =>
      expect(screen.getByDisplayValue("deepseek-v4-flash")).toBeInTheDocument(),
    )
    // Icon-only segments carry no text, so the aria-label the tooltip
    // mirrors is the only name to address them by.
    expect(
      screen.getByRole("radio", { name: "In-process classifier" }),
    ).toBeChecked()
    expect(
      screen.getByRole("radio", { name: "LLM-backed classifier" }),
    ).not.toBeChecked()
  })

  it("offers probed models but accepts one the probe never returned", async () => {
    vi.mocked(apiFetch).mockImplementation(async (path: string) =>
      path.endsWith("/probe-models")
        ? { models: ["a", "b"], fetched_via: "openai_compat:/v1/models", error: null }
        : PURPOSES_FIXTURE,
    )
    render(<LLMTab />, { wrapper })
    const field = await screen.findByLabelText("extraction model")
    await userEvent.clear(field)
    await userEvent.type(field, "c")
    expect(field).toHaveValue("c")
  })

  it("keeps the model field usable when the probe fails", async () => {
    vi.mocked(apiFetch).mockImplementation(async (path: string) =>
      path.endsWith("/probe-models")
        ? { models: [], fetched_via: "openai_compat:/v1/models", error: "HTTP 401" }
        : PURPOSES_FIXTURE,
    )
    render(<LLMTab />, { wrapper })
    expect(await screen.findByText(/HTTP 401/)).toBeInTheDocument()
    expect(screen.getByLabelText("extraction model")).toBeEnabled()
  })
})
