import { seededUnit } from "./code-graph-theme"
import { ROLE_BRIGHTNESS, type ConstellationRole, type Point, type ScoredEdge } from "./constellation-layout"

export { ROLE_BRIGHTNESS }

/** Island radius per square-rooted member, in graph units. */
export const ISLAND_K = 12
/** The island of memories with no edge is this much sparser. */
export const LOOSE_K = 22
/** Clear space between two islands, as a share of the smaller one's radius,
 *  with a floor so two small islands never touch. */
export const ISLAND_GAP = 0.1
const ISLAND_GAP_MIN = 6
/** Minimum distance between two memories, as a share of an island's even
 *  spacing. Below 1 so linked memories can still sit closer than unlinked. */
export const NODE_GAP = 0.4
/** A fitted island's 85th-percentile member sits at this share of its
 *  radius; the rest taper softly to SOFT_EDGE, never to a hard rim. */
const FIT_P85 = 0.8
const SOFT_EDGE = 1.15
/** Islands collide at this share of their radii. Below SOFT_EDGE, so two
 *  neighbours' tapered stragglers may meet while their bodies (inside
 *  FIT_P85) keep a clear gap; at SOFT_EDGE the bodies sat far apart. */
export const ISLAND_REACH = 1
const LOOSE_GROUP = "loose"
const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5))
const PLACE_ITERATIONS = 300
/** Island count past which collisions search a grid instead of every pair. */
const GRID_MIN_ISLANDS = 150
/** Share of the seeding disc the island footprints cover. It only spaces the
 *  seed slots; the simulation holds no rim. */
const PACK_FILL = 0.62
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

const islandGap = (a: IslandGroup, b: IslandGroup) =>
  Math.max(ISLAND_GAP_MIN, ISLAND_GAP * Math.min(a.radius, b.radius))

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

/**
 * Island centres from a small deterministic simulation: islands start on the
 * slots of a sunflower inside a disc, each taking the free slot nearest the
 * islands it links to (the largest island takes the middle, the loose island
 * the rim); islands sharing edges pull toward touching, a pull toward the
 * centre keeps the whole round and compact, and collisions keep a gap.
 */
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
  const foot = Float64Array.from(rad, (r) => ISLAND_REACH * r + ISLAND_GAP_MIN / 2)
  let footArea = 0
  for (let i = 0; i < n; i++) footArea += Math.PI * foot[i]! * foot[i]!
  const discR = Math.sqrt(footArea / PACK_FILL / Math.PI)

  const xs = new Float64Array(n)
  const ys = new Float64Array(n)
  seedSlots(groups, pairs, rad, discR, xs, ys)
  const separate = (i: number, j: number) => {
    const ri = rad[i]!
    const rj = rad[j]!
    const want = ISLAND_REACH * (ri + rj) + Math.max(ISLAND_GAP_MIN, ISLAND_GAP * Math.min(ri, rj))
    let dx = xs[j]! - xs[i]!
    let dy = ys[j]! - ys[i]!
    if (dx * dx + dy * dy >= want * want) return
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
  const collideAll = () => {
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) separate(i, j)
  }
  // Past about 150 islands every pair costs more than a grid. Two islands
  // touch only within the sum of their reaches, and one large island would
  // put every small one in its cell, so each island sits in the grid of its
  // own size class (cells double per class) and searches its own and every
  // larger class's grid around it. Each pair is found once per pass; the
  // grid is taken at the start of the pass.
  const reach = Float64Array.from(
    rad,
    (r) => ISLAND_REACH * r + Math.max(ISLAND_GAP_MIN, ISLAND_GAP * r) / 2,
  )
  let minReach = Infinity
  for (let i = 0; i < n; i++) minReach = Math.min(minReach, reach[i]!)
  const sizeClass = Int32Array.from(reach, (r) => Math.max(0, Math.ceil(Math.log2(r / minReach))))
  let classes = 0
  for (let i = 0; i < n; i++) classes = Math.max(classes, sizeClass[i]! + 1)
  const classCell = Array.from({ length: classes }, (_, c) => 2 * minReach * 2 ** c)
  const grids = Array.from({ length: classes }, () => new Map<number, number[]>())
  const occupied = [...new Set(sizeClass)].sort((p, q) => p - q)
  const gridKey = (gx: number, gy: number) => gx * 4294967296 + gy
  const collideGrid = () => {
    for (const g of grids) g.clear()
    for (let i = 0; i < n; i++) {
      const c = classCell[sizeClass[i]!]!
      const grid = grids[sizeClass[i]!]!
      const k = gridKey(Math.floor(xs[i]! / c), Math.floor(ys[i]! / c))
      const bucket = grid.get(k)
      if (bucket) bucket.push(i)
      else grid.set(k, [i])
    }
    for (let i = 0; i < n; i++) {
      const own = sizeClass[i]!
      for (const cls of occupied) {
        if (cls < own) continue
        const c = classCell[cls]!
        const gx = Math.floor(xs[i]! / c)
        const gy = Math.floor(ys[i]! / c)
        for (let a = -1; a <= 1; a++) {
          for (let b = -1; b <= 1; b++) {
            const bucket = grids[cls]!.get(gridKey(gx + a, gy + b))
            if (!bucket) continue
            for (const j of bucket) {
              if (cls === own && j <= i) continue
              if (i < j) separate(i, j)
              else separate(j, i)
            }
          }
        }
      }
    }
  }
  const collide = n > GRID_MIN_ISLANDS ? collideGrid : collideAll

  const pairCount = pairs.length
  const pairA = Int32Array.from(pairs, (p) => p.a)
  const pairB = Int32Array.from(pairs, (p) => p.b)
  const pairRest = Float64Array.from(
    pairs,
    (p) => ISLAND_REACH * (rad[p.a]! + rad[p.b]!) + islandGap(groups[p.a]!, groups[p.b]!),
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
    // A gather toward the centre closes the gaps and rounds the clump; a hard
    // rim would fight the collisions and squeeze small sets into a ring.
    const gather = 1 - 0.03 * alpha
    for (let i = 0; i < n; i++) {
      xs[i] = xs[i]! * gather
      ys[i] = ys[i]! * gather
    }
    collide()
  }
  for (let it = 0; it < 50; it++) collide()

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
 * Seeds the island centres on sunflower slots, visited in linkage order: each
 * island takes the free slot closest to the weighted centroid of the placed
 * islands it links to, or the innermost free slot when it links to none.
 * Slots are spaced by area, so the seed is already a round, even packing.
 */
function seedSlots(
  groups: readonly IslandGroup[],
  pairs: readonly { a: number; b: number; w: number }[],
  rad: Float64Array,
  discR: number,
  xs: Float64Array,
  ys: Float64Array,
) {
  const n = groups.length
  const order = linkageOrder(groups, pairs)
  // The first island takes the centre; slot k sits at the radius enclosing
  // the islands before it, so the large islands placed first get the middle.
  let total = 0
  for (let i = 0; i < n; i++) total += rad[i]! * rad[i]!
  const slotX = new Float64Array(n)
  const slotY = new Float64Array(n)
  let acc = 0
  order.forEach((i, k) => {
    const share = rad[i]! * rad[i]!
    const r = k === 0 ? 0 : discR * Math.sqrt((acc + share / 2) / (total || 1))
    acc += share
    const a = k * GOLDEN_ANGLE
    slotX[k] = r * Math.cos(a)
    slotY[k] = r * Math.sin(a)
  })
  const linked: Map<number, number>[] = Array.from({ length: n }, () => new Map())
  for (const { a, b, w } of pairs) {
    linked[a]!.set(b, w)
    linked[b]!.set(a, w)
  }
  const taken = new Uint8Array(n)
  const placed = new Uint8Array(n)
  for (const i of order) {
    let wx = 0
    let wy = 0
    let wt = 0
    for (const [j, w] of linked[i]!) {
      if (!placed[j]) continue
      wx += xs[j]! * w
      wy += ys[j]! * w
      wt += w
    }
    let best = -1
    let bestD = Infinity
    for (let k = 0; k < n; k++) {
      if (taken[k]) continue
      // Unlinked islands fill inward-out, so the next free slot wins.
      if (wt === 0 || groups[i]!.loose) {
        best = k
        break
      }
      const d = Math.hypot(slotX[k]! - wx / wt, slotY[k]! - wy / wt)
      if (d < bestD) {
        bestD = d
        best = k
      }
    }
    taken[best] = 1
    placed[i] = 1
    // A fixed jitter per island, or equal unlinked islands read as a spiral.
    const key = groups[i]!.key
    const j = 0.15 * rad[i]!
    xs[i] = slotX[best]! + j * (seededUnit(key, 5) - 0.5)
    ys[i] = slotY[best]! + j * (seededUnit(key, 6) - 0.5)
  }
}

/**
 * Visiting order for the packing slots: the largest island first, then each
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
  const ids = [...positions.keys()]
  const n = ids.length
  const xs = new Float64Array(n)
  const ys = new Float64Array(n)
  ids.forEach((id, i) => {
    const p = positions.get(id)!
    xs[i] = p.x
    ys[i] = p.y
  })
  const outX = new Float64Array(n)
  const outY = new Float64Array(n)
  fitIslandInto(xs, ys, 0, n, centre, radius, outX, outY, new Float64Array(n))
  const out = new Map<string, Point>()
  ids.forEach((id, i) => out.set(id, { x: outX[i]!, y: outY[i]! }))
  return out
}

/** fitIsland over the index range [from, to) of flat coordinate arrays, for a
 *  caller that reuses its buffers every frame; `dists` holds at least
 *  `to - from` entries. */
export function fitIslandInto(
  xs: Float64Array,
  ys: Float64Array,
  from: number,
  to: number,
  centre: Point,
  radius: number,
  outX: Float64Array,
  outY: Float64Array,
  dists: Float64Array,
): void {
  const n = to - from
  if (n <= 0) return
  let cx = 0
  let cy = 0
  for (let i = from; i < to; i++) {
    cx += xs[i]!
    cy += ys[i]!
  }
  cx /= n
  cy /= n
  const own = dists.subarray(0, n)
  for (let i = from; i < to; i++) own[i - from] = Math.hypot(xs[i]! - cx, ys[i]! - cy)
  own.sort()
  const p85 = own[Math.ceil(0.85 * n) - 1]!
  const scale = p85 > 1e-9 ? (FIT_P85 * radius) / p85 : 0
  const knee = FIT_P85 * radius
  const tail = (SOFT_EDGE - FIT_P85) * radius
  for (let i = from; i < to; i++) {
    let x = (xs[i]! - cx) * scale
    let y = (ys[i]! - cy) * scale
    const d = Math.hypot(x, y)
    if (d > knee) {
      const k = (knee + tail * Math.tanh((d - knee) / tail)) / d
      x *= k
      y *= k
    }
    outX[i] = centre.x + x
    outY[i] = centre.y + y
  }
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
  spreadInPlace(xs, ys, n, gap, iterations, (i) => ids[i]!, createSpreadScratch(n))
  const out = new Map<string, Point>()
  ids.forEach((id, i) => {
    const p = fitted.get(id)!
    offsets.set(id, { x: xs[i]! - p.x, y: ys[i]! - p.y })
    out.set(id, { x: xs[i]!, y: ys[i]! })
  })
  return out
}

/** The grid and step buffers spreadInPlace works in, kept by a per-frame
 *  caller so a frame allocates none. */
export interface SpreadScratch {
  readonly dx: Float64Array
  readonly dy: Float64Array
  readonly cellOf: Int32Array
  readonly cellCount: Int32Array
  readonly cellStart: Int32Array
  readonly cellFill: Int32Array
  readonly items: Int32Array
  readonly cells: Map<number, number>
}

export function createSpreadScratch(n: number): SpreadScratch {
  return {
    dx: new Float64Array(n),
    dy: new Float64Array(n),
    cellOf: new Int32Array(n),
    cellCount: new Int32Array(n),
    cellStart: new Int32Array(n),
    cellFill: new Int32Array(n),
    items: new Int32Array(n),
    cells: new Map(),
  }
}

/** spreadPoints over the first `n` entries of flat coordinate arrays, moved
 *  in place; `idOf` names a point for the tie-break of two coincident ones. */
export function spreadInPlace(
  xs: Float64Array,
  ys: Float64Array,
  n: number,
  gap: number,
  iterations: number,
  idOf: (i: number) => string,
  scratch: SpreadScratch,
): void {
  const { dx, dy, cellOf, cellCount, cellStart, cellFill, items, cells } = scratch
  const keyOf = (ix: number, iy: number) => ix * 1_000_003 + iy
  for (let it = 0; it < iterations && gap > 0 && n > 1; it++) {
    // Each cell's members in ascending index order, laid out flat.
    cells.clear()
    let m = 0
    for (let i = 0; i < n; i++) {
      const k = keyOf(Math.floor(xs[i]! / gap), Math.floor(ys[i]! / gap))
      let c = cells.get(k)
      if (c === undefined) {
        c = m++
        cells.set(k, c)
        cellCount[c] = 0
      }
      cellOf[i] = c
      cellCount[c] = cellCount[c]! + 1
    }
    let start = 0
    for (let c = 0; c < m; c++) {
      cellStart[c] = start
      cellFill[c] = start
      start += cellCount[c]!
    }
    for (let i = 0; i < n; i++) {
      const c = cellOf[i]!
      items[cellFill[c]!] = i
      cellFill[c] = cellFill[c]! + 1
    }
    dx.fill(0, 0, n)
    dy.fill(0, 0, n)
    let moved = false
    for (let i = 0; i < n; i++) {
      const ix = Math.floor(xs[i]! / gap)
      const iy = Math.floor(ys[i]! / gap)
      for (let a = -1; a <= 1; a++) {
        for (let b = -1; b <= 1; b++) {
          const c = cells.get(keyOf(ix + a, iy + b))
          if (c === undefined) continue
          const end = cellStart[c]! + cellCount[c]!
          for (let q = cellStart[c]!; q < end; q++) {
            const j = items[q]!
            if (j <= i) continue
            const ex = xs[j]! - xs[i]!
            const ey = ys[j]! - ys[i]!
            const d = Math.hypot(ex, ey)
            if (d >= gap) continue
            let ux: number
            let uy: number
            if (d < 1e-9) {
              const t = seededUnit(`${idOf(i)}|${idOf(j)}`, 5) * Math.PI * 2
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
}
