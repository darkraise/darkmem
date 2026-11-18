import { describe, it, expect, vi, beforeEach } from "vitest"
import { CodeGlowCanvasStub } from "@/test/code-glow-canvas-stub"
import type { CodeGlowCanvasProps } from "@/features/code/components/code-glow-canvas"
import { render, screen, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.hoisted(() => {
  const g = globalThis as Record<string, unknown>
  g.WebGL2RenderingContext ??= class {}
  g.WebGLRenderingContext ??= class {}
})

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
// The stub imports drawnGraph from the mocked module, so the factory must not
// import the stub itself (it would wait on its own mock); the component looks
// the stub up at render time instead.
vi.mock("@/features/code/components/code-glow-canvas", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/code/components/code-glow-canvas")>()),
  CodeGlowCanvas: (props: CodeGlowCanvasProps) => <CodeGlowCanvasStub {...props} />,
}))

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
  fetch_enabled: false,
  fetch_interval_seconds: 300,
  index_on_commit_enabled: false,
  commit_poll_seconds: 60,
  index_uncommitted: false,
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
    if (path.startsWith("/code/graph/r1")) return Promise.resolve(GRAPH)
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

  it("spells out the counter and stacks its panes below lg", async () => {
    mockApi()
    const { container } = render(
      <RealCodeGraphView
        repoId="r1"
        onRepoChange={vi.fn()}
        onOpenRepositories={vi.fn()}
      />,
      { wrapper },
    )
    await screen.findByText("ingestion")
    expect(screen.getByText(/^\d+ nodes · \d+ edges$/)).toBeInTheDocument()
    expect(screen.queryByText("Layout")).toBeNull()
    expect(screen.queryByRole("group", { name: "Graph layout" })).toBeNull()
    expect(screen.getByText("Colour by")).toBeInTheDocument()
    const heading = screen.getByText("Selected symbol")
    expect(heading.closest("span")).not.toHaveClass("uppercase")
    expect(container.querySelector(".lg\\:flex-row")).not.toBeNull()
    expect(container.querySelector(".md\\:flex-row")).toBeNull()
  })

  it("asks the server for the auto level of detail and draws a small repo whole", async () => {
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
    expect(
      vi.mocked(apiFetch).mock.calls.some(
        ([path]) => path === "/code/graph/r1?level=auto",
      ),
    ).toBe(true)
    expect(screen.queryByRole("region", { name: "Graph level of detail" })).toBeNull()
  })

  describe("a repository folded to files", () => {
    const FOLDED = {
      level: "file",
      requested_level: "auto",
      scope: null,
      auto_limit: 2000,
      stats: {
        files: 5,
        symbols: 4200,
        files_drawn: 3,
        files_without_symbols: 2,
        symbol_edges: 9100,
        file_edges: 2,
        boundary_edges: 0,
      },
      nodes: [
        { id: "pkg/a.py", label: "pkg/a.py", kind: "file", file_path: "pkg/a.py", symbol_count: 2000 },
        { id: "pkg/b.py", label: "pkg/b.py", kind: "file", file_path: "pkg/b.py", symbol_count: 2000 },
        { id: "web/c.ts", label: "web/c.ts", kind: "file", file_path: "web/c.ts", symbol_count: 200 },
      ],
      edges: [
        { source: "pkg/a.py", target: "pkg/b.py", type: "depends_on", properties: { weight: 40, edge_types: { calls: 40 } } },
        { source: "web/c.ts", target: "pkg/a.py", type: "depends_on", properties: { weight: 1, edge_types: { calls: 1 } } },
      ],
    }
    const SCOPED = {
      ...GRAPH,
      level: "symbol",
      requested_level: "auto",
      scope: "pkg/a.py",
      auto_limit: 2000,
      stats: { files: 1, symbols: 2 },
    }

    function mockFolded() {
      vi.mocked(apiFetch).mockImplementation((path: string) => {
        if (path === "/repos") return Promise.resolve([REPO])
        if (path === "/code/graph/r1?level=auto") return Promise.resolve(FOLDED)
        if (path.startsWith("/code/graph/r1?")) return Promise.resolve(SCOPED)
        if (path === "/code/files/r1")
          return Promise.resolve(
            ["pkg/a.py", "pkg/b.py", "web/c.ts", "README.md"].map((file_path, i) => ({
              id: `f${i}`, file_path, language: null, last_commit_sha: "abc", indexed_at: "2026-07-27T00:00:00Z",
            })),
          )
        return Promise.resolve({})
      })
    }

    it("says what is folded and counts files, not symbols", async () => {
      mockFolded()
      render(
        <RealCodeGraphView repoId="r1" onRepoChange={vi.fn()} onOpenRepositories={vi.fn()} />,
        { wrapper },
      )
      const banner = await screen.findByRole("region", { name: "Graph level of detail" })
      expect(banner.textContent).toContain("Folded to files.")
      expect(banner.textContent).toContain(
        "4,200 symbols and 9,100 symbol edges are drawn as 3 files and 2 file → file edges",
      )
      expect(banner.textContent).toContain("2 files that define no symbol are not drawn.")
      expect(screen.getByText("3 files · 2 edges")).toBeInTheDocument()
      expect(screen.getByRole("button", { name: "pkg/a.py (file)" })).toBeInTheDocument()
    })

    it("drills into a folder the server is asked to scope to", async () => {
      mockFolded()
      const user = userEvent.setup()
      render(
        <RealCodeGraphView repoId="r1" onRepoChange={vi.fn()} onOpenRepositories={vi.fn()} />,
        { wrapper },
      )
      await screen.findByRole("region", { name: "Graph level of detail" })
      await user.click(screen.getByRole("combobox", { name: "Drill into a folder" }))
      await user.click(await screen.findByRole("option", { name: /^pkg\/ · 2 files$/ }))

      await screen.findByText("ingestion")
      expect(
        vi.mocked(apiFetch).mock.calls.some(
          ([path]) => path === "/code/graph/r1?level=auto&scope=pkg",
        ),
      ).toBe(true)
    })

    it("opening a drawn file in the explorer shows that file's symbols", async () => {
      mockFolded()
      const user = userEvent.setup()
      render(
        <RealCodeGraphView repoId="r1" onRepoChange={vi.fn()} onOpenRepositories={vi.fn()} />,
        { wrapper },
      )
      await screen.findByRole("region", { name: "Graph level of detail" })
      await user.click(screen.getByRole("button", { name: /^pkg$/ }))
      await user.click(await screen.findByRole("button", { name: /^a\.py/ }))

      const banner = await screen.findByText(/Showing the symbols in/)
      expect(banner.textContent).toContain("pkg/a.py")
      expect(
        vi.mocked(apiFetch).mock.calls.some(
          ([path]) => path === "/code/graph/r1?level=auto&scope=pkg%2Fa.py",
        ),
      ).toBe(true)
      await user.click(screen.getByRole("button", { name: "Up to pkg" }))
      expect(
        vi.mocked(apiFetch).mock.calls.some(
          ([path]) => path === "/code/graph/r1?level=auto&scope=pkg",
        ),
      ).toBe(true)
    })
  })

  it("the filter box narrows the drawn graph and its counter, not only the explorer", async () => {
    mockApi()
    const user = userEvent.setup()
    render(
      <RealCodeGraphView repoId="r1" onRepoChange={vi.fn()} onOpenRepositories={vi.fn()} />,
      { wrapper },
    )
    await screen.findByText("ingestion")
    expect(screen.getByText("3 nodes · 2 edges")).toBeInTheDocument()

    await user.type(
      screen.getByRole("textbox", { name: /Filter the graph and explorer/ }),
      "rrf",
    )
    expect(screen.getByText("1 of 3 nodes · 0 of 2 edges")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "rrf_fuse (function)" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "process_batch (function)" })).toBeNull()

    await user.clear(screen.getByRole("textbox", { name: /Filter the graph and explorer/ }))
    await user.type(
      screen.getByRole("textbox", { name: /Filter the graph and explorer/ }),
      "zzznomatch",
    )
    expect(screen.getByText("0 of 3 nodes · 0 of 2 edges")).toBeInTheDocument()
  })
})
