import {
  useRef,
  useEffect,
  useCallback,
  forwardRef,
  useImperativeHandle,
} from "react"
import Graph from "graphology"
import Sigma from "sigma"
import EdgeCurveProgram, { indexParallelEdgesIndex } from "@sigma/edge-curve"
import FA2Layout from "graphology-layout-forceatlas2/worker"
import { inferSettings } from "graphology-layout-forceatlas2"
import noverlap from "graphology-layout-noverlap"
import {
  communityColor,
  seededUnit,
  type GraphThemeTokens,
} from "../lib/code-graph-theme"

// ── Color helpers (matching GitNexus) ─────────────────────────

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return result
    ? {
        // regex has three capture groups, guaranteed present when result is non-null
        r: parseInt(result[1]!, 16),
        g: parseInt(result[2]!, 16),
        b: parseInt(result[3]!, 16),
      }
    : { r: 100, g: 100, b: 100 }
}

function rgbToHex(r: number, g: number, b: number): string {
  return (
    "#" +
    [r, g, b]
      .map((x) =>
        Math.max(0, Math.min(255, Math.round(x)))
          .toString(16)
          .padStart(2, "0"),
      )
      .join("")
  )
}

// Fade `hex` toward the live surface background by `amount` (0 = full bg,
// 1 = original). `bgHex` comes from the resolved --background token so dimmed
// nodes blend into whatever surface the active theme paints.
function dimColor(hex: string, amount: number, bgHex: string): string {
  const rgb = hexToRgb(hex)
  const bg = hexToRgb(bgHex)
  return rgbToHex(
    bg.r + (rgb.r - bg.r) * amount,
    bg.g + (rgb.g - bg.g) * amount,
    bg.b + (rgb.b - bg.b) * amount,
  )
}

function brightenColor(hex: string, factor: number): string {
  const rgb = hexToRgb(hex)
  return rgbToHex(
    rgb.r + ((255 - rgb.r) * (factor - 1)) / factor,
    rgb.g + ((255 - rgb.g) * (factor - 1)) / factor,
    rgb.b + ((255 - rgb.b) * (factor - 1)) / factor,
  )
}

// ── Node constants ────────────────────────────────────────────

const NODE_SIZES: Record<string, number> = {
  project: 20,
  package: 16,
  module: 13,
  folder: 10,
  file: 6,
  class: 8,
  struct: 8,
  record: 8,
  function: 4,
  method: 3,
  constructor: 4,
  interface: 7,
  trait: 7,
  enum: 5,
  variable: 2,
  import: 1.5,
  decorator: 2,
  type: 3,
  impl: 3,
  namespace: 13,
  property: 2,
  route: 5,
  tool: 5,
  model: 4,
  community: 6,
  process: 5,
  const: 2,
  static: 2,
}
const DEFAULT_NODE_SIZE = 3

const EDGE_SIZE_MULTIPLIERS: Record<string, number> = {
  contains: 0.4,
  defines: 0.5,
  imports: 0.6,
  calls: 0.8,
  extends: 1.0,
  implements: 0.9,
  has_method: 0.5,
  has_property: 0.4,
  handles_route: 0.7,
  handles_tool: 0.7,
  method_overrides: 0.8,
  method_implements: 0.8,
  accesses: 0.5,
  member_of: 0.3,
  step_in_process: 0.5,
  entry_point_of: 0.7,
  queries: 0.6,
  fetches: 0.6,
}
const DEFAULT_EDGE_SIZE = 0.5

const HIERARCHY_EDGE_TYPES = new Set(["contains", "defines", "imports"])
const STRUCTURAL_TYPES = new Set([
  "project",
  "package",
  "module",
  "folder",
  "namespace",
])

// ── Layout helpers ────────────────────────────────────────────

function getNodeMass(kind: string, nodeCount: number): number {
  const m = nodeCount > 5000 ? 2 : nodeCount > 1000 ? 1.5 : 1
  switch (kind) {
    case "project":
      return 50 * m
    case "package":
      return 30 * m
    case "module":
      return 20 * m
    case "folder":
    case "namespace":
      return 15 * m
    case "class":
    case "interface":
      return 5 * m
    case "file":
      return 3 * m
    case "function":
    case "method":
      return 2 * m
    case "community":
    case "process":
      return 3 * m
    case "route":
    case "tool":
      return 3 * m
    case "model":
      return 3 * m
    case "property":
      return 1
    default:
      return 1
  }
}

function getScaledNodeSize(baseSize: number, nodeCount: number): number {
  if (nodeCount > 50000) return Math.max(1, baseSize * 0.4)
  if (nodeCount > 20000) return Math.max(1.5, baseSize * 0.5)
  if (nodeCount > 5000) return Math.max(2, baseSize * 0.65)
  if (nodeCount > 1000) return Math.max(2.5, baseSize * 0.8)
  return baseSize
}

function getFA2Settings(nodeCount: number) {
  const isSmall = nodeCount < 500
  const isMedium = nodeCount >= 500 && nodeCount < 2000
  const isLarge = nodeCount >= 2000 && nodeCount < 10000

  return {
    gravity: isSmall ? 0.8 : isMedium ? 0.5 : isLarge ? 0.3 : 0.15,
    scalingRatio: isSmall ? 15 : isMedium ? 30 : isLarge ? 60 : 100,
    slowDown: isSmall ? 1 : isMedium ? 2 : isLarge ? 3 : 5,
    barnesHutOptimize: nodeCount > 200,
    barnesHutTheta: isLarge ? 0.8 : 0.6,
    strongGravityMode: false,
    outboundAttractionDistribution: true,
    linLogMode: false,
    adjustSizes: true,
    edgeWeightInfluence: 1,
  }
}

function getLayoutDuration(nodeCount: number): number {
  if (nodeCount > 10000) return 45000
  if (nodeCount > 5000) return 35000
  if (nodeCount > 2000) return 30000
  if (nodeCount > 1000) return 30000
  if (nodeCount > 500) return 25000
  return 20000
}

const NOVERLAP_SETTINGS = {
  maxIterations: 20,
  settings: {
    ratio: 1.1,
    margin: 10,
    expansion: 1.05,
  },
}

// ── Manual layouts (tree / concentric) ────────────────────────
// No external layout libs beyond FA2 + noverlap; tree/circles positions
// are computed by BFS over the structural hierarchy.

const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5))

// Edges that flow outward from a structural root toward its members. Used to
// seed depth for both manual layouts; broader than HIERARCHY_EDGE_TYPES so a
// class's methods and a module's imports land on the next ring/band.
const STRUCTURAL_OUTWARD_EDGES = new Set([
  "contains",
  "defines",
  "has_method",
  "has_property",
  "imports",
])

// BFS depth from structural roots following outward edges. Nodes unreachable
// from any root (orphans) get the max-depth + 1 so they ring the outside.
function computeStructuralDepths(
  nodeIds: string[],
  edges: Array<{ source: string; target: string; type: string }>,
  rootIds: string[],
): Map<string, number> {
  const adjacency = new Map<string, string[]>()
  for (const e of edges) {
    if (!STRUCTURAL_OUTWARD_EDGES.has(e.type?.toLowerCase() ?? "")) continue
    if (!adjacency.has(e.source)) adjacency.set(e.source, [])
    adjacency.get(e.source)!.push(e.target)
  }

  const depth = new Map<string, number>()
  const queue: string[] = []
  for (const root of rootIds) {
    if (!depth.has(root)) {
      depth.set(root, 0)
      queue.push(root)
    }
  }

  let head = 0
  while (head < queue.length) {
    const current = queue[head++]!
    const d = depth.get(current)!
    for (const next of adjacency.get(current) ?? []) {
      if (!depth.has(next)) {
        depth.set(next, d + 1)
        queue.push(next)
      }
    }
  }

  let maxDepth = 0
  for (const d of depth.values()) if (d > maxDepth) maxDepth = d
  const orphanDepth = maxDepth + 1
  for (const id of nodeIds) {
    if (!depth.has(id)) depth.set(id, orphanDepth)
  }
  return depth
}

// Concentric rings by depth; ring radius grows linearly, within-ring spread by
// golden angle so successive nodes do not stack.
function assignConcentricLayout(
  graph: Graph,
  depth: Map<string, number>,
): void {
  const ringSpacing = Math.max(60, Math.sqrt(graph.order) * 12)
  const withinRingIndex = new Map<number, number>()

  graph.forEachNode((nodeId) => {
    const d = depth.get(nodeId) ?? 0
    const idx = withinRingIndex.get(d) ?? 0
    withinRingIndex.set(d, idx + 1)

    if (d === 0) {
      graph.setNodeAttribute(nodeId, "x", 0)
      graph.setNodeAttribute(nodeId, "y", 0)
      return
    }

    const radius = (d + 1) * ringSpacing
    const angle = idx * GOLDEN_ANGLE
    graph.setNodeAttribute(nodeId, "x", radius * Math.cos(angle))
    graph.setNodeAttribute(nodeId, "y", radius * Math.sin(angle))
  })
}

// Depth-banded tree: roots at the top, each depth a horizontal band, nodes
// within a band spread along x and centered around the origin.
function assignTreeLayout(graph: Graph, depth: Map<string, number>): void {
  const gap = Math.max(60, Math.sqrt(graph.order) * 12)

  const byDepth = new Map<number, string[]>()
  graph.forEachNode((nodeId) => {
    const d = depth.get(nodeId) ?? 0
    if (!byDepth.has(d)) byDepth.set(d, [])
    byDepth.get(d)!.push(nodeId)
  })

  for (const [d, ids] of byDepth) {
    const count = ids.length
    const offset = ((count - 1) * gap) / 2
    ids.forEach((nodeId, i) => {
      graph.setNodeAttribute(nodeId, "x", i * gap - offset)
      graph.setNodeAttribute(nodeId, "y", d * gap)
    })
  }
}

// ── Component ─────────────────────────────────────────────────

export type CodeGraphLayout = "force" | "tree" | "circles"

export type CodeGraphColorMode = "type" | "community"

export interface CodeGraphHandle {
  zoomIn: () => void
  zoomOut: () => void
  fitView: () => void
  focusNode: (id: string) => void
  clearSelection: () => void
  setLayoutRunning: (running: boolean) => void
  isLayoutRunning: () => boolean
}

interface CodeGraphRendererProps {
  nodes: Array<{
    id: string
    label: string
    kind?: string
    language?: string
    file_path?: string
  }>
  edges: Array<{ source: string; target: string; type: string }>
  selectedId: string | null
  onSelect: (
    node: {
      id: string
      label: string
      kind?: string
      file_path?: string
    } | null,
  ) => void
  highlightedIds?: Set<string>
  emphasisNodeIds?: Set<string>
  visibleEdgeTypes?: Set<string>
  nodeColors: Record<string, string>
  edgeColors: Record<string, string>
  tokens: GraphThemeTokens
  layout?: CodeGraphLayout
  colorMode?: CodeGraphColorMode
}

export const CodeGraphRenderer = forwardRef<
  CodeGraphHandle,
  CodeGraphRendererProps
>(function CodeGraphRenderer(
  {
    nodes,
    edges,
    selectedId,
    onSelect,
    highlightedIds,
    emphasisNodeIds,
    visibleEdgeTypes,
    nodeColors,
    edgeColors,
    tokens,
    layout = "force",
    colorMode = "type",
  },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null)
  const sigmaRef = useRef<Sigma | null>(null)
  const graphRef = useRef<Graph | null>(null)
  const fa2Ref = useRef<FA2Layout | null>(null)
  const layoutTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const selectedIdRef = useRef(selectedId)
  const hoveredNodeRef = useRef<string | null>(null)
  const highlightedIdsRef = useRef(highlightedIds)
  const emphasisNodeIdsRef = useRef(emphasisNodeIds)
  const visibleEdgeTypesRef = useRef(visibleEdgeTypes)
  const onSelectRef = useRef(onSelect)
  onSelectRef.current = onSelect
  const layoutRef = useRef(layout)
  layoutRef.current = layout
  // Tracks whether the FA2 worker is actively running, so play/pause and the
  // imperative handle report the real state rather than the last command.
  const layoutRunningRef = useRef(false)
  const edgesRef = useRef(edges)
  edgesRef.current = edges

  // Theme identity in the key forces a full rebuild — node/edge colors, the
  // dim base, labels, and hover/selection chrome are all baked at build time,
  // so they must recompute when the accent or mode flips.
  const themeKey = `${tokens.primary}:${tokens.background}:${tokens.isDark}`
  const graphKey = `${nodes.length}:${edges.length}:${nodes[0]?.id ?? ""}:${nodes[nodes.length - 1]?.id ?? ""}:${themeKey}:${colorMode}`

  const buildGraph = useCallback(() => {
    if (!containerRef.current) return

    if (layoutTimeoutRef.current) {
      clearTimeout(layoutTimeoutRef.current)
      layoutTimeoutRef.current = null
    }
    if (fa2Ref.current) {
      fa2Ref.current.kill()
      fa2Ref.current = null
    }
    if (sigmaRef.current) {
      sigmaRef.current.kill()
      sigmaRef.current = null
      graphRef.current = null
    }

    const graph = new Graph()
    graphRef.current = graph

    const defaultNodeColor = tokens.mutedForeground
    const defaultEdgeColor = dimColor(tokens.border, 0.6, tokens.background)
    const bg = tokens.background

    const nodeCount = nodes.length

    // ── Community membership map (community mode) ─────────────
    // Each `member_of` edge points a member symbol at its community node, so
    // the source resolves to a community id and the community node itself is
    // keyed on its own id. Members with no edge fall back to mutedForeground.
    const nodeToCommunity = new Map<string, string>()
    if (colorMode === "community") {
      const communityIds = new Set(
        nodes
          .filter((n) => n.kind?.toLowerCase() === "community")
          .map((n) => n.id),
      )
      for (const e of edges) {
        if ((e.type?.toLowerCase() ?? "") !== "member_of") continue
        if (communityIds.has(e.target)) nodeToCommunity.set(e.source, e.target)
      }
    }

    const colorForNode = (node: {
      id: string
      kind?: string
    }): string => {
      const kind = node.kind?.toLowerCase() ?? ""
      if (colorMode === "community") {
        if (kind === "community") return communityColor(node.id, tokens)
        const communityId = nodeToCommunity.get(node.id)
        return communityId !== undefined
          ? communityColor(communityId, tokens)
          : defaultNodeColor
      }
      return nodeColors[kind] ?? defaultNodeColor
    }
    const edgeBaseSize = nodeCount > 20000 ? 0.4 : nodeCount > 5000 ? 0.6 : 1.0

    // ── Build parent-child hierarchy from edges ───────────────
    const parentToChildren = new Map<string, string[]>()
    const childToParent = new Map<string, string>()

    for (const e of edges) {
      const edgeType = e.type?.toLowerCase() ?? ""
      if (HIERARCHY_EDGE_TYPES.has(edgeType)) {
        if (!parentToChildren.has(e.source)) parentToChildren.set(e.source, [])
        parentToChildren.get(e.source)!.push(e.target)
        childToParent.set(e.target, e.source)
      }
    }

    const nodeMap = new Map(nodes.map((n) => [n.id, n]))
    const structuralNodes = nodes.filter((n) =>
      STRUCTURAL_TYPES.has(n.kind?.toLowerCase() ?? ""),
    )
    const structuralSpread = Math.sqrt(nodeCount) * 40
    const childJitter = Math.sqrt(nodeCount) * 3

    // ── Position structural nodes in golden-angle spiral ──────
    const goldenAngle = Math.PI * (3 - Math.sqrt(5))
    const nodePositions = new Map<string, { x: number; y: number }>()

    structuralNodes.forEach((node, index) => {
      const angle = index * goldenAngle
      const radius =
        structuralSpread *
        Math.sqrt((index + 1) / Math.max(structuralNodes.length, 1))
      const jitter = structuralSpread * 0.15
      const x = radius * Math.cos(angle) + (seededUnit(node.id, 0) - 0.5) * jitter
      const y = radius * Math.sin(angle) + (seededUnit(node.id, 1) - 0.5) * jitter
      nodePositions.set(node.id, { x, y })
    })

    // ── BFS to position children near parents ─────────────────
    const addNode = (nodeId: string) => {
      if (graph.hasNode(nodeId)) return
      const node = nodeMap.get(nodeId)
      if (!node) return

      let x: number, y: number
      const parentId = childToParent.get(nodeId)
      const parentPos = parentId ? nodePositions.get(parentId) : null

      if (parentPos) {
        x = parentPos.x + (seededUnit(nodeId, 0) - 0.5) * childJitter
        y = parentPos.y + (seededUnit(nodeId, 1) - 0.5) * childJitter
      } else {
        x = (seededUnit(nodeId, 0) - 0.5) * structuralSpread * 0.5
        y = (seededUnit(nodeId, 1) - 0.5) * structuralSpread * 0.5
      }

      nodePositions.set(nodeId, { x, y })

      const kind = node.kind?.toLowerCase() ?? ""
      const baseSize = NODE_SIZES[kind] ?? DEFAULT_NODE_SIZE
      const size = getScaledNodeSize(baseSize, nodeCount)

      graph.addNode(nodeId, {
        x,
        y,
        label: node.label,
        size,
        color: colorForNode(node),
        mass: getNodeMass(kind, nodeCount),
        _kind: node.kind,
        _filePath: node.file_path,
        _baseSize: size,
      })
    }

    // Add structural nodes first
    for (const node of structuralNodes) {
      if (graph.hasNode(node.id)) continue
      const kind = node.kind?.toLowerCase() ?? ""
      const baseSize = NODE_SIZES[kind] ?? DEFAULT_NODE_SIZE
      const size = getScaledNodeSize(baseSize, nodeCount)
      const pos = nodePositions.get(node.id)!

      graph.addNode(node.id, {
        x: pos.x,
        y: pos.y,
        label: node.label,
        size,
        color: colorForNode(node),
        mass: getNodeMass(kind, nodeCount),
        _kind: node.kind,
        _filePath: node.file_path,
        _baseSize: size,
      })
    }

    // BFS from structural nodes
    const queue = [...structuralNodes.map((n) => n.id)]
    const visited = new Set(queue)

    while (queue.length > 0) {
      const currentId = queue.shift()!
      const children = parentToChildren.get(currentId) || []
      for (const childId of children) {
        if (!visited.has(childId)) {
          visited.add(childId)
          addNode(childId)
          queue.push(childId)
        }
      }
    }

    // Orphan nodes
    for (const node of nodes) {
      if (!graph.hasNode(node.id)) {
        addNode(node.id)
      }
    }

    // ── Add edges ─────────────────────────────────────────────
    for (const e of edges) {
      if (!graph.hasNode(e.source) || !graph.hasNode(e.target)) continue
      try {
        const edgeType = e.type?.toLowerCase() ?? ""
        graph.addEdge(e.source, e.target, {
          color: edgeColors[edgeType] || defaultEdgeColor,
          size:
            edgeBaseSize *
            (EDGE_SIZE_MULTIPLIERS[edgeType] || DEFAULT_EDGE_SIZE),
          type: "curve",
          curvature: 0.12 + seededUnit(`${e.source}->${e.target}`, 2) * 0.08,
          _relType: edgeType,
        })
      } catch {
        /* duplicate edge */
      }
    }

    indexParallelEdgesIndex(graph, {
      edgeIndexAttribute: "parallelIndex",
      edgeMaxIndexAttribute: "parallelMaxIndex",
    })

    // ── Sigma instance ────────────────────────────────────────
    const sigma = new Sigma(graph, containerRef.current, {
      allowInvalidContainer: true,
      renderLabels: true,
      renderEdgeLabels: false,
      labelSize: 11,
      labelWeight: "500",
      labelFont: tokens.fontMono,
      labelColor: { color: tokens.foreground },
      labelRenderedSizeThreshold: 8,
      labelDensity: 0.1,
      labelGridCellSize: 70,
      defaultEdgeType: "curve",
      edgeProgramClasses: { curve: EdgeCurveProgram },
      stagePadding: 60,
      defaultNodeColor: defaultNodeColor,
      defaultEdgeColor: defaultEdgeColor,
      minCameraRatio: 0.002,
      maxCameraRatio: 50,
      hideEdgesOnMove: true,
      zIndex: true,

      // Custom hover: dark pill label + glow ring (matching GitNexus)
      defaultDrawNodeHover: (context, data, settings) => {
        const label = data.label
        if (!label) return

        const size = settings.labelSize || 11
        const font = settings.labelFont || tokens.fontMono
        const weight = settings.labelWeight || "500"

        context.font = `${weight} ${size}px ${font}`
        const textWidth = context.measureText(label).width

        const nodeSize = data.size || 8
        const x = data.x
        const y = data.y - nodeSize - 10
        const paddingX = 8
        const paddingY = 5
        const height = size + paddingY * 2
        const width = textWidth + paddingX * 2
        const radius = 4

        context.fillStyle = tokens.popover
        context.beginPath()
        context.roundRect(x - width / 2, y - height / 2, width, height, radius)
        context.fill()

        context.strokeStyle = data.color || tokens.primary
        context.lineWidth = 2
        context.stroke()

        context.fillStyle = tokens.popoverForeground
        context.textAlign = "center"
        context.textBaseline = "middle"
        context.fillText(label, x, y)

        context.beginPath()
        context.arc(data.x, data.y, nodeSize + 4, 0, Math.PI * 2)
        context.strokeStyle = data.color || tokens.primary
        context.lineWidth = 2
        context.globalAlpha = 0.5
        context.stroke()
        context.globalAlpha = 1
      },

      nodeReducer(node, data) {
        const res = { ...data }
        const baseSize = (data._baseSize as number) || DEFAULT_NODE_SIZE
        const hl = highlightedIdsRef.current
        const hasHighlights = hl && hl.size > 0
        const emph = emphasisNodeIdsRef.current
        const hasEmphasis = emph && emph.size > 0
        const sel = selectedIdRef.current
        const hov = hoveredNodeRef.current

        if (hasHighlights && !sel) {
          if (hl.has(node)) {
            res.color = tokens.destructive
            res.size = baseSize * 1.8
            res.zIndex = 3
            res.highlighted = true
          } else {
            res.color = dimColor(data.color || defaultNodeColor, 0.15, bg)
            res.size = baseSize * 0.4
            res.zIndex = 0
          }
          return res
        }

        // Process emphasis: ring the flow's nodes in --primary and dim the rest.
        // Kept independent of the destructive blast-radius branch above so the
        // two highlight modes never bleed into each other.
        if (hasEmphasis && !sel) {
          if (emph.has(node)) {
            res.color = tokens.primary
            res.size = baseSize * 1.6
            res.zIndex = 3
            res.highlighted = true
          } else {
            res.color = dimColor(data.color || defaultNodeColor, 0.18, bg)
            res.size = baseSize * 0.45
            res.zIndex = 0
          }
          return res
        }

        if (sel) {
          const isSelected = node === sel
          const isNeighbor =
            graph.hasEdge(node, sel) || graph.hasEdge(sel, node)

          if (isSelected) {
            res.color = data.color
            res.size = baseSize * 1.8
            res.zIndex = 2
            res.highlighted = true
          } else if (isNeighbor) {
            res.color = data.color
            res.size = baseSize * 1.3
            res.zIndex = 1
          } else {
            res.color = dimColor(data.color || defaultNodeColor, 0.25, bg)
            res.size = baseSize * 0.6
            res.zIndex = 0
          }
          return res
        }

        if (hov === node) {
          res.color = brightenColor(data.color || defaultNodeColor, 1.5)
          res.size = baseSize * 1.4
          res.zIndex = 2
          res.highlighted = true
        } else if (hov) {
          const isHovNeighbor =
            graph.hasEdge(hov, node) || graph.hasEdge(node, hov)
          if (isHovNeighbor) {
            res.color = data.color
            res.size = baseSize * 1.2
            res.zIndex = 1
          }
        }

        return res
      },

      edgeReducer(edge, data) {
        const res = { ...data }
        const edgeType =
          (graph.getEdgeAttribute(edge, "_relType") as string) || ""

        if (
          visibleEdgeTypesRef.current &&
          !visibleEdgeTypesRef.current.has(edgeType)
        ) {
          res.hidden = true
          return res
        }

        const hl = highlightedIdsRef.current
        const hasHighlights = hl && hl.size > 0
        const emph = emphasisNodeIdsRef.current
        const hasEmphasis = emph && emph.size > 0
        const sel = selectedIdRef.current
        const hov = hoveredNodeRef.current
        const [src, tgt] = graph.extremities(edge)

        if (hasHighlights && !sel) {
          const srcActive = hl.has(src)
          const tgtActive = hl.has(tgt)

          if (srcActive && tgtActive) {
            res.color = tokens.destructive
            res.size = Math.max(2, (data.size || 1) * 3)
            res.zIndex = 2
          } else if (srcActive || tgtActive) {
            res.color = dimColor(tokens.primary, 0.4, bg)
            res.size = 1
            res.zIndex = 1
          } else {
            res.color = dimColor(data.color || defaultEdgeColor, 0.08, bg)
            res.size = 0.2
            res.zIndex = 0
          }
          return res
        }

        if (hasEmphasis && !sel) {
          const srcActive = emph.has(src)
          const tgtActive = emph.has(tgt)

          if (srcActive && tgtActive) {
            res.color = tokens.primary
            res.size = Math.max(2, (data.size || 1) * 3)
            res.zIndex = 2
          } else if (srcActive || tgtActive) {
            res.color = dimColor(tokens.primary, 0.4, bg)
            res.size = 1
            res.zIndex = 1
          } else {
            res.color = dimColor(data.color || defaultEdgeColor, 0.08, bg)
            res.size = 0.2
            res.zIndex = 0
          }
          return res
        }

        if (sel) {
          const isConnected = src === sel || tgt === sel
          if (isConnected) {
            res.color = brightenColor(data.color || defaultEdgeColor, 1.5)
            res.size = Math.max(3, (data.size || 1) * 4)
            res.zIndex = 2
          } else {
            res.color = dimColor(data.color || defaultEdgeColor, 0.1, bg)
            res.size = 0.3
            res.zIndex = 0
          }
          return res
        }

        if (hov && (src === hov || tgt === hov)) {
          res.size = (data.size || DEFAULT_EDGE_SIZE) * 2
          const neighborNode = src === hov ? tgt : src
          res.color = brightenColor(
            (graph.getNodeAttribute(neighborNode, "color") as string) ||
              defaultNodeColor,
            1.3,
          )
        }

        return res
      },
    })

    sigma.on("enterNode", ({ node }) => {
      hoveredNodeRef.current = node
      if (containerRef.current) containerRef.current.style.cursor = "pointer"
      sigma.refresh()
    })
    sigma.on("leaveNode", () => {
      hoveredNodeRef.current = null
      if (containerRef.current) containerRef.current.style.cursor = "grab"
      sigma.refresh()
    })
    sigma.on("clickNode", ({ node }) => {
      const attrs = graph.getNodeAttributes(node)
      onSelectRef.current({
        id: node,
        label: attrs.label as string,
        kind: attrs._kind as string | undefined,
        file_path: attrs._filePath as string | undefined,
      })

      const nodePosition = sigma.getNodeDisplayData(node)
      if (nodePosition) {
        sigma
          .getCamera()
          .animate(
            { x: nodePosition.x, y: nodePosition.y, ratio: 0.15 },
            { duration: 400 },
          )
      }
    })
    sigma.on("clickStage", () => onSelectRef.current(null))

    sigmaRef.current = sigma

    // The FA2 worker is always instantiated so play/pause can resume it, but it
    // only auto-starts for the force layout. Tree/circles get manual positions
    // applied by the layout effect that runs right after this build.
    const fa2Settings = getFA2Settings(nodeCount)
    const fa2 = new FA2Layout(graph, {
      settings: { ...inferSettings(graph), ...fa2Settings },
    })
    fa2Ref.current = fa2

    if (layoutRef.current !== "force") {
      layoutRunningRef.current = false
      // Apply manual positions now so a rebuild (data/filter/theme change) while
      // tree/circles is active keeps the chosen layout instead of the FA2 seed.
      const rootIds = graph.filterNodes((_, attrs) =>
        STRUCTURAL_TYPES.has((attrs._kind as string)?.toLowerCase() ?? ""),
      )
      const depth = computeStructuralDepths(graph.nodes(), edges, rootIds)
      if (layoutRef.current === "circles") assignConcentricLayout(graph, depth)
      else assignTreeLayout(graph, depth)
      sigma.refresh()
      return
    }

    fa2.start()
    layoutRunningRef.current = true

    const duration = getLayoutDuration(nodeCount)

    layoutTimeoutRef.current = setTimeout(() => {
      if (fa2Ref.current) {
        fa2Ref.current.stop()
      }
      layoutRunningRef.current = false
      if (!graphRef.current || !sigmaRef.current) return

      noverlap.assign(graphRef.current, NOVERLAP_SETTINGS)
      sigmaRef.current.refresh()
    }, duration)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graphKey])

  useEffect(() => {
    const frame = requestAnimationFrame(() => buildGraph())
    return () => {
      cancelAnimationFrame(frame)
      if (layoutTimeoutRef.current) {
        clearTimeout(layoutTimeoutRef.current)
        layoutTimeoutRef.current = null
      }
      if (fa2Ref.current) {
        fa2Ref.current.kill()
        fa2Ref.current = null
      }
      if (sigmaRef.current) {
        sigmaRef.current.kill()
        sigmaRef.current = null
        graphRef.current = null
      }
    }
  }, [buildGraph])

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver(() => sigmaRef.current?.refresh())
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    selectedIdRef.current = selectedId

    const sigma = sigmaRef.current
    if (!sigma) return

    // Camera nudge to force edge re-render (Sigma edge caching workaround).
    // Only nudge on an actual selection; deselect just needs a plain refresh so
    // the camera does not drift when the user clicks empty stage.
    if (selectedId) {
      const camera = sigma.getCamera()
      camera.animate({ ratio: camera.ratio * 1.0001 }, { duration: 50 })
    }
    sigma.refresh()

    if (selectedId && graphRef.current?.hasNode(selectedId)) {
      const nodePosition = sigma.getNodeDisplayData(selectedId)
      if (nodePosition) {
        sigma
          .getCamera()
          .animate(
            { x: nodePosition.x, y: nodePosition.y, ratio: 0.15 },
            { duration: 400 },
          )
      }
    }
  }, [selectedId])

  useEffect(() => {
    highlightedIdsRef.current = highlightedIds
    sigmaRef.current?.refresh()
  }, [highlightedIds])

  useEffect(() => {
    emphasisNodeIdsRef.current = emphasisNodeIds
    sigmaRef.current?.refresh()
  }, [emphasisNodeIds])

  useEffect(() => {
    visibleEdgeTypesRef.current = visibleEdgeTypes
    sigmaRef.current?.refresh()
  }, [visibleEdgeTypes])

  const fitView = useCallback(() => {
    sigmaRef.current?.getCamera().animatedReset({ duration: 400 })
  }, [])

  // Re-layout on switch (or after a rebuild) without touching graph data, node
  // sizes, or colors — only x/y are reassigned. Force restarts the FA2 worker;
  // tree/circles stop it and apply manual positions, then fit the camera.
  useEffect(() => {
    const sigma = sigmaRef.current
    const graph = graphRef.current
    if (!sigma || !graph) return

    if (layout === "force") {
      if (layoutTimeoutRef.current) {
        clearTimeout(layoutTimeoutRef.current)
        layoutTimeoutRef.current = null
      }
      if (fa2Ref.current && !layoutRunningRef.current) {
        fa2Ref.current.start()
        layoutRunningRef.current = true
      }
      return
    }

    if (layoutTimeoutRef.current) {
      clearTimeout(layoutTimeoutRef.current)
      layoutTimeoutRef.current = null
    }
    if (fa2Ref.current) {
      fa2Ref.current.stop()
    }
    layoutRunningRef.current = false

    const rootIds = graph.filterNodes((_, attrs) =>
      STRUCTURAL_TYPES.has((attrs._kind as string)?.toLowerCase() ?? ""),
    )
    const depth = computeStructuralDepths(graph.nodes(), edgesRef.current, rootIds)

    if (layout === "circles") assignConcentricLayout(graph, depth)
    else assignTreeLayout(graph, depth)

    sigma.refresh()
    fitView()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layout, graphKey, fitView])

  useImperativeHandle(
    ref,
    (): CodeGraphHandle => ({
      zoomIn: () => sigmaRef.current?.getCamera().animatedZoom({ duration: 200 }),
      zoomOut: () =>
        sigmaRef.current?.getCamera().animatedUnzoom({ duration: 200 }),
      fitView,
      focusNode: (id: string) => {
        const sigma = sigmaRef.current
        if (!sigma || !graphRef.current?.hasNode(id)) return
        const pos = sigma.getNodeDisplayData(id)
        if (pos) {
          sigma
            .getCamera()
            .animate({ x: pos.x, y: pos.y, ratio: 0.15 }, { duration: 400 })
        }
      },
      clearSelection: () => onSelectRef.current(null),
      setLayoutRunning: (running: boolean) => {
        const fa2 = fa2Ref.current
        if (!fa2 || layoutRef.current !== "force") return
        if (running && !layoutRunningRef.current) {
          if (layoutTimeoutRef.current) {
            clearTimeout(layoutTimeoutRef.current)
            layoutTimeoutRef.current = null
          }
          fa2.start()
          layoutRunningRef.current = true
        } else if (!running && layoutRunningRef.current) {
          fa2.stop()
          layoutRunningRef.current = false
        }
      },
      isLayoutRunning: () => layoutRunningRef.current,
    }),
    [fitView],
  )

  return (
    <div
      ref={containerRef}
      className="absolute inset-0 bg-background"
      style={{ cursor: "grab" }}
    />
  )
})
