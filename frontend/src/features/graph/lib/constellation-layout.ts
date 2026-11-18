import { seededUnit } from "./code-graph-theme"

export type ConstellationRole = "core" | "satellite" | "halo"

export const CORE_MIN = 8
export const CORE_SHARE = 0.45
export const SATELLITE_RING_START = 1.15
export const HALO_MIN_OUTER = 2.6
export const ROLE_BRIGHTNESS: Record<ConstellationRole, number> = {
  core: 1,
  satellite: 0.8,
  halo: 0.45,
}

export const CORE_K = 10
export const CLUMP_R0 = 3
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
  const union = (source: string, target: string) => {
    const a = index.get(source)
    const b = index.get(target)
    if (a === undefined || b === undefined || a === b) return
    const ra = find(a)
    const rb = find(b)
    if (ra === rb) return
    inCore -= big(size[ra]!) + big(size[rb]!)
    parent[ra] = rb
    size[rb]! += size[ra]!
    inCore += big(size[rb]!)
  }

  const scored: { source: string; target: string; score: number }[] = []
  for (const e of edges) {
    if (typeof e.score === "number") scored.push(e as { source: string; target: string; score: number })
    else union(e.source, e.target)
  }
  if (scored.length === 0) return -Infinity
  scored.sort((a, b) => b.score - a.score)

  const limit = share * nodeIds.length
  let cut = scored[0]!.score
  let i = 0
  while (i < scored.length) {
    const score = scored[i]!.score
    let j = i
    while (j < scored.length && scored[j]!.score === score) {
      union(scored[j]!.source, scored[j]!.target)
      j++
    }
    if (i > 0 && inCore > limit) break
    cut = score
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

export function placeOuter(c: Classification, R: number): OuterLayout {
  const positions = new Map<string, Point>()
  let satelliteOuter = SATELLITE_RING_START * R

  let innerEdge = SATELLITE_RING_START * R + CLUMP_R0
  let ring: { rho: number; rOpen: number } | null = null
  let angle = 0
  let prevHalf = 0
  for (const members of c.satellites) {
    const clumpRadius = CLUMP_R0 * Math.sqrt(members.length - 1) + CLUMP_R0
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
    const cx = ring.rho * Math.cos(angle)
    const cy = ring.rho * Math.sin(angle)
    members.forEach((id, i) => {
      const r = CLUMP_R0 * Math.sqrt(i)
      const a = i * GOLDEN_ANGLE
      positions.set(id, { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) })
    })
  }

  const haloInner =
    R === 0 && c.satellites.length === 0 ? 0 : satelliteOuter + HALO_GAP * R
  const haloOuter = Math.max(
    HALO_MIN_OUTER * R,
    haloInner + HALO_C * Math.sqrt(c.halo.length),
  )
  const inner2 = haloInner * haloInner
  const span2 = haloOuter * haloOuter - inner2
  for (const id of c.halo) {
    const a = seededUnit(id, 1) * TAU
    const r = Math.sqrt(inner2 + seededUnit(id, 2) * span2)
    positions.set(id, { x: r * Math.cos(a), y: r * Math.sin(a) })
  }
  return { positions, satelliteOuter, haloInner, haloOuter }
}

export function fitCore(
  positions: ReadonlyMap<string, Point>,
  R: number,
): Map<string, Point> {
  let cx = 0
  let cy = 0
  for (const p of positions.values()) {
    cx += p.x
    cy += p.y
  }
  const count = positions.size || 1
  cx /= count
  cy /= count
  let far = 0
  for (const p of positions.values()) far = Math.max(far, Math.hypot(p.x - cx, p.y - cy))
  const scale = far > 0 ? R / far : 0
  const out = new Map<string, Point>()
  for (const [id, p] of positions) {
    out.set(id, { x: (p.x - cx) * scale, y: (p.y - cy) * scale })
  }
  return out
}
