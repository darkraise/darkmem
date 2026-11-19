import Graph from "graphology"
import FA2Layout from "graphology-layout-forceatlas2/worker"
import { seededUnit } from "./code-graph-theme"
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
  fitIsland,
  layoutIslands,
  seedIsland,
  simulationCentres,
  spreadPoints,
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

  const placeRiders = (pos: Map<string, Point>) => {
    for (const { id, linked } of riders) {
      let x = 0
      let y = 0
      for (const m of linked) {
        const p = pos.get(m)!
        x += p.x
        y += p.y
      }
      const jitter = 0.25 * ISLAND_K
      pos.set(id, {
        x: x / linked.length + (seededUnit(id, 2) - 0.5) * jitter,
        y: y / linked.length + (seededUnit(id, 3) - 0.5) * jitter,
      })
    }
    return pos
  }

  const offsets = new Map<string, Point>()
  const arrange = (sim: ReadonlyMap<string, Point>, iterations: number) => {
    const fitted = new Map<string, Point>(fixed)
    for (const g of simulatedGroups) {
      const own = new Map<string, Point>()
      for (const id of g.members) own.set(id, sim.get(id)!)
      for (const [id, p] of fitIsland(own, centres.get(g.key)!, g.radius)) fitted.set(id, p)
    }
    return placeRiders(spreadPoints(fitted, layout.gap, offsets, iterations))
  }
  const first = arrange(startAt, SETTLE_ITERATIONS)

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
    const p = first.get(id) ?? { x: 0, y: 0 }
    return {
      ...attrs,
      _role: r,
      brightness: ROLE_BRIGHTNESS[r],
      phase: seededUnit(id, 7),
      ...(looseIds.has(id) ? { size: looseSize } : {}),
      x: p.x,
      y: p.y,
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

  let worker: FA2Layout | null = null
  let simGraph: Graph | null = null
  let frame: number | null = null
  let timer: ReturnType<typeof setTimeout> | null = null
  let running = false

  const mirror = (iterations = FRAME_ITERATIONS) => {
    if (!simGraph) return
    const sim = new Map<string, Point>()
    simGraph.forEachNode((id, a) => sim.set(id, { x: a.x as number, y: a.y as number }))
    const placed = arrange(sim, iterations)
    graph.updateEachNodeAttributes(
      (id, attrs) => {
        const p = placed.get(id)
        // In place: a copy per node per frame is garbage at 20k nodes.
        if (p) {
          attrs.x = p.x
          attrs.y = p.y
        }
        return attrs
      },
      { attributes: ["x", "y"] },
    )
  }
  const loop = () => {
    mirror()
    frame = requestAnimationFrame(loop)
  }
  const halt = () => {
    if (frame !== null) cancelAnimationFrame(frame)
    if (timer !== null) clearTimeout(timer)
    frame = null
    timer = null
    worker?.stop()
    running = false
  }

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
      if (running) return
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
      worker?.kill()
      worker = new FA2Layout(simGraph, { settings: opts.fa2Settings })
      worker.start()
      running = true
      frame = requestAnimationFrame(loop)
      timer = setTimeout(() => {
        halt()
        mirror(SETTLE_ITERATIONS)
        opts.onStop?.()
      }, opts.layoutMs)
    },
    stop() {
      halt()
    },
    kill() {
      halt()
      worker?.kill()
      worker = null
    },
    isRunning() {
      return running
    },
  }
}
