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
  hideOnMove: boolean
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
    hideOnMove: false,
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
    hideOnMove: false,
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
    hideOnMove: true,
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
    hideOnMove: true,
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

export interface ClusterAnchor {
  x: number
  y: number
  spread: number
}

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5))
const ANCHOR_SPACING = 10
const SPREAD_PER_ROOT_MEMBER = 0.8

/**
 * One anchor per cluster on a golden-angle spiral, largest cluster at the
 * centre. Seeding a node beside its cluster's anchor starts the layout close
 * to where it will settle, so a large graph converges in seconds rather than
 * untangling uniform noise.
 */
export function clusterAnchors(
  memories: { cluster: number }[],
): Map<number, ClusterAnchor> {
  const sizes = new Map<number, number>()
  for (const m of memories) {
    if (m.cluster >= 0) sizes.set(m.cluster, (sizes.get(m.cluster) ?? 0) + 1)
  }
  const ordered = [...sizes.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0])
  const anchors = new Map<number, ClusterAnchor>()
  ordered.forEach(([cluster, size], i) => {
    const r = ANCHOR_SPACING * Math.sqrt(i)
    const theta = i * GOLDEN_ANGLE
    anchors.set(cluster, {
      x: r * Math.cos(theta),
      y: r * Math.sin(theta),
      spread: Math.sqrt(size) * SPREAD_PER_ROOT_MEMBER,
    })
  })
  return anchors
}

/** A point in the anchor's disc; `u` and `v` are uniform draws in [0, 1). */
export function seedAroundAnchor(
  anchor: ClusterAnchor,
  u: number,
  v: number,
): { x: number; y: number } {
  const angle = u * 2 * Math.PI
  const radius = anchor.spread * Math.sqrt(v)
  return {
    x: anchor.x + radius * Math.cos(angle),
    y: anchor.y + radius * Math.sin(angle),
  }
}
