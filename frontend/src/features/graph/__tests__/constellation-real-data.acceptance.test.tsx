import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { act, render } from "@testing-library/react"
import Graph from "graphology"
import { readFileSync } from "node:fs"
import { resolve } from "node:path"
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

import { loadRealCorpus, type RealCorpusSize } from "@/features/graph/fixtures/real-corpus"
import {
  classify,
  classifyWithCut,
  coreRadius,
  CORE_MIN,
  fitCore,
  HALO_SIZE,
  placeOuter,
  roleCut,
  type Classification,
  type ConstellationRole,
  type Point,
  type ScoredEdge,
} from "@/features/graph/lib/constellation-layout"
import { createConstellationRunner } from "@/features/graph/lib/constellation-runner"
import {
  COVERAGE_TARGET,
  createNodeGlowProgram,
  trackDensityGain,
  type GlowClock,
} from "@/features/graph/lib/node-glow-program"
import { topHubs } from "@/features/graph/lib/hubs"
import { NODE_LIMIT_DEFAULT, useGraphPrefs } from "@/features/graph/lib/graph-prefs"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
import { Graph2DRenderer } from "@/features/graph/components/graph-2d-renderer"

// ---------------------------------------------------------------------------
// Helpers

const note = (line: string) => process.stdout.write(`${line}\n`)
const SIZES: RealCorpusSize[] = [200, 1000, "all"]
const RANK: Record<ConstellationRole, number> = { halo: 0, satellite: 1, core: 2 }
const radius = (p: Point) => Math.hypot(p.x, p.y)
const round3 = (x: number) => Math.round(x * 1000) / 1000
const ids = (prefix: string, n: number) => Array.from({ length: n }, (_, i) => `${prefix}${i}`)
const chain = (nodes: string[], scoreOf: (i: number) => number): ScoredEdge[] =>
  nodes.slice(1).map((t, i) => ({ source: nodes[i]!, target: t, score: scoreOf(i) }))

function rng(seed: number) {
  let a = seed >>> 0
  return () => {
    a = (Math.imul(a, 1664525) + 1013904223) >>> 0
    return a / 4294967296
  }
}
function shuffled<T>(xs: T[], seed: number): T[] {
  const r = rng(seed)
  const out = xs.slice()
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(r() * (i + 1))
    ;[out[i], out[j]] = [out[j]!, out[i]!]
  }
  return out
}

function realRoles(size: RealCorpusSize) {
  const c = loadRealCorpus(size)
  const nodeIds = c.memories.map((m) => m.id)
  return { corpus: c, nodeIds, result: classifyWithCut(nodeIds, c.edges) }
}

// ---------------------------------------------------------------------------
// A14 runs first, before any rendering test has allocated.

describe("performance", () => {
  it("A14: roleCut + classify + placeOuter take 50 ms or less at 20,000 nodes and 110,000 scored edges (median of 5)", () => {
    const N = 20_000
    const E = 110_000
    const BLOCK = 50
    const r = rng(14)
    const nodeIds = Array.from({ length: N }, (_, i) => `n${i}`)
    const edges: ScoredEdge[] = []
    for (let k = 0; k < E; k++) {
      const a = Math.floor(r() * N)
      const intra = r() < 0.8
      let b = intra ? Math.floor(a / BLOCK) * BLOCK + Math.floor(r() * BLOCK) : Math.floor(r() * N)
      if (b === a) b = (a + 1) % N
      edges.push({
        source: nodeIds[a]!,
        target: nodeIds[b]!,
        score: round3(intra ? 0.6 + 0.4 * r() : 0.5 + 0.2 * r()),
      })
    }
    expect(edges).toHaveLength(110_000)

    const timings: number[] = []
    let last: Classification | null = null
    for (let run = 0; run < 5; run++) {
      const t0 = performance.now()
      const cut = roleCut(nodeIds, edges)
      const kept = edges.filter((e) => typeof e.score !== "number" || e.score >= cut)
      const c = classify(nodeIds, kept)
      placeOuter(c, coreRadius(c.core.length))
      timings.push(performance.now() - t0)
      last = c
    }
    const median = timings.slice().sort((x, y) => x - y)[2]!
    note(`A14 timings ms: ${timings.map((t) => t.toFixed(1)).join(", ")} median ${median.toFixed(1)}`)
    expect(last!.core.length + last!.satellites.flat().length + last!.halo.length).toBe(N)
    expect(last!.core.length).toBeGreaterThan(0)
    expect(median).toBeLessThanOrEqual(50)
  })
})

// ---------------------------------------------------------------------------
// A1: roleCut

describe("roleCut", () => {
  it("A1: returns the lowest score at which 8+ node components hold at most 45% of the nodes", () => {
    const nodes = ids("p", 101)
    const edges = chain(nodes, (i) => round3(0.99 - 0.005 * i))
    // Through edge i the path holds i + 2 nodes; 45% of 101 is 45.45, so edge 43 is the last that fits.
    expect(roleCut(nodes, shuffled(edges, 1))).toBe(0.775)
    expect(roleCut(nodes, edges)).toBe(0.775)
    expect(roleCut(nodes, edges, 0.45)).toBe(0.775)
  })

  it("A1: adds equal scores together, never half a score group", () => {
    const nodes = ids("p", 101)
    // Triples of equal scores: group g ends with 3g + 4 nodes. g = 13 gives 43, g = 14 gives 46 (> 45.45).
    const edges = chain(nodes, (i) => round3(0.9 - 0.01 * Math.floor(i / 3)))
    expect(roleCut(nodes, shuffled(edges, 2))).toBe(0.77)
  })

  it("A1: components below CORE_MIN do not count toward the share", () => {
    expect(CORE_MIN).toBe(8)
    const pairs = Array.from({ length: 40 }, (_, k) => ({
      source: `q${k}a`,
      target: `q${k}b`,
      score: 0.9,
    }))
    const nodes = [...pairs.flatMap((e) => [e.source, e.target]), ...ids("w", 30), ...ids("iso", 10)]
    const edges = [...pairs, ...chain(ids("w", 30), () => 0.6)]
    // 30 of 120 nodes sit in an 8+ component at most, so every edge is kept.
    expect(roleCut(nodes, edges)).toBe(0.6)
  })

  it("A1: when every edge keeps the 8+ components at or below 45%, returns the lowest edge score", () => {
    const body = ids("m", 10)
    const nodes = [...body, "x0", "x1", ...ids("iso", 88)]
    const edges = [...chain(body, (i) => round3(0.8 - 0.02 * i)), { source: "x0", target: "x1", score: 0.3 }]
    expect(roleCut(nodes, edges)).toBe(0.3)
    expect(roleCut(nodes, shuffled(edges, 3))).toBe(0.3)
  })

  it("A1: when the highest score group alone passes 45%, returns the highest score", () => {
    const body = ids("m", 15)
    const nodes = [...body, ...ids("t", 3), ...ids("iso", 2)]
    const edges = [...chain(body, () => 0.9), ...chain(ids("t", 3), () => 0.5)]
    expect(roleCut(nodes, edges)).toBe(0.9)
    expect(roleCut(nodes, shuffled(edges, 4))).toBe(0.9)
  })
})

// ---------------------------------------------------------------------------
// A2, A3: roles on the real corpus

describe("roles on the real corpus", () => {
  for (const size of SIZES) {
    it(`A2: the ${size} fixture holds 35-50% core, 10-25% satellites and 25-45% halo`, () => {
      const { nodeIds, result } = realRoles(size)
      const n = nodeIds.length
      const core = result.core.length / n
      const sat = result.satellites.flat().length / n
      const halo = result.halo.length / n
      note(`A2 ${size}: n=${n} core=${core.toFixed(3)} sat=${sat.toFixed(3)} halo=${halo.toFixed(3)}`)
      expect(result.core.length + result.satellites.flat().length + result.halo.length).toBe(n)
      expect(core).toBeGreaterThanOrEqual(0.35)
      expect(core).toBeLessThanOrEqual(0.5)
      expect(sat).toBeGreaterThanOrEqual(0.1)
      expect(sat).toBeLessThanOrEqual(0.25)
      expect(halo).toBeGreaterThanOrEqual(0.25)
      expect(halo).toBeLessThanOrEqual(0.45)
    })
  }

  it("A3: raising Edges from 0.5 to 0.8 in steps of 0.05 never pulls a memory inward while an 8+ component remains", () => {
    const { corpus, nodeIds } = realRoles(1000)
    const thresholds = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]
    const roles = thresholds.map((t) => {
      const kept = corpus.edges.filter((e) => e.score >= t)
      const r = classifyWithCut(nodeIds, kept)
      // Largest component of the drawn edges, to know whether an 8+ component remains.
      const parent = new Map(nodeIds.map((id) => [id, id]))
      const find = (x: string): string => {
        while (parent.get(x) !== x) {
          parent.set(x, parent.get(parent.get(x)!)!)
          x = parent.get(x)!
        }
        return x
      }
      for (const e of kept) parent.set(find(e.source), find(e.target))
      const sizes = new Map<string, number>()
      for (const id of nodeIds) sizes.set(find(id), (sizes.get(find(id)) ?? 0) + 1)
      return { r, largest: Math.max(...sizes.values()), edges: kept.length }
    })
    note(`A3 largest components: ${roles.map((x) => x.largest).join(", ")}; edges: ${roles.map((x) => x.edges).join(", ")}`)
    let checked = 0
    for (let k = 1; k < thresholds.length; k++) {
      if (roles[k]!.largest < CORE_MIN) continue
      checked++
      for (const id of nodeIds) {
        const before = RANK[roles[k - 1]!.r.role.get(id)!]
        const after = RANK[roles[k]!.r.role.get(id)!]
        expect(after, `memory ${id} at ${thresholds[k]}`).toBeLessThanOrEqual(before)
      }
    }
    expect(checked).toBe(thresholds.length - 1)
  })
})

// ---------------------------------------------------------------------------
// A5, A6, A7: placement and core fit

function clumpDiscs(c: Classification, positions: Map<string, Point>) {
  return c.satellites.map((members) => {
    // A clump is packed outward from its first member, which sits at its centre.
    const pts = members.map((id) => positions.get(id)!)
    const { x: cx, y: cy } = pts[0]!
    return { cx, cy, r: Math.max(...pts.map((p) => Math.hypot(p.x - cx, p.y - cy))), n: members.length }
  })
}

function syntheticClassification(clumps: number, haloCount: number, coreCount = 60): Classification {
  const r = rng(5)
  const nodes: string[] = [...ids("core", coreCount)]
  const edges: { source: string; target: string }[] = []
  for (let i = 1; i < coreCount; i++) edges.push({ source: `core${i - 1}`, target: `core${i}` })
  for (let k = 0; k < clumps; k++) {
    const size = 2 + Math.floor(r() * 6)
    const m = ids(`k${k}_`, size)
    nodes.push(...m)
    for (let i = 1; i < size; i++) edges.push({ source: m[i - 1]!, target: m[i]! })
  }
  nodes.push(...ids("halo", haloCount))
  return classify(nodes, edges)
}

describe("placeOuter", () => {
  const sectorShare = (discs: { cx: number; cy: number }[]) => {
    const angles = discs.map((d) => Math.atan2(d.cy, d.cx)).sort((a, b) => a - b)
    let worst = 0
    for (const a of angles) {
      const inWindow = angles.filter((b) => {
        let d = b - a
        while (d < 0) d += 2 * Math.PI
        return d < Math.PI / 2
      }).length
      worst = Math.max(worst, inWindow)
    }
    return worst / angles.length
  }

  it("A5: on a synthetic graph no two clumps overlap and every clump centre clears 1.15R plus its radius", () => {
    const c = syntheticClassification(70, 600)
    const R = coreRadius(c.core.length)
    const { positions } = placeOuter(c, R)
    const discs = clumpDiscs(c, positions)
    expect(discs).toHaveLength(70)
    for (const d of discs) expect(Math.hypot(d.cx, d.cy)).toBeGreaterThanOrEqual(1.15 * R + d.r)
    for (let i = 0; i < discs.length; i++) {
      for (let j = i + 1; j < discs.length; j++) {
        const a = discs[i]!
        const b = discs[j]!
        expect(Math.hypot(a.cx - b.cx, a.cy - b.cy)).toBeGreaterThan(a.r + b.r)
      }
    }
  })

  for (const size of SIZES) {
    it(`A5: on the ${size} fixture clumps do not overlap, clear 1.15R plus radius, sit within 2.0R and no 90 degree sector holds over half`, () => {
      const { result } = realRoles(size)
      const R = coreRadius(result.core.length)
      const { positions } = placeOuter(result, R)
      const discs = clumpDiscs(result, positions)
      expect(discs.length).toBeGreaterThan(4)
      const quadrants = [0, 0, 0, 0]
      for (const d of discs) {
        quadrants[(d.cx >= 0 ? 0 : 1) + (d.cy >= 0 ? 0 : 2)]!++
      }
      note(
        `A5 ${size}: clumps=${discs.length} R=${R.toFixed(1)} maxCentre/R=${(Math.max(...discs.map((d) => Math.hypot(d.cx, d.cy))) / R).toFixed(3)} ` +
          `slidingSector=${sectorShare(discs).toFixed(3)} quadrants=${quadrants.join("/")}`,
      )
      for (const d of discs) {
        expect(Math.hypot(d.cx, d.cy)).toBeGreaterThanOrEqual(1.15 * R + d.r)
        expect(Math.hypot(d.cx, d.cy)).toBeLessThanOrEqual(2.0 * R)
      }
      for (let i = 0; i < discs.length; i++) {
        for (let j = i + 1; j < discs.length; j++) {
          const a = discs[i]!
          const b = discs[j]!
          expect(Math.hypot(a.cx - b.cx, a.cy - b.cy)).toBeGreaterThan(a.r + b.r)
        }
      }
      expect(sectorShare(discs)).toBeLessThanOrEqual(0.5)
    })
  }

  it("A6: every halo node lies between 1.15R and the halo's outer radius, denser in the inner half of that span", () => {
    for (const c of [syntheticClassification(40, 3000), realRoles("all").result]) {
      const R = coreRadius(c.core.length)
      const outer = placeOuter(c, R)
      const inner = 1.15 * R
      expect(outer.haloOuter).toBeGreaterThan(inner)
      const mid = (inner + outer.haloOuter) / 2
      let innerCount = 0
      let outerCount = 0
      for (const id of c.halo) {
        const d = radius(outer.positions.get(id)!)
        expect(d).toBeGreaterThanOrEqual(inner - 1e-9)
        expect(d).toBeLessThanOrEqual(outer.haloOuter + 1e-9)
        if (d < mid) innerCount++
        else outerCount++
      }
      const innerDensity = innerCount / (Math.PI * (mid ** 2 - inner ** 2))
      const outerDensity = outerCount / (Math.PI * (outer.haloOuter ** 2 - mid ** 2))
      note(`A6: halo=${c.halo.length} inner/outer density ${(innerDensity / outerDensity).toFixed(2)}`)
      expect(c.halo.length).toBeGreaterThan(1000)
      expect(innerDensity).toBeGreaterThan(outerDensity)
    }
  })

  it("A6: a halo node's position is identical across placements with equal radii", () => {
    const base = realRoles("all").result
    const R = coreRadius(base.core.length)
    // Same core count and halo ids; the satellites are other nodes entirely.
    const other: Classification = {
      ...base,
      satellites: base.satellites.map((g) => g.map((id) => `renamed:${id}`)),
    }
    const a = placeOuter(base, R)
    const b = placeOuter(other, R)
    expect(b.haloInner).toBe(a.haloInner)
    expect(b.haloOuter).toBe(a.haloOuter)
    for (const id of base.halo) expect(b.positions.get(id)).toEqual(a.positions.get(id))
    const again = placeOuter(base, R)
    for (const id of base.halo) expect(again.positions.get(id)).toEqual(a.positions.get(id))
  })
})

describe("fitCore", () => {
  const cases: [string, (r: () => number) => Point][] = [
    ["uniform square", (r) => ({ x: (r() - 0.5) * 100, y: (r() - 0.5) * 100 })],
    ["gaussian blob far from the origin", (r) => ({ x: 5000 + Math.sqrt(-2 * Math.log(r() + 1e-12)) * Math.cos(6.283 * r()) * 40, y: -3000 + Math.sqrt(-2 * Math.log(r() + 1e-12)) * Math.sin(6.283 * r()) * 40 })],
    ["heavy tail", (r) => { const d = 1 / (r() + 1e-6) ** 1.5; const a = 6.283 * r(); return { x: d * Math.cos(a), y: d * Math.sin(a) } }],
    ["tiny spread", (r) => ({ x: r() * 0.001, y: r() * 0.001 })],
    ["huge spread", (r) => ({ x: (r() - 0.3) * 1e6, y: (r() - 0.8) * 1e6 })],
  ]
  for (const [name, gen] of cases) {
    it(`A7: ${name}: no core node beyond R and at most 10% beyond 0.85R`, () => {
      for (const R of [60, 316.2]) {
        const r = rng(77)
        const pos = new Map<string, Point>()
        for (let i = 0; i < 1000; i++) pos.set(`n${i}`, gen(r))
        const fitted = [...fitCore(pos, R).values()]
        expect(fitted).toHaveLength(1000)
        expect(fitted.filter((p) => radius(p) > R).length).toBe(0)
        const beyondKnee = fitted.filter((p) => radius(p) > 0.85 * R + 1e-9).length
        expect(beyondKnee).toBeLessThanOrEqual(100)
      }
    })
  }
})

// ---------------------------------------------------------------------------
// A8: halo density control

describe("halo density", () => {
  function fitViewGain(haloSize: number, viewport: { w: number; h: number }) {
    const { result: c } = realRoles("all")
    const R = coreRadius(c.core.length)
    const outer = placeOuter(c, R)
    const pxPerUnit = Math.min(viewport.w, viewport.h) / (2 * outer.haloOuter)
    const handlers: (() => void)[] = []
    const sigma = {
      on: (event: string, fn: () => void) => {
        if (event === "beforeRender") handlers.push(fn)
        return sigma
      },
      graphToViewport: (p: { x: number; y: number }) => ({
        x: viewport.w / 2 + p.x * pxPerUnit,
        y: viewport.h / 2 + p.y * pxPerUnit,
      }),
      scaleSize: (s: number) => s,
    }
    const sizes = new Map<string, number>()
    for (const id of c.halo) sizes.set(id, haloSize)
    for (const id of [...c.core, ...c.satellites.flat()]) sizes.set(id, 3)
    const graph = { getNodeAttribute: (id: string) => sizes.get(id) as unknown }
    const clock: GlowClock = { time: 0 }
    trackDensityGain(sigma as never, graph, c, clock, outer)
    expect(handlers).toHaveLength(1)
    handlers[0]!()
    const spacingPx = Math.sqrt((Math.PI * (outer.haloOuter ** 2 - outer.haloInner ** 2)) / c.halo.length) * pxPerUnit
    const scaledRadius = haloSize * (clock.haloScale ?? 1)
    return { clock, spacingPx, coverage: (scaledRadius * scaledRadius) / (spacingPx * spacingPx) }
  }

  for (const haloSize of [1.5, 20]) {
    for (const viewport of [{ w: 1280, h: 800 }, { w: 1920, h: 1080 }]) {
      it(`A8: halo gain times coverage stays at or below COVERAGE_TARGET at the fit view, halo size ${haloSize}, ${viewport.w}x${viewport.h}`, () => {
        const { clock, spacingPx, coverage } = fitViewGain(haloSize, viewport)
        note(`A8 size=${haloSize} ${viewport.w}x${viewport.h}: spacing=${spacingPx.toFixed(2)}px gain=${clock.haloGain} scale=${clock.haloScale} coverage=${coverage.toFixed(3)}`)
        expect(typeof clock.haloGain).toBe("number")
        expect(typeof clock.haloScale).toBe("number")
        expect(clock.haloGain!).toBeGreaterThan(0)
        expect(clock.haloGain!).toBeLessThanOrEqual(1)
        expect(clock.haloScale!).toBeGreaterThan(0)
        expect(clock.haloScale!).toBeLessThanOrEqual(1)
        expect(clock.haloGain! * coverage).toBeLessThanOrEqual(COVERAGE_TARGET + 1e-9)
      })
    }
  }

  const gl = () => ({ uniform1f: vi.fn(), uniform2f: vi.fn(), uniformMatrix3fv: vi.fn() })
  const params = { matrix: new Float32Array(9), sizeRatio: 1, correctionRatio: 1, pixelRatio: 1, zoomRatio: 1, width: 10, height: 10, downSizingRatio: 1 }
  const locations = { u_time: "T", u_matrix: "M", u_sizeRatio: "S", u_correctionRatio: "C", u_haloGain: "HG", u_haloScale: "HS" }
  type Proto = {
    setUniforms: (p: unknown, i: unknown) => void
    getDefinition: () => { VERTEX_SHADER_SOURCE: string; UNIFORMS: string[] }
  }

  it("A8: the program feeds u_haloGain and u_haloScale from the clock, live", () => {
    const clock: GlowClock = { time: 1, haloGain: 0.3, haloScale: 0.5 }
    const proto = createNodeGlowProgram({ additive: true, clock }).prototype as unknown as Proto
    const g = gl()
    proto.setUniforms.call({}, params, { gl: g, uniformLocations: locations })
    expect(g.uniform1f).toHaveBeenCalledWith("HG", 0.3)
    expect(g.uniform1f).toHaveBeenCalledWith("HS", 0.5)
    clock.haloGain = 0.12
    clock.haloScale = 0.25
    const g2 = gl()
    proto.setUniforms.call({}, params, { gl: g2, uniformLocations: locations })
    expect(g2.uniform1f).toHaveBeenCalledWith("HG", 0.12)
    expect(g2.uniform1f).toHaveBeenCalledWith("HS", 0.25)
    const g3 = gl()
    const fresh = createNodeGlowProgram({ additive: true, clock: { time: 0 } }).prototype as unknown as Proto
    fresh.setUniforms.call({}, params, { gl: g3, uniformLocations: locations })
    expect(g3.uniform1f).toHaveBeenCalledWith("HG", 1)
    expect(g3.uniform1f).toHaveBeenCalledWith("HS", 1)
  })

  // Resolves the `#ifdef LIGHT_MODE` blocks the way the GLSL preprocessor would.
  function activeSource(source: string, defined: Set<string>): string {
    const out: string[] = []
    const stack: boolean[] = []
    for (const line of source.split("\n")) {
      const t = line.trim()
      let m: RegExpMatchArray | null
      if ((m = t.match(/^#ifdef\s+(\w+)/))) stack.push(defined.has(m[1]!))
      else if ((m = t.match(/^#ifndef\s+(\w+)/))) stack.push(!defined.has(m[1]!))
      else if (t.startsWith("#else")) stack.push(!stack.pop()!)
      else if (t.startsWith("#endif")) stack.pop()
      else if ((m = t.match(/^#define\s+(\w+)/))) {
        if (stack.every(Boolean)) defined.add(m[1]!)
      } else if (stack.every(Boolean)) out.push(line)
    }
    return out.join("\n")
  }

  it("A8: the dark-theme shader scales halo radius and brightness by them; the light-theme shader does not", () => {
    const dark = createNodeGlowProgram({ additive: true, clock: { time: 0 } }).prototype as unknown as Proto
    const light = createNodeGlowProgram({ additive: false, clock: { time: 0 } }).prototype as unknown as Proto
    const darkDef = dark.getDefinition.call({})
    expect(darkDef.UNIFORMS).toEqual(expect.arrayContaining(["u_haloGain", "u_haloScale"]))
    const darkSrc = activeSource(darkDef.VERTEX_SHADER_SOURCE, new Set())
    expect(darkSrc).toMatch(/radius\s*\*=\s*u_haloScale/)
    expect(darkSrc).toMatch(/brightness\s*\*=\s*u_haloGain/)
    const withoutDeclarations = (src: string) =>
      src.split("\n").filter((l) => !l.trim().startsWith("uniform")).join("\n")
    const lightSrc = withoutDeclarations(activeSource(light.getDefinition.call({}).VERTEX_SHADER_SOURCE, new Set()))
    expect(lightSrc).not.toMatch(/u_haloScale/)
    expect(lightSrc).not.toMatch(/u_haloGain/)
  })
})

// ---------------------------------------------------------------------------
// A11: default node limit

describe("graph prefs", () => {
  const KEY = "darkmem-graph-prefs"
  const load = async (nodeLimit: number, version = 0) => {
    localStorage.setItem(KEY, JSON.stringify({ state: { nodeLimit, allNodes: false, dimUnrelated: 15 }, version }))
    await useGraphPrefs.persist.rehydrate()
    return useGraphPrefs.getState().nodeLimit
  }
  afterEach(() => localStorage.removeItem(KEY))

  it("A11: the default node limit is 1,000", async () => {
    expect(NODE_LIMIT_DEFAULT).toBe(1000)
    expect(useGraphPrefs.getInitialState().nodeLimit).toBe(1000)
    localStorage.removeItem(KEY)
    useGraphPrefs.setState({ nodeLimit: 4321 })
    useGraphPrefs.setState(useGraphPrefs.getInitialState(), true)
    expect(useGraphPrefs.getState().nodeLimit).toBe(1000)
  })

  it("A11: a stored 200 from before the change loads as 1,000", async () => {
    expect(await load(200, 0)).toBe(1000)
  })

  it("A11: any other stored value from before the change loads unchanged", async () => {
    for (const v of [50, 100, 199, 201, 300, 500, 1000, 1500, 5000, 50_000]) {
      expect(await load(v, 0), `stored ${v}`).toBe(v)
    }
  })
})

// ---------------------------------------------------------------------------
// A12: the code canvas keeps its classification

describe("code canvas roles", () => {
  it("A12: the roles a code graph gets are those of the unscored classification", () => {
    const path = (prefix: string, n: number) => ids(prefix, n)
    const components: [string[], ConstellationRole][] = [
      [path("a", 12), "core"],
      [path("b", 8), "core"],
      [path("c", 7), "satellite"],
      [path("d", 2), "satellite"],
      [["e0", "e1", "e2"], "satellite"],
    ]
    const iso = ids("iso", 5)
    const expected = new Map<string, ConstellationRole>()
    const g = new Graph({ type: "undirected" })
    for (const [members, role] of components) {
      members.forEach((id, i) => {
        expected.set(id, role)
        g.addNode(id, { x: Math.cos(i), y: Math.sin(i), size: 4 })
        if (id.startsWith("e")) {
          if (i > 0) g.addEdge("e0", id)
        } else if (i > 0) g.addEdge(members[i - 1]!, id)
      })
    }
    for (const id of iso) {
      expected.set(id, "halo")
      g.addNode(id, { x: 0, y: 0, size: 4 })
    }
    const runner = createConstellationRunner(g, { layoutMs: 1000, fa2Settings: {} })
    try {
      for (const [id, role] of expected) {
        expect(runner.classification.role.get(id), id).toBe(role)
        expect(g.getNodeAttribute(id, "_role"), id).toBe(role)
      }
      expect(new Set(runner.classification.core)).toEqual(
        new Set(components.filter(([, r]) => r === "core").flatMap(([m]) => m)),
      )
      expect(runner.classification.halo.slice().sort()).toEqual(iso)
      expect(runner.classification.satellites.map((s) => s.length).sort((x, y) => y - x)).toEqual([7, 3, 2])
    } finally {
      runner.kill()
    }
  })
})

// ---------------------------------------------------------------------------
// A13: fixtures carry no real data

describe("committed fixtures", () => {
  const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i
  const files = ["200", "1000", "all"].map((s) => `real-corpus-${s}.json`)

  function violations(node: unknown, where: string, out: string[]) {
    if (typeof node === "string") {
      if (UUID.test(node)) out.push(`${where}: UUID-shaped string`)
      return
    }
    if (Array.isArray(node)) {
      node.forEach((v, i) => violations(v, `${where}[${i}]`, out))
      return
    }
    if (node && typeof node === "object") {
      for (const [k, v] of Object.entries(node)) {
        if (k === "tags" || k === "project") out.push(`${where}.${k}: key present`)
        if (k === "content" && !(typeof v === "string" && /^Memory \d+$/.test(v))) {
          out.push(`${where}.content: ${JSON.stringify(v)}`)
        }
        if (k === "clusterNames" && v && typeof v === "object") {
          for (const [ck, cv] of Object.entries(v)) {
            if (!(typeof cv === "string" && /^Cluster \d+$/.test(cv))) out.push(`${where}.clusterNames.${ck}: ${JSON.stringify(cv)}`)
          }
        }
        if (k === "name" && !(typeof v === "string" && /^Entity \d+$/.test(v))) {
          out.push(`${where}.name: ${JSON.stringify(v)}`)
        }
        violations(v, `${where}.${k}`, out)
      }
    }
  }

  for (const file of files) {
    it(`A13: ${file} holds no content, tag, project, cluster name or UUID beyond the anonymised forms`, () => {
      const raw = readFileSync(resolve(process.cwd(), "src/features/graph/fixtures", file), "utf8")
      expect(raw).not.toMatch(UUID)
      const json = JSON.parse(raw) as { memories: { id: string }[] }
      const found: string[] = []
      violations(json, file, found)
      expect(found).toEqual([])
      expect(json.memories.length).toBeGreaterThan(0)
      for (const m of json.memories) expect(m.id).toMatch(/^[0-9a-f]{12}$/)
    })
  }

  for (const size of SIZES) {
    it(`A13: the ${size} corpus as loaded has contents of the form "Memory <i>" and no UUID ids`, () => {
      const c = loadRealCorpus(size)
      expect(c.memories.length).toBeGreaterThan(0)
      for (const m of c.memories) {
        expect(m.content).toMatch(/^Memory \d+$/)
        expect(m.id).not.toMatch(UUID)
        expect(m.tags).toEqual([])
        expect("project" in m).toBe(false)
      }
      for (const name of Object.values(c.clusterNames)) expect(name).toMatch(/^Cluster \d+$/)
    })
  }
})

// ---------------------------------------------------------------------------
// Renderer harness: A4, A9, A10

type RendererProps = ComponentProps<typeof Graph2DRenderer>

function Scene(props: {
  size: RealCorpusSize
  entityLayer?: boolean
  sizeMode?: string
  selectedNodeId?: string | null
}) {
  const { tokens, palette } = useMemoryGraphTheme()
  const c = loadRealCorpus(props.size)
  return (
    <div style={{ position: "relative", width: 800, height: 600 }}>
      <Graph2DRenderer
        filteredMemories={c.memories}
        filteredEdges={c.edges}
        selectedNodeId={props.selectedNodeId ?? null}
        onNodeSelect={() => {}}
        onReady={() => {}}
        sizeMode={(props.sizeMode ?? "connections") as RendererProps["sizeMode"]}
        colorMode="cluster"
        hullMode="none"
        entityLayerEnabled={props.entityLayer ?? false}
        entities={c.entities}
        entityRelations={c.entityRelations}
        tokens={tokens}
        palette={palette}
        clusterNames={c.clusterNames}
      />
    </div>
  )
}

interface FakeSigmaView {
  graph: Graph
  camera: { setState: (s: { ratio?: number }) => void }
  emit: (event: string, ...args: unknown[]) => void
  settings: { nodeReducer: (id: string, data: Record<string, unknown>) => Record<string, unknown> }
}
const lastSigma = () => h.sigmas[h.sigmas.length - 1] as FakeSigmaView
const advance = (ms: number) =>
  act(() => {
    vi.advanceTimersByTime(ms)
  })
const labelOf = (s: FakeSigmaView, id: string) =>
  (s.settings.nodeReducer(id, s.graph.getNodeAttributes(id)).label as string | undefined) ?? ""

describe("memory 2D renderer on the real corpus", () => {
  beforeEach(() => {
    h.sigmas.length = 0
    h.workers.length = 0
    vi.useFakeTimers({
      toFake: ["setTimeout", "clearTimeout", "requestAnimationFrame", "cancelAnimationFrame", "performance"],
    })
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it("A4: with the entity layer on, an entity takes the highest role of its memories and no memory role changes", () => {
    const { corpus, nodeIds } = realRoles(1000)
    const memoryIds = new Set(nodeIds)
    const off = render(<Scene size={1000} entityLayer={false} />)
    advance(50)
    const gOff = lastSigma().graph
    const offRoles = new Map(nodeIds.map((id) => [id, gOff.getNodeAttribute(id, "_role") as ConstellationRole]))
    off.unmount()

    render(<Scene size={1000} entityLayer={true} />)
    advance(50)
    const g = lastSigma().graph
    for (const id of nodeIds) expect(g.getNodeAttribute(id, "_role"), id).toBe(offRoles.get(id))
    expect(g.edges().some((e) => g.getEdgeAttribute(e, "_edgeKind") === "membership")).toBe(true)
    expect(g.edges().some((e) => g.getEdgeAttribute(e, "_edgeKind") === "relation")).toBe(true)

    const tally: Record<string, number> = { core: 0, satellite: 0, halo: 0 }
    for (const ent of corpus.entities) {
      const linked = ent.memory_ids.filter((m) => memoryIds.has(m))
      if (linked.length === 0 || !g.hasNode(`entity:${ent.id}`)) continue
      const best = Math.max(...linked.map((m) => RANK[offRoles.get(m)!]))
      const role = g.getNodeAttribute(`entity:${ent.id}`, "_role") as ConstellationRole
      expect(RANK[role], `entity ${ent.id}`).toBe(best)
      tally[role]!++
    }
    note(`A4 entity roles: ${JSON.stringify(tally)}`)
    expect(tally.core! + tally.satellite! + tally.halo!).toBeGreaterThan(100)
    expect(tally.core).toBeGreaterThan(0)
  })

  for (const sizeMode of ["importance", "connections", "uniform"]) {
    it(`A9: every halo node's size equals HALO_SIZE, at most 40% of the median core size (size mode ${sizeMode})`, () => {
      render(<Scene size={1000} sizeMode={sizeMode} />)
      advance(50)
      const g = lastSigma().graph
      const halo = g.filterNodes((_id, a) => a._role === "halo")
      const core = g
        .filterNodes((_id, a) => a._role === "core")
        .map((id) => g.getNodeAttribute(id, "size") as number)
        .sort((a, b) => a - b)
      expect(halo.length).toBeGreaterThan(100)
      expect(core.length).toBeGreaterThan(100)
      const median = core.length % 2 ? core[core.length >> 1]! : (core[core.length / 2 - 1]! + core[core.length / 2]!) / 2
      for (const id of halo) expect(g.getNodeAttribute(id, "size"), id).toBe(HALO_SIZE)
      expect(HALO_SIZE).toBeLessThanOrEqual(0.4 * median)
      expect(new Set(halo.map((id) => g.getNodeAttribute(id, "_degree"))).size).toBeGreaterThan(1)
    })
  }

  it("A10: at most 2% of the 1,000 memories are hubs", () => {
    const { corpus, nodeIds } = realRoles(1000)
    const degrees = new Map(nodeIds.map((id) => [id, 0]))
    for (const e of corpus.edges) {
      degrees.set(e.source, degrees.get(e.source)! + 1)
      degrees.set(e.target, degrees.get(e.target)! + 1)
    }
    const hubs = topHubs(degrees)
    expect(hubs.size).toBeGreaterThan(0)
    expect(hubs.size).toBeLessThanOrEqual(0.02 * nodeIds.length)

    render(<Scene size={1000} />)
    advance(50)
    const s = lastSigma()
    s.camera.setState({ ratio: 0.3 })
    advance(50)
    const labelled = s.graph.nodes().filter((id) => labelOf(s, id) !== "")
    note(`A10 labelled once zoomed in: ${labelled.length}`)
    expect(labelled.length).toBeGreaterThan(0)
    expect(labelled.length).toBeLessThanOrEqual(0.02 * nodeIds.length)
  })

  it("A10: at the fit view only a hovered or selected node carries a label", () => {
    const { rerender } = render(<Scene size={1000} />)
    advance(50)
    const s = lastSigma()
    const all = s.graph.nodes()
    expect(all).toHaveLength(1000)
    const labelled = (ids_: string[]) => ids_.filter((id) => labelOf(s, id) !== "")
    expect(labelled(all)).toEqual([])

    const target = all[17]!
    act(() => s.emit("enterNode", { node: target }))
    advance(50)
    expect(labelOf(s, target)).not.toBe("")
    const neighbours = new Set(s.graph.neighbors(target))
    expect(labelled(all.filter((id) => id !== target && !neighbours.has(id)))).toEqual([])
    act(() => s.emit("leaveNode", { node: target }))
    advance(50)
    expect(labelled(all)).toEqual([])

    rerender(<Scene size={1000} selectedNodeId={target} />)
    advance(50)
    expect(labelOf(s, target)).not.toBe("")
    const around = new Set(s.graph.neighbors(target))
    expect(labelled(all.filter((id) => id !== target && !around.has(id)))).toEqual([])
    note(`A10 selected ${target}: neighbours=${around.size} labelled neighbours=${labelled([...around]).length}`)
  })
})
