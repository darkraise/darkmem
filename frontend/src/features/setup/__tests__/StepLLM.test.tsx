import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { StepLLM } from "../components/StepLLM"
import { useSetupWizardStore } from "../setupWizardStore"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  useSetupWizardStore.getState().reset()
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        models: ["gpt-4o-mini", "gpt-4o"],
        fetched_via: "openai",
        error: null,
      }),
    }),
  )
})

afterEach(() => {
  vi.unstubAllGlobals()
})

const addProvider = (name: string) => {
  fireEvent.click(screen.getByRole("button", { name: "Add provider" }))
  fireEvent.change(screen.getByLabelText("new provider name"), {
    target: { value: name },
  })
  fireEvent.click(screen.getByRole("button", { name: "Create" }))
}

describe("StepLLM", () => {
  it("shows an empty state until a provider is defined", () => {
    render(<StepLLM />, { wrapper })
    expect(screen.getByText("No providers defined")).toBeInTheDocument()
  })

  it("adding a provider lists it and clears the empty state", () => {
    render(<StepLLM />, { wrapper })
    addProvider("user-openai")
    expect(screen.queryByText("No providers defined")).not.toBeInTheDocument()
    expect(screen.getByText("user-openai")).toBeInTheDocument()
  })

  it("Test hits the unauthenticated wizard probe and reports the count", async () => {
    render(<StepLLM />, { wrapper })
    addProvider("user-openai")
    // A new provider probes on its own; Test re-runs that probe.
    fireEvent.click(await screen.findByRole("button", { name: "Test" }))
    await waitFor(() => expect(screen.getByText("2 models")).toBeInTheDocument())
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/setup/probe-models",
      expect.objectContaining({ method: "POST" }),
    )
  })

  it("reports a provider's probe failure once, on the provider, in plain words", async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        models: [],
        fetched_via: "openai",
        error: "API key required for api_kind='openai'",
      }),
    } as Response)
    render(<StepLLM />, { wrapper })
    addProvider("user-openai")
    for (const purpose of ["extraction", "classification", "reasoning"]) {
      useSetupWizardStore
        .getState()
        .setLlmPurpose(purpose as "extraction", { provider_name: "user-openai" })
    }
    expect(
      await screen.findByText("This provider needs an API key."),
    ).toBeInTheDocument()
    await waitFor(() =>
      expect(
        screen.getAllByText("This provider needs an API key."),
      ).toHaveLength(1),
    )
    expect(screen.queryByText(/api_kind=/)).not.toBeInTheDocument()
    // One request for the provider, however many purposes picked it.
    expect(
      vi
        .mocked(fetch)
        .mock.calls.filter(([url]) => String(url).includes("probe-models")),
    ).toHaveLength(1)
  })

  it("refuses a provider the server would refuse, saying why", () => {
    render(<StepLLM />, { wrapper })
    fireEvent.click(screen.getByRole("button", { name: "Add provider" }))
    fireEvent.change(screen.getByLabelText("new provider name"), {
      target: { value: "my/openai" },
    })
    fireEvent.change(screen.getByLabelText("new provider base_url"), {
      target: { value: "api.openai.com" },
    })
    expect(
      screen.getByText(/Use only letters, digits, dot, dash and underscore/),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Enter an http:\/\/ or https:\/\/ address with a host/),
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Create" })).toBeDisabled()
  })

  it("marks extraction, classification and reasoning as required; the rest optional", () => {
    render(<StepLLM />, { wrapper })
    const label = (purpose: string) =>
      screen
        .getAllByText(purpose, { exact: false })
        .map((el) => el.closest(".font-medium"))
        .find((el): el is HTMLElement => el !== null)!.textContent
    expect(label("extraction")).toBe("extraction*")
    expect(label("classification")).toBe("classification*")
    expect(label("reasoning")).toBe("reasoning*")
    expect(label("embedding")).toBe("embedding")
    expect(label("summarization")).toBe("summarization")
    expect(label("reranker")).toBe("reranker")
  })
})
