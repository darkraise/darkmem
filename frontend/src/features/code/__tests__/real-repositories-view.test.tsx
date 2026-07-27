import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/demo/flag", () => ({ DEMO: false }))
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
  auto_sync: true,
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
})
