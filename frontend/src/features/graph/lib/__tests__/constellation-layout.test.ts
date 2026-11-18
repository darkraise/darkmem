import { describe, it, expect } from "vitest"
import { loadRealCorpus, type RealCorpusSize } from "../../fixtures/real-corpus"
import {
  classify,
  coreRadius,
  fitCore,
  placeOuter,
  placeOuterRing,
  fitCoreToFarthest,
  roleCut,
  classifyWithCut,
  CORE_MIN,
  SATELLITE_RING_START,
  SATELLITE_BAND,
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

  it("placeOuterRing: keeps every satellite and halo node beyond the satellite ring start", () => {
    const { c, sats, halo, R } = scene()
    const out = placeOuterRing(c, R)
    for (const id of [...sats.flat(), ...halo]) {
      expect(dist(out.positions.get(id)!)).toBeGreaterThan(SATELLITE_RING_START * R)
    }
    expect(out.haloOuter).toBeGreaterThanOrEqual(2.6 * R)
    expect(out.haloInner).toBeGreaterThanOrEqual(out.satelliteOuter)
  })

  for (const place of [placeOuter, placeOuterRing]) {
    it(`${place.name}: never overlaps two satellite clumps`, () => {
      const { c, R } = scene()
      const out = place(c, R)
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

    it(`${place.name}: places a halo node by its id alone`, () => {
      const core = ids("c", 20)
      const a = classify([...core, "h1", "h2", "h3"], chain(core))
      const b = classify([...core, "h1", "h9"], chain(core))
      const R = coreRadius(core.length)
      const pa = place(a, R)
      const pb = place(b, R)
      expect(pa.haloInner).toBe(pb.haloInner)
      expect(pa.haloOuter).toBe(pb.haloOuter)
      expect(pa.positions.get("h1")).toEqual(pb.positions.get("h1"))
    })

    it(`${place.name}: fills a full disc from the centre when there is no core`, () => {
      const c = classify(ids("n", 50), [])
      const out = place(c, coreRadius(0))
      expect(coreRadius(0)).toBe(0)
      expect(out.haloInner).toBe(0)
      expect(out.positions.size).toBe(50)
      for (const p of out.positions.values()) {
        expect(Number.isFinite(p.x) && Number.isFinite(p.y)).toBe(true)
        expect(dist(p)).toBeLessThanOrEqual(out.haloOuter)
      }
    })

    it(`${place.name}: keeps every other clump in place when the last-placed clump goes`, () => {
      const core = ids("c", 30)
      const sats = Array.from({ length: 12 }, (_, k) => ids(`s${k}_`, 7 - (k % 5)))
      const withAll = classify([...core, ...sats.flat()], [...chain(core), ...sats.flatMap(chain)])
      const last = withAll.satellites[withAll.satellites.length - 1]!
      const keptSats = sats.filter((s) => !s.some((id) => last.includes(id)))
      const without = classify([...core, ...keptSats.flat()], [...chain(core), ...keptSats.flatMap(chain)])
      const R = coreRadius(core.length)
      const a = place(withAll, R)
      const b = place(without, R)
      for (const id of keptSats.flat()) expect(b.positions.get(id)).toEqual(a.positions.get(id))
    })

    it(`${place.name}: is deterministic`, () => {
      const { c, R } = scene()
      expect([...place(c, R).positions]).toEqual([...place(c, R).positions])
    })

    it(`${place.name}: classifies and places 20,000 nodes and 110,000 edges within 50 ms`, () => {
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
        place(c, coreRadius(c.core.length))
        return performance.now() - t0
      }
      run()
      expect(Math.min(run(), run(), run())).toBeLessThanOrEqual(50)
    })
  }
})

describe("fitCore", () => {
  it("fitCoreToFarthest: centres the core on the origin with its farthest node at R", () => {
    const pos = new Map<string, Point>([
      ["a", { x: 100, y: 100 }],
      ["b", { x: 300, y: -50 }],
      ["c", { x: -20, y: 400 }],
    ])
    const fitted = [...fitCoreToFarthest(pos, 10).values()]
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


const ring = (p: string, n: number, score: number) =>
  Array.from({ length: n }, (_, i) => ({ source: `${p}${i}`, target: `${p}${(i + 1) % n}`, score }))
const named = (p: string, n: number) => Array.from({ length: n }, (_, i) => `${p}${i}`)

describe("roleCut", () => {
  it("A1: returns the lowest score that keeps 8+ components at or below 45% of nodes", () => {
    const ids = [...named("a", 9), ...named("b", 11)]
    const edges = [...ring("a", 9, 0.9), ...ring("b", 11, 0.8), { source: "a0", target: "b0", score: 0.7 }]
    expect(roleCut(ids, edges)).toBe(0.9)
  })
  it("A1: adds equal scores together", () => {
    const ids = [...named("a", 8), ...named("b", 8), ...named("z", 14)]
    const edges = [...ring("a", 8, 0.85), ...ring("b", 8, 0.85), { source: "z0", target: "z1", score: 0.95 }]
    expect(roleCut(ids, edges)).toBe(0.95)
  })
  it("A1: is the lowest score when every edge keeps the core at or below 45%", () => {
    const ids = named("n", 40)
    expect(roleCut(ids, [...ring("n", 8, 0.9), { source: "n20", target: "n21", score: 0.55 }])).toBe(0.55)
  })
  it("A1: keeps the highest score group even when it alone passes 45%", () => {
    const ids = named("a", 10)
    expect(roleCut(ids, [...ring("a", 9, 0.9), { source: "a8", target: "a9", score: 0.5 }])).toBe(0.9)
  })
  it("keeps a core on a graph too small for 45% to hold CORE_MIN nodes", () => {
    const ids = named("c", 15)
    const chain = ids.slice(1).map((id, i) => ({ source: ids[i]!, target: id, score: 0.9 - i * 0.01 }))
    const cut = roleCut(ids, chain)
    expect(cut).toBeCloseTo(0.84)
    expect(classifyWithCut(ids, chain).core).toHaveLength(8)
  })
  it("A1: is -Infinity when no edge carries a score", () => {
    expect(roleCut(named("n", 4), [{ source: "n0", target: "n1" }])).toBe(-Infinity)
  })
  it("an edge without a score counts at every cut", () => {
    const c = classifyWithCut(named("n", 20), [{ source: "n18", target: "n19" }, ...ring("n", 8, 0.9)])
    expect(c.role.get("n18")).toBe("satellite")
    expect(c.cut).toBe(0.9)
  })
  it("A4: an attachment takes the highest linked role and never changes a memory's role", () => {
    const ids = [...named("c", 8), "s0", "s1", "h0", ...named("z", 10)]
    const edges = [...ring("c", 8, 0.9), { source: "s0", target: "s1", score: 0.9 }]
    const attachments = [
      { id: "e:core", linked: ["h0", "c3"] },
      { id: "e:sat", linked: ["s1", "h0"] },
      { id: "e:halo", linked: ["h0"] },
      { id: "e:bridge", linked: ["s0", "h0", "z1"] },
      { id: "e:none", linked: ["missing"] },
    ]
    const c = classifyWithCut(ids, edges, attachments)
    const plain = classifyWithCut(ids, edges)
    expect(c.role.get("e:core")).toBe("core")
    expect(c.core).toContain("e:core")
    expect(c.role.get("e:sat")).toBe("satellite")
    expect(c.satellites.find((g) => g.includes("s1"))).toContain("e:sat")
    expect(c.role.get("e:halo")).toBe("halo")
    expect(c.role.get("e:none")).toBe("halo")
    for (const id of ids) expect(c.role.get(id)).toBe(plain.role.get(id))
  })
})

const layoutOf = (size: RealCorpusSize) => {
  const c = loadRealCorpus(size)
  const cls = classifyWithCut(c.memories.map((m) => m.id), c.edges)
  const R = coreRadius(cls.core.length)
  return { cls, R, out: placeOuter(cls, R) }
}

describe("placement on the real corpus", () => {
  it("A5: clumps never overlap, sit beyond 1.15R plus their radius, stay within 2R and spread around the core", () => {
    for (const size of [200, 1000, "all"] as RealCorpusSize[]) {
      const { cls, R, out } = layoutOf(size)
      const clumps = cls.satellites.map((g) => {
        const c = out.positions.get(g[0]!)!
        const r = Math.max(...g.map((id) => {
          const p = out.positions.get(id)!
          return Math.hypot(p.x - c.x, p.y - c.y)
        }))
        return { x: c.x, y: c.y, r }
      })
      for (let i = 0; i < clumps.length; i++) {
        const a = clumps[i]!
        const d = Math.hypot(a.x, a.y)
        expect(d).toBeGreaterThanOrEqual(1.15 * R + a.r - 1e-6)
        expect(d).toBeLessThanOrEqual(SATELLITE_BAND * R + 1e-6)
        for (let j = i + 1; j < clumps.length; j++) {
          const b = clumps[j]!
          expect(Math.hypot(a.x - b.x, a.y - b.y)).toBeGreaterThanOrEqual(a.r + b.r)
        }
      }
      expect(clumps.length).toBeGreaterThanOrEqual(8)
      const angles = clumps.map((c) => (Math.atan2(c.y, c.x) + 2 * Math.PI) % (2 * Math.PI))
      for (let k = 0; k < 24; k++) {
        const start = (k * Math.PI) / 12
        const inSector = angles.filter((a) => ((a - start + 2 * Math.PI) % (2 * Math.PI)) < Math.PI / 2).length
        expect(inSector).toBeLessThanOrEqual(clumps.length / 2)
      }
    }
  })

  it("A6: the halo fills 1.15R to its outer radius, thins outward, and depends only on id and radii", () => {
    const { cls, R, out } = layoutOf(1000)
    expect(out.haloInner).toBeCloseTo(1.15 * R)
    expect(out.haloOuter).toBeGreaterThanOrEqual(3 * R)
    const mid = (out.haloInner + out.haloOuter) / 2
    let inner = 0
    let outer = 0
    for (const id of cls.halo) {
      const p = out.positions.get(id)!
      const d = Math.hypot(p.x, p.y)
      expect(d).toBeGreaterThanOrEqual(out.haloInner - 1e-6)
      expect(d).toBeLessThanOrEqual(out.haloOuter + 1e-6)
      if (d < mid) inner++
      else outer++
    }
    const ring = (a: number, b: number) => Math.PI * (b * b - a * a)
    expect(inner / ring(out.haloInner, mid)).toBeGreaterThan(outer / ring(mid, out.haloOuter))
    // Same halo count and R, other halo ids and no satellites: shared ids do not move.
    const kept = cls.halo.slice(0, Math.floor(cls.halo.length / 2))
    const swapped = { ...cls, satellites: [], halo: [...kept, ...cls.halo.slice(kept.length).map((id) => `x${id}`)] }
    const again = placeOuter(swapped, R)
    expect(again.haloOuter).toBeCloseTo(out.haloOuter)
    for (const id of kept) expect(again.positions.get(id)).toEqual(out.positions.get(id))
  })

  it("A7: fitCore puts the 90th percentile at 0.85R and softens the tail inside R", () => {
    const pts = new Map<string, { x: number; y: number }>()
    for (let i = 0; i < 450; i++) pts.set(`n${i}`, { x: Math.cos(i), y: Math.sin(i * 1.3) })
    for (let i = 0; i < 50; i++) pts.set(`f${i}`, { x: 50 * Math.cos(i), y: 50 * Math.sin(i) })
    const all = [...pts.values()]
    const cx = all.reduce((s, p) => s + p.x, 0) / all.length
    const cy = all.reduce((s, p) => s + p.y, 0) / all.length
    const raw = [...pts.keys()].map((id) => Math.hypot(pts.get(id)!.x - cx, pts.get(id)!.y - cy))
    const p90 = [...raw].sort((a, b) => a - b)[449]!
    const out = fitCore(pts, 100)
    const d = [...pts.keys()].map((id) => Math.hypot(out.get(id)!.x, out.get(id)!.y))
    expect(Math.max(...d)).toBeLessThan(100)
    expect(d.filter((x) => x > 85 + 1e-9).length).toBeLessThanOrEqual(50)
    raw.forEach((r, i) => {
      const scaled = (r * 85) / p90
      const want = scaled <= 85 ? scaled : 85 + 15 * Math.tanh((scaled - 85) / 15)
      expect(d[i]!).toBeCloseTo(want, 6)
    })
  })

  it("A14: roleCut + classify + placeOuter take 50 ms or less for 20,000 nodes and 110,000 scored edges", () => {
    const ids = named("n", 20000)
    let seed = 7
    const rnd = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648)
    const edges = Array.from({ length: 110000 }, () => ({
      source: ids[Math.floor(rnd() * ids.length)]!,
      target: ids[Math.floor(rnd() * ids.length)]!,
      score: Math.round((0.5 + rnd() * 0.45) * 1000) / 1000,
    }))
    const runs: number[] = []
    for (let i = 0; i < 5; i++) {
      const t0 = performance.now()
      const cls = classifyWithCut(ids, edges)
      placeOuter(cls, coreRadius(cls.core.length))
      runs.push(performance.now() - t0)
    }
    runs.sort((a, b) => a - b)
    expect(runs[2]!).toBeLessThanOrEqual(50)
  })
})
