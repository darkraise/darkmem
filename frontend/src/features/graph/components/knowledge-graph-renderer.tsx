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
import { drawNodeLabel, drawThemedDiscNodeHover } from "@/features/graph/lib/node-hover"
import type { ChromeKind } from "@/features/graph/lib/node-hover"
import type { NodeDisplayData } from "sigma/types"
import {
  focusTier,
  groundEdgeAlpha,
  groundNodeAlpha,
  hoverGroundAlpha,
  labelVisible,
  recede,
} from "@/features/graph/lib/focus-model"
import { useGraphPrefs } from "@/features/graph/lib/graph-prefs"
import FA2Layout from "graphology-layout-forceatlas2/worker"
import { inferSettings } from "graphology-layout-forceatlas2"
import { NodeCircleBorderedProgram } from "@/features/graph/lib/node-circle-bordered-program"
import {
  entityTypeColor,
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
/** A connected edge must be unmistakably heavier than its neighbours -- that
 *  emphasis is most of what makes a selection legible. Both are scaled off
 *  each kind's own weight so the relation/similarity/membership hierarchy
 *  survives the emphasis, and hovering stays lighter than selecting so the
 *  two remain distinguishable while a selection is held. */
/** Emphasis is a flat width, not a per-kind multiple. Scaling each kind by
 *  the same factor made connected relation edges visibly heavier than
 *  connected similarity ones, which reads as "some of these matter more"
 *  rather than as one highlight. The hierarchy still holds at rest. */
const HOVER_EDGE_SIZE = 4.5
const SELECTED_EDGE_SIZE = 6.5

/** Relation over similarity over membership — the same hierarchy the memory
 *  graph draws, so one corpus does not read two ways across two views. */
/** Entities are the subject here, so a typed relation outranks everything --
 *  the opposite of the memory graph, whose subject is its memories. The two
 *  orders are deliberately different; do not "unify" them. */
function edgeWeight(kind: unknown): number {
  if (kind === "relation") return 3.4
  if (kind === "membership") return 2.2
  return 2.8
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

  const selectionColor = useGraphPrefs((s) => s.selectionColor)
  const dimUnrelated = useGraphPrefs((s) => s.dimUnrelated)
  const prefsRef = useRef({ selectionColor, dimUnrelated })
  prefsRef.current = { selectionColor, dimUnrelated }

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
      const borderColor = entityTypeColor(e.entity_type, paletteRef.current)
      graph.addNode(nodeId, {
        x: (seededUnit(nodeId, 0) - 0.5) * 10,
        y: (seededUnit(nodeId, 1) - 0.5) * 10,
        label: e.name,
        size: 14,
        color: paletteRef.current.entityFill,
        borderColor,
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
      // Per-node so a grounded label can recede with its node; sigma's
      // label renderer reads this attribute and falls back to `color`.
      labelColor: { attribute: "labelColor", color: t.foreground },
      labelFont: "Inter, sans-serif",
      edgeLabelSize: 10,
      edgeLabelColor: { color: t.mutedForeground },
      defaultEdgeType: "curvedArrow",
      defaultNodeType: "bordered",
      nodeProgramClasses: { bordered: NodeCircleBorderedProgram },
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
          prefsRef.current.selectionColor,
          kind,
        )
      },
      stagePadding: 40,
      labelRenderedSizeThreshold: 6,
      defaultDrawNodeLabel: drawNodeLabel,
      defaultNodeColor: t.mutedForeground,
      nodeReducer(node, data) {
        const tk = tokensRef.current
        const { dimUnrelated } = prefsRef.current
        const res: Partial<NodeDisplayData> & {
          _chromeKind?: ChromeKind
          labelColor?: string
          borderColor?: string
        } = {
          ...data,
        }
        const hov = hoveredNodeRef.current
        const sel = selectedIdRef.current
        const isNeighbour =
          !!sel && (graph.hasEdge(sel, node) || graph.hasEdge(node, sel))
        const tier = focusTier(node, sel, isNeighbour)
        const hoverNeighbour =
          !!hov && (graph.hasEdge(hov, node) || graph.hasEdge(node, hov))

        if (tier === "focus") {
          res.size = (data.size || 14) * FOCUS_SCALE
          res.highlighted = true
          res._chromeKind = "focus"
        } else if (hov === node) {
          res.size = (data.size || 14) * HOVER_SCALE
          res.highlighted = true
          res._chromeKind = "hover"
        }

        // The border recedes with the fill for the same reason the label
        // does below: a node dimmed to the background but still wearing a
        // full-strength outline reads as picked out, not as receded.
        const dim = (alpha: number) => {
          res.color = recede(
            data.color || tk.mutedForeground,
            tk.background,
            alpha,
          )
          res.borderColor = recede(
            (data as { borderColor?: string }).borderColor ||
              data.color ||
              tk.mutedForeground,
            tk.background,
            alpha,
          )
        }
        if (tier === "ground") {
          dim(groundNodeAlpha(dimUnrelated))
        } else if (!sel && hov && hov !== node && !hoverNeighbour) {
          // Nothing selected, but the pointer is on something: sort the
          // canvas the same way, half as far.
          dim(hoverGroundAlpha(dimUnrelated))
        }

        // A dimmed node with an undimmed label reads as a label floating over
        // nothing -- the label has to recede with the thing it names.
        if (tier === "ground") {
          res.labelColor = recede(
            tk.foreground,
            tk.background,
            groundNodeAlpha(dimUnrelated),
          )
        } else if (!sel && hov && hov !== node && !hoverNeighbour) {
          res.labelColor = recede(
            tk.foreground,
            tk.background,
            hoverGroundAlpha(dimUnrelated),
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

        // Emphasis never recolours an edge: its colour is its endpoints', and
        // repainting it the selection colour threw that away exactly when the
        // neighbourhood mattered most.
        if (sel) {
          if (src === sel || tgt === sel) {
            res.size = SELECTED_EDGE_SIZE
          } else {
            res.color = recede(
              data.color || tk.border,
              tk.background,
              groundEdgeAlpha(dimUnrelated),
            )
          }
        }

        if (hov) {
          if (src === hov || tgt === hov) {
            res.size = Math.max(res.size ?? 0, HOVER_EDGE_SIZE)
          } else if (!sel) {
            // Hovering with nothing selected sorts the canvas too, half as
            // far as a committed selection does.
            res.color = recede(
              data.color || tk.border,
              tk.background,
              hoverGroundAlpha(dimUnrelated) * 0.35,
            )
          }
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
      graph.mergeNodeAttributes(id, {
        color: paletteRef.current.entityFill,
        borderColor: entityTypeColor(
          attrs._entityType as string,
          paletteRef.current,
        ),
      })
    })
    graph.forEachEdge((edge) => {
      graph.setEdgeAttribute(
        edge,
        "color",
        membershipEdgeColor(tokensRef.current),
      )
    })
    // Attribute form, or per-node label dimming is undone on theme change.
    sigma.setSetting("labelColor", {
      attribute: "labelColor",
      color: tokensRef.current.foreground,
    })
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
