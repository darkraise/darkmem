import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen } from "@testing-library/react"
import { RouterProvider, createMemoryHistory, createRouter } from "@tanstack/react-router"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
// The full route tree imports the graph pages, whose renderer reads WebGL
// globals at module scope; nothing here draws a graph.
vi.hoisted(() => {
  const g = globalThis as Record<string, unknown>
  g.WebGL2RenderingContext ??= class {}
  g.WebGLRenderingContext ??= class {}
})

import { routeTree } from "@/routeTree.gen"
import { json, routeFetch } from "@/lib/__tests__/session-test-kit"
import { StepLLM } from "../components/StepLLM"
import { useSetupWizardStore } from "../setupWizardStore"

function renderAt(path: string) {
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: [path] }),
  })
  return render(<RouterProvider router={router} />)
}

beforeEach(() => {
  localStorage.clear()
  sessionStorage.clear()
  useSetupWizardStore.getState().reset()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("setup status", () => {
  it("a server error shows an error with Retry, not the wizard", async () => {
    routeFetch({
      "/setup/status": [
        json({ detail: "database unavailable" }, 500),
        json({ initialized: false }),
      ],
    })
    renderAt("/setup")

    expect(await screen.findByText("Setup status could not be read")).toBeInTheDocument()
    expect(screen.queryByLabelText("Admin password")).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Retry" }))
    expect(await screen.findByLabelText("Admin password")).toBeInTheDocument()
  })

  it("an uninitialized instance shows the wizard", async () => {
    routeFetch({ "/setup/status": [json({ initialized: false })] })
    renderAt("/setup")
    expect(await screen.findByLabelText("Admin password")).toBeInTheDocument()
  })

  it("vendor API keys never reach localStorage", () => {
    routeFetch({
      "/setup/llm/probe-models": [json({ models: [], fetched_via: "openai", error: null })],
    })
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={qc}>
        <StepLLM />
      </QueryClientProvider>,
    )
    fireEvent.click(screen.getByRole("button", { name: "Add provider" }))
    fireEvent.change(screen.getByLabelText("new provider name"), {
      target: { value: "user-openai" },
    })
    fireEvent.click(screen.getByRole("button", { name: "Create" }))
    const secret = "sk-test-0123456789abcdef"
    fireEvent.change(screen.getByLabelText("user-openai api_key"), {
      target: { value: secret },
    })

    const { setStep } = useSetupWizardStore.getState()
    setStep(3)
    setStep(4)

    const stored = [localStorage, sessionStorage].flatMap((storage) =>
      Array.from({ length: storage.length }, (_, i) => storage.getItem(storage.key(i)!) ?? ""),
    )
    expect(localStorage.getItem("darkmem-setup-wizard")).toContain("user-openai")
    expect(stored.some((value) => value.includes(secret))).toBe(false)
    expect(useSetupWizardStore.getState().llm.providers[0]?.api_key).toBe(secret)
  })
})
