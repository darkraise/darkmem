import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type Graph from "graphology"
import type { ComponentProps, ReactNode } from "react"

const h = vi.hoisted(() => {
  const GL = { FLOAT: 0x1406, UNSIGNED_BYTE: 0x1401, TRIANGLES: 0x0004, ONE: 1, ONE_MINUS_SRC_ALPHA: 0x0303 }
  Object.assign(globalThis, { WebGLRenderingContext: GL, WebGL2RenderingContext: GL })
  return { sigmas: [] as FakeSigmaLike[], workers: [] as { running: boolean }[] }
})

interface FakeSigmaLike {
  graph: Graph
  settings: Record<string, unknown>
  camera: {
    x: number
    y: number
    ratio: number
    angle: number
    setState(s: Partial<{ x: number; y: number; ratio: number; angle: number }>): unknown
  }
  killed: boolean
  emit(event: string, payload?: unknown): void
}

vi.mock("sigma", () => {
  class FakeCamera {
    x = 0.5
    y = 0.5
    ratio = 1
    angle = 0
    private listeners = new Set<() => void>()
    on(_: string, fn: () => void) {
      this.listeners.add(fn)
      return this
    }
    removeListener(_: string, fn: () => void) {
      this.listeners.delete(fn)
      return this
    }
    off(_: string, fn: () => void) {
      return this.removeListener(_, fn)
    }
    setState(s: Partial<{ x: number; y: number; ratio: number; angle: number }>) {
      Object.assign(this, s)
      for (const fn of this.listeners) fn()
      return this
    }
    animate(s: Partial<{ x: number; y: number; ratio: number; angle: number }>) {
      this.setState(s)
      return Promise.resolve()
    }
    animatedZoom(o: { factor: number }) {
      return this.animate({ ratio: this.ratio / o.factor })
    }
    animatedUnzoom(o: { factor: number }) {
      return this.animate({ ratio: this.ratio * o.factor })
    }
    animatedReset() {
      return this.animate({ x: 0.5, y: 0.5, ratio: 1, angle: 0 })
    }
    isAnimated() {
      return false
    }
  }
  class FakeSigma {
    camera = new FakeCamera()
    killed = false
    handlers = new Map<string, Array<(p?: unknown) => void>>()
    constructor(
      public graph: Graph,
      public container: HTMLElement,
      public settings: Record<string, unknown>,
    ) {
      h.sigmas.push(this as unknown as FakeSigmaLike)
    }
    getCamera() {
      return this.camera
    }
    getGraph() {
      return this.graph
    }
    getContainer() {
      return this.container
    }
    on(event: string, fn: (p?: unknown) => void) {
      this.handlers.set(event, [...(this.handlers.get(event) ?? []), fn])
      return this
    }
    emit(event: string, payload?: unknown) {
      for (const fn of this.handlers.get(event) ?? []) fn(payload)
    }
    getDimensions() {
      return { width: 800, height: 600 }
    }
    getNodeDisplayData(id: string) {
      if (!this.graph.hasNode(id)) return undefined
      return { x: this.graph.getNodeAttribute(id, "x"), y: this.graph.getNodeAttribute(id, "y"), size: 4 }
    }
    graphToViewport(p: { x: number; y: number }) {
      return p
    }
    framedGraphToViewport(p: { x: number; y: number }) {
      const c = this.camera
      return { x: 400 + ((p.x - c.x) * 800) / c.ratio, y: 300 + ((p.y - c.y) * 600) / c.ratio }
    }
    viewportToFramedGraph(p: { x: number; y: number }) {
      return { x: this.camera.x + (p.x - 400) / 800, y: this.camera.y + (p.y - 300) / 600 }
    }
    scaleSize(s: number) {
      return s
    }
    scheduleRender() {}
    refresh() {}
    kill() {
      this.killed = true
      this.emit("kill")
    }
  }
  return { default: FakeSigma }
})

vi.mock("graphology-layout-forceatlas2/worker", () => ({
  default: class {
    running = false
    constructor() {
      h.workers.push(this)
    }
    start() {
      this.running = true
    }
    stop() {
      this.running = false
    }
    kill() {
      this.running = false
    }
    isRunning() {
      return this.running
    }
  },
}))

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { CodeGlowCanvas } from "../components/code-glow-canvas"
import { RealCodeGraphView } from "../components/real-code-graph-view"

const GRAPH = {
  repo_id: "r1",
  nodes: [
    { id: "a", name: "a.py", kind: "file" as const, file: "a.py", community: "c1" },
    { id: "b", name: "load", kind: "function" as const, file: "a.py", community: "c1" },
    { id: "c", name: "save", kind: "function" as const, file: "a.py", community: "c2" },
  ],
  edges: [
    { source: "a", target: "b", type: "CONTAINS" },
    { source: "a", target: "c", type: "CONTAINS" },
  ],
  communities: [
    { id: "c1", label: "one", chart: 1 as const },
    { id: "c2", label: "two", chart: 2 as const },
  ],
  processes: [],
}

type Props = ComponentProps<typeof CodeGlowCanvas>
const base: Props = {
  graph: GRAPH,
  colorBy: "community",
  selectedId: null,
  onSelect: () => {},
  visibleIds: null,
  blastIds: null,
  highlightCommunity: null,
  processIds: null,
}
const last = () => h.sigmas[h.sigmas.length - 1]!

beforeEach(() => {
  h.sigmas.length = 0
  h.workers.length = 0
})

describe("CodeGlowCanvas camera", () => {
  it("runs a host command against the live camera, wherever the reader moved it", () => {
    const { rerender } = render(<CodeGlowCanvas {...base} />)
    const camera = last().camera
    camera.setState({ ratio: 0.2, x: 0.9 })
    rerender(<CodeGlowCanvas {...base} cameraCommand={{ action: { type: "zoom", factor: 1.25 } }} />)
    expect(camera.ratio).toBeCloseTo(0.16)
    rerender(<CodeGlowCanvas {...base} cameraCommand={{ action: { type: "fit" } }} />)
    expect(camera).toMatchObject({ x: 0.5, y: 0.5, ratio: 1 })
  })

  it("runs the same command twice when the host sends it twice", () => {
    const { rerender } = render(<CodeGlowCanvas {...base} />)
    const camera = last().camera
    rerender(<CodeGlowCanvas {...base} cameraCommand={{ action: { type: "zoom", factor: 2 } }} />)
    rerender(<CodeGlowCanvas {...base} cameraCommand={{ action: { type: "zoom", factor: 2 } }} />)
    expect(camera.ratio).toBeCloseTo(0.25)
  })

  it("moves to a node picked outside the canvas but not to one clicked on it", () => {
    const onSelect = vi.fn()
    const { rerender } = render(<CodeGlowCanvas {...base} onSelect={onSelect} />)
    const sigma = last()
    sigma.emit("clickNode", { node: "b" })
    expect(onSelect).toHaveBeenCalledWith("b")
    rerender(<CodeGlowCanvas {...base} onSelect={onSelect} selectedId="b" />)
    expect(sigma.camera.ratio).toBe(1)
    rerender(<CodeGlowCanvas {...base} onSelect={onSelect} selectedId="c" />)
    expect(sigma.camera.ratio).toBeCloseTo(0.15)
    expect(sigma.camera.x).toBe(sigma.graph.getNodeAttribute("c", "x"))
  })
})

describe("CodeGlowCanvas rebuilds", () => {
  it("keeps settled positions and the view through a recolour, without re-running the layout", () => {
    vi.useFakeTimers()
    try {
      const { rerender } = render(<CodeGlowCanvas {...base} />)
      const first = last()
      expect(h.workers).toHaveLength(1)
      vi.advanceTimersByTime(60_000) // the run ends; the core is settled
      first.camera.setState({ x: 0.7, ratio: 0.4 })
      const before = { x: first.graph.getNodeAttribute("b", "x"), y: first.graph.getNodeAttribute("b", "y") }
      rerender(<CodeGlowCanvas {...base} colorBy="kind" />)
      const second = last()
      expect(second).not.toBe(first)
      expect(second.graph.getNodeAttribute("b", "x")).toBeCloseTo(before.x)
      expect(second.graph.getNodeAttribute("b", "y")).toBeCloseTo(before.y)
      expect(second.camera).toMatchObject({ x: 0.7, ratio: 0.4 })
      expect(h.workers).toHaveLength(1)
    } finally {
      vi.useRealTimers()
    }
  })

  it("lays out again when the drawn nodes change", () => {
    vi.useFakeTimers()
    try {
      const { rerender } = render(<CodeGlowCanvas {...base} />)
      vi.advanceTimersByTime(60_000)
      rerender(<CodeGlowCanvas {...base} hiddenKinds={new Set(["file"])} />)
      expect(h.workers).toHaveLength(2)
    } finally {
      vi.useRealTimers()
    }
  })
})

describe("CodeGlowCanvas container resize", () => {
  it("a container resize refreshes the renderer", () => {
    const observers: Array<{
      callback: ResizeObserverCallback
      observed: Element[]
      disconnected: boolean
    }> = []
    vi.stubGlobal(
      "ResizeObserver",
      class {
        entry: (typeof observers)[number]
        constructor(callback: ResizeObserverCallback) {
          this.entry = { callback, observed: [], disconnected: false }
          observers.push(this.entry)
        }
        observe(el: Element) {
          this.entry.observed.push(el)
        }
        unobserve() {}
        disconnect() {
          this.entry.disconnected = true
        }
      },
    )
    try {
      const { unmount } = render(<CodeGlowCanvas {...base} />)
      const sigma = last()
      const container = (sigma as unknown as { container: HTMLElement }).container
      const watching = observers.filter((o) => o.observed.includes(container))
      expect(watching).toHaveLength(1)

      const refresh = vi.spyOn(sigma as unknown as { refresh: () => void }, "refresh")
      watching[0]!.callback(
        [{ target: container, contentRect: { width: 320, height: 600 } } as unknown as ResizeObserverEntry],
        {} as ResizeObserver,
      )
      expect(refresh).toHaveBeenCalledTimes(1)

      unmount()
      expect(watching[0]!.disconnected).toBe(true)
    } finally {
      vi.unstubAllGlobals()
    }
  })
})

describe("CodeGlowCanvas reducers", () => {
  const reduce = (props: Partial<Props>, id: string) => {
    render(<CodeGlowCanvas {...base} {...props} />)
    const sigma = last()
    const nodeReducer = sigma.settings.nodeReducer as (id: string, d: Record<string, unknown>) => Record<string, unknown>
    return nodeReducer(id, { ...sigma.graph.getNodeAttributes(id) })
  }

  it("names a selected leaf even below sigma's label threshold", () => {
    const res = reduce({ selectedId: "c" }, "c")
    expect(res.label).toBe("save")
    expect(res.forceLabel).toBe(true)
  })

  it("recedes a node outside the highlighted community toward the canvas", () => {
    const res = reduce({ highlightCommunity: "c1" }, "c")
    expect(res.color).not.toBe(last().graph.getNodeAttribute("c", "color"))
  })

  it("fades an edge that touches a dimmed node", () => {
    render(<CodeGlowCanvas {...base} highlightCommunity="c1" />)
    const sigma = last()
    const edgeReducer = sigma.settings.edgeReducer as (e: string, d: Record<string, unknown>) => Record<string, unknown>
    const edge = sigma.graph.edge("a", "c")!
    const res = edgeReducer(edge, { ...sigma.graph.getEdgeAttributes(edge) })
    expect(res.color).toMatch(/^rgba\(.*0\.08\)$/)
  })
})

describe("CodeGlowCanvas search", () => {
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
    file_count: 1,
    symbol_count: 2,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-07-27T00:00:00Z",
  }
  const RAW = {
    nodes: [
      { id: "main.py", label: "main.py", kind: "file", file_path: "main.py" },
      { id: "load::main.py", label: "load", kind: "function", file_path: "main.py" },
      { id: "save::main.py", label: "save", kind: "function", file_path: "main.py" },
    ],
    edges: [
      { source: "main.py", target: "load::main.py", type: "CONTAINS" },
      { source: "main.py", target: "save::main.py", type: "CONTAINS" },
    ],
  }

  function wrapper({ children }: { children: ReactNode }) {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }

  it("typing in the search dims without rebuilding", async () => {
    vi.mocked(apiFetch).mockImplementation(((path: string) => {
      if (path === "/repos") return Promise.resolve([REPO])
      if (path.startsWith("/code/graph/")) return Promise.resolve(RAW)
      return Promise.resolve([])
    }) as typeof apiFetch)
    const user = userEvent.setup()
    render(<RealCodeGraphView repoId="r1" onRepoChange={() => {}} onOpenRepositories={() => {}} />, {
      wrapper,
    })
    const field = await screen.findByPlaceholderText("Filter files & symbols…")
    const sigmas = h.sigmas.length
    const workers = h.workers.length
    const sigma = last()
    sigma.camera.setState({ x: 0.3, y: 0.6, ratio: 0.5 })

    for (const text of ["s", "sa", "sav", "save", "l"]) {
      await user.clear(field)
      await user.type(field, text)
    }
    await user.clear(field)
    await user.type(field, "save")

    expect(h.sigmas.length).toBe(sigmas)
    expect(h.workers.length).toBe(workers)
    expect(sigma.killed).toBe(false)
    expect(sigma.camera).toMatchObject({ x: 0.3, y: 0.6, ratio: 0.5 })
    const nodeReducer = sigma.settings.nodeReducer as (
      id: string,
      d: Record<string, unknown>,
    ) => Record<string, unknown>
    const color = (id: string) =>
      nodeReducer(id, { ...sigma.graph.getNodeAttributes(id) }).color
    expect(color("load::main.py")).not.toBe(sigma.graph.getNodeAttribute("load::main.py", "color"))
    expect(color("save::main.py")).toBe(sigma.graph.getNodeAttribute("save::main.py", "color"))
  })
})

describe("CodeGlowCanvas selection across a rebuild", () => {
  it("a rebuild re-centres a persisting selection", () => {
    const { rerender } = render(<CodeGlowCanvas {...base} selectedId="b" />)
    last().camera.setState({ x: 0.9, y: 0.1, ratio: 1 })
    rerender(<CodeGlowCanvas {...base} selectedId="b" hiddenKinds={new Set(["file"])} />)
    const sigma = last()
    expect(h.sigmas).toHaveLength(2)
    expect(sigma.camera.x).toBe(sigma.graph.getNodeAttribute("b", "x"))
    expect(sigma.camera.y).toBe(sigma.graph.getNodeAttribute("b", "y"))
    expect(sigma.camera.ratio).toBeCloseTo(0.15)
  })
})

describe("CodeGlowCanvas overlay and follow", () => {
  function fakeContext() {
    const arcs: Array<[number, number]> = []
    const ctx = new Proxy(
      { arc: (x: number, y: number) => void arcs.push([x, y]) } as Record<string, unknown>,
      {
        get: (target, key) =>
          key in target ? target[key as string] : () => ({ addColorStop: () => {} }),
        set: () => true,
      },
    )
    return { arcs, ctx }
  }

  it("ring overlay follows the selected node", () => {
    const { arcs, ctx } = fakeContext()
    const spy = vi
      .spyOn(HTMLCanvasElement.prototype, "getContext")
      .mockReturnValue(ctx as never)
    try {
      render(<CodeGlowCanvas {...base} selectedId="c" />)
      const sigma = last() as FakeSigmaLike & {
        getNodeDisplayData(id: string): { x: number; y: number }
        framedGraphToViewport(p: { x: number; y: number }): { x: number; y: number }
      }
      for (const state of [{ x: 0.2, ratio: 0.5 }, { x: 0.8, y: 0.3, ratio: 2 }]) {
        sigma.camera.setState(state)
        arcs.length = 0
        sigma.emit("afterRender")
        const at = sigma.framedGraphToViewport(sigma.getNodeDisplayData("c"))
        expect(arcs).toHaveLength(1)
        expect(arcs[0]![0]).toBeCloseTo(at.x)
        expect(arcs[0]![1]).toBeCloseTo(at.y)
      }
    } finally {
      spy.mockRestore()
    }
  })

  it("camera follows during the core run", () => {
    vi.useFakeTimers()
    try {
      const { rerender } = render(<CodeGlowCanvas {...base} />)
      const sigma = last()
      rerender(<CodeGlowCanvas {...base} selectedId="c" />)
      const setState = vi.spyOn(sigma.camera, "setState")

      sigma.graph.setNodeAttribute("c", "x", 7)
      sigma.graph.setNodeAttribute("c", "y", -3)
      sigma.emit("beforeRender")
      expect(setState).toHaveBeenCalledTimes(1)
      expect(sigma.camera).toMatchObject({ x: 7, y: -3 })
      sigma.emit("beforeRender")
      expect(setState).toHaveBeenCalledTimes(1)

      vi.advanceTimersByTime(60_000) // the run ends
      sigma.graph.setNodeAttribute("c", "x", 11)
      sigma.emit("beforeRender")
      expect(setState).toHaveBeenCalledTimes(1)
      expect(sigma.camera.x).toBe(7)
    } finally {
      vi.useRealTimers()
    }
  })
})
