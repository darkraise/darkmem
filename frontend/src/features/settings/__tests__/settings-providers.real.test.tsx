import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import {
  fireEvent,
  render,
  renderHook,
  screen,
  waitFor,
} from "@testing-library/react"
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

// Editing now lives behind a dialog, so every field assertion opens it first.
// The assertions themselves are unchanged: what a frozen provider disables,
// and the exact body a save puts on the wire, are the same properties as
// before — only the number of clicks to reach them moved.
async function openEditor(name: string) {
  fireEvent.click(await screen.findByLabelText(`Edit ${name}`))
  return await screen.findByLabelText(`${name} base_url`)
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
    await openEditor("verification-judge")
    expect(screen.getByLabelText("verification-judge base_url")).toBeDisabled()
    expect(screen.getByLabelText("verification-judge api_kind")).toBeDisabled()
    expect(screen.getByLabelText("verification-judge api_key")).toBeEnabled()
  })

  it("does not freeze base_url and api_kind on a non-verification provider", async () => {
    vi.mocked(apiFetch).mockResolvedValue(PROVIDERS)
    render(<ProvidersPanel />, { wrapper })
    await openEditor("ollama-local")
    expect(screen.getByLabelText("ollama-local base_url")).toBeEnabled()
    expect(screen.getByLabelText("ollama-local api_kind")).toBeEnabled()
    expect(screen.getByLabelText("ollama-local api_key")).toBeEnabled()
  })

  // PUT is a full replace, so a body that omits an unchanged connection field
  // is a 422 and not a partial update. These two pin the body from the panel's
  // side; the route's own suite pins the contract they have to match.
  it("sends a full-replace body when rotating a frozen provider's key", async () => {
    vi.mocked(apiFetch).mockImplementation((_path: string, init?: RequestInit) =>
      init?.method === "PUT"
        ? Promise.resolve({ ...PROVIDERS.providers[1], no_embedding_purposes: [] })
        : Promise.resolve(PROVIDERS),
    )
    render(<ProvidersPanel />, { wrapper })
    await openEditor("verification-judge")
    fireEvent.change(screen.getByLabelText("verification-judge api_key"), {
      target: { value: "sk-rotated" },
    })
    fireEvent.click(screen.getByRole("button", { name: "Save" }))

    await waitFor(() =>
      expect(vi.mocked(apiFetch).mock.calls.some(
        ([path]) => path === "/config/llm-providers/verification-judge",
      )).toBe(true),
    )
    const call = vi.mocked(apiFetch).mock.calls.find(
      ([path]) => path === "/config/llm-providers/verification-judge",
    )!
    expect(JSON.parse((call[1] as RequestInit)!.body as string)).toEqual({
      api_kind: "openai",
      base_url: "https://api.openai.com/v1",
      api_key: "sk-rotated",
    })
  })

  it("resends the unchanged fields on an ordinary connection edit", async () => {
    vi.mocked(apiFetch).mockImplementation((_path: string, init?: RequestInit) =>
      init?.method === "PUT"
        ? Promise.resolve({ ...PROVIDERS.providers[0], no_embedding_purposes: [] })
        : Promise.resolve(PROVIDERS),
    )
    render(<ProvidersPanel />, { wrapper })
    const baseUrl = await openEditor("ollama-local")
    fireEvent.change(baseUrl, { target: { value: "http://moved:11434/v1" } })
    fireEvent.click(screen.getByRole("button", { name: "Save" }))

    await waitFor(() =>
      expect(vi.mocked(apiFetch).mock.calls.some(
        ([path]) => path === "/config/llm-providers/ollama-local",
      )).toBe(true),
    )
    const call = vi.mocked(apiFetch).mock.calls.find(
      ([path]) => path === "/config/llm-providers/ollama-local",
    )!
    expect(JSON.parse((call[1] as RequestInit)!.body as string)).toEqual({
      api_kind: "openai",
      base_url: "http://moved:11434/v1",
      api_key: "***",
    })
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

  it("switches layout and persists the choice per panel", async () => {
    vi.mocked(apiFetch).mockResolvedValue(PROVIDERS)
    const { unmount } = render(<ProvidersPanel />, { wrapper })
    await screen.findByLabelText("Edit ollama-local")

    // Icon-only segments have no text, so the tooltip label is the only
    // handle — which is exactly the part that has to keep working.
    fireEvent.click(screen.getByRole("radio", { name: "List layout" }))
    expect(screen.getByRole("radio", { name: "List layout" })).toBeChecked()
    expect(
      JSON.parse(localStorage.getItem("darkmem-llm-providers-layout") ?? "{}")
        .state.layout,
    ).toBe("list")

    // The purposes panel keeps its own key, so one panel's density is not the
    // other's.
    expect(localStorage.getItem("darkmem-llm-purposes-layout")).toBeNull()

    unmount()
    render(<ProvidersPanel />, { wrapper })
    await waitFor(() =>
      expect(screen.getByRole("radio", { name: "List layout" })).toBeChecked(),
    )
  })

  it("adds a provider through the dialog rather than an inline card", async () => {
    vi.mocked(apiFetch).mockImplementation((_path: string, init?: RequestInit) =>
      init?.method === "POST"
        ? Promise.resolve({ ...PROVIDERS.providers[0], name: "new-one" })
        : Promise.resolve(PROVIDERS),
    )
    render(<ProvidersPanel />, { wrapper })
    await screen.findByLabelText("Edit ollama-local")

    // No name field exists until the dialog is opened: the panel itself is
    // read-only.
    expect(screen.queryByLabelText("new provider name")).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: /Add provider/ }))
    fireEvent.change(await screen.findByLabelText("new provider name"), {
      target: { value: "new-one" },
    })
    fireEvent.change(screen.getByLabelText("new provider base_url"), {
      target: { value: "http://new/v1" },
    })
    fireEvent.click(screen.getByRole("button", { name: "Create" }))

    await waitFor(() => {
      const call = vi
        .mocked(apiFetch)
        .mock.calls.find(([, init]) => (init as RequestInit)?.method === "POST")
      expect(call).toBeDefined()
      expect(JSON.parse((call![1] as RequestInit).body as string)).toEqual({
        name: "new-one",
        api_kind: "openai",
        base_url: "http://new/v1",
        api_key: null,
      })
    })
  })

  it("shows no editable connection field until the editor is opened", async () => {
    vi.mocked(apiFetch).mockResolvedValue(PROVIDERS)
    render(<ProvidersPanel />, { wrapper })
    await screen.findByLabelText("Edit ollama-local")
    expect(
      screen.queryByLabelText("ollama-local base_url"),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByLabelText("ollama-local api_key"),
    ).not.toBeInTheDocument()
  })

})
