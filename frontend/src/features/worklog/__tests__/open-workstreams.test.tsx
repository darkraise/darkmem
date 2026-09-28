import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({
    children,
    params,
    search,
  }: {
    children: ReactNode
    params: { project: string }
    search: { tab: string; workstream: string }
  }) => (
    <a href={`/projects/${params.project}?tab=${search.tab}&workstream=${search.workstream}`}>
      {children}
    </a>
  ),
}))

import { apiFetch } from "@/lib/api"
import { OpenWorkstreams } from "../components/open-workstreams"

function project(name: string, open: number, kind: "project" | "personal" = "project") {
  return {
    name,
    kind,
    memory_count: 0,
    document_count: 0,
    page_count: 0,
    workstream_count: open,
    open_workstream_count: open,
    last_worklog_at: null,
    last_event_day: null,
  }
}

const OPEN = {
  id: "w1",
  project: "darkmem",
  key: "plan-a",
  title: "Plan A",
  client: null,
  state: "open",
  closed_at: null,
  retain: false,
  properties: {},
  last_entry_at: "2026-09-28T10:00:00Z",
  created_at: "2026-09-28T08:00:00Z",
  updated_at: "2026-09-28T10:00:00Z",
}

function entry(seq: number, kind: string, body: string) {
  return {
    id: `e${seq}`,
    workstream_id: "w1",
    seq,
    run_key: "r",
    kind,
    body,
    properties: {},
    created_at: "2026-09-28T10:00:00Z",
  }
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("OpenWorkstreams", () => {
  it("lists every project's open workstreams with their latest entry", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/projects") {
        return Promise.resolve([
          project("darkmem", 1),
          project("quiet", 0),
          project("notes", 1, "personal"),
        ])
      }
      if (path === "/worklog/workstreams?project=darkmem&state=open&limit=50") {
        return Promise.resolve({ items: [OPEN], next_before: null })
      }
      if (path === "/worklog/resume?project=darkmem&workstream=plan-a") {
        return Promise.resolve({
          workstream: OPEN,
          checkpoint: entry(4, "checkpoint", "## Halfway\n\nmore"),
          notes: [entry(2, "note", "a note")],
          notes_truncated: false,
          ledger: [entry(5, "ledger", "Task 3: done\n")],
        })
      }
      return Promise.reject(new Error(`unrouted ${path}`))
    })
    render(<OpenWorkstreams />, { wrapper })

    const link = await screen.findByRole("link", { name: /Plan A/ })
    expect(link).toHaveAttribute("href", "/projects/darkmem?tab=progress&workstream=plan-a")
    expect(await screen.findByText("ledger: Task 3: done")).toBeInTheDocument()
    const asked = vi.mocked(apiFetch).mock.calls.map(([path]) => String(path))
    expect(asked.some((path) => path.includes("project=quiet"))).toBe(false)
    expect(asked.some((path) => path.includes("project=notes"))).toBe(false)
  })

  it("says so when no project has an open workstream", async () => {
    vi.mocked(apiFetch).mockResolvedValue([project("quiet", 0)])
    render(<OpenWorkstreams />, { wrapper })
    expect(await screen.findByText("No open workstreams")).toBeInTheDocument()
  })
})
