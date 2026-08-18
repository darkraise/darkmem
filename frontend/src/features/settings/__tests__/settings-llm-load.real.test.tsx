import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { LLMTab } from "../components/llm-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const CONFIG = {
  classification: {
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

describe("LLMTab first paint (DEMO off)", () => {
  afterEach(() => vi.clearAllMocks())

  // The cards seeded their editable draft with `useState(() => toDraft(purpose))`
  // while the query was still in flight, so they froze the empty placeholder
  // the binding builds from `query.data?.[p]` and never re-read it. The fields
  // stayed blank until the tab was unmounted and remounted, which is what
  // switching away and back does.
  it("shows the loaded values without needing a remount", async () => {
    vi.mocked(apiFetch).mockResolvedValue(CONFIG)
    render(<LLMTab />, { wrapper })

    await waitFor(() =>
      expect(screen.getByDisplayValue("deepseek-v4-flash")).toBeInTheDocument(),
    )
    expect(screen.getByDisplayValue("https://api.deepseek.com/v1")).toBeInTheDocument()
  })

  // The control read `query.data?.classification?.classifier_kind`, which the
  // response schema did not carry, so it always resolved to the "llm" default
  // no matter what the database held.
  it("reflects the served classifier_kind rather than the fallback", async () => {
    vi.mocked(apiFetch).mockResolvedValue(CONFIG)
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
})
