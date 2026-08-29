import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { RealRepositoriesView } from "../components/real-repositories-view"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const BASE_REPO = {
  id: "r1",
  name: "darkmem-backend",
  url: "https://example.invalid/darkmem-backend",
  local_path: null,
  provider: "github",
  default_branch: "main",
  fetch_enabled: false,
  fetch_interval_seconds: 300,
  index_on_commit_enabled: false,
  commit_poll_seconds: 60,
  index_uncommitted: false,
  file_count: 400,
  symbol_count: 5000,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-07-27T00:00:00Z",
}

describe("RealRepositoriesView", () => {
  beforeEach(() => vi.clearAllMocks())

  it("names the last-good sha and the cause on a stale repo — never a silently-empty graph", async () => {
    vi.mocked(apiFetch).mockResolvedValue([
      {
        ...BASE_REPO,
        status: "stale",
        status_message:
          "Indexing failed; still serving the graph from commit 4b7e120. Cause: Leiden partitioning step timed out after 90s",
        last_indexed_commit: "4b7e120",
        last_indexed_at: "2026-07-19T14:02:00Z",
        index_debt: {
          queued: 0,
          deferred_total: 0,
          drained_total: 0,
          last_defer: null,
          last_drain: null,
        },
      },
    ])

    render(<RealRepositoriesView />, { wrapper })

    await screen.findByText(
      "Last index failed — serving the last-good graph, marked stale",
    )
    expect(
      screen.getByText(/Leiden partitioning step timed out after 90s/),
    ).toBeInTheDocument()
    expect(screen.getByText("last-good HEAD 4b7e120")).toBeInTheDocument()
  })

  it("shows the queued count and reads as draining when a drain has landed", async () => {
    vi.mocked(apiFetch).mockResolvedValue([
      {
        ...BASE_REPO,
        status: "ready",
        status_message: null,
        last_indexed_commit: "9a1c2d3",
        last_indexed_at: "2026-07-27T09:00:00Z",
        index_debt: {
          queued: 168,
          deferred_total: 320,
          drained_total: 152,
          last_defer: {
            at: "2026-07-27T09:00:00Z",
            count: 40,
            commit: "9a1c2d3",
            vanished: 0,
          },
          last_drain: {
            at: "2026-07-27T08:55:00Z",
            count: 24,
            commit: "9a1c2d2",
            vanished: 1,
          },
        },
      },
    ])

    render(<RealRepositoriesView />, { wrapper })

    await screen.findByText(/168 dependent files queued for re-trace/)
    expect(screen.getByText(/draining — last drained 24 files/)).toBeInTheDocument()
    expect(screen.getByText(/commit 9a1c2d2/)).toBeInTheDocument()
    expect(screen.getByText(/1 vanished — no longer referenced/)).toBeInTheDocument()
  })

  it("reads as not-yet-drained, never silently dropped, when nothing has drained yet", async () => {
    vi.mocked(apiFetch).mockResolvedValue([
      {
        ...BASE_REPO,
        status: "ready",
        status_message: null,
        last_indexed_commit: "abc1234",
        last_indexed_at: "2026-07-27T09:00:00Z",
        index_debt: {
          queued: 12,
          deferred_total: 12,
          drained_total: 0,
          last_defer: {
            at: "2026-07-27T09:00:00Z",
            count: 12,
            commit: "abc1234",
            vanished: 0,
          },
          last_drain: null,
        },
      },
    ])

    render(<RealRepositoriesView />, { wrapper })

    await screen.findByText(/12 dependent files queued for re-trace/)
    expect(
      screen.getByText(/no drain recorded yet — 12 deferred, 0 drained so far/),
    ).toBeInTheDocument()
  })

  it("hides the debt indicator entirely for a repo with no debt history", async () => {
    vi.mocked(apiFetch).mockResolvedValue([
      {
        ...BASE_REPO,
        status: "ready",
        status_message: null,
        last_indexed_commit: "abc1234",
        last_indexed_at: "2026-07-27T09:00:00Z",
        index_debt: {
          queued: 0,
          deferred_total: 0,
          drained_total: 0,
          last_defer: null,
          last_drain: null,
        },
      },
    ])

    render(<RealRepositoriesView />, { wrapper })

    await screen.findByText("darkmem-backend")
    expect(screen.queryByText(/queued for re-trace/)).not.toBeInTheDocument()
  })

  it("renders the live phase label from status_message while indexing, not a bare spinner", async () => {
    vi.mocked(apiFetch).mockResolvedValue([
      {
        ...BASE_REPO,
        status: "indexing",
        status_message: "Building structure graph...",
        last_indexed_commit: null,
        last_indexed_at: null,
        index_debt: {
          queued: 0,
          deferred_total: 0,
          drained_total: 0,
          last_defer: null,
          last_drain: null,
        },
      },
    ])

    render(<RealRepositoriesView />, { wrapper })

    await screen.findByText(/indexing — Building structure graph\.\.\./)
  })

  it("shows an honest auto-provisioned marker for a queued repo, never fabricating a source", async () => {
    vi.mocked(apiFetch).mockResolvedValue([
      {
        ...BASE_REPO,
        status: "queued",
        status_message: "Queued for auto-provision indexing",
        last_indexed_commit: null,
        last_indexed_at: null,
        created_at: "2026-07-22T10:00:00Z",
        index_debt: {
          queued: 0,
          deferred_total: 0,
          drained_total: 0,
          last_defer: null,
          last_drain: null,
        },
      },
    ])

    render(<RealRepositoriesView />, { wrapper })

    await screen.findByText(/auto-provisioned — queued/)
    expect(
      screen.getByText(/Queued for auto-provision indexing/),
    ).toBeInTheDocument()
  })

  it("submits the reindex options the dialog collected, in POST /repos/{id}/reindex's own shape", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/repos") return Promise.resolve([{ ...BASE_REPO, status: "ready" }])
      return Promise.resolve({})
    })

    const user = userEvent.setup()
    render(<RealRepositoriesView />, { wrapper })

    await screen.findByText("darkmem-backend")
    await user.click(screen.getByRole("button", { name: "Reindex" }))

    const dialog = await screen.findByRole("dialog")
    await user.click(within(dialog).getByLabelText("enrich_symbols"))
    await user.click(within(dialog).getByRole("button", { name: "Run reindex" }))

    const reindexCall = vi
      .mocked(apiFetch)
      .mock.calls.find(([path]) => path === "/repos/r1/reindex")
    expect(reindexCall).toBeTruthy()
    const [, init] = reindexCall!
    expect(init?.method).toBe("POST")
    expect(JSON.parse(String(init?.body))).toEqual({
      full: true,
      enrich_symbols: true,
      generate_wiki: false,
    })
  })

  it("issues a POST /repos with the create form's fields on Add repository", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/repos") return Promise.resolve([])
      return Promise.resolve({ id: "new-repo" })
    })

    const user = userEvent.setup()
    render(<RealRepositoriesView />, { wrapper })

    await screen.findByText("No repositories indexed yet")
    await user.click(screen.getByRole("button", { name: /Add repository/ }))

    const dialog = await screen.findByRole("dialog")
    const nameField = within(dialog).getAllByRole("textbox")[0]!
    await user.type(nameField, "new-service")
    await user.click(within(dialog).getByRole("button", { name: "Add Repository" }))

    const createCall = vi
      .mocked(apiFetch)
      .mock.calls.find(([path]) => path === "/repos")
    expect(createCall).toBeTruthy()
    const bodies = vi
      .mocked(apiFetch)
      .mock.calls.filter(([path]) => path === "/repos")
      .map(([, init]) => init)
    const postCall = bodies.find((init) => init?.method === "POST")
    expect(postCall).toBeTruthy()
    expect(JSON.parse(String(postCall?.body))).toMatchObject({
      name: "new-service",
    })
  })
})
