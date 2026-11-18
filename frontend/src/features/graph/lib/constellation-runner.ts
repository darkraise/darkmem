import Graph from "graphology"
import FA2Layout from "graphology-layout-forceatlas2/worker"
import { inferSettings } from "graphology-layout-forceatlas2"
import { seededUnit } from "./code-graph-theme"
import {
  classify,
  classifyWithCut,
  CORE_K,
  coreRadius as computeCoreRadius,
  fitCore,
  fitCoreToFarthest,
  HALO_SIZE,
  placeOuter,
  placeOuterRing,
  spreadCore,
  ROLE_BRIGHTNESS,
  type Attachment,
  type Classification,
  type ConstellationEdge,
  type OuterLayout,
  type Point,
  type ScoredEdge,
} from "./constellation-layout"

/** spreadCore passes per animation frame, and when the layout settles. */
const FRAME_ITERATIONS = 2
const SETTLE_ITERATIONS = 40

export interface ConstellationRunner {
  readonly classification: Classification
  readonly coreRadius: number
  readonly outer: OuterLayout
  start(): void
  stop(): void
  kill(): void
  isRunning(): boolean
}

export function constellationFa2Settings(
  graph: Graph,
  tier: { slowDown: number; barnesHutOptimize: boolean },
): Record<string, unknown> {
  return {
    ...inferSettings(graph),
    linLogMode: true,
    outboundAttractionDistribution: false,
    strongGravityMode: true,
    gravity: 1,
    scalingRatio: 10,
    slowDown: tier.slowDown,
    barnesHutOptimize: tier.barnesHutOptimize,
  }
}

export function createConstellationRunner(
  graph: Graph,
  opts: {
    layoutMs: number
    fa2Settings: Record<string, unknown>
    onStop?: () => void
    roles?: {
      nodeIds: readonly string[]
      edges: readonly ScoredEdge[]
      attachments: readonly Attachment[]
    }
  },
): ConstellationRunner {
  const { roles } = opts
  let classification: Classification
  if (roles) {
    classification = classifyWithCut(roles.nodeIds, roles.edges, roles.attachments)
    graph.forEachNode((id) => {
      if (!classification.role.has(id)) {
        classification.role.set(id, "halo")
        classification.halo.push(id)
        classification.degree.set(id, graph.degree(id))
      }
    })
  } else {
    const edges: ConstellationEdge[] = []
    graph.forEachEdge((_e, _a, source, target) => edges.push({ source, target }))
    classification = classify(graph.nodes(), edges)
  }
  // The code canvas passes no roles and keeps its ring, farthest-node fit and
  // strong gravity; only the memory canvas takes the scattered arrangement.
  const place = roles ? placeOuter : placeOuterRing
  const fit = roles ? fitCore : fitCoreToFarthest
  const fa2Settings = roles
    ? { ...opts.fa2Settings, strongGravityMode: false, gravity: 0.05 }
    : opts.fa2Settings
  // A core entity rides on its memories rather than joining the core's
  // simulation: its membership links would pull every memory sharing it into
  // one stack, and its count would widen the core, so toggling the entity
  // layer would re-arrange the memories and pile their glows onto one spot.
  const attached = new Set(roles?.attachments.map((a) => a.id) ?? [])
  const simulated = classification.core.filter((id) => !attached.has(id))
  const simulatedSet = new Set(simulated)
  const riders = (roles?.attachments ?? [])
    .filter((a) => classification.role.get(a.id) === "core")
    .map((a) => ({ id: a.id, linked: a.linked.filter((m) => simulatedSet.has(m)) }))
  const R = computeCoreRadius(simulated.length)
  const outer = place(classification, R)
  const coreSet = new Set(simulated)

  const placeRiders = (fitted: Map<string, Point>) => {
    for (const { id, linked } of riders) {
      let x = 0
      let y = 0
      for (const m of linked) {
        const p = fitted.get(m)!
        x += p.x
        y += p.y
      }
      const n = linked.length || 1
      const jitter = 0.25 * CORE_K
      fitted.set(id, {
        x: x / n + (seededUnit(id, 2) - 0.5) * jitter,
        y: y / n + (seededUnit(id, 3) - 0.5) * jitter,
      })
    }
    return fitted
  }

  const currentCore = () => {
    const pos = new Map<string, Point>()
    for (const id of simulated) {
      pos.set(id, {
        x: (graph.getNodeAttribute(id, "x") as number | undefined) ?? 0,
        y: (graph.getNodeAttribute(id, "y") as number | undefined) ?? 0,
      })
    }
    return pos
  }
  // Only the memory canvas spreads its core; the code canvas keeps its fit.
  const offsets = new Map<string, Point>()
  const layoutCore = (pos: Map<string, Point>, iterations: number) =>
    placeRiders(roles ? spreadCore(fit(pos, R), R, offsets, iterations) : fit(pos, R))
  const fittedCore = layoutCore(currentCore(), SETTLE_ITERATIONS)

  const coreSizes = simulated
    .map((id) => graph.getNodeAttribute(id, "size") as number)
    .sort((a, b) => a - b)
  const mid = coreSizes.length >> 1
  const medianCore =
    coreSizes.length === 0
      ? 0
      : coreSizes.length % 2
        ? coreSizes[mid]!
        : (coreSizes[mid - 1]! + coreSizes[mid]!) / 2
  const haloSize = coreSizes.length === 0 ? HALO_SIZE : Math.min(HALO_SIZE, 0.4 * medianCore)

  graph.updateEachNodeAttributes((id, attrs) => {
    const role = classification.role.get(id)!
    const p = fittedCore.get(id) ?? outer.positions.get(id)!
    return {
      ...attrs,
      _role: role,
      brightness: ROLE_BRIGHTNESS[role],
      phase: seededUnit(id, 7),
      ...(role === "halo" && !attached.has(id) ? { size: haloSize } : {}),
      x: p.x,
      y: p.y,
    }
  })

  let worker: FA2Layout | null = null
  let coreGraph: Graph | null = null
  let frame: number | null = null
  let timer: ReturnType<typeof setTimeout> | null = null
  let running = false

  const mirror = (iterations = FRAME_ITERATIONS) => {
    if (!coreGraph) return
    const pos = new Map<string, Point>()
    coreGraph.forEachNode((id, a) => pos.set(id, { x: a.x as number, y: a.y as number }))
    const fitted = layoutCore(pos, iterations)
    graph.updateEachNodeAttributes(
      (id, attrs) => {
        const p = fitted.get(id)
        // In place: a copy per core node per frame is garbage at 20k nodes.
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
    classification,
    coreRadius: R,
    outer,
    start() {
      if (running) return
      coreGraph = new Graph({ type: "undirected" })
      for (const id of simulated) {
        coreGraph.addNode(id, {
          x: graph.getNodeAttribute(id, "x") as number,
          y: graph.getNodeAttribute(id, "y") as number,
        })
      }
      graph.forEachEdge((_e, _a, source, target) => {
        if (source !== target && coreSet.has(source) && coreSet.has(target)) {
          coreGraph!.mergeEdge(source, target)
        }
      })
      worker?.kill()
      worker = new FA2Layout(coreGraph, { settings: fa2Settings })
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
