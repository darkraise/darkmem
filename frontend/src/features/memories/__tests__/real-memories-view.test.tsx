import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
// Link needs a router context this test never sets up; a plain anchor
// keeps the row's honesty labels and trace toggle testable in isolation.
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({
    children,
    to: _to,
    params: _params,
    ...rest
  }: {
    children?: ReactNode
    to?: string
    params?: unknown
    [key: string]: unknown
  }) => <a {...rest}>{children}</a>,
}))

import { apiFetch } from "@/lib/api"
import { AppPageHeader } from "@/components/app-chrome"
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"
import { RealMemoriesView } from "../components/real-memories-view"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  // useMainVirtualizer scrolls #main-content, not its own overflow box.
  return (
    <div id="main-content" style={{ height: 800 }}>
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    </div>
  )
}

describe("RealMemoriesView", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: null })
  })

  it("renders the exclusion strip even when every match was excluded (honesty/exclusions-on-empty)", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
      envelope: {
        query: "cookie-secure",
        channels: { semantic: { ran: true }, keyword: { ran: true } },
        reranked: false,
        weights: { semantic_weight: 0.7 },
        excluded: { technologies: 2 },
      },
    })

    render(<RealMemoriesView />, { wrapper })
    fireEvent.change(screen.getByLabelText("Search memories"), {
      target: { value: "cookie-secure" },
    })

    await screen.findByText(/2 memories excluded/i)
    // The zero-row empty state still renders alongside the strip — the
    // exclusion strip is not itself the only thing on screen.
    expect(screen.getByText(/no matches/i)).toBeInTheDocument()
  })

  it("shows the per-channel contribution and the fused rrf_score on demand (never labels a per-modality score as 'the score')", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [
        {
          id: "m1",
          content: "RRF fuses semantic and keyword ranks",
          tags: [],
          source: "mcp",
          created_at: new Date().toISOString(),
          status: "active",
          flags: [],
          trace: {
            scores: { semantic: 0.81, keyword: 0.34, rrf_score: 0.0271, rerank_score: null },
            rank_fusion_factor: 1.0,
            rank_fusion_breakdown: {},
          },
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
      envelope: {
        query: "rrf",
        channels: { semantic: { ran: true }, keyword: { ran: true } },
        reranked: false,
        weights: { semantic_weight: 0.7 },
        excluded: {},
      },
    })

    render(<RealMemoriesView initialQuery="rrf" />, { wrapper })
    await screen.findByText(/RRF fuses semantic and keyword ranks/i)

    fireEvent.click(screen.getByRole("button", { name: /show why retrieved/i }))

    expect(screen.getByText("semantic")).toBeInTheDocument()
    expect(screen.getByText("keyword")).toBeInTheDocument()
    expect(screen.getByText("rrf_score")).toBeInTheDocument()
    expect(screen.getByText("0.0271")).toBeInTheDocument()
  })

  it("offers no why? on the plain list, where nothing was retrieved", async () => {
    // With no query the trace reads "semantic off / keyword off / 0.0000".
    vi.mocked(apiFetch).mockResolvedValue({
      items: [
        {
          id: "m1",
          content: "listed, not retrieved",
          tags: [],
          source: "mcp",
          created_at: new Date().toISOString(),
          status: "active",
          flags: [],
          trace: {
            scores: { semantic: null, keyword: null, rrf_score: 0, rerank_score: null },
            rank_fusion_factor: 1.0,
            rank_fusion_breakdown: {},
          },
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    })
    render(<RealMemoriesView />, { wrapper })
    await screen.findByText("listed, not retrieved")
    expect(screen.queryByRole("button", { name: /show why retrieved/i })).toBeNull()
  })

  it("shows a superseded row by default, with its badge — never filtered out", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      items: [
        {
          id: "m1",
          content: "the superseded row",
          tags: [],
          source: "mcp",
          created_at: new Date().toISOString(),
          status: "superseded",
          superseded_by: "m2",
          flags: [],
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
      envelope: {
        query: "",
        channels: {},
        reranked: false,
        weights: {},
        excluded: {},
      },
    })

    render(<RealMemoriesView />, { wrapper })
    await screen.findByText(/the superseded row/i)
    expect(screen.getByText("superseded")).toBeInTheDocument()
  })

  it("shows a loading skeleton, not an empty state, while the first page is in flight", () => {
    vi.mocked(apiFetch).mockReturnValue(new Promise(() => {}))
    render(<RealMemoriesView />, { wrapper })
    expect(screen.getByLabelText(/loading memories/i)).toBeInTheDocument()
    expect(screen.queryByText(/no matches/i)).not.toBeInTheDocument()
  })

  it("surfaces a failed load as an explicit error, not an empty-list no-match", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("both channels failed"))
    render(<RealMemoriesView />, { wrapper })
    await screen.findByText(/search failed/i)
    expect(screen.queryByText(/no matches/i)).not.toBeInTheDocument()
  })

  it("the create action opens CreateMemoryDialog and submits a real, wait_process=true mutation", async () => {
    const user = userEvent.setup()
    const captured: { call: { path: string; body: Record<string, unknown> } | null } = {
      call: null,
    }
    vi.mocked(apiFetch).mockImplementation((path: unknown, options?: unknown) => {
      const p = path as string
      if (p === "/memories/search/paginated") {
        return Promise.resolve({ items: [], total: 0, limit: 50, offset: 0 })
      }
      if (p.startsWith("/memories?")) {
        captured.call = {
          path: p,
          body: JSON.parse((options as RequestInit).body as string),
        }
        return Promise.resolve({ schema_version: 1, id: "new-id", status: "accepted" })
      }
      return Promise.reject(new Error(`unmocked path: ${p}`))
    })

    render(
      <>
        <AppPageHeader />
        <RealMemoriesView />
      </>,
      { wrapper },
    )

    await user.click(screen.getByRole("button", { name: /create memory/i }))
    expect(screen.getByRole("dialog", { name: /new memory/i })).toBeInTheDocument()

    await user.type(
      screen.getByLabelText("Content"),
      "captured from the real create dialog",
    )
    await user.click(screen.getByRole("button", { name: "Create Memory" }))

    await waitFor(() => expect(captured.call).not.toBeNull())
    expect(captured.call?.path).toBe("/memories?wait_process=true")
    expect(captured.call?.body.content).toBe(
      "captured from the real create dialog",
    )
  })

  it("files a new memory under the header's project, and refuses spaces alone", async () => {
    // The dialog used to drop the scope and file every capture under
    // "default", so a memory created while scoped never showed in the list.
    useProjectStore.setState({ activeProject: "webapp", missingProject: null })
    const user = userEvent.setup()
    const bodies: Record<string, unknown>[] = []
    vi.mocked(apiFetch).mockImplementation((path: unknown, options?: unknown) => {
      const p = path as string
      if (p === "/memories/search/paginated") {
        return Promise.resolve({ items: [], total: 0, limit: 50, offset: 0 })
      }
      if (p.startsWith("/memories?")) {
        bodies.push(JSON.parse((options as RequestInit).body as string))
        return Promise.resolve({ schema_version: 1, id: "new-id", status: "accepted" })
      }
      return Promise.reject(new Error(`unmocked path: ${p}`))
    })
    render(
      <>
        <AppPageHeader />
        <RealMemoriesView />
      </>,
      { wrapper },
    )

    await user.click(screen.getByRole("button", { name: /create memory/i }))
    const dialog = screen.getByRole("dialog", { name: /new memory/i })
    expect(dialog).toHaveTextContent("saved to project webapp")

    await user.type(screen.getByLabelText("Content"), "   ")
    await user.click(screen.getByRole("button", { name: "Create Memory" }))
    expect(await screen.findByText("Content required")).toBeInTheDocument()
    expect(bodies).toEqual([])

    await user.clear(screen.getByLabelText("Content"))
    await user.type(screen.getByLabelText("Content"), "scoped capture")
    await user.click(screen.getByRole("button", { name: "Create Memory" }))
    await waitFor(() => expect(bodies).toHaveLength(1))
    expect(bodies[0]).toMatchObject({ content: "scoped capture", project: "webapp" })
  })

  it("scopes by the header switcher and offers no project field of its own", async () => {
    useProjectStore.setState({ activeProject: "acme", missingProject: null })
    vi.mocked(apiFetch).mockResolvedValue({
      items: [],
      total: 0,
      limit: 50,
      offset: 0,
      envelope: {
        query: "",
        channels: { semantic: { ran: false }, keyword: { ran: false } },
        reranked: false,
        weights: { semantic_weight: 0.7 },
        excluded: {},
      },
    })
    render(<RealMemoriesView />, { wrapper })

    expect(await screen.findByText("0 of 0 shown")).toBeInTheDocument()
    expect(screen.queryByRole("textbox", { name: "Project scope" })).toBeNull()
    const bodies = vi
      .mocked(apiFetch)
      .mock.calls.map((call) => JSON.parse(String((call[1] as RequestInit | undefined)?.body ?? "{}")))
    expect(bodies.some((body) => body.project === "acme")).toBe(true)
  })

  // M8: the semantic arm has no score floor, so a query no memory contains
  // still fills the list; the keyword arm's own count says so.
  function semanticOnlyPage(keywordHits: number) {
    return {
      items: [
        {
          id: "m1",
          content: "Postgres with pgvector for the memory store",
          tags: [],
          source: "api",
          created_at: new Date().toISOString(),
          status: "active",
          flags: [],
          trace: {
            scores: { semantic: 0.0, keyword: null, rrf_score: 0.0115, rerank_score: null },
            rank_fusion_factor: 1.0,
            rank_fusion_breakdown: {},
          },
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
      envelope: {
        query: "zzqqxxnomatch",
        channels: {
          semantic: { ran: true, failed: false, hits: 1 },
          keyword: { ran: true, failed: false, hits: keywordHits },
        },
        reranked: false,
        weights: { semantic_weight: 0.7 },
        excluded: {},
      },
    }
  }

  it("says no memory contains the words when the keyword arm matched nothing", async () => {
    useProjectStore.setState({ activeProject: "webapp", missingProject: null })
    vi.mocked(apiFetch).mockResolvedValue(semanticOnlyPage(0))
    render(<RealMemoriesView initialQuery="zzqqxxnomatch" />, { wrapper })

    await screen.findByText(/Postgres with pgvector/)
    expect(screen.getByRole("status")).toHaveTextContent(
      "No memory in project webapp contains these words; these are the closest by meaning.",
    )
  })

  it("makes no such claim when a keyword hit ranked below the loaded rows", async () => {
    vi.mocked(apiFetch).mockResolvedValue(semanticOnlyPage(1))
    render(<RealMemoriesView initialQuery="pgvector" />, { wrapper })

    await screen.findByText(/Postgres with pgvector/)
    expect(screen.queryByText(/contains these words/)).toBeNull()
  })
})
