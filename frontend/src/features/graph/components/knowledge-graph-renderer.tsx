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
import FA2Layout from "graphology-layout-forceatlas2/worker"
import { inferSettings } from "graphology-layout-forceatlas2"
import {
  entityTypeColor,
  lightenHex,
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
      defaultDrawNodeHover: (context, data, settings) =>
        drawThemedDiscNodeHover(context, data, settings, tokensRef.current),
      stagePadding: 40,
      labelRenderedSizeThreshold: 6,
      defaultNodeColor: t.mutedForeground,
      nodeReducer(node, data) {
        const tk = tokensRef.current
        const res = { ...data }
        const hov = hoveredNodeRef.current
        const sel = selectedIdRef.current
        if (hov === node) {
          res.color = lightenHex(data.color || tk.mutedForeground, 0.4)
          res.size = (data.size || 14) * 1.4
          res.highlighted = true
        } else if (sel === node) {
          res.color = lightenHex(data.color || tk.mutedForeground, 0.4)
          res.size = (data.size || 14) * 1.4
          res.highlighted = true
          res.borderColor = tk.foreground
          res.borderSize = 3
        } else if (sel && sel !== node) {
          const isNeighbor =
            graph.hasEdge(sel, node) || graph.hasEdge(node, sel)
          if (!isNeighbor) {
            res.color = tk.border
            res.label = ""
          }
        }
        return res
      },
      edgeReducer(edge, data) {
        const tk = tokensRef.current
        const res = { ...data }
        const hov = hoveredNodeRef.current
        const sel = selectedIdRef.current
        const src = graph.source(edge)
        const tgt = graph.target(edge)

        if (sel) {
          if (src === sel || tgt === sel) {
            res.size = (data.size || 1.5) * 2
            const neighborColor =
              graph.getNodeAttribute(src === sel ? tgt : src, "color") ||
              tk.mutedForeground
            res.color = lightenHex(neighborColor, 0.3)
          } else {
            res.color = tk.border
            res.size = (data.size || 1.5) * 0.5
          }
        }

        if (hov && (src === hov || tgt === hov)) {
          res.size = (data.size || 1.5) * 2
          const neighborColor =
            graph.getNodeAttribute(src === hov ? tgt : src, "color") ||
            tk.mutedForeground
          res.color = lightenHex(neighborColor, 0.3)
        }

        return res
      },
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
