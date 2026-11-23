import type Graph from "graphology"
import { seededUnit } from "./code-graph-theme"

export type ConstellationRole = "core" | "satellite" | "halo"

export const CORE_MIN = 8
export const HALO_SIZE = 1.5
export const SATELLITE_RING_START = 1.15
const RING_HALO_MIN_OUTER = 2.6
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

/** `fitCoreToFarthest` over parallel coordinate arrays, rewritten in place,
 *  for the per-frame path that must not allocate. */
export function fitCoreInPlace(xs: Float64Array, ys: Float64Array, R: number): void {
  const n = xs.length
  let cx = 0
  let cy = 0
  for (let i = 0; i < n; i++) {
    cx += xs[i]!
    cy += ys[i]!
  }
  cx /= n || 1
  cy /= n || 1
  let far = 0
  for (let i = 0; i < n; i++) far = Math.max(far, Math.hypot(xs[i]! - cx, ys[i]! - cy))
  const scale = far > 0 ? R / far : 0
  for (let i = 0; i < n; i++) {
    xs[i] = (xs[i]! - cx) * scale
    ys[i] = (ys[i]! - cy) * scale
  }
}

/** Copies the simulated core's positions, fitted to R, onto the drawn graph
 *  each frame through arrays and an index built once. */
export function createCoreMirror(ids: readonly string[], R: number) {
  const index = new Map<string, number>()
  ids.forEach((id, i) => index.set(id, i))
  const xs = new Float64Array(ids.length)
  const ys = new Float64Array(ids.length)
  return {
    xs,
    ys,
    apply(core: Graph, target: Graph) {
      for (let i = 0; i < ids.length; i++) {
        xs[i] = core.getNodeAttribute(ids[i]!, "x") as number
        ys[i] = core.getNodeAttribute(ids[i]!, "y") as number
      }
      fitCoreInPlace(xs, ys, R)
      target.updateEachNodeAttributes(
        (id, attrs) => {
          const i = index.get(id)
          if (i !== undefined) {
            attrs.x = xs[i]
            attrs.y = ys[i]
          }
          return attrs
        },
        { attributes: ["x", "y"] },
      )
    },
  }
}
