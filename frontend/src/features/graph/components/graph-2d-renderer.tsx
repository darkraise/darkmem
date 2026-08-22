import { useRef, useEffect, useCallback } from "react"
import Graph from "graphology"
import Sigma from "sigma"
import EdgeCurveProgram from "@sigma/edge-curve"
import {
  NodeDiamondProgram,
  drawDiamondNodeHover,
} from "@/features/graph/lib/node-diamond-program"
import { drawThemedDiscNodeHover } from "@/features/graph/lib/node-hover"
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
import { computeSize } from "@/features/graph/lib/graph-utils"
import {
  computeHullGroups,
  drawHullForSigma,
  drawRegionChip,
  hullTopAnchor,
  regionChipLabel,
} from "@/features/graph/lib/graph-geometry"
import type { HullMode } from "@/features/graph/lib/graph-geometry"
import type { SizeMode } from "@/features/graph/lib/graph-utils"
import {
  resolveNodeColor,
  resolveGroupColor,
  entityTypeColor,
  darkenHex,
  hexToRgba,
  memoryEdgeColor,
  relationEdgeColor,
  membershipEdgeColor,
  type ColorMode,
  type MemoryPalette,
} from "@/features/graph/lib/graph-colors"
import {
  seededUnit,
  type GraphThemeTokens,
} from "@/features/graph/lib/code-graph-theme"
import type {
  UnifiedMemory,
  GraphEntity,
  EntityRelation,
} from "@/hooks/api"

interface Graph2DRendererProps {
  filteredMemories: UnifiedMemory[]
  filteredEdges: { source: string; target: string; score: number }[]
  selectedNodeId: string | null
  onNodeSelect: (nodeId: string | null) => void
  onReady: () => void
  sizeMode: SizeMode
  colorMode: ColorMode
  spacing: number
  clusterTightness: number
  hullMode: HullMode
  entityLayerEnabled: boolean
  entities: GraphEntity[]
  entityRelations: EntityRelation[]
  onEntitySelect?: (entityId: string | null) => void
  tokens: GraphThemeTokens
  palette: MemoryPalette
  /** Derived cluster labels, keyed by cluster id. Region chips fall back to
   *  the raw group key when a cluster has no derived name — which is what a
   *  tag or source hull group already is. */
  clusterNames?: Record<string, string>
}

/** Focus and hover must not look alike; the scales differ as well as the
 *  chrome. Both are gentler than the 1.4x the previous model used for both. */
const FOCUS_SCALE = 1.22
const HOVER_SCALE = 1.08

/** Degree at or above which a node's label survives at any zoom. */
const HUB_DEGREE = 5

/** Sigma's camera ratio counts down as you move in, so *below* this is
 *  closer. 0.72 is the 1.4x of the spec, inverted. */
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

/** The edge hierarchy: relation over similarity over membership. */
function edgeWeight(kind: unknown): number {
  if (kind === "relation") return 3.4
  if (kind === "membership") return 2.2
  return 2.8
}

export function Graph2DRenderer({
  filteredMemories,
  filteredEdges,
  selectedNodeId,
  onNodeSelect,
  onReady,
  sizeMode,
  colorMode,
  spacing,
  clusterTightness,
  hullMode,
  entityLayerEnabled,
  entities,
  entityRelations,
  onEntitySelect,
  tokens,
  palette,
  clusterNames = {},
}: Graph2DRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const sigmaRef = useRef<Sigma | null>(null)
  const graphRef = useRef<Graph | null>(null)
  const fa2Ref = useRef<FA2Layout | null>(null)
  const fa2StopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const selectedNodeIdRef = useRef(selectedNodeId)
  const hoveredNodeRef = useRef<string | null>(null)
  const colorModeRef = useRef(colorMode)
  const hullModeRef = useRef(hullMode)
  const filteredMemoriesRef = useRef(filteredMemories)
  const tokensRef = useRef(tokens)
  tokensRef.current = tokens
  const paletteRef = useRef(palette)
  paletteRef.current = palette
  const clusterNamesRef = useRef(clusterNames)
  clusterNamesRef.current = clusterNames

  const selectionColor = useGraphPrefs((s) => s.selectionColor)
  const dimUnrelated = useGraphPrefs((s) => s.dimUnrelated)
  const prefsRef = useRef({ selectionColor, dimUnrelated })
  prefsRef.current = { selectionColor, dimUnrelated }

  // Camera ratio, not a zoom "level": sigma counts down as you move in, so
  // below the threshold is closer. Read in the node reducer to gate the
  // ordinary label tier.
  const zoomRatioRef = useRef(1)

  // An entity puts its type colour on its border and keeps a shared neutral
  // body, so it is never read as a memory that happens to carry that colour.
  // Memory nodes run on sigma's stock disc program, which draws no border, so
  // only their fill is ever painted.
  const nodeColors = (
    attrs: Record<string, unknown>,
  ): { color: string; borderColor: string } => {
    if (attrs._kind === "entity") {
      const et =
        (attrs._entityData as { entity_type: string } | undefined)
          ?.entity_type ?? ""
      const p = paletteRef.current
      return { color: p.entityFill, borderColor: entityTypeColor(et, p) }
    }
    const m = attrs._mem as {
      cluster: number
      memory_type: string | null
      tags: string[]
    }
    const color = resolveNodeColor(m, colorModeRef.current, paletteRef.current)
    return { color, borderColor: darkenHex(color) }
  }

  // An entity's identity colour lives on its border, so an edge leaving one
  // has to read the border — taking `color` would flatten every relation to
  // the one shared neutral body.
  const endpointTint = (attrs: Record<string, unknown>): string =>
    attrs._kind === "entity"
      ? (attrs.borderColor as string)
      : (attrs.color as string)
  const edgeBaseColor = (kind: string, srcHex: string): string => {
    if (kind === "relation") return relationEdgeColor(tokensRef.current, srcHex)
    if (kind === "membership")
      return membershipEdgeColor(tokensRef.current, srcHex)
    return memoryEdgeColor(srcHex, tokensRef.current)
  }

  const buildGraph = useCallback(() => {
    if (!containerRef.current) return

    if (fa2StopTimerRef.current !== null) {
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

    const t = tokensRef.current
    const mutedColor = t.mutedForeground
    const labelColorToken = t.foreground

    const graph = new Graph()
    graphRef.current = graph

    const connMap = new Map<string, number>()
    for (const e of filteredEdges) {
      connMap.set(e.source, (connMap.get(e.source) ?? 0) + 1)
      connMap.set(e.target, (connMap.get(e.target) ?? 0) + 1)
    }

    const allNodeIds = new Set<string>()
    for (const m of filteredMemories) {
      const { color, borderColor } = nodeColors({
        _kind: "memory",
        _mem: { cluster: m.cluster, memory_type: m.memory_type, tags: m.tags },
      })
      const conns = connMap.get(m.id) ?? 0
      const size = computeSize(sizeMode, conns, m.importance)
      allNodeIds.add(m.id)
      graph.addNode(m.id, {
        x: (seededUnit(m.id, 0) - 0.5) * 10,
        y: (seededUnit(m.id, 1) - 0.5) * 10,
        label: m.content.slice(0, 30) + (m.content.length > 30 ? "…" : ""),
        size: size * 0.5,
        _degree: conns,
        color,
        borderColor,
        _kind: "memory",
        _mem: { cluster: m.cluster, memory_type: m.memory_type, tags: m.tags },
      })
    }

    for (const e of filteredEdges) {
      if (graph.hasNode(e.source) && graph.hasNode(e.target)) {
        try {
          const srcColor =
            graph.getNodeAttribute(e.source, "color") || mutedColor
          const edgeColor = edgeBaseColor("memory", srcColor)
          graph.addEdge(e.source, e.target, {
            color: edgeColor,
            size: 2.5,
            _edgeKind: "memory",
          })
        } catch {
          /* duplicate */
        }
      }
    }

    if (entityLayerEnabled) {
      const visibleEntities = entities.filter((ent) =>
        ent.memory_ids.some((mid) => allNodeIds.has(mid)),
      )
      const entityIdSet = new Set(visibleEntities.map((ent) => ent.id))

      for (const ent of visibleEntities) {
        const { color: bg, borderColor } = nodeColors({
          _kind: "entity",
          _entityData: ent,
        })
        graph.addNode(`entity:${ent.id}`, {
          x: (seededUnit(`entity:${ent.id}`, 0) - 0.5) * 10,
          y: (seededUnit(`entity:${ent.id}`, 1) - 0.5) * 10,
          label: ent.name,
          size: 10,
          _degree: ent.memory_ids.length,
          color: bg,
          borderColor,
          type: "diamond",
          _kind: "entity",
          _entityData: ent,
        })
      }

      for (const r of entityRelations) {
        if (entityIdSet.has(r.source) && entityIdSet.has(r.target)) {
          try {
            const relSrc =
              (graph.getNodeAttribute(
                `entity:${r.source}`,
                "borderColor",
              ) as string) || ""
            graph.addEdge(`entity:${r.source}`, `entity:${r.target}`, {
              color: edgeBaseColor("relation", relSrc),
              size: 2.5,
              label: r.type,
              _edgeKind: "relation",
            })
          } catch {
            /* duplicate */
          }
        }
      }

      for (const ent of visibleEntities) {
        for (const mid of ent.memory_ids) {
          if (allNodeIds.has(mid)) {
            try {
              // Prefer the memory's colour over the entity's: the memory is
              // the thing the current colour mode is actually encoding, and
              // an entity's tint says only what type of entity it is.
              graph.addEdge(`entity:${ent.id}`, mid, {
                color: edgeBaseColor(
                  "membership",
                  graph.getNodeAttribute(mid, "color") ||
                    (graph.getNodeAttribute(
                      `entity:${ent.id}`,
                      "borderColor",
                    ) as string),
                ),
                size: 2.5,
                _edgeKind: "membership",
              })
            } catch {
              /* duplicate */
            }
          }
        }
      }
    }

    const sigma = new Sigma(graph, containerRef.current, {
      antiAliasingFeather: 2,
      renderLabels: true,
      renderEdgeLabels: false,
      labelSize: 12,
      // Per-node so a grounded label can recede with its node; sigma's
      // label renderer reads this attribute and falls back to `color`.
      labelColor: { attribute: "labelColor", color: labelColorToken },
      labelFont: "Inter, sans-serif",
      defaultEdgeType: "curve",
      nodeProgramClasses: { diamond: NodeDiamondProgram },
      edgeProgramClasses: { curve: EdgeCurveProgram },
      defaultDrawNodeHover: (context, data, settings) => {
        // `_chromeKind` rides the reducer output: sigma mutates the reduced
        // object in place through applyNodeDefaults, so custom keys survive
        // into display data. It is the only way this callback can tell the
        // node you selected from the one under the pointer.
        const kind =
          (data as { _chromeKind?: ChromeKind })._chromeKind ?? "hover"
        const color = prefsRef.current.selectionColor
        if (data.type === "diamond") {
          drawDiamondNodeHover(context, data, settings, tokensRef.current, color, kind)
        } else {
          drawThemedDiscNodeHover(context, data, settings, tokensRef.current, color, kind)
        }
      },
      stagePadding: 40,
      labelRenderedSizeThreshold: 6,
      defaultNodeColor: mutedColor,
      nodeReducer(node, data) {
        const t = tokensRef.current
        const { dimUnrelated } = prefsRef.current
        const res: Partial<NodeDisplayData> & {
          _chromeKind?: ChromeKind
          labelColor?: string
          borderColor?: string
        } = {
          ...data,
        }
        const hov = hoveredNodeRef.current
        const sel = selectedNodeIdRef.current
        const isNeighbour =
          !!sel && (graph.hasEdge(sel, node) || graph.hasEdge(node, sel))
        const tier = focusTier(node, sel, isNeighbour)
        const hoverNeighbour =
          !!hov && (graph.hasEdge(hov, node) || graph.hasEdge(node, hov))

        // A focused node keeps its own fill. Selection is announced by what is
        // drawn around it, never by repainting it — the fill is already
        // carrying cluster or type, and overwriting that trades one signal for
        // another instead of adding one.
        if (tier === "focus") {
          res.size = (data.size || 5) * FOCUS_SCALE
          res.highlighted = true
          res._chromeKind = "focus"
        } else if (hov === node) {
          res.size = (data.size || 5) * HOVER_SCALE
          res.highlighted = true
          res._chromeKind = "hover"
        }

        // Ground recedes but is never repainted: hue and position survive, so
        // the surrounding map stays readable as context.
        // The border recedes with the fill for the same reason the label
        // does below: an entity dimmed to the background but still wearing a
        // full-strength outline reads as picked out, not as receded.
        const dim = (alpha: number) => {
          res.color = recede(data.color || t.mutedForeground, t.background, alpha)
          res.borderColor = recede(
            (data as { borderColor?: string }).borderColor ||
              data.color ||
              t.mutedForeground,
            t.background,
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
            t.foreground,
            t.background,
            groundNodeAlpha(dimUnrelated),
          )
        } else if (!sel && hov && hov !== node && !hoverNeighbour) {
          res.labelColor = recede(
            t.foreground,
            t.background,
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
        const t = tokensRef.current
        const { dimUnrelated } = prefsRef.current
        const res = { ...data }
        const hov = hoveredNodeRef.current
        const sel = selectedNodeIdRef.current
        const src = graph.source(edge)
        const tgt = graph.target(edge)

        // A similarity edge, a typed relation and a membership link are three
        // different claims and carry three different weights. The eye follows
        // the heaviest line, so the heaviest line is the most meaningful one.
        res.size = edgeWeight(data._edgeKind)

        // Emphasis never recolours an edge: its colour is its endpoints', and
        // repainting it the selection colour threw that away exactly when the
        // neighbourhood mattered most.
        if (sel) {
          if (src === sel || tgt === sel) {
            res.size = SELECTED_EDGE_SIZE
          } else {
            res.color = recede(
              data.color || t.border,
              t.background,
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
              data.color || t.border,
              t.background,
              hoverGroundAlpha(dimUnrelated) * 0.35,
            )
          }
        }

        return res
      },
    })

    // Label tiers gate on zoom, so a camera move has to re-run the reducers.
    zoomRatioRef.current = sigma.getCamera().ratio
    sigma.getCamera().on("updated", () => {
      const next = sigma.getCamera().ratio
      const crossed =
        next < LABEL_ZOOM_RATIO !== zoomRatioRef.current < LABEL_ZOOM_RATIO
      zoomRatioRef.current = next
      // Only when the threshold is actually crossed: refreshing on every
      // frame of a zoom would re-reduce the whole graph per wheel tick.
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
      if (attrs._kind === "entity") {
        onEntitySelect?.(attrs._entityData?.id ?? null)
      } else {
        onNodeSelect(node)
      }
    })
    sigma.on("clickStage", () => {
      onNodeSelect(null)
      onEntitySelect?.(null)
    })

    sigmaRef.current = sigma

    const sigmaContainer = sigma.getContainer()
    const hullCanvas = document.createElement("canvas")
    hullCanvas.style.position = "absolute"
    hullCanvas.style.inset = "0"
    hullCanvas.style.pointerEvents = "none"
    hullCanvas.style.zIndex = "1"
    sigmaContainer.appendChild(hullCanvas)
    const hullCtx = hullCanvas.getContext("2d")!

    function drawHulls() {
      if (!sigmaRef.current || !containerRef.current) return
      const w = containerRef.current.clientWidth
      const h = containerRef.current.clientHeight
      const dpr = window.devicePixelRatio || 1
      if (hullCanvas.width !== w * dpr || hullCanvas.height !== h * dpr) {
        hullCanvas.width = w * dpr
        hullCanvas.height = h * dpr
        hullCanvas.style.width = w + "px"
        hullCanvas.style.height = h + "px"
      }
      hullCtx.setTransform(dpr, 0, 0, dpr, 0, 0)
      hullCtx.clearRect(0, 0, w, h)

      const hullGroups = computeHullGroups(
        filteredMemoriesRef.current,
        hullModeRef.current,
      )
      let idx = 0
      for (const [groupKey, members] of hullGroups) {
        const color = resolveGroupColor(
          groupKey,
          idx,
          colorModeRef.current,
          hullModeRef.current,
          paletteRef.current,
        )
        const hull = drawHullForSigma(
          hullCtx,
          sigmaRef.current,
          members,
          color,
          0.06,
          0.28,
        )
        // The zone always draws; only its name gates on zoom.
        if (zoomRatioRef.current < LABEL_ZOOM_RATIO) {
          const anchor = hullTopAnchor(hull)
          if (anchor) {
            const tk = tokensRef.current
            drawRegionChip(
              hullCtx,
              anchor,
              regionChipLabel(
                clusterNamesRef.current[groupKey] ?? groupKey,
                members.length,
              ),
              {
                fill: tk.background,
                stroke: hexToRgba(color, 0.5),
                text: tk.mutedForeground,
                font: tk.fontMono,
              },
            )
          }
        }
        idx++
      }

      const borderTargets = new Set<string>()
      if (hoveredNodeRef.current) borderTargets.add(hoveredNodeRef.current)
      if (selectedNodeIdRef.current)
        borderTargets.add(selectedNodeIdRef.current)
      for (const nodeId of borderTargets) {
        if (!graph.hasNode(nodeId)) continue
        const attrs = graph.getNodeAttributes(nodeId)
        if (attrs._kind !== "entity") continue
        const displayData = sigmaRef.current.getNodeDisplayData(nodeId)
        if (!displayData) continue
        const vp = sigmaRef.current.framedGraphToViewport(displayData)
        const sizePixels = sigmaRef.current.scaleSize(displayData.size)
        const r = sizePixels * Math.SQRT2 + 1
        const border = 3
        hullCtx.beginPath()
        hullCtx.moveTo(vp.x, vp.y - r)
        hullCtx.lineTo(vp.x + r, vp.y)
        hullCtx.lineTo(vp.x, vp.y + r)
        hullCtx.lineTo(vp.x - r, vp.y)
        hullCtx.closePath()
        hullCtx.strokeStyle = tokensRef.current.foreground
        hullCtx.lineWidth = border
        hullCtx.stroke()
      }
    }

    sigma.on("afterRender", drawHulls)
    sigma.on("kill", () => hullCanvas.remove())

    const fa2 = new FA2Layout(graph, {
      settings: {
        ...inferSettings(graph),
        linLogMode: true,
        outboundAttractionDistribution: false,
        strongGravityMode: true,
        // Drive the two toolbar sliders: higher spacing spreads nodes out
        // (scalingRatio), higher tightness pulls them to the centre (gravity).
        // Defaults (spacing 100, tightness 300) reproduce the previous
        // hardcoded gravity:1 / scalingRatio:10.
        gravity: Math.max(0.1, clusterTightness / 300),
        scalingRatio: Math.max(1, spacing / 10),
        slowDown: 12,
      },
    })
    fa2Ref.current = fa2
    fa2.start()
    fa2StopTimerRef.current = setTimeout(() => {
      fa2StopTimerRef.current = null
      if (fa2Ref.current) fa2Ref.current.stop()
    }, 8000)

    onReady()
    // dispatchers read refs; listing them would rebuild + resettle every render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    filteredMemories,
    filteredEdges,
    sizeMode,
    colorMode,
    spacing,
    clusterTightness,
    entityLayerEnabled,
    entities,
    entityRelations,
    onNodeSelect,
    onEntitySelect,
    onReady,
  ])

  useEffect(() => {
    const frame = requestAnimationFrame(() => buildGraph())
    return () => {
      cancelAnimationFrame(frame)
      if (fa2StopTimerRef.current !== null) {
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
    const observer = new ResizeObserver(() => {
      sigmaRef.current?.refresh()
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    selectedNodeIdRef.current = selectedNodeId
    sigmaRef.current?.refresh()
  }, [selectedNodeId])

  useEffect(() => {
    colorModeRef.current = colorMode
    hullModeRef.current = hullMode
    filteredMemoriesRef.current = filteredMemories
    sigmaRef.current?.refresh()
  }, [colorMode, hullMode, filteredMemories])

  useEffect(() => {
    const sigma = sigmaRef.current
    const graph = graphRef.current
    if (!sigma || !graph) return // initial mount: buildGraph already painted

    graph.forEachNode((id, attrs) => {
      graph.mergeNodeAttributes(id, nodeColors(attrs))
    })
    graph.forEachEdge((edge, attrs, _s, _t, sAttrs, tAttrs) => {
      const kind = (attrs._edgeKind as string) ?? "memory"
      // Same preference as the build path: the memory endpoint wins, because
      // it is the one the active colour mode is encoding.
      const tint =
        kind === "membership" && tAttrs._kind !== "entity"
          ? endpointTint(tAttrs)
          : endpointTint(sAttrs)
      graph.setEdgeAttribute(
        edge,
        "color",
        edgeBaseColor(kind, tint ?? tokensRef.current.mutedForeground),
      )
    })
    // Keeps the attribute form: a plain `{ color }` here would silently undo
    // per-node label dimming on every theme change.
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
