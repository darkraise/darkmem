import Graph from "graphology"
import { seededUnit } from "./code-graph-theme"
import { createLayoutLoop } from "./layout-loop"
import {
  HALO_SIZE,
  ROLE_BRIGHTNESS,
  type Attachment,
  type Classification,
  type ConstellationRole,
  type OuterLayout,
  type Point,
  type ScoredEdge,
} from "./constellation-layout"
import {
  ISLAND_K,
  createSpreadScratch,
  fitIslandInto,
  layoutIslands,
  seedIsland,
  simulationCentres,
  spreadInPlace,
  type IslandLayout,
} from "./cluster-layout"

/** spreadPoints passes per animation frame, and when the layout settles. */
const FRAME_ITERATIONS = 2
const SETTLE_ITERATIONS = 40
/** Weakest edge's pull as a share of the strongest's: every link gathers its
 *  memories a little, a strong one gathers them most. */
const WEAK_EDGE_WEIGHT = 0.15

export interface ClusterRunner {
  readonly layout: IslandLayout
  /** The role groups the glow program's density tuning reads. */
  readonly classification: Pick<Classification, "core" | "satellites" | "halo">
  readonly outer: Pick<OuterLayout, "haloInner" | "haloOuter" | "clumpSpacing">
  /** Island key of every node, entities included, for the at-rest edge rule. */
  readonly groupOf: ReadonlyMap<string, string>
  start(): void
  stop(): void
  kill(): void
  isRunning(): boolean
}

export function createClusterRunner(
  graph: Graph,
  opts: {
    layoutMs: number
    fa2Settings: Record<string, unknown>
    memories: readonly { id: string; cluster: number }[]
    edges: readonly ScoredEdge[]
    attachments: readonly Attachment[]
    /** Memories with no settled position to keep; they start on their island. */
    fresh: ReadonlySet<string>
    onStop?: () => void
  },
): ClusterRunner {
  const layout = layoutIslands(opts.memories, opts.edges)
  const { groups, centres } = layout
  const groupOf = new Map(layout.groupOf)
  const role = new Map<string, ConstellationRole>(layout.role)

  const looseGroup = groups.find((g) => g.loose)
  const fixed = looseGroup ? seedIsland(looseGroup, centres.get(looseGroup.key)!) : new Map()
  const simulatedGroups = groups.filter((g) => !g.loose)
  const simulated = new Set(simulatedGroups.flatMap((g) => g.members))

  // Simulation space, not drawn space: islands run far apart so one island's
  // repulsion cannot stretch another, and every frame refits each island onto
  // its drawn centre.
  const simAt = simulationCentres(simulatedGroups)
  const startAt = new Map<string, Point>()
  for (const g of simulatedGroups) {
    const drawn = centres.get(g.key)!
    const sim = simAt.get(g.key)!
    const seeds = seedIsland(g, sim)
    for (const id of g.members) {
      const x = graph.getNodeAttribute(id, "x") as number | undefined
      const y = graph.getNodeAttribute(id, "y") as number | undefined
      startAt.set(
        id,
        opts.fresh.has(id) || x === undefined || y === undefined
          ? seeds.get(id)!
          : { x: x - drawn.x + sim.x, y: y - drawn.y + sim.y },
      )
    }
  }

  // An entity rides on its memories, as on the old core: its membership links
  // would otherwise drag every memory sharing it into one stack.
  const riders = opts.attachments
    .map((a) => ({ id: a.id, linked: a.linked.filter((m) => groupOf.has(m)) }))
    .filter((a) => a.linked.length > 0)
  for (const { id, linked } of riders) {
    const votes = new Map<string, number>()
    let best: ConstellationRole = "halo"
    for (const m of linked) {
      const k = groupOf.get(m)!
      votes.set(k, (votes.get(k) ?? 0) + 1)
      const r = role.get(m)!
      if (r === "core" || (r === "satellite" && best === "halo")) best = r
    }
    let top = ""
    let topVotes = -1
    for (const [k, v] of votes) {
      if (v > topVotes || (v === topVotes && k < top)) {
        top = k
        topVotes = v
      }
    }
    groupOf.set(id, top)
    role.set(id, best)
  }

  // Every placed node has one index for the whole run: the loose island's
  // fixed members, then each simulated island's members together, then the
  // riders. The layout runs for seconds at up to 20k nodes, so a frame works
  // in these buffers and allocates nothing per node.
  const order: string[] = [...fixed.keys()]
  const spans = simulatedGroups.map((g) => {
    const from = order.length
    order.push(...g.members)
    return { from, to: order.length, centre: centres.get(g.key)!, radius: g.radius }
  })
  const pointCount = order.length
  for (const r of riders) order.push(r.id)
  const indexOf = new Map(order.map((id, i) => [id, i]))
  const fixedX = Float64Array.from(fixed.values(), (p: Point) => p.x)
  const fixedY = Float64Array.from(fixed.values(), (p: Point) => p.y)
  const riderLinks = riders.map((r) => Int32Array.from(r.linked, (m) => indexOf.get(m)!))
  const jitter = 0.25 * ISLAND_K
  const riderDx = Float64Array.from(riders, (r) => (seededUnit(r.id, 2) - 0.5) * jitter)
  const riderDy = Float64Array.from(riders, (r) => (seededUnit(r.id, 3) - 0.5) * jitter)
  const simX = new Float64Array(pointCount)
  const simY = new Float64Array(pointCount)
  const fitX = new Float64Array(pointCount)
  const fitY = new Float64Array(pointCount)
  const offX = new Float64Array(pointCount)
  const offY = new Float64Array(pointCount)
  const outX = new Float64Array(order.length)
  const outY = new Float64Array(order.length)
  const dists = new Float64Array(spans.reduce((m, sp) => Math.max(m, sp.to - sp.from), 0))
  const scratch = createSpreadScratch(pointCount)
  const idOf = (i: number) => order[i]!

  const arrange = (iterations: number) => {
    fitX.set(fixedX)
    fitY.set(fixedY)
    for (const sp of spans) {
      fitIslandInto(simX, simY, sp.from, sp.to, sp.centre, sp.radius, fitX, fitY, dists)
    }
    for (let i = 0; i < pointCount; i++) {
      outX[i] = fitX[i]! + offX[i]!
      outY[i] = fitY[i]! + offY[i]!
    }
    spreadInPlace(outX, outY, pointCount, layout.gap, iterations, idOf, scratch)
    for (let i = 0; i < pointCount; i++) {
      offX[i] = outX[i]! - fitX[i]!
      offY[i] = outY[i]! - fitY[i]!
    }
    for (let r = 0; r < riderLinks.length; r++) {
      const linked = riderLinks[r]!
      let x = 0
      let y = 0
      for (let k = 0; k < linked.length; k++) {
        x += outX[linked[k]!]!
        y += outY[linked[k]!]!
      }
      outX[pointCount + r] = x / linked.length + riderDx[r]!
      outY[pointCount + r] = y / linked.length + riderDy[r]!
    }
  }
  for (const [id, p] of startAt) {
    const i = indexOf.get(id)!
    simX[i] = p.x
    simY[i] = p.y
  }
  arrange(SETTLE_ITERATIONS)

  const glowSizes = [...simulated]
    .map((id) => graph.getNodeAttribute(id, "size") as number)
    .sort((a, b) => a - b)
  const mid = glowSizes.length >> 1
  const median =
    glowSizes.length === 0
      ? 0
      : glowSizes.length % 2
        ? glowSizes[mid]!
        : (glowSizes[mid - 1]! + glowSizes[mid]!) / 2
  const looseSize = glowSizes.length === 0 ? HALO_SIZE : Math.min(HALO_SIZE, 0.4 * median)
  const looseIds = new Set(looseGroup?.members ?? [])

  graph.updateEachNodeAttributes((id, attrs) => {
    const r = role.get(id) ?? "halo"
    const i = indexOf.get(id)
    return {
      ...attrs,
      _role: r,
      brightness: ROLE_BRIGHTNESS[r],
      phase: seededUnit(id, 7),
      ...(looseIds.has(id) ? { size: looseSize } : {}),
      x: i === undefined ? 0 : outX[i]!,
      y: i === undefined ? 0 : outY[i]!,
    }
  })

  let lo = Infinity
  let hi = -Infinity
  for (const e of opts.edges) {
    const s = e.score ?? 0
    if (s < lo) lo = s
    if (s > hi) hi = s
  }
  const weightOf = (s: number | undefined) =>
    hi > lo ? WEAK_EDGE_WEIGHT + (1 - WEAK_EDGE_WEIGHT) * (((s ?? lo) - lo) / (hi - lo)) : 1

  let simGraph: Graph | null = null

  const readSim = (id: string, a: Record<string, unknown>) => {
    const i = indexOf.get(id)!
    simX[i] = a.x as number
    simY[i] = a.y as number
  }
  // In place: a copy per node per frame is garbage at 20k nodes.
  const writePlaced = (id: string, attrs: Record<string, unknown>) => {
    const i = indexOf.get(id)
    if (i !== undefined) {
      attrs.x = outX[i]
      attrs.y = outY[i]
    }
    return attrs
  }
  const XY = { attributes: ["x", "y"] }
  const mirror = (iterations = FRAME_ITERATIONS) => {
    if (!simGraph) return
    simGraph.forEachNode(readSim)
    arrange(iterations)
    graph.updateEachNodeAttributes(writePlaced, XY)
  }
  const loop = createLayoutLoop({
    layoutMs: opts.layoutMs,
    fa2Settings: opts.fa2Settings,
    onFrame: () => mirror(),
    onSettle: () => {
      mirror(SETTLE_ITERATIONS)
      opts.onStop?.()
    },
  })

  return {
    layout,
    classification: {
      core: groups.flatMap((g) => (g.loose ? [] : g.members.slice(0, g.members.length - g.riders.length))),
      satellites: groups.filter((g) => g.riders.length > 0).map((g) => g.riders),
      halo: looseGroup?.members ?? [],
    },
    outer: { haloInner: 0, haloOuter: looseGroup?.radius ?? 0, clumpSpacing: layout.gap },
    groupOf,
    start() {
      if (loop.isRunning()) return
      simGraph = new Graph({ type: "undirected" })
      for (const id of simulated) simGraph.addNode(id, { ...startAt.get(id)! })
      // Only an island's own edges move it: an edge to another island would
      // tug a member toward wherever that island happens to sit in the
      // simulation, which is not where it is drawn.
      for (const e of opts.edges) {
        if (e.source === e.target || !simulated.has(e.source) || !simulated.has(e.target)) continue
        if (groupOf.get(e.source) !== groupOf.get(e.target)) continue
        simGraph.mergeEdge(e.source, e.target, { weight: weightOf(e.score) })
      }
      if (simGraph.size === 0) {
        opts.onStop?.()
        return
      }
      loop.start(simGraph)
    },
    stop: loop.stop,
    kill: loop.kill,
    isRunning: loop.isRunning,
  }
}
