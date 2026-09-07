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
import { Route } from "../notes"
import { FULL_HEIGHT_ROUTES } from "../../_authenticated"

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

  it("is registered as a full-height route", () => {
    // Without this the resizable split falls back to the 60vh floor.
    expect(FULL_HEIGHT_ROUTES).toContain("/notes")
  })
})
