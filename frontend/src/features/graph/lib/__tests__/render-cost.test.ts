import { afterEach, describe, expect, it, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import Graph from "graphology"

// sigma reads WebGL enums off the global constructors at module load; the test
// DOM ships neither.
vi.hoisted(() => {
  const GL = { FLOAT: 0x1406, UNSIGNED_BYTE: 0x1401, TRIANGLES: 0x0004, ONE: 1 }
  Object.assign(globalThis, { WebGLRenderingContext: GL, WebGL2RenderingContext: GL })
})

vi.mock("graphology-layout-forceatlas2/worker", () => ({
  default: class {
    constructor(public graph: Graph) {}
    start() {}
    stop() {}
    kill() {}
    isRunning() {
      return false
    }
  },
}))

import { trackDensityGain, type GlowClock } from "../node-glow-program"
import { useMemoryGraphTheme } from "../memory-graph-theme"
import { createClusterRunner } from "../cluster-runner"
import type { DemoCodeNode } from "@/features/code/types"

const SOURCES = import.meta.glob<string>("/src/**/*.{ts,tsx}", {
  query: "?raw",
  import: "default",
  eager: true,
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe("render cost", () => {
  it("the density grid is cached per layout version", () => {
    const g = new Graph()
    for (let i = 0; i < 400; i++) {
      g.addNode(`c${i}`, { x: (i % 20) * 3, y: Math.floor(i / 20) * 3, size: 6 })
    }
    const ids = g.nodes()
    let render = () => {}
    const sigma = {
      on: (event: string, f: () => void) => {
        if (event === "beforeRender") render = f
      },
      graphToViewport: (p: { x: number; y: number }) => p,
      scaleSize: (s: number) => s,
    }
    const clock: GlowClock = { time: 0 }
    trackDensityGain(sigma as never, g, { core: ids, satellites: [], halo: [] }, clock, undefined, true)

    const reads = vi.spyOn(g, "getNodeAttribute")
    const sets = vi.spyOn(Map.prototype, "set")
    const xReads = () => reads.mock.calls.filter((c) => c[1] === "x").length
    for (let i = 0; i < 10; i++) render()
    expect(xReads()).toBe(ids.length)
    expect(sets.mock.calls.filter((c) => typeof c[0] === "string")).toEqual([])

    g.updateEachNodeAttributes(
      (_id, attrs) => {
        attrs.x = (attrs.x as number) * 0.5
        return attrs
      },
      { attributes: ["x", "y"] },
    )
    for (let i = 0; i < 10; i++) render()
    expect(xReads()).toBe(2 * ids.length)
  })

  it("one theme observer serves every consumer", () => {
    const Real = globalThis.MutationObserver
    let created = 0
    let disconnected = 0
    class Counting extends Real {
      constructor(callback: MutationCallback) {
        super(callback)
        created++
      }
      disconnect() {
        disconnected++
        super.disconnect()
      }
    }
    vi.stubGlobal("MutationObserver", Counting)
    const hooks = Array.from({ length: 6 }, () => renderHook(() => useMemoryGraphTheme()))
    expect(created).toBe(1)
    for (const h of hooks) h.unmount()
    expect(disconnected).toBe(1)
  })

  it("remembered positions are pruned to the drawn nodes", async () => {
    const { forgetUndrawn, rememberPositions } = await import("../remembered-positions")
    const before = new Graph()
    for (let i = 0; i < 1000; i++) before.addNode(`n${i}`, { x: i, y: -i })
    const settled = new Map<string, { x: number; y: number }>()
    rememberPositions(settled, before)
    expect(settled.size).toBe(1000)
    const after = new Graph()
    for (let i = 0; i < 100; i++) after.addNode(`n${i * 10}`, { x: 0, y: 0 })
    forgetUndrawn(settled, after)
    expect(settled.size).toBe(100)
    expect(settled.get("n10")).toEqual({ x: 10, y: -10 })
    for (const renderer of [
      "/src/features/graph/components/graph-2d-renderer.tsx",
      "/src/features/code/components/code-glow-canvas.tsx",
    ]) {
      expect(SOURCES[renderer], renderer).toMatch(/forgetUndrawn\(/)
    }
  })

  it("symbolsByFile groups in linear time", async () => {
    const { groupSymbolsByFile } = await import("@/features/code/components/code-explorer")
    const symbol = (i: number, file: string): DemoCodeNode => ({
      id: `s${i}`,
      name: `sym${i}`,
      kind: "function",
      file,
      community: "c",
    })
    const mixed = [
      { id: "f", name: "a.py", kind: "file", file: "a.py", community: "c" } as DemoCodeNode,
      ...Array.from({ length: 5000 }, (_, i) => symbol(i, i % 3 ? "a.py" : "b.py")),
    ]
    const reference = new Map<string, DemoCodeNode[]>()
    for (const n of mixed) {
      if (n.kind === "file" || n.kind === "module") continue
      const list = reference.get(n.file) ?? []
      list.push(n)
      reference.set(n.file, list)
    }
    expect(groupSymbolsByFile(mixed)).toEqual(reference)
    const big = Array.from({ length: 50_000 }, (_, i) => symbol(i, "one.py"))
    const t0 = performance.now()
    const grouped = groupSymbolsByFile(big)
    expect(performance.now() - t0).toBeLessThan(200)
    expect(grouped.get("one.py")).toHaveLength(50_000)
  })

  it("KIND_CHART has one definition", () => {
    const declarations = Object.entries(SOURCES).flatMap(([file, text]) =>
      [...text.matchAll(/\b(?:const|let|var)\s+KIND_CHART\b/g)].map(() => file),
    )
    expect(declarations).toHaveLength(1)
  })

  it("runners share their scheduling code", () => {
    for (const runner of ["cluster-runner", "constellation-runner"]) {
      const text = SOURCES[`/src/features/graph/lib/${runner}.ts`]!
      expect(text, runner).toMatch(/from "\.\/layout-loop"/)
      expect(text, runner).not.toMatch(/requestAnimationFrame|setTimeout|forceatlas2\/worker/)
    }

    const frames: FrameRequestCallback[] = []
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => frames.push(cb))
    vi.stubGlobal("cancelAnimationFrame", () => {})
    const graph = new Graph()
    const memories = Array.from({ length: 300 }, (_, i) => ({ id: `m${i}`, cluster: i % 5 }))
    for (const m of memories) graph.addNode(m.id, { size: 4 })
    const edges = memories
      .filter((_m, i) => i >= 5)
      .map((m, i) => ({ source: m.id, target: `m${i}`, score: 0.5 + (i % 7) / 20 }))
    const runner = createClusterRunner(graph, {
      layoutMs: 60_000,
      fa2Settings: {},
      memories,
      edges,
      attachments: [],
      fresh: new Set(memories.map((m) => m.id)),
    })
    runner.start()
    expect(frames).toHaveLength(1)

    const RealMap = globalThis.Map
    let maps = 0
    class CountingMap<K, V> extends RealMap<K, V> {
      constructor(entries?: Iterable<readonly [K, V]> | null) {
        super(entries)
        maps++
      }
    }
    vi.stubGlobal("Map", CountingMap)
    try {
      for (let i = 0; i < 50; i++) frames[frames.length - 1]!(i * 16)
    } finally {
      vi.stubGlobal("Map", RealMap)
    }
    runner.kill()
    expect(frames.length).toBeGreaterThanOrEqual(50)
    expect(maps).toBe(0)
  })
})
