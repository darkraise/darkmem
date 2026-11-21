import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, fireEvent, render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { forwardRef, useImperativeHandle, type ReactNode } from "react"
import type Graph from "graphology"
import type { UnifiedGraphData, UnifiedMemory } from "@/hooks/api"

// sigma's programs read WebGL enums off the global constructors at module load.
const h = vi.hoisted(() => {
  const GL = {
    FLOAT: 0x1406,
    UNSIGNED_BYTE: 0x1401,
    TRIANGLES: 0x0004,
    ONE: 1,
    ONE_MINUS_SRC_ALPHA: 0x0303,
    BLEND: 0x0be2,
  }
  Object.assign(globalThis, { WebGLRenderingContext: GL, WebGL2RenderingContext: GL })
  return {
    sigmas: [] as unknown[],
    workerStarts: 0,
    demo: false,
    fg: { props: null as Record<string, unknown> | null, reheats: 0 },
  }
})

vi.mock("sigma", () => {
  class FakeCamera {
    x = 0.5
    y = 0.5
    ratio = 1
    angle = 0
    on() {
      return this
    }
    off() {
      return this
    }
    removeListener() {
      return this
    }
    setState(s: Record<string, number>) {
      Object.assign(this, s)
      return this
    }
    animate(s: Record<string, number>) {
      this.setState(s)
      return Promise.resolve()
    }
    getState() {
      return { x: this.x, y: this.y, ratio: this.ratio, angle: this.angle }
    }
    isAnimated() {
      return false
    }
  }
  class FakeSigma {
    camera = new FakeCamera()
    handlers = new Map<string, Array<(...a: unknown[]) => void>>()
    constructor(
      public graph: Graph,
      public container: HTMLElement,
      public settings: Record<string, unknown>,
    ) {
      h.sigmas.push(this)
    }
    getCamera() {
      return this.camera
    }
    on(event: string, fn: (...a: unknown[]) => void) {
      const list = this.handlers.get(event) ?? []
      list.push(fn)
      this.handlers.set(event, list)
      return this
    }
    emit(event: string, ...args: unknown[]) {
      for (const fn of this.handlers.get(event) ?? []) fn(...args)
    }
    getContainer() {
      return this.container
    }
    createCanvas() {
      const canvas = document.createElement("canvas")
      this.container.appendChild(canvas)
      return canvas
    }
    getGraph() {
      return this.graph
    }
    scheduleRender() {}
    // sigma 3's refresh() renders synchronously, and a render always ends on
    // afterRender.
    refresh() {
      this.emit("afterRender")
    }
    setSetting() {}
    getDimensions() {
      return { width: 800, height: 600 }
    }
    getNodeDisplayData(id: string) {
      if (!this.graph.hasNode(id)) return undefined
      return {
        x: this.graph.getNodeAttribute(id, "x") as number,
        y: this.graph.getNodeAttribute(id, "y") as number,
        size: 4,
      }
    }
    graphToViewport(p: { x: number; y: number }) {
      return { x: 400 + p.x, y: 300 + p.y }
    }
    framedGraphToViewport(p: { x: number; y: number }) {
      return { x: p.x * 800, y: p.y * 600 }
    }
    viewportToFramedGraph(p: { x: number; y: number }) {
      return { x: p.x / 800, y: p.y / 600 }
    }
    scaleSize(s: number) {
      return s
    }
    kill() {
      this.emit("kill")
    }
  }
  return { default: FakeSigma }
})

vi.mock("graphology-layout-forceatlas2/worker", () => ({
  default: class {
    running = false
    start() {
      h.workerStarts++
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

vi.mock("react-force-graph-3d", () => ({
  default: forwardRef(function FakeForceGraph(
    props: Record<string, unknown>,
    ref,
  ) {
    h.fg.props = props
    useImperativeHandle(ref, () => {
      const force = { strength: () => force, distance: () => force }
      return {
        d3Force: () => force,
        d3ReheatSimulation: () => {
          h.fg.reheats++
        },
        scene: () => ({ add() {}, remove() {} }),
        refresh() {},
        cameraPosition() {},
      }
    })
    return null
  }),
}))

vi.mock("@/lib/demo-flag", () => ({
  get DEMO() {
    return h.demo
  },
}))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
vi.mock("@/features/chat/components/chat-overlay", () => ({ ChatOverlay: () => null }))
vi.mock("@/features/graph/components/mini-graph", () => ({ MiniGraph: () => null }))

const mockUseUnifiedGraph = vi.fn()
vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useUnifiedGraph: (...args: unknown[]) => mockUseUnifiedGraph(...args),
}))

import { apiFetch } from "@/lib/api"
import { RealMemoryGraphPage } from "@/features/memory-graph/components/real-memory-graph-page"
import { Graph2DRenderer } from "../graph-2d-renderer"
import { GraphDetailPanel } from "../graph-detail-panel"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
import { syntheticMemoryGraph } from "@/features/graph/lib/synthetic-graph"
import type { ColorMode } from "@/features/graph/lib/graph-colors"
import type { HullMode } from "@/features/graph/lib/graph-geometry"
import type { Node3D } from "@/features/graph/lib/graph-utils"

let frames: FrameRequestCallback[] = []
const flushFrame = () =>
  act(() => {
    const pending = frames
    frames = []
    for (const cb of pending) cb(performance.now())
  })

beforeEach(() => {
  h.sigmas.length = 0
  h.workerStarts = 0
  h.fg.props = null
  h.fg.reheats = 0
  frames = []
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
    frames.push(cb)
    return frames.length
  })
})
afterEach(() => {
  vi.restoreAllMocks()
})

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const MEMORIES: UnifiedMemory[] = Array.from({ length: 6 }, (_, i) => ({
  id: `m${i}`,
  content: `memory ${i}`,
  source: "api",
  tags: [],
  memory_type: i % 2 ? "fact" : "decision",
  importance: 0.5,
  cluster: i < 3 ? 0 : 1,
}))
const DATA: UnifiedGraphData = {
  memories: MEMORIES,
  clusters: { "0": ["m0", "m1", "m2"], "1": ["m3", "m4", "m5"] },
  cluster_names: { "0": "alpha", "1": "beta" },
  similarity_edges: [],
  entities: [
    { id: "e1", name: "postgres", entity_type: "tool", properties: {}, memory_ids: ["m0"] },
  ],
}

function withSizedContainers() {
  vi.stubGlobal(
    "ResizeObserver",
    class {
      constructor(private cb: ResizeObserverCallback) {}
      observe() {
        this.cb(
          [{ contentRect: { width: 800, height: 600 } } as ResizeObserverEntry],
          this as unknown as ResizeObserver,
        )
      }
      unobserve() {}
      disconnect() {}
    },
  )
}

function openSettings() {
  fireEvent.click(screen.getByRole("button", { name: /toggle graph settings/i }))
}

describe("memory graph in 3D", () => {
  beforeEach(() => {
    withSizedContainers()
    mockUseUnifiedGraph.mockReturnValue({ data: DATA, isLoading: false })
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("clicking an entity in 3D shows that entity", () => {
    render(<RealMemoryGraphPage />, { wrapper })
    openSettings()
    fireEvent.click(screen.getByRole("radio", { name: "3D" }))
    const onNodeClick = h.fg.props!.onNodeClick as (n: Partial<Node3D>) => void
    act(() =>
      onNodeClick({ id: "entity:e1", nodeKind: "entity", entityName: "postgres", x: 1, y: 1, z: 1 }),
    )
    expect(screen.getByText("Entity Detail")).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "postgres" })).toBeInTheDocument()
  })

  it("colour mode recolours in place", () => {
    render(<RealMemoryGraphPage />, { wrapper })
    openSettings()
    fireEvent.click(screen.getByRole("radio", { name: "3D" }))
    const before = h.fg.props!.graphData
    fireEvent.click(screen.getByRole("radio", { name: "Tag" }))
    expect(h.fg.props!.graphData).toBe(before)
    expect(h.fg.reheats).toBe(0)
  })
})

describe("memory graph details panel", () => {
  beforeEach(() => {
    withSizedContainers()
    mockUseUnifiedGraph.mockReturnValue({ data: DATA, isLoading: false })
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("takes focus when opened from its button and gives it back on close", () => {
    render(<RealMemoryGraphPage />, { wrapper })
    const close = screen.queryByRole("button", { name: "Close details" })
    if (close) fireEvent.click(close)
    const opener = screen.getByRole("button", { name: "Show details panel" })
    if (close) expect(opener).toHaveFocus()
    fireEvent.click(opener)
    const closeAgain = screen.getByRole("button", { name: "Close details" })
    expect(closeAgain).toHaveFocus()
    fireEvent.click(closeAgain)
    expect(screen.getByRole("button", { name: "Show details panel" })).toHaveFocus()
  })
})

function Renderer2D({ colorMode, hullMode }: { colorMode: ColorMode; hullMode: HullMode }) {
  const { tokens, palette } = useMemoryGraphTheme()
  const graph = syntheticGraph
  return (
    <div style={{ position: "relative", width: 800, height: 600 }}>
      <Graph2DRenderer
        filteredMemories={graph.memories}
        filteredEdges={graph.edges}
        selectedNodeId={null}
        onNodeSelect={noopSelect}
        onReady={noop}
        sizeMode="connections"
        colorMode={colorMode}
        hullMode={hullMode}
        entityLayerEnabled={false}
        entities={[]}
        entityRelations={[]}
        tokens={tokens}
        palette={palette}
        clusterNames={graph.clusterNames}
      />
    </div>
  )
}
const syntheticGraph = syntheticMemoryGraph(30, 3, 2)
const noop = () => {}
const noopSelect = (_id: string | null) => {}
const lastSigma = () => h.sigmas[h.sigmas.length - 1] as { graph: Graph }

// Every 2D context records the calls made on it, keyed by its canvas.
let canvasCalls: Array<{ canvas: HTMLCanvasElement; op: string }> = []
function recordCanvasCalls() {
  canvasCalls = []
  const calls = canvasCalls
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockImplementation(function (
    this: HTMLCanvasElement,
  ) {
    const canvas = this
    return new Proxy({} as Record<string, unknown>, {
      get(target, prop: string) {
        if (prop in target) return target[prop]
        if (prop === "measureText") return () => ({ width: 40 })
        if (prop === "canvas") return canvas
        return (...args: unknown[]) => {
          calls.push({ canvas, op: prop })
          if (prop.startsWith("create")) return { addColorStop() {} }
          void args
          return undefined
        }
      },
      set(target, prop: string, value) {
        target[prop] = value
        return true
      },
    }) as unknown as CanvasRenderingContext2D
  } as never)
}

describe("memory graph in 2D", () => {
  beforeEach(recordCanvasCalls)
  it("colour mode recolours in place", () => {
    const { rerender } = render(<Renderer2D colorMode="type" hullMode="none" />)
    flushFrame()
    expect(h.sigmas).toHaveLength(1)
    const id = syntheticGraph.memories[0]!.id
    const before = lastSigma().graph.getNodeAttribute(id, "color")
    rerender(<Renderer2D colorMode="cluster" hullMode="none" />)
    flushFrame()
    expect(h.sigmas).toHaveLength(1)
    expect(lastSigma().graph.getNodeAttribute(id, "color")).not.toBe(before)
  })

  it("the deferred runner start is one frame late", () => {
    render(<Renderer2D colorMode="type" hullMode="none" />)
    flushFrame()
    expect(h.sigmas).toHaveLength(1)
    expect(h.workerStarts).toBe(0)
    flushFrame()
    expect(h.workerStarts).toBe(1)
  })

  it("turning Regions off clears outlines and chips in the same frame", () => {
    const calls = canvasCalls
    const { rerender } = render(<Renderer2D colorMode="cluster" hullMode="cluster" />)
    flushFrame()
    const sigma = lastSigma() as unknown as { emit: (e: string) => void; container: HTMLElement }
    act(() => sigma.emit("afterRender"))
    const hullCanvas = [...sigma.container.querySelectorAll("canvas")].find(
      (c) => c.style.zIndex === "1",
    )!
    const onHull = () => calls.filter((c) => c.canvas === hullCanvas).map((c) => c.op)
    // Outlines are drawn; this fixture's regions are too small to seat a chip.
    expect(onHull()).toContain("stroke")

    calls.length = 0
    rerender(<Renderer2D colorMode="cluster" hullMode="none" />)
    const ops = onHull()
    expect(ops).toContain("clearRect")
    const afterClear = ops.slice(ops.lastIndexOf("clearRect"))
    for (const draw of ["roundRect", "stroke", "fill", "fillText"]) {
      expect(afterClear).not.toContain(draw)
    }
  })
})

describe("graph detail panel", () => {
  const panel = (memory: UnifiedMemory) => (
    <GraphDetailPanel
      colorMode="type"
      selectedMemory={memory}
      clusterName=""
      memories={[memory]}
      clusterNames={{}}
      visibleEdges={[]}
      onClose={noop}
    />
  )

  it("the close button is named", () => {
    render(panel(MEMORIES[0]!), { wrapper })
    expect(screen.getByRole("button", { name: "Close details" })).toBeInTheDocument()
  })

  it("the detail panel loads the full text of a truncated node", async () => {
    const full = "x".repeat(400)
    vi.mocked(apiFetch).mockResolvedValue({ id: "m9", content: full })
    const truncated = { ...MEMORIES[0]!, id: "m9", content: "x".repeat(280), content_truncated: true }
    const { unmount } = render(panel(truncated), { wrapper })
    expect(await screen.findByText(full)).toBeInTheDocument()
    expect(vi.mocked(apiFetch).mock.calls.filter(([p]) => p === "/memories/m9")).toHaveLength(1)
    unmount()

    vi.mocked(apiFetch).mockClear()
    render(panel({ ...MEMORIES[1]!, content_truncated: false }), { wrapper })
    expect(screen.getByText("memory 1")).toBeInTheDocument()
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it("in demo mode a truncated node requests nothing", () => {
    h.demo = true
    try {
      render(panel({ ...MEMORIES[0]!, content_truncated: true }), { wrapper })
      expect(screen.getByText("memory 0")).toBeInTheDocument()
      expect(apiFetch).not.toHaveBeenCalled()
    } finally {
      h.demo = false
    }
  })
})
