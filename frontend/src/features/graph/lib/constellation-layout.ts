import { seededUnit } from "./code-graph-theme"

export type ConstellationRole = "core" | "satellite" | "halo"

export const CORE_MIN = 8
export const CORE_SHARE = 0.45
export const HALO_SIZE = 1.5
export const SATELLITE_RING_START = 1.15
export const HALO_MIN_OUTER = 3.0
export const SATELLITE_BAND = 2.0
const RING_HALO_MIN_OUTER = 2.6
export const ROLE_BRIGHTNESS: Record<ConstellationRole, number> = {
  core: 1,
  satellite: 0.8,
  halo: 0.45,
}

export const CORE_K = 10
export const CLUMP_R0 = 3
/** The memory canvas packs its clumps this far apart, so a clump of a few
 *  memories reads as a group of points rather than one speck. The code
 *  canvas keeps CLUMP_R0. */
export const MEMORY_CLUMP_R0 = 6
/** spreadCore's minimum distance between core nodes, as a share of the
 *  spacing an even disc of the same count would give. */
export const CORE_GAP = 0.8
const HALO_GAP = 0.25
const HALO_C = 6
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5))
const TAU = Math.PI * 2

export interface ConstellationEdge {
  source: string
  target: string
}

export interface ScoredEdge {
  source: string
  target: string
  score?: number
}

export interface Attachment {
  id: string
  linked: readonly string[]
}

export interface Point {
  x: number
  y: number
}

export interface Classification {
  role: Map<string, ConstellationRole>
  core: string[]
  satellites: string[][]
  halo: string[]
  degree: Map<string, number>
}

export interface OuterLayout {
  positions: Map<string, Point>
  /** Distance between neighbouring members of a clump. */
  clumpSpacing: number
  satelliteOuter: number
  haloInner: number
  haloOuter: number
}

export function classify(
  nodeIds: readonly string[],
  edges: readonly ConstellationEdge[],
): Classification {
  const index = new Map<string, number>()
  const ids: string[] = []
  for (const id of nodeIds) {
    if (!index.has(id)) {
      index.set(id, ids.length)
      ids.push(id)
    }
  }
  const n = ids.length
  const parent = new Int32Array(n)
  for (let i = 0; i < n; i++) parent[i] = i
  const deg = new Int32Array(n)
  const find = (i: number): number => {
    let r = i
    while (parent[r] !== r) r = parent[r]!
    while (parent[i] !== r) {
      const next = parent[i]!
      parent[i] = r
      i = next
    }
    return r
  }
  for (const e of edges) {
    const a = index.get(e.source)
    const b = index.get(e.target)
    if (a === undefined || b === undefined || a === b) continue
    deg[a]!++
    deg[b]!++
    const ra = find(a)
    const rb = find(b)
    if (ra !== rb) parent[ra] = rb
  }

  const groups = new Map<number, number[]>()
  for (let i = 0; i < n; i++) {
    const r = find(i)
    const g = groups.get(r)
    if (g) g.push(i)
    else groups.set(r, [i])
  }

  const minId = (g: number[]) => {
    let m = ids[g[0]!]!
    for (const i of g) if (ids[i]! < m) m = ids[i]!
    return m
  }
  const multi: { members: number[]; min: string }[] = []
  for (const g of groups.values()) if (g.length >= 2) multi.push({ members: g, min: minId(g) })
  multi.sort((a, b) =>
    b.members.length !== a.members.length
      ? b.members.length - a.members.length
      : a.min < b.min
        ? -1
        : a.min > b.min
          ? 1
          : 0,
  )

  const isCore = new Uint8Array(n)
  let anyCore = false
  for (const g of multi) {
    if (g.members.length >= CORE_MIN) {
      anyCore = true
      for (const i of g.members) isCore[i] = 1
    }
  }
  const satelliteGroups = multi.filter((g) => g.members.length < CORE_MIN)
  if (!anyCore && satelliteGroups.length > 0) {
    for (const i of satelliteGroups.shift()!.members) isCore[i] = 1
  }

  const role = new Map<string, ConstellationRole>()
  const degree = new Map<string, number>()
  const core: string[] = []
  const halo: string[] = []
  for (let i = 0; i < n; i++) {
    const id = ids[i]!
    degree.set(id, deg[i]!)
    if (isCore[i]) {
      role.set(id, "core")
      core.push(id)
    } else if (groups.get(find(i))!.length === 1) {
      role.set(id, "halo")
      halo.push(id)
    } else {
      role.set(id, "satellite")
    }
  }
  const satellites = satelliteGroups.map((g) =>
    g.members
      .sort((a, b) => deg[b]! - deg[a]! || (ids[a]! < ids[b]! ? -1 : ids[a]! > ids[b]! ? 1 : 0))
      .map((i) => ids[i]!),
  )
  return { role, core, satellites, halo, degree }
}

export function roleCut(
  nodeIds: readonly string[],
  edges: readonly ScoredEdge[],
  share: number = CORE_SHARE,
): number {
  const index = new Map<string, number>()
  for (const id of nodeIds) if (!index.has(id)) index.set(id, index.size)
  const n = index.size
  const parent = new Int32Array(n)
  const size = new Int32Array(n)
  for (let i = 0; i < n; i++) {
    parent[i] = i
    size[i] = 1
  }
  const find = (i: number): number => {
    while (parent[i] !== i) {
      parent[i] = parent[parent[i]!]!
      i = parent[i]!
    }
    return i
  }
  const big = (s: number) => (s >= CORE_MIN ? s : 0)
  let inCore = 0
  const union = (a: number, b: number) => {
    if (a < 0 || b < 0 || a === b) return
    const ra = find(a)
    const rb = find(b)
    if (ra === rb) return
    inCore -= big(size[ra]!) + big(size[rb]!)
    parent[ra] = rb
    size[rb]! += size[ra]!
    inCore += big(size[rb]!)
  }

  let m = 0
  for (const e of edges) if (typeof e.score === "number") m++
  if (m === 0) return -Infinity
  const ends = new Int32Array(2 * m)
  const score = new Float64Array(m)
  let hi = -Infinity
  let lo = Infinity
  let k = 0
  for (const e of edges) {
    const a = index.get(e.source) ?? -1
    const b = index.get(e.target) ?? -1
    if (typeof e.score !== "number") {
      union(a, b)
      continue
    }
    ends[2 * k] = a
    ends[2 * k + 1] = b
    score[k] = e.score
    if (e.score > hi) hi = e.score
    if (e.score < lo) lo = e.score
    k++
  }

  // A bucket pass orders 110k edges well inside the 50 ms layout budget, where
  // a comparator sort over edge objects alone takes most of it.
  const buckets = new Int32Array(m + 1)
  const bucketOf = (s: number) =>
    hi > lo ? Math.min(m - 1, Math.floor(((hi - s) / (hi - lo)) * m)) : 0
  for (let e = 0; e < m; e++) buckets[bucketOf(score[e]!) + 1]!++
  for (let i = 0; i < m; i++) buckets[i + 1]! += buckets[i]!
  const fill = buckets.slice(0, m)
  const order = new Int32Array(m)
  for (let e = 0; e < m; e++) order[fill[bucketOf(score[e]!)]!++] = e
  for (let i = 0; i < m; i++) {
    const from = buckets[i]!
    const to = buckets[i + 1]!
    if (to - from < 2) continue
    let mixed = false
    for (let j = from + 1; j < to && !mixed; j++) mixed = score[order[j]!] !== score[order[from]!]
    if (mixed) order.subarray(from, to).sort((x, y) => score[y]! - score[x]!)
  }

  const limit = share * nodeIds.length
  let cut = score[order[0]!]!
  let i = 0
  while (i < m) {
    const s = score[order[i]!]!
    const hadCore = inCore > 0
    let j = i
    while (j < m && score[order[j]!] === s) {
      const e = order[j]!
      union(ends[2 * e]!, ends[2 * e + 1]!)
      j++
    }
    // Under ~18 nodes share × n is below CORE_MIN, so any core overflows it:
    // there, groups are kept until the first core forms.
    if (i > 0 && inCore > limit && (hadCore || limit >= CORE_MIN)) break
    cut = s
    i = j
  }
  return cut
}

export function classifyWithCut(
  nodeIds: readonly string[],
  edges: readonly ScoredEdge[],
  attachments: readonly Attachment[] = [],
  share: number = CORE_SHARE,
): Classification & { cut: number } {
  const cut = roleCut(nodeIds, edges, share)
  const kept = edges.filter((e) => typeof e.score !== "number" || e.score >= cut)
  const c = classify(nodeIds, kept)
  const satelliteGroup = new Map<string, string[]>()
  for (const g of c.satellites) for (const id of g) satelliteGroup.set(id, g)
  const memberRole = new Map(c.role)
  for (const a of attachments) {
    let best: ConstellationRole = "halo"
    let anchor: string | null = null
    for (const id of a.linked) {
      const r = memberRole.get(id)
      if (r === "core") best = "core"
      else if (r === "satellite" && best !== "core") {
        best = "satellite"
        if (anchor === null || id < anchor) anchor = id
      }
    }
    c.role.set(a.id, best)
    c.degree.set(a.id, a.linked.length)
    if (best === "core") c.core.push(a.id)
    else if (best === "satellite") satelliteGroup.get(anchor!)!.push(a.id)
    else c.halo.push(a.id)
  }
  return { ...c, cut }
}

export function coreRadius(coreCount: number): number {
  return coreCount === 0 ? 0 : CORE_K * Math.sqrt(coreCount)
}

const clumpRadiusOf = (count: number, r0 = CLUMP_R0) => r0 * Math.sqrt(count - 1) + r0

function packClump(
  members: readonly string[],
  cx: number,
  cy: number,
  positions: Map<string, Point>,
  r0 = CLUMP_R0,
) {
  members.forEach((id, i) => {
    const r = r0 * Math.sqrt(i)
    const a = i * GOLDEN_ANGLE
    positions.set(id, { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) })
  })
}

const minOf = (ids: readonly string[]) => {
  let m = ids[0]!
  for (const id of ids) if (id < m) m = id
  return m
}

export function placeOuter(c: Classification, R: number): OuterLayout {
  const positions = new Map<string, Point>()
  const r0 = MEMORY_CLUMP_R0
  const clumps = c.satellites
    .map((members) => ({ members, cr: clumpRadiusOf(members.length, r0), minId: minOf(members) }))
    .sort((a, b) => b.members.length - a.members.length)

  let maxCr = 0
  for (const k of clumps) maxCr = Math.max(maxCr, k.cr)
  const cell = 2 * maxCr + r0
  const grid = new Map<string, { x: number; y: number; cr: number }[]>()
  const keyOf = (ix: number, iy: number) => `${ix},${iy}`
  const clear = (x: number, y: number, cr: number) => {
    const ix = Math.floor(x / cell)
    const iy = Math.floor(y / cell)
    for (let dx = -1; dx <= 1; dx++) {
      for (let dy = -1; dy <= 1; dy++) {
        for (const o of grid.get(keyOf(ix + dx, iy + dy)) ?? []) {
          if (Math.hypot(o.x - x, o.y - y) < cr + o.cr + r0) return false
        }
      }
    }
    return true
  }

  let satelliteOuter = 0
  clumps.forEach(({ members, cr, minId }, j) => {
    const lo = SATELLITE_RING_START * R + cr
    const hi = Math.max(lo, SATELLITE_BAND * R)
    let angle = 0
    let rho = lo
    let placed = false
    for (let k = 0; k < 24 && !placed; k++) {
      angle = (j * GOLDEN_ANGLE + (k * TAU) / 24) % TAU
      rho = lo + seededUnit(minId, 11 + 2 * k) * (hi - lo)
      placed = clear(rho * Math.cos(angle), rho * Math.sin(angle), cr)
    }
    while (!placed) {
      rho += r0
      placed = clear(rho * Math.cos(angle), rho * Math.sin(angle), cr)
    }
    const x = rho * Math.cos(angle)
    const y = rho * Math.sin(angle)
    const key = keyOf(Math.floor(x / cell), Math.floor(y / cell))
    const bucket = grid.get(key)
    if (bucket) bucket.push({ x, y, cr })
    else grid.set(key, [{ x, y, cr }])
    satelliteOuter = Math.max(satelliteOuter, rho + cr)
    packClump(members, x, y, positions, r0)
  })

  const haloInner = R === 0 && c.satellites.length === 0 ? 0 : SATELLITE_RING_START * R
  const haloOuter = Math.max(
    HALO_MIN_OUTER * R,
    SATELLITE_BAND * R + HALO_C * Math.sqrt(c.halo.length),
  )
  for (const id of c.halo) {
    const a = seededUnit(id, 1) * TAU
    const u = seededUnit(id, 2)
    // With no core the spec keeps the old full disc of even area density.
    const r =
      haloInner === 0
        ? haloOuter * Math.sqrt(u)
        : haloInner + u * (haloOuter - haloInner)
    positions.set(id, { x: r * Math.cos(a), y: r * Math.sin(a) })
  }
  return { positions, clumpSpacing: r0, satelliteOuter, haloInner, haloOuter }
}

export function placeOuterRing(c: Classification, R: number): OuterLayout {
  const positions = new Map<string, Point>()
  let satelliteOuter = SATELLITE_RING_START * R

  let innerEdge = SATELLITE_RING_START * R + CLUMP_R0
  let ring: { rho: number; rOpen: number } | null = null
  let angle = 0
  let prevHalf = 0
  for (const members of c.satellites) {
    const clumpRadius = clumpRadiusOf(members.length)
    const halfWidth = (rho: number) => Math.asin((clumpRadius + CLUMP_R0 / 2) / rho)
    let half = ring ? halfWidth(ring.rho) : 0
    if (ring && angle + prevHalf + 2 * half > TAU) {
      innerEdge = ring.rho + ring.rOpen + CLUMP_R0
      ring = null
    }
    if (!ring) {
      ring = { rho: innerEdge + clumpRadius, rOpen: clumpRadius }
      half = halfWidth(ring.rho)
      angle = half
    } else {
      angle += prevHalf + half
    }
    prevHalf = half
    satelliteOuter = ring.rho + ring.rOpen
    packClump(members, ring.rho * Math.cos(angle), ring.rho * Math.sin(angle), positions)
  }

  const haloInner =
    R === 0 && c.satellites.length === 0 ? 0 : satelliteOuter + HALO_GAP * R
  const haloOuter = Math.max(
    RING_HALO_MIN_OUTER * R,
    haloInner + HALO_C * Math.sqrt(c.halo.length),
  )
  const inner2 = haloInner * haloInner
  const span2 = haloOuter * haloOuter - inner2
  for (const id of c.halo) {
    const a = seededUnit(id, 1) * TAU
    const r = Math.sqrt(inner2 + seededUnit(id, 2) * span2)
    positions.set(id, { x: r * Math.cos(a), y: r * Math.sin(a) })
  }
  return { positions, clumpSpacing: CLUMP_R0, satelliteOuter, haloInner, haloOuter }
}

const centroidOf = (positions: ReadonlyMap<string, Point>) => {
  let cx = 0
  let cy = 0
  for (const p of positions.values()) {
    cx += p.x
    cy += p.y
  }
  const count = positions.size || 1
  return { cx: cx / count, cy: cy / count }
}

export function fitCore(
  positions: ReadonlyMap<string, Point>,
  R: number,
): Map<string, Point> {
  const { cx, cy } = centroidOf(positions)
  const dists = [...positions.values()]
    .map((p) => Math.hypot(p.x - cx, p.y - cy))
    .sort((a, b) => a - b)
  const p90 = dists.length > 0 ? dists[Math.ceil(0.9 * dists.length) - 1]! : 0
  const knee = 0.85 * R
  const tail = 0.15 * R
  const scale = p90 > 0 ? knee / p90 : 0
  const out = new Map<string, Point>()
  for (const [id, p] of positions) {
    const x = (p.x - cx) * scale
    const y = (p.y - cy) * scale
    const d = Math.hypot(x, y)
    if (d > knee) {
      // Math.tanh returns exactly 1 past about 19, which would land a node on R.
      const k = (knee + tail * Math.min(Math.tanh((d - knee) / tail), 1 - 1e-9)) / d
      out.set(id, { x: x * k, y: y * k })
    } else {
      out.set(id, { x, y })
    }
  }
  return out
}

export function fitCoreToFarthest(
  positions: ReadonlyMap<string, Point>,
  R: number,
): Map<string, Point> {
  const { cx, cy } = centroidOf(positions)
  let far = 0
  for (const p of positions.values()) far = Math.max(far, Math.hypot(p.x - cx, p.y - cy))
  const scale = far > 0 ? R / far : 0
  const out = new Map<string, Point>()
  for (const [id, p] of positions) {
    out.set(id, { x: (p.x - cx) * scale, y: (p.y - cy) * scale })
  }
  return out
}

/**
 * Pushes core nodes apart until none sits closer than CORE_GAP of an even
 * disc's spacing. A force layout keeps contracting each community toward a
 * point for as long as it runs, and the percentile fit then stacks a whole
 * community on a few pixels, which the additive glow sums to white. `offsets`
 * carries each node's last correction, so a caller re-fitting every frame
 * starts from where the previous frame settled and needs few iterations.
 */
export function spreadCore(
  fitted: ReadonlyMap<string, Point>,
  R: number,
  offsets: Map<string, Point>,
  iterations: number,
): Map<string, Point> {
  const ids = [...fitted.keys()]
  const n = ids.length
  const xs = new Float64Array(n)
  const ys = new Float64Array(n)
  ids.forEach((id, i) => {
    const p = fitted.get(id)!
    const o = offsets.get(id)
    xs[i] = p.x + (o?.x ?? 0)
    ys[i] = p.y + (o?.y ?? 0)
  })
  const gap = n > 1 && R > 0 ? CORE_GAP * R * Math.sqrt(Math.PI / n) : 0
  const limit = 0.995 * R
  const dx = new Float64Array(n)
  const dy = new Float64Array(n)
  const keyOf = (ix: number, iy: number) => ix * 1_000_003 + iy
  for (let it = 0; it < iterations && gap > 0; it++) {
    const cells = new Map<number, number[]>()
    for (let i = 0; i < n; i++) {
      const k = keyOf(Math.floor(xs[i]! / gap), Math.floor(ys[i]! / gap))
      const bucket = cells.get(k)
      if (bucket) bucket.push(i)
      else cells.set(k, [i])
    }
    dx.fill(0)
    dy.fill(0)
    let moved = false
    for (let i = 0; i < n; i++) {
      const ix = Math.floor(xs[i]! / gap)
      const iy = Math.floor(ys[i]! / gap)
      for (let a = -1; a <= 1; a++) {
        for (let b = -1; b <= 1; b++) {
          for (const j of cells.get(keyOf(ix + a, iy + b)) ?? []) {
            if (j <= i) continue
            const ex = xs[j]! - xs[i]!
            const ey = ys[j]! - ys[i]!
            const d = Math.hypot(ex, ey)
            if (d >= gap) continue
            let ux: number
            let uy: number
            if (d < 1e-9) {
              // Coincident: split along a direction fixed by the pair's ids.
              const t = seededUnit(`${ids[i]}|${ids[j]}`, 5) * TAU
              ux = Math.cos(t)
              uy = Math.sin(t)
            } else {
              ux = ex / d
              uy = ey / d
            }
            const push = (gap - d) / 2
            dx[i] = dx[i]! - ux * push
            dy[i] = dy[i]! - uy * push
            dx[j] = dx[j]! + ux * push
            dy[j] = dy[j]! + uy * push
            moved = true
          }
        }
      }
    }
    if (!moved) break
    for (let i = 0; i < n; i++) {
      // Half steps: a node pushed by several neighbours at once overshoots.
      xs[i] = xs[i]! + dx[i]! * 0.5
      ys[i] = ys[i]! + dy[i]! * 0.5
      const r = Math.hypot(xs[i]!, ys[i]!)
      if (r > limit) {
        xs[i] = xs[i]! * limit / r
        ys[i] = ys[i]! * limit / r
      }
    }
  }
  const out = new Map<string, Point>()
  ids.forEach((id, i) => {
    const p = fitted.get(id)!
    offsets.set(id, { x: xs[i]! - p.x, y: ys[i]! - p.y })
    out.set(id, { x: xs[i]!, y: ys[i]! })
  })
  return out
}
