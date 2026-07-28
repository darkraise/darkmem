import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/demo/flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { RealWikiView } from "../components/real-wiki-view"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const REPO = {
  id: "r1",
  name: "darkmem-backend",
  url: null,
  local_path: "/repo",
  provider: "local",
  default_branch: "main",
  last_indexed_commit: "abc1234",
  last_indexed_at: "2026-07-27T00:00:00Z",
  status: "ready",
  status_message: null,
  auto_sync: true,
  file_count: 1,
  symbol_count: 2,
  index_debt: {
    queued: 0,
    deferred_total: 0,
    drained_total: 0,
    last_defer: null,
    last_drain: null,
  },
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-07-27T00:00:00Z",
}

const WIKI = {
  repo_name: "darkmem-backend",
  overview: "Ingests and retrieves memories.",
  modules: [
    {
      path: "services",
      summary: "The pipeline modules.",
      symbol_count: 3,
      files: [
        {
          path: "services/pipeline.py",
          language: "python",
          symbols: [
            {
              name: "ProcessingPipeline",
              kind: "class",
              signature: null,
              summary: "Runs the five-phase batch pipeline.",
              line_start: 12,
            },
          ],
        },
      ],
    },
  ],
  total_modules: 1,
  total_files: 1,
}

describe("RealWikiView", () => {
  beforeEach(() => vi.clearAllMocks())

  it("renders the generated wiki's overview and modules from GET /code/wiki", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/repos") return Promise.resolve([REPO])
      if (path === "/code/wiki/r1") return Promise.resolve(WIKI)
      return Promise.resolve({})
    })

    render(<RealWikiView repoId="r1" onRepoChange={vi.fn()} />, { wrapper })

    await screen.findByText("Ingests and retrieves memories.")
    expect(screen.getByText("services")).toBeInTheDocument()
    expect(screen.getByText("1 modules")).toBeInTheDocument()
  })

  it("empty state points at the reindex dialog, never implicitly generates", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/repos") return Promise.resolve([REPO])
      if (path === "/code/wiki/r1") return Promise.resolve(null)
      return Promise.resolve({})
    })

    render(<RealWikiView repoId="r1" onRepoChange={vi.fn()} />, { wrapper })

    await screen.findByText("No wiki generated yet for this repository")
    expect(
      screen.getByRole("button", { name: /Open reindex dialog/ }),
    ).toBeInTheDocument()
  })

  it("the empty-state CTA opens a dialog the user must explicitly submit — it never mutates directly on click", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/repos") return Promise.resolve([REPO])
      if (path === "/code/wiki/r1") return Promise.resolve(null)
      return Promise.resolve({})
    })

    const user = userEvent.setup()
    render(<RealWikiView repoId="r1" onRepoChange={vi.fn()} />, { wrapper })

    await screen.findByText("No wiki generated yet for this repository")
    await user.click(screen.getByRole("button", { name: /Open reindex dialog/ }))

    // The dialog must be open — proving the click routed through it rather
    // than skipping straight to a mutation.
    await screen.findByRole("dialog")

    const nonGetCalls = vi
      .mocked(apiFetch)
      .mock.calls.filter(([, init]) => {
        const method = init?.method
        return method !== undefined && method !== "GET"
      })
    expect(nonGetCalls).toEqual([])
  })

  it("submitting the opened dialog is the one path that legitimately calls the reindex mutation", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/repos") return Promise.resolve([REPO])
      if (path === "/code/wiki/r1") return Promise.resolve(null)
      return Promise.resolve({})
    })

    const user = userEvent.setup()
    render(<RealWikiView repoId="r1" onRepoChange={vi.fn()} />, { wrapper })

    await screen.findByText("No wiki generated yet for this repository")
    await user.click(screen.getByRole("button", { name: /Open reindex dialog/ }))
    const dialog = await screen.findByRole("dialog")
    await user.click(within(dialog).getByRole("button", { name: "Run reindex" }))

    const reindexCall = vi
      .mocked(apiFetch)
      .mock.calls.find(([path]) => path === "/repos/r1/reindex")
    expect(reindexCall).toBeTruthy()
    expect(reindexCall![1]?.method).toBe("POST")
  })
})
