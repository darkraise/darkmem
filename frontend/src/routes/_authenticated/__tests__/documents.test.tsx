import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ComponentType, ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
const routerMocks = vi.hoisted(() => ({
  useSearch: vi.fn((): { project?: string } => ({})),
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
  }
})
vi.mock("@/features/documents/components/project-workspace", () => ({
  ProjectWorkspace: ({ project, tab }: { project: string; tab?: string }) => (
    <div data-testid="workspace" data-tab={tab ?? "none"}>
      {project}
    </div>
  ),
}))

import { apiFetch } from "@/lib/api"
import { usePageChrome } from "@/components/app-chrome"
import type { ProjectSummary } from "@/hooks/api"
import { Route } from "../documents"
import { FULL_HEIGHT_ROUTES, FULL_WIDTH_ROUTES } from "../../_authenticated"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

/** The picker is published into the app header through PageChrome, so the
 *  test mounts the published actions beside the page the way the layout
 *  does. */
function HeaderActions() {
  return <>{usePageChrome((s) => s.actions)}</>
}

function renderRoute(search: { project?: string } = {}) {
  const Component = (Route.options ?? Route).component as ComponentType
  routerMocks.useSearch.mockReturnValue(search)
  render(
    <>
      <HeaderActions />
      <Component />
    </>,
    { wrapper },
  )
}

function mockProjects(
  rows: Array<Pick<ProjectSummary, "name" | "kind" | "document_count">>,
) {
  const full: ProjectSummary[] = rows.map((row) => ({
    memory_count: 0,
    checkpoint_count: 0,
    page_count: 0,
    last_checkpoint_at: null,
    last_event_day: null,
    ...row,
  }))
  vi.mocked(apiFetch).mockResolvedValue(full)
}

afterEach(() => vi.clearAllMocks())

describe("/documents route", () => {
  it("defaults to a project that actually holds documents", async () => {
    mockProjects([
      { name: "empty", kind: "project", document_count: 0 },
      { name: "darkmem", kind: "project", document_count: 475 },
      { name: "notes", kind: "personal", document_count: 3 },
    ])
    renderRoute()
    // `useProjects` orders busiest-first by a different measure, so the
    // default needs its own document_count filter.
    expect(await screen.findByTestId("workspace")).toHaveTextContent("darkmem")
    expect(screen.getByRole("combobox")).toHaveTextContent("darkmem")
  })

  it("mounts the workspace without the project tabs", async () => {
    mockProjects([{ name: "darkmem", kind: "project", document_count: 1 }])
    renderRoute()
    expect(await screen.findByTestId("workspace")).toHaveAttribute(
      "data-tab",
      "none",
    )
  })

  it("opens the project the URL names", async () => {
    mockProjects([
      { name: "darkmem", kind: "project", document_count: 475 },
      { name: "other", kind: "project", document_count: 2 },
    ])
    renderRoute({ project: "other" })
    expect(await screen.findByTestId("workspace")).toHaveTextContent("other")
  })

  it("falls back to the default when the URL names no eligible project", async () => {
    mockProjects([
      { name: "darkmem", kind: "project", document_count: 475 },
      { name: "notes", kind: "personal", document_count: 3 },
    ])
    renderRoute({ project: "notes" })
    expect(await screen.findByTestId("workspace")).toHaveTextContent("darkmem")
  })

  it("writes the picked project to the URL", async () => {
    mockProjects([
      { name: "darkmem", kind: "project", document_count: 475 },
      { name: "other", kind: "project", document_count: 2 },
    ])
    renderRoute()
    await userEvent.click(await screen.findByRole("combobox"))
    await userEvent.click(await screen.findByRole("option", { name: "other" }))

    const calls = routerMocks.navigate.mock.calls
    const call = calls[calls.length - 1]?.[0]
    expect(call.search({ keep: "me" })).toEqual({
      keep: "me",
      project: "other",
    })
  })

  it("keeps the personal space out of the picker", async () => {
    mockProjects([
      { name: "darkmem", kind: "project", document_count: 475 },
      { name: "notes", kind: "personal", document_count: 3 },
    ])
    renderRoute()
    await userEvent.click(await screen.findByRole("combobox"))
    // A positive assertion too: the dropdown genuinely opened and listed the
    // eligible project, rather than this test passing because it never did.
    expect(
      await screen.findByRole("option", { name: "darkmem" }),
    ).toBeInTheDocument()
    expect(screen.queryByRole("option", { name: "notes" })).toBeNull()
  })

  it("reports a failed project read instead of an empty corpus", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    renderRoute()
    expect(await screen.findByText(/could not be loaded/i)).toBeInTheDocument()
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument()
  })

  it("says so when the corpus holds no non-personal project", async () => {
    mockProjects([{ name: "notes", kind: "personal", document_count: 3 }])
    renderRoute()
    expect(await screen.findByText(/no project holds/i)).toBeInTheDocument()
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument()
  })

  it("claims the full height and width for its resizable split", () => {
    expect(FULL_HEIGHT_ROUTES).toContain("/documents")
    expect(FULL_WIDTH_ROUTES).toContain("/documents")
  })
})
