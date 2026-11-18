import { describe, it, expect, vi, beforeEach } from "vitest"
import { render } from "@testing-library/react"
import type Graph from "graphology"
import type { ComponentProps } from "react"

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
      return p
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

import { CodeGlowCanvas } from "../components/code-glow-canvas"

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
