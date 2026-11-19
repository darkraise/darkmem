import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, fireEvent, render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import Graph from "graphology"
import type { ComponentProps, ReactNode } from "react"

// Real GL enum values; sigma's programs read them off the global constructors
// at module load. Hoisted so they exist before the imports below evaluate.
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
    GL,
    sigmas: [] as unknown[],
    workers: [] as unknown[],
    densityClassifications: [] as unknown[],
  }
})

interface FakeCameraState {
  x: number
  y: number
  ratio: number
  angle: number
}

vi.mock("sigma", () => {
  class FakeCamera implements FakeCameraState {
    x = 0.5
    y = 0.5
    ratio = 1
    angle = 0
    private handlers = new Map<string, Set<() => void>>()
    on(event: string, fn: () => void) {
      const set = this.handlers.get(event) ?? new Set()
      set.add(fn)
      this.handlers.set(event, set)
      return this
    }
    off(event: string, fn: () => void) {
      this.handlers.get(event)?.delete(fn)
      return this
    }
    removeListener(event: string, fn: () => void) {
      return this.off(event, fn)
    }
    private emit() {
      for (const fn of this.handlers.get("updated") ?? []) fn()
    }
    setState(s: Partial<FakeCameraState>) {
      Object.assign(this, s)
      this.emit()
      return this
    }
    animate(s: Partial<FakeCameraState>) {
      this.setState(s)
      return Promise.resolve()
    }
    animatedZoom(o?: number | { factor?: number }) {
      const factor = typeof o === "number" ? o : (o?.factor ?? 2)
      this.setState({ ratio: this.ratio / factor })
      return Promise.resolve()
    }
    animatedUnzoom(o?: number | { factor?: number }) {
      const factor = typeof o === "number" ? o : (o?.factor ?? 2)
      this.setState({ ratio: this.ratio * factor })
      return Promise.resolve()
    }
    animatedReset() {
      this.setState({ x: 0.5, y: 0.5, ratio: 1, angle: 0 })
      return Promise.resolve()
    }
    isAnimated() {
      return false
    }
  }

  class FakeSigma {
    camera = new FakeCamera()
    handlers = new Map<string, Array<(...a: unknown[]) => void>>()
    renders = 0
    killed = false
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
    getGraph() {
      return this.graph
    }
    scheduleRender() {
      this.renders++
    }
    refresh() {}
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
      const c = this.camera
      return { x: c.x + ((p.x - 400) / 800) * c.ratio, y: c.y + ((p.y - 300) / 600) * c.ratio }
    }
    scaleSize(s: number) {
      return s
    }
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
    constructor(public graph: Graph) {
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
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({
    to,
    children,
    ...rest
  }: { to: string; children: ReactNode } & Record<string, unknown>) => (
    <a href={to} {...rest}>
      {children}
    </a>
  ),
}))
// The code hosts get an inert canvas; the real one is imported with
// importActual where a test is about the canvas itself.
vi.mock("@/features/code/components/code-glow-canvas", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/code/components/code-glow-canvas")>()
  return {
    ...actual,
    CodeGlowCanvas: (props: import("@/features/code/components/code-glow-canvas").CodeGlowCanvasProps) => {
      const { nodes, edges } = actual.drawnGraph(props.graph, props.hiddenKinds)
      return (
        <div
          role="group"
          tabIndex={0}
          aria-label={`Code graph — ${nodes.length} nodes, ${edges.length} edges`}
        />
      )
    },
  }
})

// Records what each renderer hands the density pass; the real pass still runs.
vi.mock("@/features/graph/lib/node-glow-program", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/graph/lib/node-glow-program")>()
  return {
    ...actual,
    trackDensityGain: (...args: Parameters<typeof actual.trackDensityGain>) => {
      h.densityClassifications.push(args[2])
      return actual.trackDensityGain(...args)
    },
  }
})


import { apiFetch } from "@/lib/api"
import {
  classify,
  coreRadius,
  CORE_MIN,
  fitCore,
  placeOuter,
  placeOuterRing,
  type ConstellationEdge,
  type Point,
} from "@/features/graph/lib/constellation-layout"
import { createConstellationRunner } from "@/features/graph/lib/constellation-runner"
import { createNodeGlowProgram } from "@/features/graph/lib/node-glow-program"
import { startAmbientMotion } from "@/features/graph/lib/ambient-motion"
import { entityTypeColor } from "@/features/graph/lib/graph-colors"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
import { Graph2DRenderer } from "@/features/graph/components/graph-2d-renderer"
import { GraphToolbar } from "@/features/graph/components/graph-toolbar"
import { CodeGraphTab } from "@/features/code/components/code-graph-tab"
import { RealCodeGraphView } from "@/features/code/components/real-code-graph-view"
import type { GraphEntity, SimilarityEdge, UnifiedMemory } from "@/hooks/api"

// ---------------------------------------------------------------------------
// Fixtures

const ids = (prefix: string, n: number) => Array.from({ length: n }, (_, i) => `${prefix}${i}`)
const path = (nodes: string[]): ConstellationEdge[] =>
  nodes.slice(1).map((t, i) => ({ source: nodes[i]!, target: t }))
const radius = (p: Point) => Math.hypot(p.x, p.y)

function rng(seed: number) {
  let a = seed >>> 0
  return () => {
    a = (Math.imul(a, 1664525) + 1013904223) >>> 0
    return a / 4294967296
  }
}

// ---------------------------------------------------------------------------
// A1, A2, A24: classification

describe("classify", () => {
  it("A1: isolated nodes are halo, 8+ node components are core, 2-7 node components are satellites while a core exists", () => {
    const core = ids("c", 8)
    const sat7 = ids("s", 7)
    const pair = ids("t", 2)
    const nodes = [...core, ...sat7, ...pair, "iso", "loop", "ghostLink"]
    const edges: ConstellationEdge[] = [
      ...path(core),
      ...path(sat7),
      ...path(pair),
      { source: "loop", target: "loop" },
      { source: "ghostLink", target: "absent" },
    ]
    const c = classify(nodes, edges)
    for (const id of core) expect(c.role.get(id)).toBe("core")
    for (const id of [...sat7, ...pair]) expect(c.role.get(id)).toBe("satellite")
    for (const id of ["iso", "loop", "ghostLink"]) expect(c.role.get(id)).toBe("halo")
    expect(new Set(c.core)).toEqual(new Set(core))
    expect(c.halo.slice().sort()).toEqual(["ghostLink", "iso", "loop"])
    expect(c.satellites.map((s) => new Set(s)).sort((a, b) => b.size - a.size)).toEqual([
      new Set(sat7),
      new Set(pair),
    ])
  })

  it("A1: edge direction does not matter for component membership", () => {
    const core = ids("c", 8)
    const reversed = path(core).map((e) => ({ source: e.target, target: e.source }))
    const c = classify(core, reversed)
    for (const id of core) expect(c.role.get(id)).toBe("core")
  })

  it("A2: with no 8+ component the largest component of 2+ is the core", () => {
    const five = ids("a", 5)
    const three = ids("b", 3)
    const two = ids("d", 2)
    const c = classify([...five, ...three, ...two, "iso"], [...path(five), ...path(three), ...path(two)])
    for (const id of five) expect(c.role.get(id)).toBe("core")
    for (const id of [...three, ...two]) expect(c.role.get(id)).toBe("satellite")
    expect(c.role.get("iso")).toBe("halo")
  })

  it("A2: with no edges at all every node is halo and the halo fills a full disc from the centre", () => {
    const nodes = ids("n", 4000)
    const c = classify(nodes, [])
    expect(c.core).toEqual([])
    expect(c.satellites).toEqual([])
    for (const id of nodes) expect(c.role.get(id)).toBe("halo")
    const outer = placeOuter(c, 0)
    const radii = nodes.map((id) => radius(outer.positions.get(id)!))
    const maxR = Math.max(...radii)
    expect(maxR).toBeGreaterThan(0)
    // Uniform area density over a disc: a quarter of nodes lie inside half the radius.
    const inner = radii.filter((r) => r < maxR / 2).length / nodes.length
    expect(inner).toBeGreaterThan(0.18)
    expect(inner).toBeLessThan(0.32)
    expect(Math.min(...radii)).toBeLessThan(maxR * 0.1)
    // All four quadrants are populated.
    const quadrants = new Set(
      nodes.map((id) => {
        const p = outer.positions.get(id)!
        return `${p.x >= 0}:${p.y >= 0}`
      }),
    )
    expect(quadrants.size).toBe(4)
  })

  it("A24: the core threshold is 8 nodes", () => {
    expect(CORE_MIN).toBe(8)
    const eight = ids("e", 8)
    const seven = ids("g", 7)
    const both = classify([...eight, ...seven], [...path(eight), ...path(seven)])
    for (const id of eight) expect(both.role.get(id)).toBe("core")
    for (const id of seven) expect(both.role.get(id)).toBe("satellite")

    // Seven alone is not core by threshold: it is the core only through the
    // largest-component fallback, so a pair beside it stays a satellite.
    const pair = ids("p", 2)
    const alone = classify([...seven, ...pair], [...path(seven), ...path(pair)])
    for (const id of seven) expect(alone.role.get(id)).toBe("core")
    for (const id of pair) expect(alone.role.get(id)).toBe("satellite")
  })
})

// ---------------------------------------------------------------------------
// A3, A4: placement

function shapedGraph(opts: { coreIds: string[]; sats: string[][]; halo: string[] }) {
  const nodes = [...opts.coreIds, ...opts.sats.flat(), ...opts.halo]
  const edges = [...path(opts.coreIds), ...opts.sats.flatMap(path)]
  return classify(nodes, edges)
}

describe("placeOuter", () => {
  it("A3: a halo node's position does not move when other nodes are added or removed and the radii are unchanged", () => {
    const coreA = ids("coreA", 40)
    const coreB = ids("coreB", 40)
    const satsA = [ids("sa", 3), ids("sb", 2)]
    const satsB = [ids("sc", 3), ids("sd", 2)]
    const kept = ids("keep", 6)
    const A = shapedGraph({ coreIds: coreA, sats: satsA, halo: [...kept, ...ids("goneA", 5)] })
    const B = shapedGraph({ coreIds: coreB, sats: satsB, halo: [...kept, ...ids("newB", 11)] })
    const R = coreRadius(40)
    expect(coreRadius(B.core.length)).toBe(R)
    const pa = placeOuterRing(A, R)
    const pb = placeOuterRing(B, R)
    expect(pa.satelliteOuter).toBeCloseTo(pb.satelliteOuter, 9)
    for (const id of kept) expect(pb.positions.get(id)).toEqual(pa.positions.get(id))
  })

  it("A4: satellites and halo lie beyond 1.15R and no two satellite clumps overlap", () => {
    const rand = rng(7)
    const sats: string[][] = []
    for (let i = 0; i < 70; i++) sats.push(ids(`k${i}_`, 2 + Math.floor(rand() * 6)))
    const c = shapedGraph({ coreIds: ids("core", 60), sats, halo: ids("halo", 600) })
    const R = coreRadius(c.core.length)
    expect(R).toBeGreaterThan(0)
    const { positions } = placeOuter(c, R)
    for (const id of [...c.satellites.flat(), ...c.halo]) {
      expect(radius(positions.get(id)!)).toBeGreaterThan(1.15 * R)
    }
    const discs = c.satellites.map((members) => {
      const pts = members.map((id) => positions.get(id)!)
      const cx = pts.reduce((s, p) => s + p.x, 0) / pts.length
      const cy = pts.reduce((s, p) => s + p.y, 0) / pts.length
      return { cx, cy, r: Math.max(...pts.map((p) => Math.hypot(p.x - cx, p.y - cy))) }
    })
    expect(discs).toHaveLength(70)
    for (let i = 0; i < discs.length; i++) {
      for (let j = i + 1; j < discs.length; j++) {
        const a = discs[i]!
        const b = discs[j]!
        expect(Math.hypot(a.cx - b.cx, a.cy - b.cy)).toBeGreaterThan(a.r + b.r)
      }
    }
  })
})

// ---------------------------------------------------------------------------
// A5: fitCore

describe("fitCore", () => {
  it("A5: no core node is placed beyond R, however far the simulation threw it", () => {
    const R = 60
    const rand = rng(3)
    for (const spread of [0.001, 1, 80, 1e6]) {
      const pos = new Map<string, Point>()
      for (const id of ids("n", 50)) {
        pos.set(id, { x: (rand() - 0.2) * spread, y: (rand() - 0.7) * spread })
      }
      for (const p of fitCore(pos, R).values()) expect(radius(p)).toBeLessThanOrEqual(R + 1e-6)
    }
  })

  it("A5: during the runner's run every frame mirrors core positions within R", () => {
    const queue: FrameRequestCallback[] = []
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((cb) => {
      queue.push(cb)
      return queue.length
    })
    const coreIds = ids("c", 12)
    const g = new Graph({ type: "undirected" })
    for (const id of [...coreIds, "iso"]) g.addNode(id, { x: Math.random(), y: Math.random() })
    for (const e of path(coreIds)) g.addEdge(e.source, e.target)
    const runner = createConstellationRunner(g, { layoutMs: 60_000, fa2Settings: {} })
    const R = runner.coreRadius
    expect(R).toBeGreaterThan(0)
    const before = h.workers.length
    runner.start()
    const worker = h.workers[before] as { graph: Graph }
    let scale = 1
    for (let frame = 0; frame < 6; frame++) {
      scale *= 40
      worker.graph.updateEachNodeAttributes((_id, a) => ({ ...a, x: (a.x as number) * scale + scale, y: (a.y as number) * scale - scale }))
      const cb = queue.shift()!
      cb(frame * 16)
      for (const id of coreIds) {
        const p = { x: g.getNodeAttribute(id, "x") as number, y: g.getNodeAttribute(id, "y") as number }
        expect(radius(p)).toBeLessThanOrEqual(R + 1e-6)
      }
    }
    runner.kill()
    vi.restoreAllMocks()
  })
})

// ---------------------------------------------------------------------------
// A6: speed

describe("classify + placeOuter at scale", () => {
  it("A6: 20,000 nodes and 110,000 edges complete in 50 ms or less", () => {
    const rand = rng(11)
    const nodes = ids("m", 20000)
    const edges: ConstellationEdge[] = []
    // 12,000-node giant, 600 five-node satellites, 5,000 isolated.
    for (let i = 0; i < 90_000; i++) {
      edges.push({ source: `m${Math.floor(rand() * 12000)}`, target: `m${Math.floor(rand() * 12000)}` })
    }
    for (let k = 0; k < 600; k++) {
      const base = 12000 + k * 5
      for (let j = 0; j < 4; j++) edges.push({ source: `m${base + j}`, target: `m${base + j + 1}` })
    }
    while (edges.length < 110_000) {
      edges.push({ source: `m${Math.floor(rand() * 12000)}`, target: `m${Math.floor(rand() * 12000)}` })
    }
    expect(edges).toHaveLength(110_000)
    const run = () => {
      const t0 = performance.now()
      const c = classify(nodes, edges)
      placeOuter(c, coreRadius(c.core.length))
      return performance.now() - t0
    }
    const times = [run(), run(), run(), run(), run()]
    const median = times.slice().sort((a, b) => a - b)[2]!
    console.log("A6 timings ms:", times.map((t) => t.toFixed(1)).join(", "))
    expect(median).toBeLessThanOrEqual(50)
  })
})

// ---------------------------------------------------------------------------
// A7: glow program blending

type Info = { gl: ReturnType<typeof fakeGl>; program: object; isPicking: boolean }
const events: string[] = []
function fakeGl() {
  return {
    ...h.GL,
    enable: vi.fn(),
    useProgram: vi.fn(),
    blendFunc: vi.fn((a: number, b: number) => events.push(`blend:${a},${b}`)),
    viewport: vi.fn(),
  }
}

function runBothPasses(additive: boolean) {
  events.length = 0
  const Program = createNodeGlowProgram({ additive, clock: { time: 0 } })
  const proto = Program.prototype as unknown as {
    renderProgram: (params: unknown, info: Info) => void
  }
  const gl = fakeGl()
  const self = {
    METHOD: h.GL.TRIANGLES,
    setUniforms: vi.fn(),
    drawWebGL: vi.fn((_m: number, info: Info) => events.push(info.isPicking ? "draw:pick" : "draw:normal")),
  }
  // sigma renders the picking pass, then the normal pass, through this method.
  proto.renderProgram.call(self, {}, { gl, program: {}, isPicking: true })
  proto.renderProgram.call(self, {}, { gl, program: {}, isPicking: false })
  return [...events]
}

describe("node glow program", () => {
  it("A7: dark theme draws additively, restores sigma's blend, and the picking pass never sets a blend function", () => {
    expect(runBothPasses(true)).toEqual([
      "draw:pick",
      `blend:${h.GL.ONE},${h.GL.ONE}`,
      "draw:normal",
      `blend:${h.GL.ONE},${h.GL.ONE_MINUS_SRC_ALPHA}`,
    ])
  })

  it("A7: the light theme never sets additive blending", () => {
    expect(runBothPasses(false)).toEqual(["draw:pick", "draw:normal"])
  })
})

// ---------------------------------------------------------------------------
// A8: motion loop

describe("ambient motion loop", () => {
  let reduce = false
  let mediaListener: ((e: { matches: boolean }) => void) | null = null
  let visibility: DocumentVisibilityState = "visible"
  const setVisibility = (v: DocumentVisibilityState) => {
    visibility = v
    document.dispatchEvent(new Event("visibilitychange"))
  }

  beforeEach(() => {
    reduce = false
    mediaListener = null
    visibility = "visible"
    vi.useFakeTimers({
      toFake: ["setTimeout", "clearTimeout", "requestAnimationFrame", "cancelAnimationFrame", "performance"],
    })
    vi.spyOn(window, "matchMedia").mockImplementation(
      (query: string) =>
        ({
          matches: query.includes("reduce") ? reduce : false,
          media: query,
          onchange: null,
          addEventListener: (_: string, fn: (e: { matches: boolean }) => void) => {
            mediaListener = fn
          },
          removeEventListener: vi.fn(),
          addListener: vi.fn(),
          removeListener: vi.fn(),
          dispatchEvent: vi.fn(),
        }) as unknown as MediaQueryList,
    )
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => visibility })
  })
  afterEach(() => {
    visibility = "visible"
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  const framesIn = (ms: number, nodeCount = 10) => {
    const onFrame = vi.fn()
    const stop = startAmbientMotion({ nodeCount, onFrame })
    vi.advanceTimersByTime(ms)
    const n = onFrame.mock.calls.length
    stop()
    return n
  }

  it("A8: a running loop delivers frames (control)", () => {
    expect(framesIn(1000)).toBeGreaterThan(0)
  })
  it("A8: does not start under reduced motion", () => {
    reduce = true
    expect(framesIn(1000)).toBe(0)
  })
  it("A8: does not start at 2,000 nodes or more, and does at 1,999", () => {
    expect(framesIn(1000, 2000)).toBe(0)
    expect(framesIn(1000, 5000)).toBe(0)
    expect(framesIn(1000, 1999)).toBeGreaterThan(0)
  })
  it("A8: does not start while the document is hidden", () => {
    visibility = "hidden"
    expect(framesIn(1000)).toBe(0)
  })
  it("A8: stops when reduced motion is requested or the document becomes hidden", () => {
    const onFrame = vi.fn()
    const stop = startAmbientMotion({ nodeCount: 10, onFrame })
    vi.advanceTimersByTime(500)
    expect(onFrame.mock.calls.length).toBeGreaterThan(0)

    reduce = true
    act(() => mediaListener!({ matches: true }))
    let seen = onFrame.mock.calls.length
    vi.advanceTimersByTime(1000)
    expect(onFrame.mock.calls.length).toBe(seen)

    reduce = false
    act(() => mediaListener!({ matches: false }))
    vi.advanceTimersByTime(500)
    expect(onFrame.mock.calls.length).toBeGreaterThan(seen)

    setVisibility("hidden")
    seen = onFrame.mock.calls.length
    vi.advanceTimersByTime(1000)
    expect(onFrame.mock.calls.length).toBe(seen)
    stop()
  })
})

// ---------------------------------------------------------------------------
// Renderer harness (A8 tail, A9, A12, A21)

type RendererProps = ComponentProps<typeof Graph2DRenderer>
const noop = () => {}
const noopSelect = (_id: string | null) => {}

const memory = (id: string, cluster = 1): UnifiedMemory => ({
  id,
  content: `memory ${id}`,
  source: "t",
  tags: [],
  memory_type: "fact",
  importance: 0.5,
  cluster,
  status: "active",
})
const edge = (source: string, target: string, score = 0.9): SimilarityEdge => ({ source, target, score })

function Scene(props: {
  memories: UnifiedMemory[]
  edges: SimilarityEdge[]
  entities?: GraphEntity[]
  entityLayer?: boolean
  sizeMode?: RendererProps["sizeMode"]
}) {
  const { tokens, palette } = useMemoryGraphTheme()
  return (
    <div style={{ position: "relative", width: 800, height: 600 }}>
      <Graph2DRenderer
        filteredMemories={props.memories}
        filteredEdges={props.edges}
        selectedNodeId={null}
        onNodeSelect={noopSelect}
        onReady={noop}
        sizeMode={(props.sizeMode ?? "connections") as RendererProps["sizeMode"]}
        colorMode="cluster"
        hullMode="none"
        entityLayerEnabled={props.entityLayer ?? false}
        entities={props.entities ?? []}
        entityRelations={[]}
        tokens={tokens}
        palette={palette}
      />
    </div>
  )
}

interface FakeSigmaView {
  graph: Graph
  renders: number
  killed: boolean
  settings: {
    nodeReducer: (id: string, data: Record<string, unknown>) => Record<string, unknown>
  }
}
const lastSigma = () => h.sigmas[h.sigmas.length - 1] as FakeSigmaView
const advance = (ms: number) =>
  act(() => {
    vi.advanceTimersByTime(ms)
  })

describe("memory 2D renderer", () => {
  it("A9: halo nodes take one small size whatever their importance", () => {
    const ring = ids("c", 8).map((id) => memory(id))
    const loud = { ...memory("h0"), importance: 1 }
    const quiet = { ...memory("h1"), importance: 0 }
    const memories = [...ring, loud, quiet, ...ids("z", 10).map((id) => memory(id))]
    const edges = path([...ids("c", 8), "c0"]).map((e) => edge(e.source, e.target))
    render(<Scene memories={memories} edges={edges} sizeMode={"importance" as RendererProps["sizeMode"]} />)
    advance(50)
    const g = lastSigma().graph
    const core = ids("c", 8).map((id) => g.getNodeAttribute(id, "size") as number).sort((a, b) => a - b)
    const median = (core[3]! + core[4]!) / 2
    expect(g.getNodeAttribute("h0", "size")).toBe(g.getNodeAttribute("h1", "size"))
    expect(g.getNodeAttribute("h0", "size") as number).toBeLessThanOrEqual(0.4 * median + 1e-9)
  })

  it("A10: at the fit view with nothing hovered or selected, no memory carries a label, hubs included", () => {
    const star = ["c0", ...ids("x", 9)].map((id) => memory(id))
    const edges = ids("x", 9).map((id) => edge("c0", id))
    render(<Scene memories={star} edges={edges} />)
    advance(50)
    const sigma = lastSigma()
    for (const id of sigma.graph.nodes()) {
      const out = sigma.settings.nodeReducer(id, sigma.graph.getNodeAttributes(id))
      expect(out.label ?? "").toBe("")
    }
  })

  it("UX-1: memory edges carry their score, and roles follow the cut rather than every drawn edge", () => {
    const ring = ids("c", 8).map((id) => memory(id))
    const rest = ["s0", "s1", ...ids("h", 9)].map((id) => memory(id))
    const memories = [...ring, ...rest]
    const edges = [
      ...path([...ids("c", 8), "c0"]).map((e) => edge(e.source, e.target, 0.9)),
      edge("s0", "s1", 0.9),
      edge("h0", "c0", 0.6),
    ]
    render(<Scene memories={memories} edges={edges} />)
    advance(50)
    const g = lastSigma().graph
    expect(g.getEdgeAttribute(g.edge("c0", "c1")!, "score")).toBe(0.9)
    expect(g.getNodeAttribute("c0", "_role")).toBe("core")
    expect(g.getNodeAttribute("h0", "_role")).toBe("halo")
  })

  it("A4: with the entity layer on, an entity takes its memories' highest role and memory roles do not change", () => {
    const ring = ids("c", 8).map((id) => memory(id))
    const rest = ["s0", "s1", ...ids("h", 10)].map((id) => memory(id))
    const memories = [...ring, ...rest]
    const edges = [...path([...ids("c", 8), "c0"]).map((e) => edge(e.source, e.target)), edge("s0", "s1")]
    const entity = (id: string, memory_ids: string[]): GraphEntity => ({
      id,
      name: id,
      entity_type: "tool",
      properties: {},
      memory_ids,
    })
    const roles = (layer: boolean) => {
      render(
        <Scene
          memories={memories}
          edges={edges}
          entityLayer={layer}
          entities={[entity("x", ["s1", "h1"]), entity("y", ["c2", "h2"]), entity("z", ["h3", "h4"])]}
        />,
      )
      advance(50)
      const g = lastSigma().graph
      return (id: string) => g.getNodeAttribute(id, "_role")
    }
    const off = roles(false)
    const offRoles = memories.map((m) => off(m.id))
    const on = roles(true)
    expect(on("entity:x")).toBe("satellite")
    expect(on("entity:y")).toBe("core")
    expect(on("entity:z")).toBe("halo")
    expect(memories.map((m) => on(m.id))).toEqual(offRoles)
  })

  it("A4: entity diamonds take roles but stay out of every role's glow density", () => {
    const ring = ids("c", 8).map((id) => memory(id))
    const rest = ["s0", "s1", ...ids("h", 10)].map((id) => memory(id))
    const edges = [...path([...ids("c", 8), "c0"]).map((e) => edge(e.source, e.target)), edge("s0", "s1")]
    const entity = (id: string, memory_ids: string[]): GraphEntity => ({
      id,
      name: id,
      entity_type: "tool",
      properties: {},
      memory_ids,
    })
    render(
      <Scene
        memories={[...ring, ...rest]}
        edges={edges}
        entityLayer
        entities={[entity("x", ["s1", "h1"]), entity("y", ["c2", "h2"]), entity("z", ["h3", "h4"])]}
      />,
    )
    advance(50)
    const g = lastSigma().graph
    expect(["entity:y", "entity:x", "entity:z"].map((id) => g.getNodeAttribute(id, "_role"))).toEqual([
      "core",
      "satellite",
      "halo",
    ])
    const passed = h.densityClassifications[h.densityClassifications.length - 1] as { core: string[]; satellites: string[][]; halo: string[] }
    expect(passed.core).toContain("c0")
    expect(passed.halo).toContain("h0")
    const counted = [...passed.core, ...passed.satellites.flat(), ...passed.halo]
    expect(counted.filter((id) => id.startsWith("entity:"))).toEqual([])
  })

  beforeEach(() => {
    h.sigmas.length = 0
    h.workers.length = 0
    h.densityClassifications.length = 0
    vi.useFakeTimers({
      toFake: ["setTimeout", "clearTimeout", "requestAnimationFrame", "cancelAnimationFrame", "performance"],
    })
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  const coreMemories = ids("c", 10).map((id) => memory(id))
  const coreEdges = path(ids("c", 10)).map((e) => edge(e.source, e.target))

  it("A9: the motion loop never writes node positions", () => {
    const sats = [memory("s0"), memory("s1"), memory("s2")]
    const orphans = ids("o", 20).map((id) => memory(id))
    const memories = [...coreMemories, ...sats, ...orphans]
    const edges = [...coreEdges, edge("s0", "s1"), edge("s1", "s2")]
    render(<Scene memories={memories} edges={edges} />)
    advance(50)
    const sigma = lastSigma()
    expect(sigma.graph.order).toBe(memories.length)
    // Let the core's run finish so the only thing still going is the motion loop.
    advance(120_000)
    const snapshot = () => sigma.graph.mapNodes((id, a) => `${id}:${a.x}:${a.y}`).join("|")
    const before = snapshot()
    const rendersBefore = sigma.renders
    advance(3000)
    expect(sigma.renders).toBeGreaterThan(rendersBefore + 10)
    expect(snapshot()).toBe(before)
    advance(3000)
    expect(snapshot()).toBe(before)
  })

  it("A8: the renderer stops its motion loop when a rebuild reaches 2,000 nodes", () => {
    const small = [...coreMemories]
    const { rerender } = render(<Scene memories={small} edges={coreEdges} />)
    advance(50)
    const first = lastSigma()
    const r0 = first.renders
    advance(1000)
    expect(first.renders).toBeGreaterThan(r0)

    const big = ids("b", 2000).map((id) => memory(id))
    rerender(<Scene memories={big} edges={[]} />)
    advance(50)
    const second = lastSigma()
    expect(second).not.toBe(first)
    expect(first.killed).toBe(true)
    const f = first.renders
    const s = second.renders
    advance(2000)
    expect(first.renders).toBe(f)
    expect(second.renders).toBe(s)
  })

  it("A12: raising the Edges threshold so a memory loses its last edge makes it halo on the next build", () => {
    const x = memory("x")
    const memories = [...coreMemories, x, ...ids("o", 16).map((id) => memory(id))]
    const edgesAll = [...coreEdges, edge("x", "c0", 0.6)]
    const atThreshold = (t: number) => edgesAll.filter((e) => e.score >= t)

    const { rerender } = render(<Scene memories={memories} edges={atThreshold(0.5)} />)
    advance(50)
    let g = lastSigma().graph
    expect(g.getNodeAttribute("x", "brightness")).toBe(1)
    expect(g.getNodeAttribute("c0", "brightness")).toBe(1)

    rerender(<Scene memories={memories} edges={atThreshold(0.7)} />)
    advance(50)
    g = lastSigma().graph
    expect(g.degree("x")).toBe(0)
    expect(g.getNodeAttribute("x", "brightness")).toBe(0.45)
    expect(g.getNodeAttribute("c0", "brightness")).toBe(1)

    rerender(<Scene memories={memories} edges={atThreshold(0.5)} />)
    advance(50)
    expect(lastSigma().graph.getNodeAttribute("x", "brightness")).toBe(1)
  })

  it("UX-3: a core-membership change at an unchanged node set re-runs the core layout", () => {
    const x = memory("x")
    const memories = [...coreMemories, x, ...ids("o", 16).map((id) => memory(id))]
    const edgesAll = [...coreEdges, edge("x", "c0", 0.6)]
    const atThreshold = (t: number) => edgesAll.filter((e) => e.score >= t)

    const { rerender } = render(<Scene memories={memories} edges={atThreshold(0.5)} />)
    advance(120_000)
    const n = h.workers.length

    rerender(<Scene memories={memories} edges={atThreshold(0.7)} />)
    advance(50)
    expect(h.workers.length).toBe(n + 1)

    rerender(<Scene memories={memories} edges={atThreshold(0.7)} />)
    advance(50)
    expect(h.workers.length).toBe(n + 1)
  })

  it("A21: turning the entity layer on leaves entity diamonds and type-coloured borders unchanged, in core and satellite roles", () => {
    const sats = [memory("s0"), memory("s1")]
    const memories = [...coreMemories, ...sats]
    const edges = [...coreEdges, edge("s0", "s1")]
    const entities: GraphEntity[] = [
      { id: "e-core", name: "Postgres", entity_type: "database", properties: {}, memory_ids: ["c0", "c1"] },
      { id: "e-sat", name: "Redis", entity_type: "tool", properties: {}, memory_ids: ["s0"] },
    ]
    let palette!: ReturnType<typeof useMemoryGraphTheme>["palette"]
    function Probe() {
      palette = useMemoryGraphTheme().palette
      return null
    }
    render(<Probe />)

    const { rerender } = render(<Scene memories={memories} edges={edges} entities={entities} entityLayer={false} />)
    advance(50)
    expect(lastSigma().graph.hasNode("entity:e-core")).toBe(false)

    rerender(<Scene memories={memories} edges={edges} entities={entities} entityLayer={true} />)
    advance(50)
    const sigma = lastSigma()
    const roles = new Map<string, string>()
    for (const e of entities) {
      const key = `entity:${e.id}`
      expect(sigma.graph.hasNode(key)).toBe(true)
      const attrs = sigma.graph.getNodeAttributes(key)
      expect(attrs.type).toBe("diamond")
      expect(attrs.borderColor).toBe(entityTypeColor(e.entity_type, palette))
      const drawn = sigma.settings.nodeReducer(key, attrs)
      expect(drawn.type).toBe("diamond")
      expect(drawn.borderColor).toBe(entityTypeColor(e.entity_type, palette))
      roles.set(e.id, attrs._role as string)
    }
    expect(roles.get("e-core")).toBe("core")
    expect(roles.get("e-sat")).toBe("satellite")
  })
})

// ---------------------------------------------------------------------------
// A10: toolbar

const toolbarBase = {
  viewMode: "2d" as const,
  onViewModeChange: vi.fn(),
  colorMode: "cluster" as const,
  onColorModeChange: vi.fn(),
  hullMode: "none" as const,
  onHullModeChange: vi.fn(),
  entityLayer: false,
  onEntityLayerChange: vi.fn(),
  sharedEntitiesOnly: false,
  onSharedEntitiesOnlyChange: vi.fn(),
  sizeMode: "importance" as const,
  onSizeModeChange: vi.fn(),
  similarityThreshold: 0.5,
  onSimilarityChange: vi.fn(),
  minClusterSize: 3,
  onMinClusterSizeChange: vi.fn(),
  spacing: 50,
  onSpacingChange: vi.fn(),
  onReset: vi.fn(),
}

describe("memory toolbar", () => {
  const open = () => userEvent.click(screen.getByRole("button", { name: "Toggle graph settings" }))

  it("A10: 2D mode renders no Tightness or Spacing control", async () => {
    render(<GraphToolbar {...toolbarBase} viewMode="2d" />)
    await open()
    expect(screen.getByText("Edges")).toBeInTheDocument()
    expect(screen.queryByText("Tightness")).toBeNull()
    expect(screen.queryByText("Spacing")).toBeNull()
    expect(screen.queryByRole("slider", { name: /tightness|spacing/i })).toBeNull()
  })

  it("A10: 3D mode renders Spacing", async () => {
    render(<GraphToolbar {...toolbarBase} viewMode="3d" />)
    await open()
    expect(screen.getByText("Spacing")).toBeInTheDocument()
    expect(screen.queryByText("Tightness")).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// A11: code hosts

function queryWrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const REAL_REPO = {
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
const REAL_GRAPH = {
  nodes: [
    { id: "main.py", label: "main.py", kind: "file", file_path: "main.py" },
    { id: "run::main.py", label: "run", kind: "function", file_path: "main.py" },
  ],
  edges: [{ source: "main.py", target: "run::main.py", type: "CONTAINS" }],
}

function expectNoLayoutOrPlayPause() {
  expect(screen.queryByText(/^layout$/i)).toBeNull()
  expect(screen.queryByRole("group", { name: /layout/i })).toBeNull()
  expect(screen.queryByRole("radio", { name: /layout/i })).toBeNull()
  expect(screen.queryByRole("button", { name: /layout/i })).toBeNull()
  expect(screen.queryByRole("button", { name: /^(play|pause)\b/i })).toBeNull()
  expect(screen.queryByRole("switch", { name: /play|pause|animate/i })).toBeNull()
}

describe("code hosts", () => {
  it("A11: the demo host (CodeGraphTab) renders no Layout control and no Play/Pause control", () => {
    render(<CodeGraphTab repoId="repo-backend" onRepoChange={vi.fn()} onOpenRepositories={vi.fn()} />)
    expect(screen.getByRole("group", { name: /^Code graph — \d+ nodes, \d+ edges$/ })).toBeInTheDocument()
    expectNoLayoutOrPlayPause()
  })

  it("A11: the real host (RealCodeGraphView) renders no Layout control and no Play/Pause control", async () => {
    vi.mocked(apiFetch).mockImplementation((p: string) => {
      if (p === "/repos") return Promise.resolve([REAL_REPO])
      if (p.startsWith("/code/graph/r1")) return Promise.resolve(REAL_GRAPH)
      if (p === "/code/files/r1") return Promise.resolve([])
      return Promise.resolve({})
    })
    render(<RealCodeGraphView repoId="r1" onRepoChange={vi.fn()} onOpenRepositories={vi.fn()} />, {
      wrapper: queryWrapper,
    })
    await screen.findByRole("group", { name: /^Code graph — \d+ nodes, \d+ edges$/ })
    expectNoLayoutOrPlayPause()
  })
})

// ---------------------------------------------------------------------------
// A18: code canvas keyboard

const CANVAS_GRAPH = {
  repo_id: "r1",
  nodes: [
    { id: "a", name: "main.py", kind: "file" as const, file: "main.py", community: "c1" },
    { id: "b", name: "run", kind: "function" as const, file: "main.py", community: "c1" },
    { id: "c", name: "stop", kind: "function" as const, file: "main.py", community: "c1" },
  ],
  edges: [
    { source: "a", target: "b", type: "CONTAINS" },
    { source: "a", target: "c", type: "CONTAINS" },
  ],
  communities: [{ id: "c1", label: "core", chart: 1 as const }],
  processes: [],
}

describe("code canvas keyboard", () => {
  beforeEach(() => {
    h.sigmas.length = 0
  })

  async function mountCanvas(onSelect = vi.fn()) {
    const { CodeGlowCanvas } = await vi.importActual<typeof import("@/features/code/components/code-glow-canvas")>(
      "@/features/code/components/code-glow-canvas",
    )
    const view = render(
      <CodeGlowCanvas
        graph={CANVAS_GRAPH}
        colorBy="kind"
        selectedId="b"
        onSelect={onSelect}
        visibleIds={null}
        blastIds={null}
        highlightCommunity={null}
        processIds={null}
      />,
    )
    const group = screen.getByRole("group", { name: "Code graph — 3 nodes, 2 edges" })
    const camera = (h.sigmas[h.sigmas.length - 1] as { camera: FakeCameraState }).camera
    return { group, camera, onSelect, view }
  }

  it("A18: the canvas is one tab stop labelled with its node and edge counts", async () => {
    const { group, view } = await mountCanvas()
    expect(group).toHaveAttribute("tabindex", "0")
    const stops = view.container.querySelectorAll(
      "[tabindex]:not([tabindex='-1']), button, a[href], input, select, textarea",
    )
    expect(stops).toHaveLength(1)
    expect(stops[0]).toBe(group)
  })

  it("A18: + and - zoom, arrows pan, 0 fits, Escape clears the selection", async () => {
    const { group, camera, onSelect } = await mountCanvas()
    group.focus()
    const ratio0 = camera.ratio

    fireEvent.keyDown(group, { key: "+" })
    const zoomedIn = camera.ratio
    expect(zoomedIn).toBeLessThan(ratio0)
    fireEvent.keyDown(group, { key: "-" })
    expect(camera.ratio).toBeGreaterThan(zoomedIn)
    fireEvent.keyDown(group, { key: "-" })
    expect(camera.ratio).toBeGreaterThan(ratio0)

    const x0 = camera.x
    const y0 = camera.y
    fireEvent.keyDown(group, { key: "ArrowRight" })
    const xr = camera.x
    expect(xr).not.toBe(x0)
    expect(camera.y).toBe(y0)
    fireEvent.keyDown(group, { key: "ArrowLeft" })
    fireEvent.keyDown(group, { key: "ArrowLeft" })
    expect(Math.sign(camera.x - xr)).toBe(-Math.sign(xr - x0))
    fireEvent.keyDown(group, { key: "ArrowUp" })
    const yu = camera.y
    expect(yu).not.toBe(y0)
    fireEvent.keyDown(group, { key: "ArrowDown" })
    fireEvent.keyDown(group, { key: "ArrowDown" })
    expect(Math.sign(camera.y - yu)).toBe(-Math.sign(yu - y0))

    fireEvent.keyDown(group, { key: "0" })
    expect({ x: camera.x, y: camera.y, ratio: camera.ratio }).toEqual({ x: 0.5, y: 0.5, ratio: 1 })

    expect(onSelect).not.toHaveBeenCalled()
    fireEvent.keyDown(group, { key: "Escape" })
    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect).toHaveBeenCalledWith(null)
  })

  it("A18: other keys do nothing", async () => {
    const { group, camera, onSelect } = await mountCanvas()
    const before = { x: camera.x, y: camera.y, ratio: camera.ratio }
    for (const key of ["a", "Enter", " ", "Tab"]) fireEvent.keyDown(group, { key })
    expect({ x: camera.x, y: camera.y, ratio: camera.ratio }).toEqual(before)
    expect(onSelect).not.toHaveBeenCalled()
  })

  it("A18: choosing a node by keyboard goes through the explorer", async () => {
    const user = userEvent.setup()
    render(<CodeGraphTab repoId="repo-backend" onRepoChange={vi.fn()} onOpenRepositories={vi.fn()} />)
    const canvas = screen.getByRole("group", { name: /^Code graph — \d+ nodes, \d+ edges$/ })
    // The canvas offers no per-node controls.
    expect(within(canvas).queryAllByRole("button")).toHaveLength(0)
    const panel = screen.getByText("Selected symbol", { exact: true }).parentElement!.parentElement!
    expect(panel).not.toHaveTextContent("file ·")
    expect(panel).not.toHaveTextContent("function ·")
    const panelBefore = panel.textContent

    const rowsOf = () => screen.getAllByRole("button").filter((b) => b.hasAttribute("title") && b.hasAttribute("aria-expanded") || b.closest("[style*='translateY']"))
    let activated = false
    for (let step = 0; step < 12 && !activated; step++) {
      const collapsed = rowsOf().find((b) => b.getAttribute("aria-expanded") === "false")
      const symbol = rowsOf().find((b) => !b.hasAttribute("aria-expanded"))
      const target = symbol ?? collapsed
      if (!target) break
      act(() => target.focus())
      expect(target).toHaveFocus()
      await user.keyboard("{Enter}")
      if (symbol) activated = true
    }
    expect(activated).toBe(true)
    expect(panel.textContent).not.toBe(panelBefore)
    expect(panel.textContent).toMatch(/(function|method|class|file|module|interface|struct|type|enum|trait|route|tool) ·/)
  })
})
