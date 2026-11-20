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
    createCanvas() {
      const canvas = document.createElement("canvas")
      this.container.appendChild(canvas)
      return canvas
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
import { HALO_SIZE, type ConstellationRole } from "@/features/graph/lib/constellation-layout"
import { ISLAND_K, layoutIslands } from "@/features/graph/lib/cluster-layout"
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
const ids = (prefix: string, n: number) => Array.from({ length: n }, (_, i) => `${prefix}${i}`)

function realIslands(size: RealCorpusSize) {
  const c = loadRealCorpus(size)
  const nodeIds = c.memories.map((m) => m.id)
  return { corpus: c, nodeIds, layout: layoutIslands(c.memories, c.edges) }
}

/** The real corpus clusters every memory, so a quarter is made unclustered
 *  and unlinked to load the loose island the way the halo was loaded. */
function looseIslandScene() {
  const c = loadRealCorpus("all")
  const unlinked = new Set(c.memories.filter((_m, i) => i % 4 === 0).map((m) => m.id))
  const layout = layoutIslands(
    c.memories.map((m) => (unlinked.has(m.id) ? { ...m, cluster: -1 } : m)),
    c.edges.filter((e) => !unlinked.has(e.source) && !unlinked.has(e.target)),
  )
  const loose = layout.groups.find((g) => g.loose)!
  const cls = {
    core: layout.groups.filter((g) => !g.loose).flatMap((g) => g.members),
    satellites: [] as string[][],
    halo: loose.members,
  }
  return { layout, cls, outer: { haloInner: 0, haloOuter: loose.radius } }
}

// ---------------------------------------------------------------------------
// A8: halo density control

describe("halo density", () => {
  function fitViewGain(haloSize: number, viewport: { w: number; h: number }) {
    const { layout, cls: c, outer } = looseIslandScene()
    const pxPerUnit = Math.min(viewport.w, viewport.h) / (2 * layout.extent)
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
  /** Make every fourth memory unclustered and unlinked: the loose island. */
  withLoose?: boolean
}) {
  const { tokens, palette } = useMemoryGraphTheme()
  const c = loadRealCorpus(props.size)
  const loose = new Set(props.withLoose ? c.memories.filter((_m, i) => i % 4 === 0).map((m) => m.id) : [])
  const memories = c.memories.map((m) => (loose.has(m.id) ? { ...m, cluster: -1 } : m))
  const edges = c.edges.filter((e) => !loose.has(e.source) && !loose.has(e.target))
  return (
    <div style={{ position: "relative", width: 800, height: 600 }}>
      <Graph2DRenderer
        filteredMemories={memories}
        filteredEdges={edges}
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
  settings: {
    nodeReducer: (id: string, data: Record<string, unknown>) => Record<string, unknown>
    edgeReducer: (id: string, data: Record<string, unknown>) => Record<string, unknown>
  }
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

  it("islands A10 (UX-4): on the real corpus the entity layer moves no memory and changes no role; an entity takes its memories' highest role and sits by their centroid", () => {
    const { corpus, nodeIds } = realIslands(1000)
    const memoryIds = new Set(nodeIds)
    const off = render(<Scene size={1000} entityLayer={false} />)
    advance(50)
    const gOff = lastSigma().graph
    const before = new Map(
      nodeIds.map((id) => [id, [gOff.getNodeAttribute(id, "_role"), gOff.getNodeAttribute(id, "x"), gOff.getNodeAttribute(id, "y")]]),
    )
    off.unmount()

    render(<Scene size={1000} entityLayer={true} />)
    advance(50)
    const g = lastSigma().graph
    for (const id of nodeIds) {
      const [role, x, y] = before.get(id)!
      expect(g.getNodeAttribute(id, "_role"), id).toBe(role)
      expect(g.getNodeAttribute(id, "x"), id).toBeCloseTo(x as number, 6)
      expect(g.getNodeAttribute(id, "y"), id).toBeCloseTo(y as number, 6)
    }
    expect(g.edges().some((e) => g.getEdgeAttribute(e, "_edgeKind") === "membership")).toBe(true)

    let checked = 0
    for (const ent of corpus.entities) {
      const id = `entity:${ent.id}`
      const linked = ent.memory_ids.filter((m) => memoryIds.has(m))
      if (linked.length === 0 || !g.hasNode(id)) continue
      const best = Math.max(...linked.map((m) => RANK[before.get(m)![0] as ConstellationRole]))
      expect(RANK[g.getNodeAttribute(id, "_role") as ConstellationRole], id).toBe(best)
      const cx = linked.reduce((t, m) => t + (g.getNodeAttribute(m, "x") as number), 0) / linked.length
      const cy = linked.reduce((t, m) => t + (g.getNodeAttribute(m, "y") as number), 0) / linked.length
      const d = Math.hypot((g.getNodeAttribute(id, "x") as number) - cx, (g.getNodeAttribute(id, "y") as number) - cy)
      expect(d, id).toBeLessThanOrEqual(0.25 * ISLAND_K)
      checked++
    }
    expect(checked).toBeGreaterThan(100)
  })

  it("islands A8 (UI-2): an edge is hidden at rest exactly when its endpoints are on different islands, and hovering a node lights its edges", () => {
    const { layout } = realIslands(1000)
    render(<Scene size={1000} />)
    advance(50)
    const s = lastSigma()
    const g = s.graph
    const hidden = (e: string) => !!s.settings.edgeReducer(e, g.getEdgeAttributes(e)).hidden
    let inside = 0
    let across = 0
    for (const e of g.edges()) {
      const same = layout.groupOf.get(g.source(e)) === layout.groupOf.get(g.target(e))
      expect(hidden(e), e).toBe(!same)
      if (same) inside++
      else across++
    }
    note(`islands A8 rest edges: ${inside} drawn inside an island, ${across} hidden across islands`)
    expect(inside).toBeGreaterThan(0)
    expect(across).toBeGreaterThan(0)

    const bridge = g.nodes().find((id) =>
      g.edges(id).some((e) => layout.groupOf.get(g.source(e)) !== layout.groupOf.get(g.target(e))),
    )!
    act(() => s.emit("enterNode", { node: bridge }))
    advance(50)
    for (const e of g.edges(bridge)) expect(hidden(e), e).toBe(false)
  })

  for (const sizeMode of ["importance", "connections", "uniform"]) {
    it(`islands A9 (UI-3): every loose memory's size equals HALO_SIZE, at most 40% of the median island size (size mode ${sizeMode})`, () => {
      render(<Scene size={1000} sizeMode={sizeMode} withLoose />)
      advance(50)
      const g = lastSigma().graph
      const loose = g.filterNodes((_id, a) => a._role === "halo")
      const island = g
        .filterNodes((_id, a) => a._role === "core")
        .map((id) => g.getNodeAttribute(id, "size") as number)
        .sort((a, b) => a - b)
      expect(loose.length).toBeGreaterThan(100)
      expect(island.length).toBeGreaterThan(100)
      const median = island.length % 2 ? island[island.length >> 1]! : (island[island.length / 2 - 1]! + island[island.length / 2]!) / 2
      for (const id of loose) expect(g.getNodeAttribute(id, "size"), id).toBe(HALO_SIZE)
      expect(HALO_SIZE).toBeLessThanOrEqual(0.4 * median)
    })
  }

  it("A10: at most 2% of the 1,000 memories are hubs", () => {
    const { corpus, nodeIds } = realIslands(1000)
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
