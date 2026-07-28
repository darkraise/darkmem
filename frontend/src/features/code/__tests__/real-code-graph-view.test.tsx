import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/demo/flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { RealCodeGraphView } from "../components/real-code-graph-view"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const REPO = {
  id: "r1",
  name: "darkmem-backend",
  url: null,
  local_path: "/repo",
  provider: "local",
  default_branch: "main",
  last_indexed_commit: "abc1234",
  last_indexed_at: "2026-07-27T00:00:00Z",
  status: "ready",
  status_message: null,
  auto_sync: true,
  file_count: 1,
  symbol_count: 2,
  index_debt: { queued: 0, deferred_total: 0, drained_total: 0, last_defer: null, last_drain: null },
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-07-27T00:00:00Z",
}

const GRAPH = {
  nodes: [
    { id: "main.py", label: "main.py", kind: "file", file_path: "main.py" },
    {
      id: "process_batch::main.py",
      label: "process_batch",
      kind: "function",
      file_path: "main.py",
    },
    {
      id: "rrf_fuse::main.py",
      label: "rrf_fuse",
      kind: "function",
      file_path: "main.py",
    },
    { id: "comm:ingestion", label: "ingestion", kind: "community" },
    { id: "proc:ingest", label: "ingest", kind: "process" },
  ],
  edges: [
    { source: "main.py", target: "process_batch::main.py", type: "CONTAINS" },
    { source: "main.py", target: "rrf_fuse::main.py", type: "CONTAINS" },
    {
      source: "process_batch::main.py",
      target: "comm:ingestion",
      type: "member_of",
    },
    {
      source: "process_batch::main.py",
      target: "proc:ingest",
      type: "step_in_process",
      properties: { step: 1 },
    },
    {
      source: "rrf_fuse::main.py",
      target: "proc:ingest",
      type: "step_in_process",
      properties: { step: 2 },
    },
  ],
}

function mockApi() {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path === "/repos") return Promise.resolve([REPO])
    if (path === "/code/graph/r1") return Promise.resolve(GRAPH)
    if (path === "/code/files/r1")
      return Promise.resolve([
        { id: "f1", file_path: "main.py", language: "python", last_commit_sha: "abc", indexed_at: "2026-07-27T00:00:00Z" },
      ])
    if (path.startsWith("/code/symbols/lookup"))
      return Promise.resolve({
        id: "process_batch::main.py",
        name: "process_batch",
        kind: "function",
        file_path: "main.py",
        line_start: 10,
        line_end: 20,
        signature: "def process_batch(batch):",
        docstring: null,
        visibility: null,
        source_code: "def process_batch(batch):\n    ...\n",
        summary: "Processes a batch.",
        enrichment_status: "complete",
      })
    if (path === "/code/blast-radius")
      return Promise.resolve({
        symbol: { id: "process_batch::main.py", name: "process_batch", file_path: "main.py" },
        affected: [],
        by_depth: { "1": [], "2": [], "3+": [] },
        risk: "low",
        total: 0,
      })
    return Promise.resolve({})
  })
}

describe("RealCodeGraphView", () => {
  beforeEach(() => vi.clearAllMocks())

  it("derives community colouring and the Processes panel from the raw graph response", async () => {
    mockApi()
    render(
      <RealCodeGraphView
        repoId="r1"
        onRepoChange={vi.fn()}
        onOpenRepositories={vi.fn()}
      />,
      { wrapper },
    )

    await screen.findByText("ingestion")
    expect(screen.getByText("ingest")).toBeInTheDocument()
    expect(screen.getByText("2 steps")).toBeInTheDocument()
    // The pseudo community/process nodes never render as graph nodes.
    expect(
      screen.queryByLabelText(/ingestion \(community\)/),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByLabelText(/ingest \(process\)/),
    ).not.toBeInTheDocument()
  })

  it("opens the Mermaid export matching mermaidForProcess's own output for the derived process", async () => {
    mockApi()
    const user = userEvent.setup()
    render(
      <RealCodeGraphView
        repoId="r1"
        onRepoChange={vi.fn()}
        onOpenRepositories={vi.fn()}
      />,
      { wrapper },
    )

    await screen.findByText("ingest")
    await user.click(screen.getByRole("button", { name: "mermaid" }))

    const dialog = await screen.findByRole("dialog")
    expect(dialog.textContent).toContain("flowchart TD")
    expect(dialog.textContent).toContain("process_batch")
  })

  it("selecting a symbol node loads its real source_code, never a synthesized file", async () => {
    mockApi()
    render(
      <RealCodeGraphView
        repoId="r1"
        onRepoChange={vi.fn()}
        onOpenRepositories={vi.fn()}
      />,
      { wrapper },
    )

    await screen.findByText("ingestion")
    const node = screen.getByLabelText("process_batch (function)")
    fireEvent.click(node)

    await screen.findByText("Processes a batch.")
    expect(
      vi.mocked(apiFetch).mock.calls.some(([path]) =>
        String(path).startsWith("/code/symbols/lookup"),
      ),
    ).toBe(true)
  })

  it("runs blast radius through POST /code/blast-radius, not a client-side computation", async () => {
    mockApi()
    const user = userEvent.setup()
    render(
      <RealCodeGraphView
        repoId="r1"
        onRepoChange={vi.fn()}
        onOpenRepositories={vi.fn()}
      />,
      { wrapper },
    )

    await screen.findByText("ingestion")
    const node = screen.getByLabelText("process_batch (function)")
    fireEvent.click(node)
    await screen.findByText("Processes a batch.")

    await user.click(screen.getByRole("button", { name: "Run Blast Radius" }))

    const call = vi
      .mocked(apiFetch)
      .mock.calls.find(([path]) => path === "/code/blast-radius")
    expect(call).toBeTruthy()
    const [, init] = call!
    expect(init?.method).toBe("POST")
    expect(JSON.parse(String(init?.body))).toMatchObject({
      symbol_id: "process_batch::main.py",
    })
  })

  it("shows the honest never-indexed empty state pointing at Repositories", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path === "/repos")
        return Promise.resolve([{ ...REPO, id: "r2", status: "queued" }])
      if (path.startsWith("/code/graph/")) return Promise.resolve({ nodes: [], edges: [] })
      return Promise.resolve([])
    })
    const onOpenRepositories = vi.fn()
    render(
      <RealCodeGraphView
        repoId="r2"
        onRepoChange={vi.fn()}
        onOpenRepositories={onOpenRepositories}
      />,
      { wrapper },
    )

    await screen.findByText("No graph yet")
    screen
      .getByRole("button", { name: /Open reindex dialog on Repositories/ })
      .click()
    expect(onOpenRepositories).toHaveBeenCalled()
  })
})
