import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"
import { TopicsTab } from "../components/topics-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const PROJECTS = [
  {
    name: "darkmem",
    kind: "project",
    memory_count: 10,
    document_count: 0,
    checkpoint_count: 0,
    page_count: 0,
    last_checkpoint_at: null,
    workstream_count: 0,
    open_workstream_count: 0,
    last_worklog_at: null,
    last_event_day: null,
  },
  {
    name: "docs-only",
    kind: "project",
    memory_count: 0,
    document_count: 4,
    checkpoint_count: 0,
    page_count: 0,
    last_checkpoint_at: null,
    workstream_count: 0,
    open_workstream_count: 0,
    last_worklog_at: null,
    last_event_day: null,
  },
  {
    name: "notes",
    kind: "personal",
    memory_count: 0,
    document_count: 0,
    checkpoint_count: 0,
    page_count: 3,
    last_checkpoint_at: null,
    workstream_count: 0,
    open_workstream_count: 0,
    last_worklog_at: null,
    last_event_day: null,
  },
]

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(apiFetch).mockImplementation(async (url: string) => {
    if (url === "/projects") return PROJECTS
    throw new Error(`unscoped topics read: ${url}`)
  })
})

describe("TopicsTab scope", () => {
  it("under all projects offers the projects that hold memories, and reads no topics", async () => {
    useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: null })
    render(<TopicsTab />, { wrapper })
    expect(
      await screen.findByText("Topics open one project at a time"),
    ).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^darkmem/ })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /^docs-only/ })).toBeNull()
    expect(screen.queryByRole("button", { name: /^notes/ })).toBeNull()
    expect(
      vi.mocked(apiFetch).mock.calls.every((call) => call[0] === "/projects"),
    ).toBe(true)
  })

  it("a chooser click sets the global scope", async () => {
    useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: null })
    render(<TopicsTab />, { wrapper })
    await userEvent.click(await screen.findByRole("button", { name: /^darkmem/ }))
    expect(useProjectStore.getState().activeProject).toBe("darkmem")
  })

  it("reads the scoped project's topics, never the hardcoded default", async () => {
    useProjectStore.setState({ activeProject: "darkmem", missingProject: null })
    render(<TopicsTab />, { wrapper })
    await vi.waitFor(() =>
      expect(
        vi.mocked(apiFetch).mock.calls.some((call) =>
          String(call[0]).includes("darkmem"),
        ),
      ).toBe(true),
    )
    expect(
      vi.mocked(apiFetch).mock.calls.some((call) =>
        String(call[0]).includes("default"),
      ),
    ).toBe(false)
  })
})
