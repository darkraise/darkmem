import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import type { ComponentType, ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
const routerMocks = vi.hoisted(() => ({
  useSearch: vi.fn((): { page?: string } => ({})),
  navigate: vi.fn(),
}))
vi.mock("@tanstack/react-router", async () => {
  const actual = await vi.importActual<Record<string, unknown>>(
    "@tanstack/react-router",
  )
  return {
    ...actual,
    createFileRoute: () => (opts: Record<string, unknown>) => opts,
    useSearch: () => routerMocks.useSearch(),
    useNavigate: () => routerMocks.navigate,
    Link: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  }
})
vi.mock("@/features/notes/notes-workspace", () => ({
  NotesWorkspace: ({
    project,
    selectedId,
  }: {
    project: string
    selectedId: string | null
  }) => (
    <div data-testid="notes-project" data-selected={selectedId ?? ""}>
      {project}
    </div>
  ),
}))

import { apiFetch } from "@/lib/api"
import { usePageChrome } from "@/components/app-chrome"
import { Route } from "../notes"
import { FULL_HEIGHT_ROUTES, FULL_WIDTH_ROUTES } from "../../_authenticated"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function renderRoute(search: { page?: string } = {}) {
  const Component = (Route.options ?? Route).component as ComponentType
  routerMocks.useSearch.mockReturnValue(search)
  render(<Component />, { wrapper })
}

const row = (name: string, kind: "project" | "personal") => ({
  name,
  kind,
  memory_count: 0,
  document_count: 0,
  page_count: 0,
  workstream_count: 0,
  open_workstream_count: 0,
  last_worklog_at: null,
  last_event_day: null,
})

afterEach(() => vi.clearAllMocks())

describe("notes route", () => {
  it("resolves its project from the catalogue rather than a hardcoded name", async () => {
    vi.mocked(apiFetch).mockResolvedValue([
      row("darkmem", "project"),
      row("my-notes", "personal"),
    ])
    renderRoute()

    // The singleton index guarantees at most one personal row; the route must
    // follow `kind`, not the seeded name.
    expect(await screen.findByTestId("notes-project")).toHaveTextContent(
      "my-notes",
    )
  })

  it("renders the workspace for an empty personal space", async () => {
    // A fresh install holds no documents. That is the normal first view, so
    // the workspace (and its own create button) must render.
    vi.mocked(apiFetch).mockResolvedValue([row("notes", "personal")])
    renderRoute()

    const workspace = await screen.findByTestId("notes-project")
    expect(workspace).toHaveTextContent("notes")
  })

  // `await findByTestId`, as every other case in this file does: `NotesPage`
  // renders a Skeleton while `useProjects()` is pending, so nothing with this
  // id exists on the synchronous first render.
  it("passes the page id from the search param through to the workspace", async () => {
    vi.mocked(apiFetch).mockResolvedValue([row("personal-space", "personal")])
    renderRoute({ page: "p7" })
    expect(await screen.findByTestId("notes-project")).toHaveAttribute(
      "data-selected",
      "p7",
    )
  })

  it("keeps only a non-empty string page param", () => {
    const validate = (Route.options ?? Route).validateSearch as (
      s: Record<string, unknown>,
    ) => { page?: string }
    expect(validate({ page: "p7" })).toEqual({ page: "p7" })
    expect(validate({ page: "" })).toEqual({ page: undefined })
    expect(validate({ page: 7 })).toEqual({ page: undefined })
    expect(validate({})).toEqual({ page: undefined })
  })

  it("reports a failed catalogue read instead of a blank page", async () => {
    // `return null` on a rejected read left the user staring at an empty
    // content area with no message -- the defect `projects.tsx` was already
    // fixed for ("a failed list is not an empty corpus").
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    renderRoute()

    expect(await screen.findByText(/could not be loaded/i)).toBeInTheDocument()
    expect(screen.queryByTestId("notes-project")).not.toBeInTheDocument()
    expect(screen.queryByText(/no personal space/i)).not.toBeInTheDocument()
  })

  it("says so when the catalogue holds no personal space", async () => {
    vi.mocked(apiFetch).mockResolvedValue([row("darkmem", "project")])
    renderRoute()

    expect(await screen.findByText(/no personal space/i)).toBeInTheDocument()
    expect(screen.queryByTestId("notes-project")).not.toBeInTheDocument()
  })

  it("publishes the page chrome on every branch, not only the resolved one", async () => {
    // PageChrome renders nothing itself -- it publishes into the header
    // store -- so an early `return null` above it left the header blank too.
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    renderRoute()

    await screen.findByText(/could not be loaded/i)
    expect(usePageChrome.getState().title).toBe("Notes")
  })

  it("is registered as a full-height route", () => {
    // Without this the resizable split falls back to the 60vh floor.
    expect(FULL_HEIGHT_ROUTES).toContain("/notes")
  })

  it("is registered as a full-width route", () => {
    // Identical ProjectWorkspace, identical resizable split: boxing it into
    // the reading-width column while /projects/<name> fills the screen has
    // no argument behind it.
    expect(FULL_WIDTH_ROUTES).toContain("/notes")
  })
})
