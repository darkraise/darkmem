import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import type { ComponentType, ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
const routerMocks = vi.hoisted(() => ({
  useParams: vi.fn(() => ({ project: "darkmem" })),
}))
vi.mock("@tanstack/react-router", async () => {
  const actual = await vi.importActual<Record<string, unknown>>(
    "@tanstack/react-router",
  )
  return {
    ...actual,
    createFileRoute: () => (opts: Record<string, unknown>) => opts,
    useParams: () => routerMocks.useParams(),
    useSearch: () => ({}),
    useNavigate: () => vi.fn(),
    Link: ({ children, to }: { children: ReactNode; to: string }) => (
      <a href={to}>{children}</a>
    ),
  }
})
vi.mock("@/features/documents/components/project-workspace", () => ({
  TAB_VALUES: ["artifacts", "progress"],
  ProjectWorkspace: ({ project }: { project: string }) => (
    <div data-testid="workspace">{project}</div>
  ),
}))

import { apiFetch } from "@/lib/api"
import type { ProjectSummary } from "@/hooks/api"
import { Route } from "../projects_.$project"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function renderRoute(project: string) {
  routerMocks.useParams.mockReturnValue({ project })
  const Component = (Route.options ?? Route).component as ComponentType
  render(<Component />, { wrapper })
}

const row = (name: string, kind: ProjectSummary["kind"]): ProjectSummary => ({
  name,
  kind,
  memory_count: 1,
  document_count: 1,
  page_count: 0,
  workstream_count: 0,
  open_workstream_count: 0,
  last_worklog_at: null,
  last_event_day: null,
})

afterEach(() => vi.clearAllMocks())

describe("/projects/$project — a name the catalogue does not hold", () => {
  it("says the project was not found and links back to Projects", async () => {
    // It used to render a whole empty workspace -- search box, tabs and
    // "No documents filed" -- for a typo.
    vi.mocked(apiFetch).mockResolvedValue([row("darkmem", "project")])
    renderRoute("no-such-project")

    expect(await screen.findByText("Project not found")).toBeInTheDocument()
    expect(screen.getByText(/no-such-project/, { selector: "p" })).toBeTruthy()
    expect(
      screen.getByRole("link", { name: "Back to Projects" }),
    ).toHaveAttribute("href", "/projects")
    expect(screen.queryByTestId("workspace")).toBeNull()
  })

  it("does not open the personal space as a project", async () => {
    // The personal project's documents are visible nowhere in the SPA.
    vi.mocked(apiFetch).mockResolvedValue([
      row("darkmem", "project"),
      row("notes", "personal"),
    ])
    renderRoute("notes")

    expect(await screen.findByText("Project not found")).toBeInTheDocument()
    expect(screen.queryByTestId("workspace")).toBeNull()
  })

  it("opens the workspace for a project the catalogue holds", async () => {
    vi.mocked(apiFetch).mockResolvedValue([row("darkmem", "project")])
    renderRoute("darkmem")

    expect(await screen.findByTestId("workspace")).toHaveTextContent("darkmem")
    expect(screen.queryByText("Project not found")).toBeNull()
  })

  it("still opens the workspace when the catalogue could not be read", async () => {
    // A failed read cannot say the name is unknown.
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    renderRoute("darkmem")

    expect(await screen.findByTestId("workspace")).toHaveTextContent("darkmem")
  })
})
