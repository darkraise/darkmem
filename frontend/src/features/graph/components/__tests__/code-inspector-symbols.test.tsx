import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { describe, it, expect, vi, beforeEach } from "vitest"

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { CodeInspectorPanel } from "../code-inspector-panel"
import type { CodeSymbolResponse } from "@/hooks/api"

const apiFetchMock = vi.mocked(apiFetch)

const SYMBOLS: CodeSymbolResponse[] = [
  {
    id: "s1",
    name: "UserService",
    kind: "class",
    file_path: "app/services/user.py",
    line_start: 10,
    line_end: 80,
    signature: null,
    docstring: null,
    visibility: "public",
    source_code: "",
    summary: null,
    enrichment_status: "completed",
  },
  {
    id: "s2",
    name: "login",
    kind: "method",
    file_path: "app/services/user.py",
    line_start: 20,
    line_end: 35,
    signature: null,
    docstring: null,
    visibility: "public",
    source_code: "",
    summary: null,
    enrichment_status: "pending",
  },
]

const NODE_COLORS: Record<string, string> = {
  class: "#aabbcc",
  method: "#112233",
}

function renderPanel(
  overrides: Partial<Parameters<typeof CodeInspectorPanel>[0]> = {},
) {
  const onSymbolSelect = vi.fn()
  const qc = new QueryClient()
  render(
    <QueryClientProvider client={qc}>
      <CodeInspectorPanel
        symbolDetail={null}
        searchResults={[]}
        fileList={[]}
        onFileSelect={vi.fn()}
        onSearchResultClick={vi.fn()}
        repoId="repo-1"
        nodeColors={NODE_COLORS}
        symbolKinds={["class", "method"]}
        onSymbolSelect={onSymbolSelect}
        {...overrides}
      />
    </QueryClientProvider>,
  )
  return { onSymbolSelect }
}

describe("CodeInspectorPanel — Symbols tab", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiFetchMock.mockResolvedValue({ items: SYMBOLS, total: 2 })
  })

  it("queries GET /code/symbols with repo_id, offset, and limit", async () => {
    const user = userEvent.setup()
    renderPanel()

    await user.click(screen.getByRole("tab", { name: /symbols/i }))

    await waitFor(() => expect(apiFetchMock).toHaveBeenCalled())
    const url = (apiFetchMock.mock.calls[0]?.[0] ?? "") as string
    expect(url).toMatch(/^\/code\/symbols\?/)
    const params = new URLSearchParams(url.split("?")[1])
    expect(params.get("repo_id")).toBe("repo-1")
    expect(params.get("offset")).toBe("0")
    expect(params.get("limit")).toBe("25")
  })

  it("renders a row per symbol with name, kind, and file path", async () => {
    const user = userEvent.setup()
    renderPanel()

    await user.click(screen.getByRole("tab", { name: /symbols/i }))

    expect(await screen.findByText("UserService")).toBeInTheDocument()
    expect(screen.getByText("login")).toBeInTheDocument()
    expect(screen.getAllByText("app/services/user.py").length).toBe(2)
    expect(screen.getByText("1-2 of 2")).toBeInTheDocument()
  })

  it("fires onSymbolSelect with the row's name and file path", async () => {
    const user = userEvent.setup()
    const { onSymbolSelect } = renderPanel()

    await user.click(screen.getByRole("tab", { name: /symbols/i }))
    await user.click(await screen.findByText("UserService"))

    expect(onSymbolSelect).toHaveBeenCalledWith(
      "UserService",
      "app/services/user.py",
    )
  })

  it("debounces the text filter into the q query param", async () => {
    const user = userEvent.setup()
    renderPanel()

    await user.click(screen.getByRole("tab", { name: /symbols/i }))
    await waitFor(() => expect(apiFetchMock).toHaveBeenCalled())

    await user.type(screen.getByPlaceholderText("Filter symbols…"), "login")

    await waitFor(() => {
      const calls = apiFetchMock.mock.calls
      const last = (calls[calls.length - 1]?.[0] ?? "") as string
      const params = new URLSearchParams(last.split("?")[1])
      expect(params.get("q")).toBe("login")
    })
  })
})
