import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactElement, ReactNode } from "react"

vi.hoisted(() => {
  const g = globalThis as Record<string, unknown>
  g.WebGL2RenderingContext ??= class {}
  g.WebGLRenderingContext ??= class {}
})

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))
vi.mock("@/features/code/components/code-glow-canvas", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/code/components/code-glow-canvas")>()),
  CodeGlowCanvas: () => null,
}))
vi.mock("@/features/chat/components/chat-overlay", () => ({
  ChatOverlay: () => null,
}))
vi.mock("@/features/graph/components/graph-2d-renderer", () => ({
  Graph2DRenderer: () => null,
}))
vi.mock("@/features/graph/components/graph-3d-renderer", () => ({
  Graph3DRenderer: () => null,
}))
vi.mock("@/features/graph/components/mini-graph", () => ({
  MiniGraph: () => null,
}))

import { apiFetch } from "@/lib/api"
import { ProjectSwitcher } from "../project-switcher"
import { RealCodeGraphView } from "@/features/code/components/real-code-graph-view"
import { RealWikiView } from "@/features/code/components/real-wiki-view"
import { LLMTab } from "@/features/settings/components/llm-tab"
import { RealMemoryGraphPage } from "@/features/memory-graph/components/real-memory-graph-page"
import { DEFAULT_PROJECT, useProjectStore } from "@/stores/project-store"

const noop = () => {}

const REPO = {
  id: "r1",
  name: "kept-repository",
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

const PROJECT = {
  name: "kept-project",
  kind: "project",
  memory_count: 3,
  document_count: 0,
  page_count: 0,
  workstream_count: 0,
  open_workstream_count: 0,
  last_worklog_at: null,
  last_event_day: null,
}

interface Surface {
  name: string
  /** The request whose state the surface renders. */
  path: string
  element: () => ReactElement
  failureTitle: RegExp
  /** What a successful empty load serves, and the copy it shows. */
  empty?: { body: unknown; copy: RegExp }
  /** What a successful load serves, and the text it shows; `others` answers
   *  the surface's other requests by path prefix. */
  loaded?: { body: unknown; copy: RegExp; others?: Record<string, unknown> }
  /** Reaching the surface takes a click (the switcher lives in a popover). */
  open?: (user: ReturnType<typeof userEvent.setup>) => Promise<void>
}

const SURFACES: Surface[] = [
  {
    name: "Code Graph",
    path: "/repos",
    element: () => (
      <RealCodeGraphView
        repoId={undefined}
        onRepoChange={noop}
        onOpenRepositories={noop}
      />
    ),
    failureTitle: /repositories could not be loaded/i,
    empty: { body: [], copy: /no repositories indexed yet/i },
    loaded: {
      body: [REPO],
      copy: /kept-repository/,
      others: { "/code/graph": { nodes: [], edges: [] } },
    },
  },
  {
    name: "Wiki",
    path: "/repos",
    element: () => <RealWikiView repoId={undefined} onRepoChange={noop} />,
    failureTitle: /repositories could not be loaded/i,
    empty: { body: [], copy: /no repositories indexed yet/i },
    loaded: {
      body: [REPO],
      copy: /kept-repository/,
      others: {
        "/code/wiki": {
          repo_name: "kept-repository",
          overview: "kept overview",
          modules: [],
          total_modules: 0,
          total_files: 0,
        },
      },
    },
  },
  {
    name: "the project switcher",
    path: "/projects",
    element: () => <ProjectSwitcher />,
    failureTitle: /projects could not be loaded/i,
    empty: { body: [], copy: /no project holds anything yet/i },
    loaded: { body: [PROJECT], copy: /kept-project/ },
    open: async (user) => {
      await user.click(screen.getByRole("button", { name: /project scope/i }))
    },
  },
  {
    name: "the LLM tab",
    path: "/config/llm",
    element: () => <LLMTab />,
    failureTitle: /llm configuration could not be loaded/i,
  },
  {
    name: "the graph page",
    path: "/graph/unified",
    element: () => <RealMemoryGraphPage />,
    failureTitle: /the graph could not be loaded/i,
    empty: {
      body: { memories: [], clusters: {}, cluster_names: {}, similarity_edges: [] },
      copy: /no graph yet/i,
    },
  },
]

type Answer = "pending" | "reject" | { body: unknown }

function serve(surface: Surface, answer: Answer) {
  vi.mocked(apiFetch).mockImplementation(((path: string) => {
    if (!path.startsWith(surface.path)) return Promise.resolve([])
    if (answer === "pending") return new Promise(() => {})
    if (answer === "reject") return Promise.reject(new Error("HTTP 500"))
    return Promise.resolve(answer.body)
  }) as typeof apiFetch)
}

function callsTo(path: string) {
  return vi
    .mocked(apiFetch)
    .mock.calls.filter(([p]) => String(p).startsWith(path)).length
}

async function show(surface: Surface) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
  const user = userEvent.setup()
  const view = render(surface.element(), { wrapper })
  await surface.open?.(user)
  return { user, view, qc }
}

describe("load-failure states", () => {
  beforeEach(() => {
    useProjectStore.setState({ activeProject: DEFAULT_PROJECT, missingProject: null })
  })
  afterEach(() => {
    vi.mocked(apiFetch).mockReset()
  })

  it.each(SURFACES)("shows a skeleton while loading: $name", async (surface) => {
    serve(surface, "pending")
    await show(surface)

    await waitFor(() =>
      expect(document.querySelector(".dr-skeleton")).not.toBeNull(),
    )
    expect(screen.queryByText(/no .* yet/i)).toBeNull()
    expect(document.querySelector(".dr-empty-state")).toBeNull()
  })

  it.each(SURFACES)("shows Retry after a failed load: $name", async (surface) => {
    serve(surface, "reject")
    const { user } = await show(surface)

    expect(await screen.findByText(surface.failureTitle)).toBeInTheDocument()
    expect(document.querySelector(".dr-empty-state")).not.toBeNull()
    expect(screen.queryByText(/no .* yet/i)).toBeNull()

    const before = callsTo(surface.path)
    await user.click(screen.getByRole("button", { name: "Retry" }))
    await waitFor(() => expect(callsTo(surface.path)).toBe(before + 1))
  })

  it.each(SURFACES.filter((s) => s.empty))(
    "shows the empty copy only after a successful empty load: $name",
    async (surface) => {
      serve(surface, { body: surface.empty!.body })
      await show(surface)

      expect(await screen.findByText(surface.empty!.copy)).toBeInTheDocument()
      expect(screen.queryByRole("button", { name: "Retry" })).toBeNull()
      expect(screen.queryByText(surface.failureTitle)).toBeNull()
    },
  )

  it.each(SURFACES.filter((s) => s.loaded))(
    "a failed refetch keeps what was loaded: $name",
    async (surface) => {
      const others = Object.entries(surface.loaded!.others ?? {})
      vi.mocked(apiFetch).mockImplementation(((path: string) => {
        if (path.startsWith(surface.path)) return Promise.resolve(surface.loaded!.body)
        const other = others.find(([prefix]) => path.startsWith(prefix))
        return Promise.resolve(other ? other[1] : [])
      }) as typeof apiFetch)
      const { qc } = await show(surface)
      expect((await screen.findAllByText(surface.loaded!.copy)).length).toBeGreaterThan(0)

      vi.mocked(apiFetch).mockImplementation((() =>
        Promise.reject(new Error("HTTP 500"))) as typeof apiFetch)
      await qc.refetchQueries()
      await waitFor(() =>
        expect(
          qc.getQueryCache().findAll().some((q) => q.state.status === "error" && q.state.data !== undefined),
        ).toBe(true),
      )

      expect(screen.getAllByText(surface.loaded!.copy).length).toBeGreaterThan(0)
      expect(screen.queryByText(surface.failureTitle)).toBeNull()
      expect(screen.queryByText(/failed to load/i)).toBeNull()
    },
  )

  it("the LLM tab invents no values", async () => {
    const llm = SURFACES.find((s) => s.path === "/config/llm")!
    serve(llm, "reject")
    await show(llm)

    expect(await screen.findByText(llm.failureTitle)).toBeInTheDocument()
    expect(screen.queryByText(/qwen2\.5:3b/)).toBeNull()
    expect(screen.queryByText(/ollama-local/)).toBeNull()
    expect(screen.queryByLabelText(/^Edit /)).toBeNull()
    expect(screen.queryByText("verification")).toBeNull()
  })
})
