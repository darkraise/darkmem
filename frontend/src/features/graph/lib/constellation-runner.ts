import Graph from "graphology"
import { inferSettings } from "graphology-layout-forceatlas2"
import { createLayoutLoop } from "./layout-loop"
import { seededUnit } from "./code-graph-theme"
import {
  classify,
  coreRadius as computeCoreRadius,
  createCoreMirror,
  fitCoreToFarthest,
  HALO_SIZE,
  placeOuterRing,
  ROLE_BRIGHTNESS,
  type Classification,
  type ConstellationEdge,
  type OuterLayout,
  type Point,
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
  },
): ConstellationRunner {
  const edges: ConstellationEdge[] = []
  graph.forEachEdge((_e, _a, source, target) => edges.push({ source, target }))
  const classification: Classification = classify(graph.nodes(), edges)
  const simulated = classification.core
  const R = computeCoreRadius(simulated.length)
  const outer = placeOuterRing(classification, R)
  const coreSet = new Set(simulated)

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
  const fittedCore = fitCoreToFarthest(currentCore(), R)

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
      ...(role === "halo" ? { size: haloSize } : {}),
      x: p.x,
      y: p.y,
    }
  })

  let coreGraph: Graph | null = null
  // In place: a copy per core node per frame is garbage at 20k nodes.
  const coreMirror = createCoreMirror(simulated, R)

  const mirror = () => {
    if (!coreGraph) return
    coreMirror.apply(coreGraph, graph)
  }
  const loop = createLayoutLoop({
    layoutMs: opts.layoutMs,
    fa2Settings: opts.fa2Settings,
    onFrame: mirror,
    onSettle: () => {
      mirror()
      opts.onStop?.()
    },
  })

  return {
    classification,
    coreRadius: R,
    outer,
    start() {
      if (loop.isRunning()) return
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
      loop.start(coreGraph)
    },
    stop: loop.stop,
    kill: loop.kill,
    isRunning: loop.isRunning,
  }
}
