import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ComponentProps, ReactNode } from "react"
import type Graph from "graphology"

const h = vi.hoisted(() => {
  const GL = { FLOAT: 0x1406, UNSIGNED_BYTE: 0x1401, TRIANGLES: 0x0004, ONE: 1, ONE_MINUS_SRC_ALPHA: 0x0303 }
  Object.assign(globalThis, { WebGLRenderingContext: GL, WebGL2RenderingContext: GL })
  return { sigmas: [] as Array<{ container: HTMLElement; refresh: () => void }> }
})

vi.mock("sigma", () => {
  class FakeCamera {
    x = 0.5
    y = 0.5
    ratio = 1
    angle = 0
    on() { return this }
    removeListener() { return this }
    off() { return this }
    setState(s: Record<string, number>) { Object.assign(this, s); return this }
    animate(s: Record<string, number>) { this.setState(s); return Promise.resolve() }
    animatedZoom() { return Promise.resolve() }
    animatedUnzoom() { return Promise.resolve() }
    animatedReset() { return Promise.resolve() }
    isAnimated() { return false }
  }
  class FakeSigma {
    camera = new FakeCamera()
    constructor(public graph: Graph, public container: HTMLElement, public settings: Record<string, unknown>) {
      h.sigmas.push(this as never)
    }
    getCamera() { return this.camera }
    getGraph() { return this.graph }
    getContainer() { return this.container }
    on() { return this }
    getDimensions() { return { width: 800, height: 600 } }
    getNodeDisplayData(id: string) {
      return { x: this.graph.getNodeAttribute(id, "x"), y: this.graph.getNodeAttribute(id, "y"), size: 4 }
    }
    graphToViewport(p: unknown) { return p }
    framedGraphToViewport(p: unknown) { return p }
    viewportToFramedGraph(p: unknown) { return p }
    scaleSize(s: number) { return s }
    scheduleRender() {}
    resize() {}
    refresh() {}
    kill() {}
  }
  return { default: FakeSigma }
})
vi.mock("graphology-layout-forceatlas2/worker", () => ({
  default: class {
    start() {}
    stop() {}
    kill() {}
    isRunning() { return false }
  },
}))
vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))
vi.mock("@/features/settings/components/api-keys-card", () => ({ ApiKeysCard: () => null }))
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>()
  return { ...actual, apiFetch: vi.fn() }
})
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({ children, to: _to, params: _params, ...rest }: { children?: ReactNode; [key: string]: unknown }) => (
    <a {...rest}>{children}</a>
  ),
}))

import { apiFetch, ApiError } from "@/lib/api"
import { useDetailLevel } from "@/components/darkmem"
import { BackupsTab } from "@/features/settings/components/backups-tab"
import { LLMTab } from "@/features/settings/components/llm-tab"
import { DistributionTab } from "@/features/settings/components/distribution-tab"
import { ChatSidebar } from "@/features/chat/components/chat-sidebar"
import { ReviewTab } from "@/features/knowledge/components/review-tab"
import { CodeGlowCanvas } from "@/features/code/components/code-glow-canvas"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.clearAllMocks()
  h.sigmas.length = 0
  useDetailLevel.setState({ level: "advanced" })
})
afterEach(() => {
  vi.restoreAllMocks()
  vi.mocked(apiFetch).mockReset()
})

// ---------------------------------------------------------------- A29

const LOCAL = {
  name: "disk",
  kind: "local" as const,
  enabled: true,
  retention_keep: 14,
  attachments_retention_keep: 3,
  age_recipient: null,
  ssh: null,
  s3: null,
}

describe("A29: Backups failed reads and Run now", () => {
  function serve(broken: string[], trigger?: ApiError) {
    const down = new Set(broken)
    return vi.mocked(apiFetch).mockImplementation(async (path: string) => {
      for (const prefix of down) {
        if (path.startsWith(prefix)) throw new ApiError("Internal server error", 500)
      }
      if (trigger && path === "/jobs/backup_ship/trigger") throw trigger
      if (path.startsWith("/config/backup-destinations")) return { destinations: [LOCAL] } as never
      if (path.startsWith("/events")) return { items: [], total: 0 } as never
      if (path.startsWith("/backups/inventory")) return { destinations: [] } as never
      return {} as never
    })
  }
  const callsTo = (mock: ReturnType<typeof serve>, prefix: string) =>
    mock.mock.calls.filter(([path]) => String(path).startsWith(prefix)).length

  it.each([
    ["destinations", "/config/backup-destinations"],
    ["inventory", "/backups/inventory"],
    ["outcomes", "/events?event_type=backup_shipped"],
  ])("A29: a failed %s read shows the failed state with Retry, and Retry re-reads", async (_name, prefix) => {
    const mock = serve([prefix])
    render(<BackupsTab />, { wrapper })

    expect(await screen.findByText(/could not be loaded/i)).toBeInTheDocument()
    const retry = screen.getByRole("button", { name: "Retry" })
    const before = callsTo(mock, prefix)
    fireEvent.click(retry)
    await waitFor(() => expect(callsTo(mock, prefix)).toBeGreaterThan(before))
  })

  it("A29: a 500 from Run now is not reported as already in progress", async () => {
    serve([], new ApiError("Dump failed", 500))
    render(<BackupsTab />, { wrapper })
    fireEvent.click(await screen.findByRole("button", { name: /run now/i }))
    expect(await screen.findByText("Dump failed")).toBeInTheDocument()
    expect(screen.queryByText(/already in progress/i)).toBeNull()
  })
})

// ---------------------------------------------------------------- A30

describe("A30: the stopped-processing banner on Settings -> LLM", () => {
  const STOPPED =
    "Processing is stopped: the model setup failed at startup. Captures are still queued. Save a working model configuration to start it."
  const CONFIG = {
    classification: {
      provider_name: "deepseek-primary",
      base_url: "https://api.deepseek.com/v1",
      model: "deepseek-v4-flash",
      api_key: "***",
      dimensions: null,
      reasoning: false,
      api_kind: "deepseek",
      params: {},
      classifier_kind: "llm",
    },
  }
  function serve(state: string) {
    vi.mocked(apiFetch).mockImplementation(async (path: string) =>
      (path.endsWith("/probe-models") ? { models: [], fetched_via: "", error: null } : CONFIG) as never,
    )
    return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (String(input) === "/health") {
        return new Response(
          JSON.stringify({
            status: "ok",
            pipeline: state === "ok",
            services: { pgvector: true, llm: true },
            classifier_unavailable: false,
            pipeline_state: state,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        )
      }
      return new Response("{}", { status: 404 })
    })
  }

  it("A30: shows the banner while /health answers failed_at_boot", async () => {
    serve("failed_at_boot")
    render(<LLMTab />, { wrapper })
    expect(await screen.findByText(STOPPED)).toBeInTheDocument()
  })

  it.each(["ok", "not_configured"])("A30: shows no banner while /health answers %s", async (state) => {
    const spy = serve(state)
    render(<LLMTab />, { wrapper })
    await waitFor(() => expect(spy.mock.calls.some((c) => String(c[0]) === "/health")).toBe(true))
    await waitFor(() => expect(screen.getAllByText("deepseek-v4-flash").length).toBeGreaterThan(0))
    expect(screen.queryByText(STOPPED)).toBeNull()
  })
})

// ---------------------------------------------------------------- A31

describe("A31: the code canvas follows its container", () => {
  it("A31: shrinking the container refreshes the renderer with no window resize event", () => {
    const observers: Array<{ callback: ResizeObserverCallback; observed: Element[] }> = []
    vi.stubGlobal(
      "ResizeObserver",
      class {
        entry: (typeof observers)[number]
        constructor(callback: ResizeObserverCallback) {
          this.entry = { callback, observed: [] }
          observers.push(this.entry)
        }
        observe(el: Element) {
          this.entry.observed.push(el)
        }
        unobserve() {}
        disconnect() {}
      },
    )
    const windowResizes = vi.fn()
    window.addEventListener("resize", windowResizes)
    try {
      const graph = {
        repo_id: "r1",
        nodes: [
          { id: "a", name: "a.py", kind: "file" as const, file: "a.py", community: "c1" },
          { id: "b", name: "load", kind: "function" as const, file: "a.py", community: "c1" },
        ],
        edges: [{ source: "a", target: "b", type: "CONTAINS" }],
        communities: [{ id: "c1", label: "one", chart: 1 as const }],
        processes: [],
      }
      const props: ComponentProps<typeof CodeGlowCanvas> = {
        graph,
        colorBy: "community",
        selectedId: null,
        onSelect: () => {},
        visibleIds: null,
        blastIds: null,
        highlightCommunity: null,
        processIds: null,
      }
      render(<CodeGlowCanvas {...props} />)
      const sigma = h.sigmas[h.sigmas.length - 1]!
      const refresh = vi.spyOn(sigma, "refresh")
      const watching = observers.filter((o) => o.observed.includes(sigma.container))
      expect(watching.length).toBeGreaterThan(0)
      for (const o of watching) {
        o.callback(
          [{ target: sigma.container, contentRect: { width: 320, height: 600 } } as unknown as ResizeObserverEntry],
          {} as ResizeObserver,
        )
      }
      expect(refresh).toHaveBeenCalled()
      expect(windowResizes).not.toHaveBeenCalled()
    } finally {
      window.removeEventListener("resize", windowResizes)
      vi.unstubAllGlobals()
    }
  })
})

// ---------------------------------------------------------------- A38

const CONSEQUENCE = {
  score: 0.42,
  tier: 1,
  retrieval_frequency: {
    source_memories: 3,
    peak_access_count: 12,
    last_accessed: "2026-07-01T00:00:00Z",
    decayed_access: 0.41,
    half_life_days: 30,
    weight: 0.5,
    component: 0.2,
  },
  subject_salience: { neighbour_count: 4, weight: 0.5, component: 0.15 },
  staleness: {
    stale: false,
    label: "fresh",
    dispute_opened_at: null,
    dispute_age_days: null,
    threshold_days: 14,
  },
}


const FACT_ITEM = {
  id: "f1",
  subject_name: "darkmem",
  object_name: "postgres",
  rel_type: "USES",
  fact: "darkmem uses postgres",
  project: "darkmem",
  valid_at: null,
  invalid_at: null,
  expired_at: null,
  verification_status: "disputed",
  confidence: 0.4,
  review_state: "open",
  demotion_pending_since: null,
  reason: "disputed",
  evidence: null,
  consequence: CONSEQUENCE,
  created_at: "2026-08-01T00:00:00Z",
}

describe("A38: UI-5 and UI-6", () => {
  it("A38: a chat row's Delete is not a descendant of its select control", () => {
    render(
      <ChatSidebar
        conversations={[
          {
            id: "c1",
            title: "Reranker defaults",
            created_at: "2026-10-01T00:00:00Z",
            updated_at: "2026-10-01T00:00:00Z",
            is_archived: false,
            message_count: 4,
          },
        ]}
        activeId={null}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    const select = screen.getByRole("button", { name: /^Reranker defaults/ })
    const remove = screen.getByRole("button", { name: "Delete conversation Reranker defaults" })
    expect(select.contains(remove)).toBe(false)
    expect(remove.contains(select)).toBe(false)
    expect(select.querySelector("button")).toBeNull()
    expect(select.parentElement).toBe(remove.parentElement)
  })

  it("A38: the review queue's fact row renders no block element inside a paragraph", async () => {
    vi.mocked(apiFetch).mockImplementation(async (url: string) => {
      if (url.startsWith("/review-queue/counts")) return { facts: 1, articles: 0 } as never
      if (url.startsWith("/review-queue/facts")) return { items: [FACT_ITEM], total: 1, limit: 10, offset: 0 } as never
      return { items: [], total: 0, limit: 10, offset: 0 } as never
    })
    const { container } = render(<ReviewTab />, { wrapper })
    await screen.findByText("darkmem uses postgres")
    const blocks = "div, p, ul, ol, li, table, section, article, header, footer, form, pre, blockquote, h1, h2, h3, h4, h5, h6"
    for (const p of container.querySelectorAll("p")) {
      expect(p.querySelector(blocks)).toBeNull()
    }
  })

  it("A38: Settings -> Distribution renders no inject log", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      targets: [{ tool: "test-tool-alpha", context_file: "ALPHA_CONTEXT.md", mcp_config: ".alpha/mcp.json" }],
      rejected: [],
    } as never)
    render(<DistributionTab />, { wrapper })
    await screen.findByText("test-tool-alpha")
    expect(screen.queryByText(/inject log/i)).toBeNull()
    const eventReads = vi
      .mocked(apiFetch)
      .mock.calls.map(([path]) => String(path))
      .filter((path) => /inject/.test(path) && path.startsWith("/events"))
    expect(eventReads).toEqual([])
  })
})

export type _Unused = [typeof within, typeof userEvent]
