import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import type { ComponentType, ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
vi.mock("@tanstack/react-router", async () => {
  const actual = await vi.importActual<Record<string, unknown>>(
    "@tanstack/react-router",
  )
  return {
    ...actual,
    createFileRoute: () => (opts: Record<string, unknown>) => opts,
    Link: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  }
})
vi.mock("@/features/documents/components/project-workspace", () => ({
  ProjectWorkspace: ({
    project,
    treeManagement,
  }: {
    project: string
    treeManagement?: boolean
  }) => (
    <div data-testid="workspace-project" data-tree-management={!!treeManagement}>
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

function renderRoute() {
  const Component = (Route.options ?? Route).component as ComponentType
  render(<Component />, { wrapper })
}

const row = (name: string, kind: "project" | "personal") => ({
  name,
  kind,
  memory_count: 0,
  document_count: 0,
  checkpoint_count: 0,
  page_count: 0,
  last_checkpoint_at: null,
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
    expect(await screen.findByTestId("workspace-project")).toHaveTextContent(
      "my-notes",
    )
  })

  it("renders the workspace for an empty personal space", async () => {
    // A fresh install holds no documents. That is the normal first view, so
    // the workspace (and its own create button) must render.
    vi.mocked(apiFetch).mockResolvedValue([row("notes", "personal")])
    renderRoute()

    const workspace = await screen.findByTestId("workspace-project")
    expect(workspace).toHaveTextContent("notes")
    expect(workspace).toHaveAttribute("data-tree-management", "true")
  })

  it("reports a failed catalogue read instead of a blank page", async () => {
    // `return null` on a rejected read left the user staring at an empty
    // content area with no message -- the defect `projects.tsx` was already
    // fixed for ("a failed list is not an empty corpus").
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    renderRoute()

    expect(await screen.findByText(/could not be loaded/i)).toBeInTheDocument()
    expect(screen.queryByTestId("workspace-project")).not.toBeInTheDocument()
    expect(screen.queryByText(/no personal space/i)).not.toBeInTheDocument()
  })

  it("says so when the catalogue holds no personal space", async () => {
    vi.mocked(apiFetch).mockResolvedValue([row("darkmem", "project")])
    renderRoute()

    expect(await screen.findByText(/no personal space/i)).toBeInTheDocument()
    expect(screen.queryByTestId("workspace-project")).not.toBeInTheDocument()
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
