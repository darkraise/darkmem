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

    await screen.findByText("Last index failed — showing the last good graph")
    expect(
      screen.getByText(/Leiden partitioning step timed out after 90s/),
    ).toBeInTheDocument()
    expect(screen.getByText("last-good HEAD 4b7e120")).toBeInTheDocument()
  })

  it("shows why a repository is in the error state", async () => {
    vi.mocked(apiFetch).mockResolvedValue([
      {
        ...BASE_REPO,
        status: "error",
        status_message: "Clone failed: authentication required",
        last_indexed_commit: null,
        last_indexed_at: null,
        index_debt: null,
      },
    ])

    render(<RealRepositoriesView />, { wrapper })

    expect(
      await screen.findByText("Clone failed: authentication required"),
    ).toBeInTheDocument()
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

    await screen.findByText(/168 dependent files queued for reindex/)
    expect(screen.getByText(/last drained 24 files/)).toBeInTheDocument()
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

    await screen.findByText(/12 dependent files queued for reindex/)
    expect(screen.getByText("none drained yet")).toBeInTheDocument()
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
    expect(screen.queryByText(/queued for reindex/)).not.toBeInTheDocument()
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
    await user.click(within(dialog).getByLabelText("Enrich symbols"))
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
  it("adds a local checkout by its path on the server, not a URL", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/repos") return Promise.resolve([])
      return Promise.resolve({ id: "new-repo" })
    })
    const user = userEvent.setup()
    render(<RealRepositoriesView />, { wrapper })

    await screen.findByText("No repositories indexed yet")
    await user.click(screen.getByRole("button", { name: /Add repository/ }))
    const dialog = await screen.findByRole("dialog")
    await user.type(within(dialog).getAllByRole("textbox")[0]!, "local-one")
    await user.click(within(dialog).getByRole("combobox", { name: "Provider" }))
    await user.click(await screen.findByRole("option", { name: "Local" }))
    expect(within(dialog).queryByLabelText("URL")).toBeNull()
    await user.type(
      within(dialog).getByLabelText(/Path on the server/),
      "/srv/repos/local-one",
    )
    await user.click(within(dialog).getByRole("button", { name: "Add Repository" }))

    const post = vi
      .mocked(apiFetch)
      .mock.calls.find(([path, init]) => path === "/repos" && init?.method === "POST")
    expect(JSON.parse(String(post?.[1]?.body))).toMatchObject({
      name: "local-one",
      provider: "local",
      local_path: "/srv/repos/local-one",
    })
    expect(JSON.parse(String(post?.[1]?.body)).url).toBeUndefined()
  })

  it("does not leak a touched-and-cancelled edit into the next repo's form", async () => {
    const REPO_A = {
      ...BASE_REPO,
      id: "r1",
      name: "repo-a",
      status: "ready",
      status_message: null,
      last_indexed_commit: "aaa1111",
      last_indexed_at: "2026-07-27T09:00:00Z",
      fetch_enabled: false,
      index_debt: {
        queued: 0,
        deferred_total: 0,
        drained_total: 0,
        last_defer: null,
        last_drain: null,
      },
    }
    const REPO_B = {
      ...BASE_REPO,
      id: "r2",
      name: "repo-b",
      status: "ready",
      status_message: null,
      last_indexed_commit: "bbb2222",
      last_indexed_at: "2026-07-27T09:00:00Z",
      fetch_enabled: false,
      index_debt: {
        queued: 0,
        deferred_total: 0,
        drained_total: 0,
        last_defer: null,
        last_drain: null,
      },
    }

    vi.mocked(apiFetch).mockResolvedValue([REPO_A, REPO_B])

    const user = userEvent.setup()
    render(<RealRepositoriesView />, { wrapper })

    const editButtons = await screen.findAllByRole("button", { name: "Edit" })
    expect(editButtons).toHaveLength(2)
    const [editRepoA, editRepoB] = editButtons as [HTMLElement, HTMLElement]

    // Open repo A, touch its fetch switch, then cancel without saving.
    await user.click(editRepoA)
    expect(await screen.findByDisplayValue("repo-a")).toBeInTheDocument()
    await user.click(screen.getByRole("switch", { name: /fetch from remote/i }))
    expect(
      screen.getByRole("switch", { name: /fetch from remote/i }),
    ).toBeChecked()
    await user.click(screen.getByRole("button", { name: "Cancel" }))

    // Repo B's own dialog must not inherit A's touched-but-abandoned state.
    await user.click(editRepoB)
    expect(await screen.findByDisplayValue("repo-b")).toBeInTheDocument()
    expect(
      screen.getByRole("switch", { name: /fetch from remote/i }),
    ).not.toBeChecked()
  })
})


describe("a failed repository list is not an unindexed instance", () => {
  it("reports the failure instead of claiming no repositories are indexed", async () => {
    // `repos && repos.length > 0 ? ... : EmptyState` sends an errored read to
    // the empty state, which invites the operator to add a repository they
    // already have.
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    render(<RealRepositoriesView />, { wrapper })

    expect(await screen.findByText(/could not be loaded/i)).toBeInTheDocument()
    expect(
      screen.queryByText(/no repositories indexed yet/i),
    ).not.toBeInTheDocument()
  })
})
