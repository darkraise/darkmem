/**
 * How the memory graph's renderers trade detail for speed as it grows.
 *
 * Tier boundaries match the code graph's so both canvases change behaviour at
 * the same sizes.
 */

export type ScaleTier = "small" | "medium" | "large" | "huge"

export interface ScaleSettings {
  /** Curved edges cost several times a straight one per frame. */
  curvedEdges: boolean
  hideLabelsOnMove: boolean
  /** Whether hovering with nothing selected recedes the rest of the graph.
   *  That repaints every node and edge, so past the medium tier hover lights
   *  only its own neighbourhood. */
  hoverDims: boolean
  slowDown: number
  barnesHutOptimize: boolean
  /** How long ForceAtlas2 runs before it is stopped. */
  layoutMs: number
  sphereSegments: [number, number]
  arrows3D: boolean
  hulls3D: boolean
  warmupTicks3D: number
  cooldownTicks3D: number
}

export const CURVED_EDGE_LIMIT = 2000
export const LARGE_3D_NOTICE_NODES = 5000

const TIERS: Record<ScaleTier, Omit<ScaleSettings, "curvedEdges">> = {
  small: {
    hideLabelsOnMove: false,
    hoverDims: true,
    slowDown: 12,
    barnesHutOptimize: false,
    layoutMs: 8000,
    sphereSegments: [16, 12],
    arrows3D: true,
    hulls3D: true,
    warmupTicks3D: 80,
    cooldownTicks3D: 150,
  },
  medium: {
    hideLabelsOnMove: false,
    hoverDims: true,
    slowDown: 8,
    barnesHutOptimize: true,
    layoutMs: 10000,
    sphereSegments: [16, 12],
    arrows3D: true,
    hulls3D: true,
    warmupTicks3D: 80,
    cooldownTicks3D: 150,
  },
  large: {
    hideLabelsOnMove: true,
    hoverDims: false,
    slowDown: 5,
    barnesHutOptimize: true,
    layoutMs: 15000,
    sphereSegments: [8, 6],
    arrows3D: false,
    hulls3D: false,
    warmupTicks3D: 30,
    cooldownTicks3D: 100,
  },
  huge: {
    hideLabelsOnMove: true,
    hoverDims: false,
    slowDown: 3,
    barnesHutOptimize: true,
    layoutMs: 20000,
    sphereSegments: [8, 6],
    arrows3D: false,
    hulls3D: false,
    warmupTicks3D: 10,
    cooldownTicks3D: 60,
  },
}

export function scaleTier(nodeCount: number): ScaleTier {
  if (nodeCount < 500) return "small"
  if (nodeCount < 2000) return "medium"
  if (nodeCount < 10000) return "large"
  return "huge"
}

export function scaleSettings(nodeCount: number, edgeCount: number): ScaleSettings {
  return {
    ...TIERS[scaleTier(nodeCount)],
    curvedEdges: edgeCount <= CURVED_EDGE_LIMIT,
  }
}
