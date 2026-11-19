import { seededUnit } from "./code-graph-theme"
import { ROLE_BRIGHTNESS, type ConstellationRole, type Point, type ScoredEdge } from "./constellation-layout"

export { ROLE_BRIGHTNESS }

/** Island radius per square-rooted member, in graph units. */
export const ISLAND_K = 12
/** The island of memories with no edge is this much sparser. */
export const LOOSE_K = 22
/** Clear space between two islands, as a share of the smaller one's radius,
 *  with a floor so two small islands never touch. */
export const ISLAND_GAP = 0.25
const ISLAND_GAP_MIN = 12
/** Minimum distance between two memories, as a share of an island's even
 *  spacing. Below 1 so linked memories can still sit closer than unlinked. */
export const NODE_GAP = 0.4
/** A fitted island's 85th-percentile member sits at this share of its
 *  radius; the rest taper softly to SOFT_EDGE, never to a hard rim. */
const FIT_P85 = 0.8
const SOFT_EDGE = 1.15
const LOOSE_GROUP = "loose"
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5))
const PLACE_ITERATIONS = 300
/** Width over height of the rectangle the islands are packed into. */
const PACK_ASPECT = 1.6
/** Share of that rectangle the island footprints cover. */
const PACK_FILL = 0.55
/** Distance between two islands' simulation spots per square-rooted member of
 *  the largest island: about a hundred times an island's simulated width, so
 *  ForceAtlas2's all-pairs repulsion from one island cannot stretch another. */
const SIM_SPACING_PER_ROOT = 40_000

export interface IslandGroup {
  key: string
  /** Clustered members first, then the unclustered memories riding on them. */
  members: string[]
  /** Unclustered memories that joined this island through their strongest edge. */
  riders: string[]
  loose: boolean
  radius: number
}

export interface IslandLayout {
  groups: IslandGroup[]
  groupOf: Map<string, string>
  role: Map<string, ConstellationRole>
  centres: Map<string, Point>
  /** Distance from the origin to the farthest island rim. */
  extent: number
  /** The memory spacing the spread pass enforces. */
  gap: number
}

export const clusterKey = (cluster: number) => `cluster:${cluster}`

interface EdgeIndex {
  src: Int32Array
  dst: Int32Array
  score: Float64Array
}

/** Resolves every edge endpoint to a position in `ids` once, so the passes
 *  over 100k+ edges that follow touch no strings. -1 marks an unknown id. */
function indexEdges(ids: readonly string[], edges: readonly ScoredEdge[]): EdgeIndex {
  const at = new Map<string, number>()
  for (let i = 0; i < ids.length; i++) at.set(ids[i]!, i)
  const m = edges.length
  const src = new Int32Array(m)
  const dst = new Int32Array(m)
  const score = new Float64Array(m)
  for (let i = 0; i < m; i++) {
    const e = edges[i]!
    src[i] = at.get(e.source) ?? -1
    dst[i] = at.get(e.target) ?? -1
    score[i] = e.score ?? 0
  }
  return { src, dst, score }
}

/**
 * One island per cluster. An unclustered memory joins the island of the
 * clustered neighbour it is most similar to (score, then id); one with no
 * clustered neighbour, linked or not, joins the loose island.
 */
function groupIndexed(
  memories: readonly { id: string; cluster: number }[],
  ix: EdgeIndex,
) {
  const count = memories.length
  const groupOf = new Map<string, string>()
  const clustered = new Map<string, string[]>()
  const keyAt: (string | undefined)[] = new Array(count)
  for (let i = 0; i < count; i++) {
    const m = memories[i]!
    if (m.cluster < 0) continue
    const key = clusterKey(m.cluster)
    keyAt[i] = key
    groupOf.set(m.id, key)
    const g = clustered.get(key)
    if (g) g.push(m.id)
    else clustered.set(key, [m.id])
  }
  const bestScore = new Float64Array(count).fill(-Infinity)
  const bestVia = new Int32Array(count).fill(-1)
  const offer = (at: number, other: number, score: number) => {
    const cur = bestVia[at]!
    if (
      cur < 0 ||
      score > bestScore[at]! ||
      (score === bestScore[at]! && memories[other]!.id < memories[cur]!.id)
    ) {
      bestScore[at] = score
      bestVia[at] = other
    }
  }
  for (let i = 0; i < ix.src.length; i++) {
    const a = ix.src[i]!
    const b = ix.dst[i]!
    if (a < 0 || b < 0) continue
    const ka = keyAt[a] !== undefined
    const kb = keyAt[b] !== undefined
    if (ka === kb) continue
    if (ka) offer(b, a, ix.score[i]!)
    else offer(a, b, ix.score[i]!)
  }
  const riders = new Map<string, string[]>()
  const loose: string[] = []
  const role = new Map<string, ConstellationRole>()
  const riderKey = new Map<string, string>()
  for (let i = 0; i < count; i++) {
    const id = memories[i]!.id
    if (keyAt[i] !== undefined) {
      role.set(id, "core")
      continue
    }
    const via = bestVia[i]!
    if (via >= 0) {
      const key = keyAt[via]!
      role.set(id, "satellite")
      riderKey.set(id, key)
      const r = riders.get(key)
      if (r) r.push(id)
      else riders.set(key, [id])
    } else {
      role.set(id, "halo")
      loose.push(id)
    }
  }
  for (const [id, key] of riderKey) groupOf.set(id, key)
  for (const id of loose) groupOf.set(id, LOOSE_GROUP)

  const groups: IslandGroup[] = [...clustered.entries()].map(([key, members]) => {
    const r = riders.get(key) ?? []
    const all = [...members, ...r]
    return { key, members: all, riders: r, loose: false, radius: ISLAND_K * Math.sqrt(all.length) }
  })
  if (loose.length > 0) {
    groups.push({
      key: LOOSE_GROUP,
      members: loose,
      riders: [],
      loose: true,
      radius: LOOSE_K * Math.sqrt(loose.length),
    })
  }
  groups.sort((a, b) =>
    a.loose !== b.loose
      ? a.loose
        ? 1
        : -1
      : b.members.length - a.members.length || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0),
  )
  return { groups, groupOf, role }
}

export function groupMemories(
  memories: readonly { id: string; cluster: number }[],
  edges: readonly ScoredEdge[],
): { groups: IslandGroup[]; groupOf: Map<string, string>; role: Map<string, ConstellationRole> } {
  return groupIndexed(memories, indexEdges(memories.map((m) => m.id), edges))
}

const islandGap = (a: IslandGroup, b: IslandGroup) =>
  Math.max(ISLAND_GAP_MIN, ISLAND_GAP * Math.min(a.radius, b.radius))

/**
 * Island centres from a small deterministic simulation: islands start on a
 * serpentine grid inside a PACK_ASPECT rectangle, in an order that puts
 * strongly linked islands in neighbouring cells; islands sharing edges pull
 * toward touching, collisions keep a gap, and a containment force holds each
 * island inside the rectangle. There is no pull toward a centre, so the
 * arrangement never gathers into a disc around one island.
 */
export function placeIslands(
  groups: readonly IslandGroup[],
  groupOf: ReadonlyMap<string, string>,
  edges: readonly ScoredEdge[],
): Map<string, Point> {
  const ids = [...groupOf.keys()]
  return placeIndexed(groups, islandIndexOf(groups, groupOf, ids), indexEdges(ids, edges))
}

function islandIndexOf(
  groups: readonly IslandGroup[],
  groupOf: ReadonlyMap<string, string>,
  ids: readonly string[],
): Int32Array {
  const index = new Map(groups.map((g, i) => [g.key, i]))
  const out = new Int32Array(ids.length)
  for (let i = 0; i < ids.length; i++) out[i] = index.get(groupOf.get(ids[i]!) ?? "") ?? -1
  return out
}

function placeIndexed(
  groups: readonly IslandGroup[],
  islandAt: Int32Array,
  ix: EdgeIndex,
): Map<string, Point> {
  const n = groups.length
  const links = new Map<number, number>()
  for (let i = 0; i < ix.src.length; i++) {
    const s = ix.src[i]!
    const t = ix.dst[i]!
    if (s < 0 || t < 0) continue
    const a = islandAt[s]!
    const b = islandAt[t]!
    if (a < 0 || b < 0 || a === b) continue
    if (groups[a]!.loose || groups[b]!.loose) continue
    const k = a < b ? a * n + b : b * n + a
    links.set(k, (links.get(k) ?? 0) + 1)
  }
  const pairs = [...links.entries()].map(([k, count]) => {
    const a = Math.floor(k / n)
    const b = k % n
    return {
      a,
      b,
      w: count / Math.sqrt(groups[a]!.members.length * groups[b]!.members.length),
    }
  })
  const wMax = pairs.reduce((m, p) => Math.max(m, p.w), 0) || 1

  const rad = Float64Array.from(groups, (g) => g.radius)
  const area = Float64Array.from(rad, (r) => r * r)
  const foot = Float64Array.from(rad, (r) => SOFT_EDGE * r + ISLAND_GAP_MIN / 2)
  let footArea = 0
  for (let i = 0; i < n; i++) footArea += Math.PI * foot[i]! * foot[i]!
  const boxH = Math.sqrt(footArea / PACK_FILL / PACK_ASPECT)
  const boxW = PACK_ASPECT * boxH

  const order = linkageOrder(groups, pairs)
  const cols = Math.max(1, Math.min(n, Math.round(Math.sqrt(n * PACK_ASPECT))))
  const rows = Math.ceil(n / cols)
  const xs = new Float64Array(n)
  const ys = new Float64Array(n)
  order.forEach((i, k) => {
    const row = Math.floor(k / cols)
    const col = row % 2 === 0 ? k % cols : cols - 1 - (k % cols)
    // A fixed jitter per island, or unlinked equal islands stay a grid.
    const key = groups[i]!.key
    xs[i] = ((col + 0.5 + 0.6 * (seededUnit(key, 5) - 0.5)) / cols - 0.5) * boxW
    ys[i] = ((row + 0.5 + 0.6 * (seededUnit(key, 6) - 0.5)) / rows - 0.5) * boxH
  })
  const collide = () => {
    for (let i = 0; i < n; i++) {
      const ri = rad[i]!
      for (let j = i + 1; j < n; j++) {
        const rj = rad[j]!
        const want = SOFT_EDGE * (ri + rj) + Math.max(ISLAND_GAP_MIN, ISLAND_GAP * Math.min(ri, rj))
        let dx = xs[j]! - xs[i]!
        let dy = ys[j]! - ys[i]!
        if (dx * dx + dy * dy >= want * want) continue
        let d = Math.hypot(dx, dy)
        if (d < 1e-9) {
          const t = seededUnit(`${groups[i]!.key}|${groups[j]!.key}`, 3) * Math.PI * 2
          dx = Math.cos(t)
          dy = Math.sin(t)
          d = 1
        }
        // The smaller island moves further, so big islands hold the middle.
        const ai = area[i]!
        const aj = area[j]!
        const push = want - d
        xs[i] = xs[i]! - (dx / d) * push * (aj / (ai + aj))
        ys[i] = ys[i]! - (dy / d) * push * (aj / (ai + aj))
        xs[j] = xs[j]! + (dx / d) * push * (ai / (ai + aj))
        ys[j] = ys[j]! + (dy / d) * push * (ai / (ai + aj))
      }
    }
  }

  const pairCount = pairs.length
  const pairA = Int32Array.from(pairs, (p) => p.a)
  const pairB = Int32Array.from(pairs, (p) => p.b)
  const pairRest = Float64Array.from(
    pairs,
    (p) => SOFT_EDGE * (rad[p.a]! + rad[p.b]!) + islandGap(groups[p.a]!, groups[p.b]!),
  )
  const pairPull = Float64Array.from(pairs, (p) => (0.04 * p.w) / wMax)
  for (let it = 0; it < PLACE_ITERATIONS; it++) {
    const alpha = 1 - it / PLACE_ITERATIONS
    for (let p = 0; p < pairCount; p++) {
      const a = pairA[p]!
      const b = pairB[p]!
      const dx = xs[b]! - xs[a]!
      const dy = ys[b]! - ys[a]!
      const d = Math.sqrt(dx * dx + dy * dy) || 1
      const rest = pairRest[p]!
      if (d <= rest) continue
      const pull = (d - rest) * alpha * pairPull[p]!
      xs[a] = xs[a]! + (dx / d) * pull
      ys[a] = ys[a]! + (dy / d) * pull
      xs[b] = xs[b]! - (dx / d) * pull
      ys[b] = ys[b]! - (dy / d) * pull
    }
    for (let i = 0; i < n; i++) {
      const hx = Math.max(0, boxW / 2 - foot[i]!)
      const hy = Math.max(0, boxH / 2 - foot[i]!)
      const x = xs[i]!
      const y = ys[i]!
      if (x > hx) xs[i] = x - 0.2 * (x - hx)
      else if (x < -hx) xs[i] = x - 0.2 * (x + hx)
      if (y > hy) ys[i] = y - 0.2 * (y - hy)
      else if (y < -hy) ys[i] = y - 0.2 * (y + hy)
    }
    collide()
  }
  for (let it = 0; it < 50; it++) collide()
  stretchToAspect(xs, ys, foot)

  let cx = 0
  let cy = 0
  let total = 0
  for (let i = 0; i < n; i++) {
    cx += xs[i]! * area[i]!
    cy += ys[i]! * area[i]!
    total += area[i]!
  }
  cx /= total || 1
  cy /= total || 1
  const centres = new Map<string, Point>()
  groups.forEach((g, i) => centres.set(g.key, { x: xs[i]! - cx, y: ys[i]! - cy }))
  return centres
}

/**
 * Spreads the centres along the short axis until the islands' bounding box is
 * PACK_ASPECT wide. Linked islands pull the packing into a compact clump; this
 * only moves islands apart, so it cannot create an overlap.
 */
function stretchToAspect(xs: Float64Array, ys: Float64Array, foot: Float64Array) {
  const span = (v: Float64Array, k: number) => {
    let lo = Infinity
    let hi = -Infinity
    for (let i = 0; i < v.length; i++) {
      lo = Math.min(lo, k * v[i]! - foot[i]!)
      hi = Math.max(hi, k * v[i]! + foot[i]!)
    }
    return hi - lo
  }
  const w = span(xs, 1)
  const h = span(ys, 1)
  if (w === 0 || h === 0 || w / h === PACK_ASPECT) return
  const [axis, other, want] = w / h < PACK_ASPECT ? [xs, h, PACK_ASPECT] : [ys, w, 1 / PACK_ASPECT]
  if (span(axis, 1) >= want * other) return
  let lo = 1
  let hi = 2
  while (span(axis, hi) < want * other && hi < 1e6) hi *= 2
  for (let it = 0; it < 40; it++) {
    const mid = (lo + hi) / 2
    if (span(axis, mid) < want * other) lo = mid
    else hi = mid
  }
  for (let i = 0; i < axis.length; i++) axis[i] = axis[i]! * hi
}

/**
 * Visiting order for the packing grid: the largest island first, then each
 * time the unplaced island most strongly linked to the one just placed (else
 * to any placed island, else the largest left), with the loose island last.
 */
function linkageOrder(
  groups: readonly IslandGroup[],
  pairs: readonly { a: number; b: number; w: number }[],
): number[] {
  const n = groups.length
  const linked: Map<number, number>[] = Array.from({ length: n }, () => new Map())
  for (const { a, b, w } of pairs) {
    linked[a]!.set(b, w)
    linked[b]!.set(a, w)
  }
  const placed = new Uint8Array(n)
  const toAny = new Float64Array(n)
  const order: number[] = []
  const strongest = (weights: (j: number) => number) => {
    let best = -1
    let bestW = 0
    for (let j = 0; j < n; j++) {
      if (placed[j] || groups[j]!.loose) continue
      const w = weights(j)
      if (w > bestW) {
        best = j
        bestW = w
      }
    }
    return best
  }
  const firstLeft = () => {
    for (let j = 0; j < n; j++) if (!placed[j]) return j
    return -1
  }
  let next = firstLeft()
  while (next >= 0) {
    placed[next] = 1
    order.push(next)
    for (const [j, w] of linked[next]!) toAny[j] = toAny[j]! + w
    const last = linked[next]!
    next = strongest((j) => last.get(j) ?? 0)
    if (next < 0) next = strongest((j) => toAny[j]!)
    if (next < 0) next = firstLeft()
  }
  return order
}

/**
 * Where each island runs in the force simulation, which is not where it is
 * drawn: every frame refits an island onto its drawn centre, so these spots
 * only have to keep the islands out of each other's reach.
 */
export function simulationCentres(groups: readonly IslandGroup[]): Map<string, Point> {
  const largest = groups.reduce((m, g) => Math.max(m, g.members.length), 1)
  const spacing = SIM_SPACING_PER_ROOT * Math.sqrt(largest)
  const side = Math.max(1, Math.ceil(Math.sqrt(groups.length)))
  const out = new Map<string, Point>()
  groups.forEach((g, i) => {
    out.set(g.key, {
      x: ((i % side) - (side - 1) / 2) * spacing,
      y: (Math.floor(i / side) - (side - 1) / 2) * spacing,
    })
  })
  return out
}

export function layoutIslands(
  memories: readonly { id: string; cluster: number }[],
  edges: readonly ScoredEdge[],
): IslandLayout {
  const ids = memories.map((m) => m.id)
  const ix = indexEdges(ids, edges)
  const { groups, groupOf, role } = groupIndexed(memories, ix)
  const centres = placeIndexed(groups, islandIndexOf(groups, groupOf, ids), ix)
  let extent = 0
  for (const g of groups) {
    const c = centres.get(g.key)!
    extent = Math.max(extent, Math.hypot(c.x, c.y) + SOFT_EDGE * g.radius)
  }
  return { groups, groupOf, role, centres, extent, gap: NODE_GAP * ISLAND_K * Math.sqrt(Math.PI) }
}

/**
 * Where a member sits before the force layout has said anything: a sunflower
 * over its island, so the first frame already shows the islands. The loose
 * island keeps this arrangement for good.
 */
export function seedIsland(group: IslandGroup, centre: Point): Map<string, Point> {
  const out = new Map<string, Point>()
  const n = group.members.length
  group.members.forEach((id, i) => {
    const r = group.radius * 0.95 * Math.sqrt((i + 0.5) / n)
    // A jitter fixed by the id keeps the loose island from reading as a grid.
    const a = i * GOLDEN_ANGLE + (group.loose ? (seededUnit(id, 4) - 0.5) * 0.6 : 0)
    out.set(id, { x: centre.x + r * Math.cos(a), y: centre.y + r * Math.sin(a) })
  })
  return out
}

/**
 * Maps one island's simulated positions onto its disc: centroid onto the
 * centre, the 85th-percentile member to FIT_P85 of the radius, and anything
 * further tapered toward SOFT_EDGE so a stray member trails rather than
 * flying off or being pinned to a rim.
 */
export function fitIsland(
  positions: ReadonlyMap<string, Point>,
  centre: Point,
  radius: number,
): Map<string, Point> {
  const out = new Map<string, Point>()
  if (positions.size === 0) return out
  let cx = 0
  let cy = 0
  for (const p of positions.values()) {
    cx += p.x
    cy += p.y
  }
  cx /= positions.size
  cy /= positions.size
  const dists: number[] = []
  for (const p of positions.values()) dists.push(Math.hypot(p.x - cx, p.y - cy))
  dists.sort((a, b) => a - b)
  const p85 = dists[Math.ceil(0.85 * dists.length) - 1]!
  const scale = p85 > 1e-9 ? (FIT_P85 * radius) / p85 : 0
  const knee = FIT_P85 * radius
  const tail = (SOFT_EDGE - FIT_P85) * radius
  for (const [id, p] of positions) {
    let x = (p.x - cx) * scale
    let y = (p.y - cy) * scale
    const d = Math.hypot(x, y)
    if (d > knee) {
      const k = (knee + tail * Math.tanh((d - knee) / tail)) / d
      x *= k
      y *= k
    }
    out.set(id, { x: centre.x + x, y: centre.y + y })
  }
  return out
}

/**
 * Pushes memories apart until none sits closer than `gap`, with no outer
 * bound. A force layout keeps contracting a linked group toward a point, and
 * stacked glows sum to white. `offsets` carries each node's last correction
 * so a per-frame caller starts from where the previous frame settled.
 */
export function spreadPoints(
  fitted: ReadonlyMap<string, Point>,
  gap: number,
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
  const dx = new Float64Array(n)
  const dy = new Float64Array(n)
  const keyOf = (ix: number, iy: number) => ix * 1_000_003 + iy
  for (let it = 0; it < iterations && gap > 0 && n > 1; it++) {
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
              const t = seededUnit(`${ids[i]}|${ids[j]}`, 5) * Math.PI * 2
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
