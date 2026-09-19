import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ComponentType, ReactNode } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
vi.mock("@tanstack/react-router", async () => {
  const actual = await vi.importActual<Record<string, unknown>>(
    "@tanstack/react-router",
  )
  return {
    ...actual,
    createFileRoute: () => (opts: Record<string, unknown>) => opts,
  }
})
vi.mock("@/features/documents/components/project-workspace", () => ({
  ProjectWorkspace: ({ project }: { project: string }) => (
    <div data-testid="workspace">{project}</div>
  ),
}))

import { apiFetch } from "@/lib/api"
import { usePageChrome } from "@/components/app-chrome"
import type { ProjectSummary } from "@/hooks/api"
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"
import { Route } from "../documents"
import { FULL_HEIGHT_ROUTES, FULL_WIDTH_ROUTES } from "../../_authenticated"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function HeaderActions() {
  return <>{usePageChrome((s) => s.actions)}</>
}

function renderRoute() {
  const Component = (Route.options ?? Route).component as ComponentType
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

beforeEach(() => {
  useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: null })
})
afterEach(() => vi.clearAllMocks())

describe("/documents route", () => {
  it("under all projects offers one button per project holding documents", async () => {
    mockProjects([
      { name: "empty", kind: "project", document_count: 0 },
      { name: "darkmem", kind: "project", document_count: 475 },
      { name: "other", kind: "project", document_count: 2 },
      { name: "notes", kind: "personal", document_count: 3 },
    ])
    renderRoute()
    expect(
      await screen.findByText("Documents open one project at a time"),
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^darkmem/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^other/ })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^empty/ })).toBeNull()
    expect(screen.queryByRole("button", { name: /^notes/ })).toBeNull()
    expect(screen.queryByTestId("workspace")).toBeNull()
  })

  it("a chooser click sets the global scope and opens that project", async () => {
    mockProjects([{ name: "darkmem", kind: "project", document_count: 475 }])
    renderRoute()
    await userEvent.click(await screen.findByRole("button", { name: /^darkmem/ }))
    expect(useProjectStore.getState().activeProject).toBe("darkmem")
    expect(await screen.findByTestId("workspace")).toHaveTextContent("darkmem")
  })

  it("opens the project the global scope names", async () => {
    useProjectStore.setState({ activeProject: "other", missingProject: null })
    mockProjects([
      { name: "darkmem", kind: "project", document_count: 475 },
      { name: "other", kind: "project", document_count: 2 },
    ])
    renderRoute()
    expect(await screen.findByTestId("workspace")).toHaveTextContent("other")
  })

  it("puts no project picker in the header", async () => {
    mockProjects([{ name: "darkmem", kind: "project", document_count: 475 }])
    renderRoute()
    await screen.findByText("Documents open one project at a time")
    expect(screen.queryByRole("combobox")).toBeNull()
  })

  it("says so when no project holds documents", async () => {
    mockProjects([{ name: "empty", kind: "project", document_count: 0 }])
    renderRoute()
    expect(
      await screen.findByText("No project holds documents yet"),
    ).toBeInTheDocument()
  })

  it("reports a failed project read instead of an empty corpus", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    renderRoute()
    expect(await screen.findByText(/could not be loaded/i)).toBeInTheDocument()
  })

  it("says so when the corpus holds no non-personal project", async () => {
    mockProjects([{ name: "notes", kind: "personal", document_count: 3 }])
    renderRoute()
    expect(await screen.findByText(/no project holds anything/i)).toBeInTheDocument()
  })

  it("claims the full height and width for its resizable split", () => {
    expect(FULL_HEIGHT_ROUTES).toContain("/documents")
    expect(FULL_WIDTH_ROUTES).toContain("/documents")
  })
})
