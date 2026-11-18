import { describe, it, expect } from "vitest"
import {
  classify,
  coreRadius,
  fitCore,
  placeOuter,
  CORE_MIN,
  HALO_MIN_OUTER,
  SATELLITE_RING_START,
  type ConstellationEdge,
  type Point,
} from "../constellation-layout"

const ids = (prefix: string, n: number) =>
  Array.from({ length: n }, (_, i) => `${prefix}${i}`)
const chain = (nodes: string[]): ConstellationEdge[] =>
  nodes.slice(1).map((id, i) => ({ source: nodes[i]!, target: id }))
const dist = (p: Point) => Math.hypot(p.x, p.y)

// A deterministic stand-in for Math.random, so failures reproduce.
function rng(seed: number) {
  let s = seed >>> 0
  return () => {
    s = (Math.imul(s, 1664525) + 1013904223) >>> 0
    return s / 2 ** 32
  }
}

// Built the way backend/app/utils/graph_knn.py builds similarity edges: each
// node keeps its top-5 neighbours by cosine similarity above a threshold.
function knnGraph(n: number, clusters: number, outliers: number, threshold: number) {
  const rand = rng(7)
  const dim = 16
  const centres = Array.from({ length: clusters }, () =>
    Array.from({ length: dim }, () => rand() * 2 - 1),
  )
  const vecs: number[][] = []
  for (let i = 0; i < n; i++) {
    const c = centres[i % clusters]!
    vecs.push(c.map((v) => v + (rand() - 0.5) * 0.6))
  }
  for (let i = 0; i < outliers; i++) vecs.push(Array.from({ length: dim }, () => rand() * 2 - 1))
  const unit = vecs.map((v) => {
    const len = Math.hypot(...v)
    return v.map((x) => x / len)
  })
  const nodeIds = unit.map((_, i) => `k${i}`)
  const edges: ConstellationEdge[] = []
  unit.forEach((a, i) => {
    const sims = unit
      .map((b, j) => ({ j, s: j === i ? -2 : a.reduce((t, x, d) => t + x * b[d]!, 0) }))
      .sort((p, q) => q.s - p.s)
      .slice(0, 5)
      .filter((p) => p.s >= threshold)
    for (const p of sims) edges.push({ source: nodeIds[i]!, target: nodeIds[p.j]! })
  })
  return { nodeIds, edges }
}

describe("classify", () => {
  it("puts components of CORE_MIN or more in the core, smaller ones in satellites, lone nodes in the halo", () => {
    const big = ids("c", CORE_MIN)
    const small = ids("s", CORE_MIN - 1)
    const pair = ids("p", 2)
    const lone = ids("h", 3)
    const c = classify(
      [...big, ...small, ...pair, ...lone],
      [...chain(big), ...chain(small), ...chain(pair)],
    )
    expect(CORE_MIN).toBe(8)
    for (const id of big) expect(c.role.get(id)).toBe("core")
    for (const id of [...small, ...pair]) expect(c.role.get(id)).toBe("satellite")
    for (const id of lone) expect(c.role.get(id)).toBe("halo")
    expect(c.satellites).toHaveLength(2)
  })

  it("promotes the largest component to the core when none reaches CORE_MIN", () => {
    const a = ids("a", 5)
    const b = ids("b", 3)
    const c = classify([...a, ...b, "x"], [...chain(a), ...chain(b)])
    expect(a.every((id) => c.role.get(id) === "core")).toBe(true)
    expect(b.every((id) => c.role.get(id) === "satellite")).toBe(true)
    expect(c.role.get("x")).toBe("halo")
  })

  it("makes every node halo when there are no edges", () => {
    const c = classify(ids("n", 10), [])
    expect(c.core).toHaveLength(0)
    expect(c.satellites).toHaveLength(0)
    expect(c.halo).toHaveLength(10)
  })

  it("ignores self-loops and edges to absent nodes", () => {
    const c = classify(["a", "b"], [
      { source: "a", target: "a" },
      { source: "a", target: "ghost" },
    ])
    expect(c.role.get("a")).toBe("halo")
    expect(c.role.get("b")).toBe("halo")
  })

  it("moves a memory to the halo once its last edge is filtered out", () => {
    const core = ids("c", CORE_MIN)
    const before = classify([...core, "m"], [...chain(core), { source: "m", target: "c0" }])
    expect(before.role.get("m")).toBe("core")
    const after = classify([...core, "m"], chain(core))
    expect(after.role.get("m")).toBe("halo")
  })

  it("assigns every node of a k-nearest-neighbour graph exactly one role", () => {
    const { nodeIds, edges } = knnGraph(200, 8, 30, 0.5)
    const c = classify(nodeIds, edges)
    expect(c.core.length + c.satellites.flat().length + c.halo.length).toBe(nodeIds.length)
    expect(new Set([...c.core, ...c.satellites.flat(), ...c.halo]).size).toBe(nodeIds.length)
  })
})

describe("placeOuter", () => {
  const scene = () => {
    const core = ids("c", 40)
    const sats = Array.from({ length: 40 }, (_, k) => ids(`s${k}_`, 2 + (k % 6)))
    const halo = ids("h", 300)
    const c = classify([...core, ...sats.flat(), ...halo], [...chain(core), ...sats.flatMap(chain)])
    return { c, sats, halo, R: coreRadius(c.core.length) }
  }

  it("keeps every satellite and halo node beyond the satellite ring start", () => {
    const { c, sats, halo, R } = scene()
    const out = placeOuter(c, R)
    for (const id of [...sats.flat(), ...halo]) {
      expect(dist(out.positions.get(id)!)).toBeGreaterThan(SATELLITE_RING_START * R)
    }
    expect(out.haloOuter).toBeGreaterThanOrEqual(HALO_MIN_OUTER * R)
    expect(out.haloInner).toBeGreaterThanOrEqual(out.satelliteOuter)
  })

  it("never overlaps two satellite clumps", () => {
    const { c, R } = scene()
    const out = placeOuter(c, R)
    const discs = c.satellites.map((members) => {
      const pts = members.map((id) => out.positions.get(id)!)
      const cx = pts.reduce((t, p) => t + p.x, 0) / pts.length
      const cy = pts.reduce((t, p) => t + p.y, 0) / pts.length
      const r = Math.max(...pts.map((p) => Math.hypot(p.x - cx, p.y - cy)))
      return { cx, cy, r }
    })
    for (let i = 0; i < discs.length; i++) {
      for (let j = i + 1; j < discs.length; j++) {
        const a = discs[i]!
        const b = discs[j]!
        expect(Math.hypot(a.cx - b.cx, a.cy - b.cy)).toBeGreaterThan(a.r + b.r)
      }
    }
  })

  it("places a halo node by its id alone", () => {
    const core = ids("c", 20)
    const a = classify([...core, "h1", "h2", "h3"], chain(core))
    const b = classify([...core, "h1", "h9"], chain(core))
    const R = coreRadius(core.length)
    const pa = placeOuter(a, R)
    const pb = placeOuter(b, R)
    expect(pa.haloInner).toBe(pb.haloInner)
    expect(pa.haloOuter).toBe(pb.haloOuter)
    expect(pa.positions.get("h1")).toEqual(pb.positions.get("h1"))
  })

  it("fills a full disc from the centre when there is no core", () => {
    const c = classify(ids("n", 50), [])
    const out = placeOuter(c, coreRadius(0))
    expect(coreRadius(0)).toBe(0)
    expect(out.haloInner).toBe(0)
    expect(out.positions.size).toBe(50)
    for (const p of out.positions.values()) {
      expect(Number.isFinite(p.x) && Number.isFinite(p.y)).toBe(true)
      expect(dist(p)).toBeLessThanOrEqual(out.haloOuter)
    }
  })

  it("keeps every other clump in place when the last-placed clump goes", () => {
    const core = ids("c", 30)
    const sats = Array.from({ length: 12 }, (_, k) => ids(`s${k}_`, 7 - (k % 5)))
    const withAll = classify([...core, ...sats.flat()], [...chain(core), ...sats.flatMap(chain)])
    const last = withAll.satellites[withAll.satellites.length - 1]!
    const keptSats = sats.filter((s) => !s.some((id) => last.includes(id)))
    const without = classify([...core, ...keptSats.flat()], [...chain(core), ...keptSats.flatMap(chain)])
    const R = coreRadius(core.length)
    const a = placeOuter(withAll, R)
    const b = placeOuter(without, R)
    for (const id of keptSats.flat()) expect(b.positions.get(id)).toEqual(a.positions.get(id))
  })

  it("is deterministic", () => {
    const { c, R } = scene()
    expect([...placeOuter(c, R).positions]).toEqual([...placeOuter(c, R).positions])
  })

  it("classifies and places 20,000 nodes and 110,000 edges within 50 ms", () => {
    const rand = rng(11)
    const n = 20_000
    const nodeIds = ids("n", n)
    const edges: ConstellationEdge[] = []
    for (let i = 0; i < 110_000; i++) {
      edges.push({ source: nodeIds[Math.floor(rand() * 12_000)]!, target: nodeIds[Math.floor(rand() * 12_000)]! })
    }
    const run = () => {
      const t0 = performance.now()
      const c = classify(nodeIds, edges)
      placeOuter(c, coreRadius(c.core.length))
      return performance.now() - t0
    }
    run()
    expect(Math.min(run(), run(), run())).toBeLessThanOrEqual(50)
  })
})

describe("fitCore", () => {
  it("centres the core on the origin with its farthest node at R", () => {
    const pos = new Map<string, Point>([
      ["a", { x: 100, y: 100 }],
      ["b", { x: 300, y: -50 }],
      ["c", { x: -20, y: 400 }],
    ])
    const fitted = [...fitCore(pos, 10).values()]
    const cx = fitted.reduce((t, p) => t + p.x, 0) / fitted.length
    const cy = fitted.reduce((t, p) => t + p.y, 0) / fitted.length
    expect(Math.abs(cx)).toBeLessThan(1e-9)
    expect(Math.abs(cy)).toBeLessThan(1e-9)
    for (const p of fitted) expect(dist(p)).toBeLessThanOrEqual(10 + 1e-9)
    expect(Math.max(...fitted.map(dist))).toBeCloseTo(10)
  })

  it("leaves a single node at the origin", () => {
    expect(fitCore(new Map([["a", { x: 5, y: 9 }]]), 10).get("a")).toEqual({ x: 0, y: 0 })
  })
})

