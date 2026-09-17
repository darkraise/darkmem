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

import { apiFetch } from "@/lib/api"
import { Route } from "../projects"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

afterEach(() => vi.clearAllMocks())

describe("projects index — a failed list is not an empty corpus", () => {
  it("reports the failure instead of claiming no project holds anything", async () => {
    // `useProjects` was destructured as { data, isLoading }, so an error left
    // isLoading false and data undefined -- rendering the "no project holds
    // anything yet" empty state. That sentence is a claim about the corpus,
    // and on a failed read it is false.
    vi.mocked(apiFetch).mockRejectedValue(new Error("boom"))
    const Component = (Route.options ?? Route).component as ComponentType
    render(<Component />, { wrapper })

    expect(await screen.findByText(/could not be loaded/i)).toBeInTheDocument()
    expect(
      screen.queryByText(/no project holds anything yet/i),
    ).not.toBeInTheDocument()
  })

  it("still shows the empty state when the corpus really is empty", async () => {
    vi.mocked(apiFetch).mockResolvedValue([])
    const Component = (Route.options ?? Route).component as ComponentType
    render(<Component />, { wrapper })

    expect(
      await screen.findByText(/no project holds anything yet/i),
    ).toBeInTheDocument()
  })
})

describe("projects index — the personal notes space is not a project card", () => {
  it("omits the personal notes space from the catalogue", async () => {
    // The notes space has its own route and its own workspace. Offering it
    // here would open it in a surface built for project artifacts.
    vi.mocked(apiFetch).mockResolvedValue([
      { name: "darkmem", kind: "project", memory_count: 3, document_count: 0,
        checkpoint_count: 0, page_count: 0, last_checkpoint_at: null, last_event_day: null },
      { name: "notes", kind: "personal", memory_count: 0, document_count: 12,
        checkpoint_count: 0, page_count: 0, last_checkpoint_at: null, last_event_day: null },
    ])
    const Component = (Route.options ?? Route).component as ComponentType
    render(<Component />, { wrapper })

    expect(await screen.findByText("darkmem")).toBeInTheDocument()
    expect(screen.queryByText("notes")).not.toBeInTheDocument()
  })

  it("shows the empty state when only the personal notes space exists", async () => {
    // Filtering it out must feed the same rows the empty-state check reads,
    // or a corpus holding only the notes space would render neither a card
    // nor the empty state.
    vi.mocked(apiFetch).mockResolvedValue([
      { name: "notes", kind: "personal", memory_count: 0, document_count: 12,
        checkpoint_count: 0, page_count: 0, last_checkpoint_at: null, last_event_day: null },
    ])
    const Component = (Route.options ?? Route).component as ComponentType
    render(<Component />, { wrapper })

    expect(
      await screen.findByText(/no project holds anything yet/i),
    ).toBeInTheDocument()
    expect(screen.queryByText("notes")).not.toBeInTheDocument()
  })
})
