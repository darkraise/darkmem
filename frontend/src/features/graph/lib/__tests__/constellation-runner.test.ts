import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import Graph from "graphology"

const fa2 = vi.hoisted(() => ({
  instances: [] as Array<{
    graph: import("graphology").default
    running: boolean
    params?: { settings?: Record<string, unknown> }
  }>,
}))

vi.mock("graphology-layout-forceatlas2/worker", () => ({
  default: class {
    running = false
    constructor(
      public graph: import("graphology").default,
      public params?: { settings?: Record<string, unknown> },
    ) {
      fa2.instances.push(this)
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

import { constellationFa2Settings, createConstellationRunner } from "../constellation-runner"
import { classify, CORE_MIN, HALO_SIZE, placeOuterRing, ROLE_BRIGHTNESS } from "../constellation-layout"

function buildGraph() {
  const g = new Graph()
  for (let i = 0; i < CORE_MIN; i++) {
    g.addNode(`c${i}`, { x: i * 50, y: (i % 3) * 40, type: "glow", color: "#abcdef" })
  }
  for (let i = 1; i < CORE_MIN; i++) g.addEdge(`c${i - 1}`, `c${i}`)
  g.addNode("s0", { x: 0, y: 0, type: "glow", color: "#abcdef" })
  g.addNode("s1", { x: 0, y: 0, type: "glow", color: "#abcdef" })
  g.addEdge("s0", "s1")
  g.addNode("h0", { x: 0, y: 0, type: "glow", color: "#abcdef" })
  g.addNode("entity:e1", { x: 0, y: 0, type: "diamond", color: "#222222", borderColor: "#123456" })
  g.addEdge("entity:e1", "c0")
  return g
}

const opts = (extra: Partial<{ onStop: () => void }> = {}) => ({
  layoutMs: 1000,
  fa2Settings: { gravity: 1 },
  ...extra,
})

beforeEach(() => {
  fa2.instances.length = 0
  vi.useFakeTimers({
    toFake: ["setTimeout", "clearTimeout", "requestAnimationFrame", "cancelAnimationFrame"],
  })
})
afterEach(() => vi.useRealTimers())

describe("createConstellationRunner", () => {
  it("writes each node's role and brightness, entities included", () => {
    const g = buildGraph()
    createConstellationRunner(g, opts())
    expect(g.getNodeAttribute("c0", "_role")).toBe("core")
    expect(g.getNodeAttribute("entity:e1", "_role")).toBe("core")
    expect(g.getNodeAttribute("s0", "_role")).toBe("satellite")
    expect(g.getNodeAttribute("h0", "_role")).toBe("halo")
    expect(g.getNodeAttribute("c0", "brightness")).toBe(ROLE_BRIGHTNESS.core)
    expect(g.getNodeAttribute("h0", "brightness")).toBe(ROLE_BRIGHTNESS.halo)
    expect(typeof g.getNodeAttribute("h0", "phase")).toBe("number")
  })

  it("simulates the core only", () => {
    const g = buildGraph()
    createConstellationRunner(g, opts()).start()
    const sim = fa2.instances[0]!.graph
    expect(sim.order).toBe(CORE_MIN + 1)
    expect(sim.hasNode("h0")).toBe(false)
    expect(sim.hasNode("s0")).toBe(false)
  })

  it("places satellites and the halo before the run and never moves them", () => {
    const g = buildGraph()
    const r = createConstellationRunner(g, opts())
    const s0 = { x: g.getNodeAttribute("s0", "x"), y: g.getNodeAttribute("s0", "y") }
    const h0 = { x: g.getNodeAttribute("h0", "x"), y: g.getNodeAttribute("h0", "y") }
    expect(Math.hypot(h0.x, h0.y)).toBeGreaterThan(r.coreRadius)
    r.start()
    fa2.instances[0]!.graph.updateEachNodeAttributes((_, a) => ({
      ...a,
      x: (a.x as number) * 7 + 900,
      y: -(a.y as number) * 5,
    }))
    vi.advanceTimersByTime(1100)
    expect({ x: g.getNodeAttribute("s0", "x"), y: g.getNodeAttribute("s0", "y") }).toEqual(s0)
    expect({ x: g.getNodeAttribute("h0", "x"), y: g.getNodeAttribute("h0", "y") }).toEqual(h0)
  })

  it("keeps every core node within the core radius while running", () => {
    const g = buildGraph()
    const r = createConstellationRunner(g, opts())
    r.start()
    let i = 0
    fa2.instances[0]!.graph.updateEachNodeAttributes((_, a) => ({
      ...a,
      x: 10_000 + 400 * i++,
      y: -8_000 + 90 * i,
    }))
    vi.advanceTimersByTime(100)
    g.forEachNode((_, a) => {
      if (a._role === "core") {
        expect(Math.hypot(a.x as number, a.y as number)).toBeLessThanOrEqual(r.coreRadius + 1e-6)
      }
    })
  })

  it("stops after layoutMs and calls onStop once", () => {
    const onStop = vi.fn()
    const r = createConstellationRunner(buildGraph(), opts({ onStop }))
    r.start()
    expect(r.isRunning()).toBe(true)
    vi.advanceTimersByTime(999)
    expect(onStop).not.toHaveBeenCalled()
    vi.advanceTimersByTime(2)
    expect(onStop).toHaveBeenCalledTimes(1)
    expect(r.isRunning()).toBe(false)
  })

  it("gives every caller the same force settings", () => {
    expect(constellationFa2Settings(buildGraph(), { slowDown: 5, barnesHutOptimize: true })).toMatchObject({
      linLogMode: true,
      outboundAttractionDistribution: false,
      strongGravityMode: true,
      gravity: 1,
      scalingRatio: 10,
      slowDown: 5,
      barnesHutOptimize: true,
    })
  })

  it("never changes a node's type, colour or border", () => {
    const g = buildGraph()
    createConstellationRunner(g, opts()).start()
    vi.advanceTimersByTime(1100)
    expect(g.getNodeAttribute("entity:e1", "type")).toBe("diamond")
    expect(g.getNodeAttribute("entity:e1", "borderColor")).toBe("#123456")
    expect(g.getNodeAttribute("entity:e1", "color")).toBe("#222222")
    expect(g.getNodeAttribute("c0", "type")).toBe("glow")
    expect(g.getNodeAttribute("c0", "color")).toBe("#abcdef")
  })
})


describe("runner roles", () => {
  const build = (withScores: boolean) => {
    const g = new Graph({ type: "undirected" })
    const ids = [...Array.from({ length: 8 }, (_, i) => `c${i}`), "s0", "s1", ...Array.from({ length: 9 }, (_, i) => `h${i}`)]
    for (const id of ids) g.addNode(id, { x: 0, y: 0, size: 6 })
    g.addNode("entity:e1", { x: 0, y: 0, size: 6 })
    const add = (a: string, b: string, score: number) => g.addEdge(a, b, withScores ? { score } : {})
    for (let i = 0; i < 8; i++) add(`c${i}`, `c${(i + 1) % 8}`, 0.9)
    add("s0", "s1", 0.9)
    add("h0", "c0", 0.6)
    g.addEdge("entity:e1", "s1", {})
    return { g, ids }
  }

  it("A12: without roles the runner classifies over every drawn edge, as before", () => {
    const { g } = build(false)
    const edges: { source: string; target: string }[] = []
    g.forEachEdge((_e, _a, source, target) => edges.push({ source, target }))
    const runner = createConstellationRunner(g, { layoutMs: 10, fa2Settings: {} })
    const plain = classify(g.nodes(), edges)
    expect([...runner.classification.role.entries()]).toEqual([...plain.role.entries()])
    expect(g.getNodeAttribute("h0", "_role")).toBe("core")
  })

  it("UX-1: with roles the runner classifies by the cut and gives attachments their linked role", () => {
    const { g, ids } = build(true)
    const edges: { source: string; target: string; score?: number }[] = []
    g.forEachEdge((_e, a, source, target) => {
      if (!source.startsWith("entity:") && !target.startsWith("entity:")) edges.push({ source, target, score: a.score as number })
    })
    createConstellationRunner(g, {
      layoutMs: 10,
      fa2Settings: {},
      roles: { nodeIds: ids, edges, attachments: [{ id: "entity:e1", linked: ["s1"] }] },
    })
    expect(g.getNodeAttribute("c0", "_role")).toBe("core")
    expect(g.getNodeAttribute("h0", "_role")).toBe("halo")
    expect(g.getNodeAttribute("entity:e1", "_role")).toBe("satellite")
  })

  it("A12: without roles the runner keeps today's ring placement", () => {
    const { g } = build(false)
    const edges: { source: string; target: string }[] = []
    g.forEachEdge((_e, _a, source, target) => edges.push({ source, target }))
    const runner = createConstellationRunner(g, { layoutMs: 10, fa2Settings: {} })
    expect(runner.outer).toEqual(placeOuterRing(classify(g.nodes(), edges), runner.coreRadius))
  })

  it("UI-3: the code canvas's halo shrinks to 40% of the median core size", () => {
    const { g } = build(false)
    for (let i = 0; i < 8; i++) g.setNodeAttribute(`c${i}`, "size", 2)
    createConstellationRunner(g, { layoutMs: 10, fa2Settings: {} })
    for (let i = 1; i < 9; i++) expect(g.getNodeAttribute(`h${i}`, "size")).toBeCloseTo(0.8)
    expect(g.getNodeAttribute("c0", "size")).toBe(2)
  })

  it("UI-3: with no core the halo takes HALO_SIZE", () => {
    const { g, ids } = build(true)
    createConstellationRunner(g, {
      layoutMs: 10,
      fa2Settings: {},
      roles: { nodeIds: ids, edges: [], attachments: [] },
    })
    for (const id of ids) expect(g.getNodeAttribute(id, "size")).toBe(HALO_SIZE)
  })

  it("UX-1: the memory core runs LinLog without strong gravity; the code canvas keeps its forces", () => {
    const base = constellationFa2Settings(build(false).g, { slowDown: 1, barnesHutOptimize: false })
    const scored = build(true)
    const edges: { source: string; target: string; score?: number }[] = []
    scored.g.forEachEdge((_e, a, source, target) => {
      if (!source.startsWith("entity:") && !target.startsWith("entity:")) edges.push({ source, target, score: a.score as number })
    })
    createConstellationRunner(scored.g, {
      layoutMs: 10,
      fa2Settings: base,
      roles: { nodeIds: scored.ids, edges, attachments: [] },
    }).start()
    createConstellationRunner(build(false).g, { layoutMs: 10, fa2Settings: base }).start()
    const [memory, code] = fa2.instances.map((w) => w.params?.settings)
    expect(memory).toMatchObject({ linLogMode: true, strongGravityMode: false, gravity: 0.05 })
    expect(code).toEqual(base)
  })
})
