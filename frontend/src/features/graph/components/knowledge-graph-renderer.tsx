import { useRef, useEffect, useCallback } from "react"
import Graph from "graphology"
import Sigma from "sigma"
import {
  EdgeCurvedArrowProgram,
  indexParallelEdgesIndex,
  createDrawCurvedEdgeLabel,
  DEFAULT_EDGE_CURVE_PROGRAM_OPTIONS,
} from "@sigma/edge-curve"
import { DEFAULT_EDGE_ARROW_HEAD_PROGRAM_OPTIONS } from "sigma/rendering"
import { drawThemedDiscNodeHover } from "@/features/graph/lib/node-hover"
import type { ChromeKind } from "@/features/graph/lib/node-hover"
import type { NodeDisplayData } from "sigma/types"
import {
  focusTier,
  groundEdgeAlpha,
  groundNodeAlpha,
  labelVisible,
} from "@/features/graph/lib/focus-model"
import { useGraphPrefs } from "@/features/graph/lib/graph-prefs"
import FA2Layout from "graphology-layout-forceatlas2/worker"
import { inferSettings } from "graphology-layout-forceatlas2"
import {
  entityTypeColor,
  hexToRgba,
  darkenHex,
  membershipEdgeColor,
} from "@/features/graph/lib/graph-colors"
import { seededUnit } from "@/features/graph/lib/code-graph-theme"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"

export interface KGSelection {
  kind: "node" | "edge"
  id: string
  label: string
  type: string
  weight?: number
  source?: string
  target?: string
}

interface KnowledgeGraphRendererProps {
  entities: Array<{ id?: string; name: string; entity_type: string }>
  relations: Array<{
    source: string
    target: string
    type?: string
    weight?: number
  }>
  selectedId: string | null
  onSelect: (selected: KGSelection | null) => void
}

const FOCUS_SCALE = 1.22
const HOVER_SCALE = 1.08
const HUB_DEGREE = 5
const LABEL_ZOOM_RATIO = 0.72
const FOCUS_EDGE_SIZE = 2.2

/** Relation over similarity over membership — the same hierarchy the memory
 *  graph draws, so one corpus does not read two ways across two views. */
function edgeWeight(kind: unknown): number {
  if (kind === "relation") return 1.8
  if (kind === "membership") return 1
  return 1.1
}

export function KnowledgeGraphRenderer({
  entities,
  relations,
  selectedId,
  onSelect,
}: KnowledgeGraphRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const sigmaRef = useRef<Sigma | null>(null)
  const graphRef = useRef<Graph | null>(null)
  const fa2Ref = useRef<FA2Layout | null>(null)
  const fa2StopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const selectedIdRef = useRef(selectedId)
  const hoveredNodeRef = useRef<string | null>(null)

  const { tokens, palette } = useMemoryGraphTheme()
  const tokensRef = useRef(tokens)
  tokensRef.current = tokens

  const selectionTreatment = useGraphPrefs((s) => s.selectionTreatment)
  const dimUnrelated = useGraphPrefs((s) => s.dimUnrelated)
  const prefsRef = useRef({ selectionTreatment, dimUnrelated })
  prefsRef.current = { selectionTreatment, dimUnrelated }

  // Sigma's camera ratio counts down as you move in.
  const zoomRatioRef = useRef(1)
  const paletteRef = useRef(palette)
  paletteRef.current = palette

  const buildGraph = useCallback(() => {
    if (!containerRef.current) return

    if (fa2Ref.current) {
      fa2Ref.current.kill()
      fa2Ref.current = null
    }
    if (sigmaRef.current) {
      sigmaRef.current.kill()
      sigmaRef.current = null
      graphRef.current = null
    }

    const t = tokensRef.current

    const graph = new Graph()
    graphRef.current = graph

    for (const e of entities) {
      const nodeId = e.id || e.name
      if (graph.hasNode(nodeId)) continue
      const color = entityTypeColor(e.entity_type, paletteRef.current)
      graph.addNode(nodeId, {
        x: (seededUnit(nodeId, 0) - 0.5) * 10,
        y: (seededUnit(nodeId, 1) - 0.5) * 10,
        label: e.name,
        size: 14,
        color,
        borderColor: darkenHex(color),
        _entityType: e.entity_type,
      })
    }

    for (const r of relations) {
      if (!graph.hasNode(r.source) || !graph.hasNode(r.target)) continue
      try {
        graph.addEdge(r.source, r.target, {
          color: membershipEdgeColor(tokensRef.current),
          size: 1.5,
          label: r.type || "",
          _weight: r.weight ?? 0.5,
          _edgeKind: "membership",
        })
      } catch {
        /* duplicate edge */
      }
    }

    indexParallelEdgesIndex(graph, {
      edgeIndexAttribute: "parallelIndex",
      edgeMaxIndexAttribute: "parallelMaxIndex",
    })

    const sigma = new Sigma(graph, containerRef.current, {
      antiAliasingFeather: 2,
      renderLabels: true,
      renderEdgeLabels: true,
      labelSize: 12,
      labelColor: { color: t.foreground },
      labelFont: "Inter, sans-serif",
      edgeLabelSize: 10,
      edgeLabelColor: { color: t.mutedForeground },
      defaultEdgeType: "curvedArrow",
      edgeProgramClasses: { curvedArrow: EdgeCurvedArrowProgram },
      defaultDrawEdgeLabel: createDrawCurvedEdgeLabel({
        ...DEFAULT_EDGE_CURVE_PROGRAM_OPTIONS,
        arrowHead: DEFAULT_EDGE_ARROW_HEAD_PROGRAM_OPTIONS,
      }),
      defaultDrawNodeHover: (context, data, settings) => {
        const kind =
          (data as { _chromeKind?: ChromeKind })._chromeKind ?? "hover"
        drawThemedDiscNodeHover(
          context,
          data,
          settings,
          tokensRef.current,
          prefsRef.current.selectionTreatment,
          kind,
        )
      },
      stagePadding: 40,
      labelRenderedSizeThreshold: 6,
      defaultNodeColor: t.mutedForeground,
      nodeReducer(node, data) {
        const tk = tokensRef.current
        const { dimUnrelated } = prefsRef.current
        const res: Partial<NodeDisplayData> & { _chromeKind?: ChromeKind } = {
          ...data,
        }
        const hov = hoveredNodeRef.current
        const sel = selectedIdRef.current
        const isNeighbour =
          !!sel && (graph.hasEdge(sel, node) || graph.hasEdge(node, sel))
        const tier = focusTier(node, sel, isNeighbour)

        if (tier === "focus") {
          res.size = (data.size || 14) * FOCUS_SCALE
          res.highlighted = true
          res._chromeKind = "focus"
        } else if (hov === node) {
          res.size = (data.size || 14) * HOVER_SCALE
          res.highlighted = true
          res._chromeKind = "hover"
        }

        if (tier === "ground") {
          res.color = hexToRgba(
            data.color || tk.mutedForeground,
            groundNodeAlpha(dimUnrelated),
          )
        }

        if (
          !labelVisible({
            tier,
            isHub: (data._degree ?? 0) >= HUB_DEGREE,
            zoomedIn: zoomRatioRef.current < LABEL_ZOOM_RATIO,
            isHovered: hov === node,
          })
        ) {
          res.label = ""
        }

        return res
      },
      edgeReducer(edge, data) {
        const tk = tokensRef.current
        const { dimUnrelated } = prefsRef.current
        const res = { ...data }
        const hov = hoveredNodeRef.current
        const sel = selectedIdRef.current
        const src = graph.source(edge)
        const tgt = graph.target(edge)

        res.size = edgeWeight(data._edgeKind)

        if (sel) {
          if (src === sel || tgt === sel) {
            res.size = FOCUS_EDGE_SIZE
            res.color = tk.primary
          } else {
            res.color = hexToRgba(tk.border, groundEdgeAlpha(dimUnrelated))
          }
        }

        if (hov && (src === hov || tgt === hov)) {
          res.size = FOCUS_EDGE_SIZE
          res.color = tk.primary
        }

        return res
      },
    })

    zoomRatioRef.current = sigma.getCamera().ratio
    sigma.getCamera().on("updated", () => {
      const next = sigma.getCamera().ratio
      const crossed =
        next < LABEL_ZOOM_RATIO !== zoomRatioRef.current < LABEL_ZOOM_RATIO
      zoomRatioRef.current = next
      if (crossed) sigma.refresh()
    })

    sigma.on("enterNode", ({ node }) => {
      hoveredNodeRef.current = node
      containerRef.current!.style.cursor = "pointer"
      sigma.refresh()
    })
    sigma.on("leaveNode", () => {
      hoveredNodeRef.current = null
      containerRef.current!.style.cursor = "default"
      sigma.refresh()
    })
    sigma.on("clickNode", ({ node }) => {
      const attrs = graph.getNodeAttributes(node)
      onSelect({
        kind: "node",
        id: node,
        label: attrs.label as string,
        type: attrs._entityType as string,
      })
    })
    sigma.on("clickStage", () => onSelect(null))

    sigmaRef.current = sigma

    const fa2 = new FA2Layout(graph, {
      settings: {
        ...inferSettings(graph),
        linLogMode: true,
        outboundAttractionDistribution: false,
        strongGravityMode: true,
        gravity: 1,
        slowDown: 12,
      },
    })
    fa2Ref.current = fa2
    fa2.start()
    fa2StopTimerRef.current = setTimeout(() => {
      fa2StopTimerRef.current = null
      if (fa2Ref.current) fa2Ref.current.stop()
    }, 5000)
  }, [entities, relations, onSelect])

  useEffect(() => {
    const frame = requestAnimationFrame(() => buildGraph())
    return () => {
      cancelAnimationFrame(frame)
      if (fa2StopTimerRef.current) {
        clearTimeout(fa2StopTimerRef.current)
        fa2StopTimerRef.current = null
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
    sigmaRef.current?.refresh()
  }, [selectedId])

  useEffect(() => {
    const sigma = sigmaRef.current
    const graph = graphRef.current
    if (!sigma || !graph) return

    graph.forEachNode((id, attrs) => {
      const color = entityTypeColor(
        attrs._entityType as string,
        paletteRef.current,
      )
      graph.mergeNodeAttributes(id, { color, borderColor: darkenHex(color) })
    })
    graph.forEachEdge((edge) => {
      graph.setEdgeAttribute(
        edge,
        "color",
        membershipEdgeColor(tokensRef.current),
      )
    })
    sigma.setSetting("labelColor", { color: tokensRef.current.foreground })
    sigma.setSetting("edgeLabelColor", {
      color: tokensRef.current.mutedForeground,
    })
    sigma.setSetting("defaultNodeColor", tokensRef.current.mutedForeground)
    sigma.refresh()
    // Keyed on a primitive theme signature so incidental re-renders don't recolor.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [`${tokens.background}:${tokens.isDark}:${tokens.primary}:${tokens.border}`])

  return <div ref={containerRef} className="absolute inset-0" />
}
