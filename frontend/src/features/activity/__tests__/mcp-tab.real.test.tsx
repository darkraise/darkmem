import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    params,
  }: {
    children: ReactNode
    params: { memoryId: string }
  }) => <a href={`/memories/${params.memoryId}`}>{children}</a>,
}))

import { apiFetch } from "@/lib/api"
import { DEMO_MCP_CALLS, DEMO_MCP_CALL_SUMMARY } from "@/demo/mcp-calls"
import { McpTab } from "../components/mcp-tab"
import { formatArguments } from "../mcp-format"

function renderTab() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <McpTab />
    </QueryClientProvider>,
  )
}

describe("formatArguments", () => {
  it("reads minimised values as sizes, never as the value", () => {
    expect(
      formatArguments({
        query: { chars: 12 },
        entries: { items: 3 },
        tags_any: ["a", "b", { more: 4 }],
        limit: 5,
        project: "darkmem",
      }),
    ).toBe(
      "query=‹12 chars›  entries=‹3 items›  tags_any=[a, b, +4]  limit=5  project=darkmem",
    )
  })
})

describe("McpTab (DEMO off — real /mcp-calls)", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiFetch).mockImplementation(async (url: string) =>
      url.startsWith("/mcp-calls/summary")
        ? DEMO_MCP_CALL_SUMMARY
        : DEMO_MCP_CALLS,
    )
  })

  it("shows the summary and the recent calls", async () => {
    renderTab()

    await waitFor(() => expect(screen.getByText("412")).toBeInTheDocument())
    expect(
      screen.getAllByText("laptop-claude-code · claude-code").length,
    ).toBeGreaterThan(0)
    expect(
      screen.getByText("key lacks the 'capture' scope"),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Search queries are stored as their length only/),
    ).toBeInTheDocument()
    expect(apiFetch).toHaveBeenCalledWith(
      expect.stringMatching(/^\/mcp-calls\/summary\?since=/),
    )
    expect(apiFetch).toHaveBeenCalledWith("/mcp-calls?limit=50")
  })

  it("filters the list to the calls that returned an item", async () => {
    renderTab()
    await waitFor(() => expect(screen.getAllByText("show").length).toBe(3))

    fireEvent.click(screen.getAllByText("show")[1]!)

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        "/mcp-calls?object_id=doc-0007&limit=50",
      ),
    )
  })

  it("links an item to its memory only when only memory tools returned it", async () => {
    renderTab()
    await waitFor(() => expect(screen.getAllByText("show").length).toBe(3))

    expect(screen.getByRole("link", { name: "mem-0001" })).toHaveAttribute(
      "href",
      "/memories/mem-0001",
    )
    expect(screen.queryByRole("link", { name: "doc-0007" })).toBeNull()
  })
})
