import Graph from "graphology"
import FA2Layout from "graphology-layout-forceatlas2/worker"
import { inferSettings } from "graphology-layout-forceatlas2"
import { seededUnit } from "./code-graph-theme"
import {
  classify,
  classifyWithCut,
  coreRadius as computeCoreRadius,
  fitCore,
  fitCoreToFarthest,
  placeOuter,
  placeOuterRing,
  ROLE_BRIGHTNESS,
  type Attachment,
  type Classification,
  type ConstellationEdge,
  type OuterLayout,
  type Point,
  type ScoredEdge,
} from "./constellation-layout"

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
  const R = computeCoreRadius(classification.core.length)
  const outer = place(classification, R)
  const coreSet = new Set(classification.core)

  const currentCore = () => {
    const pos = new Map<string, Point>()
    for (const id of classification.core) {
      pos.set(id, {
        x: (graph.getNodeAttribute(id, "x") as number | undefined) ?? 0,
        y: (graph.getNodeAttribute(id, "y") as number | undefined) ?? 0,
      })
    }
    return pos
  }
  const fittedCore = fit(currentCore(), R)

  graph.updateEachNodeAttributes((id, attrs) => {
    const role = classification.role.get(id)!
    const p = coreSet.has(id) ? fittedCore.get(id)! : outer.positions.get(id)!
    return {
      ...attrs,
      _role: role,
      brightness: ROLE_BRIGHTNESS[role],
      phase: seededUnit(id, 7),
      x: p.x,
      y: p.y,
    }
  })

  let worker: FA2Layout | null = null
  let coreGraph: Graph | null = null
  let frame: number | null = null
  let timer: ReturnType<typeof setTimeout> | null = null
  let running = false

  const mirror = () => {
    if (!coreGraph) return
    const pos = new Map<string, Point>()
    coreGraph.forEachNode((id, a) => pos.set(id, { x: a.x as number, y: a.y as number }))
    const fitted = fit(pos, R)
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
      for (const id of classification.core) {
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
        mirror()
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
