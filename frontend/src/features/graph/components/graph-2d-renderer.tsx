import { useRef, useEffect, useCallback } from "react"
import Graph from "graphology"
import Sigma from "sigma"
import EdgeCurveProgram from "@sigma/edge-curve"
import {
  NodeDiamondProgram,
  drawDiamondNodeHover,
} from "@/features/graph/lib/node-diamond-program"
import { drawDiscNodeHover } from "sigma/rendering"
import FA2Layout from "graphology-layout-forceatlas2/worker"
import { inferSettings } from "graphology-layout-forceatlas2"
import { computeSize } from "@/features/graph/lib/graph-utils"
import {
  computeHullGroups,
  drawHullForSigma,
} from "@/features/graph/lib/graph-geometry"
import type { HullMode } from "@/features/graph/lib/graph-geometry"
import type { SizeMode } from "@/features/graph/lib/graph-utils"
import {
  resolveNodeColor,
  resolveGroupColor,
  entityTypeColor,
  lightenHex,
  darkenHex,
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

  const nodeBaseColor = (attrs: Record<string, unknown>): string => {
    if (attrs._kind === "entity") {
      const et =
        (attrs._entityData as { entity_type: string } | undefined)
          ?.entity_type ?? ""
      return entityTypeColor(et, paletteRef.current)
    }
    const m = attrs._mem as {
      cluster: number
      memory_type: string | null
      tags: string[]
    }
    return resolveNodeColor(m, colorModeRef.current, paletteRef.current)
  }
  const edgeBaseColor = (kind: string, srcHex: string): string => {
    if (kind === "relation") return relationEdgeColor(tokensRef.current)
    if (kind === "membership") return membershipEdgeColor(tokensRef.current)
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
      const color = nodeBaseColor({
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
        color,
        borderColor: darkenHex(color),
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
        const bg = entityTypeColor(ent.entity_type, paletteRef.current)
        graph.addNode(`entity:${ent.id}`, {
          x: (seededUnit(`entity:${ent.id}`, 0) - 0.5) * 10,
          y: (seededUnit(`entity:${ent.id}`, 1) - 0.5) * 10,
          label: ent.name,
          size: 10,
          color: bg,
          borderColor: darkenHex(bg),
          type: "diamond",
          _kind: "entity",
          _entityData: ent,
        })
      }

      for (const r of entityRelations) {
        if (entityIdSet.has(r.source) && entityIdSet.has(r.target)) {
          try {
            graph.addEdge(`entity:${r.source}`, `entity:${r.target}`, {
              color: edgeBaseColor("relation", ""),
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
              graph.addEdge(`entity:${ent.id}`, mid, {
                color: edgeBaseColor("membership", ""),
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
      labelColor: { color: labelColorToken },
      labelFont: "Inter, sans-serif",
      defaultEdgeType: "curve",
      nodeProgramClasses: { diamond: NodeDiamondProgram },
      edgeProgramClasses: { curve: EdgeCurveProgram },
      defaultDrawNodeHover: (context, data, settings) => {
        if (data.type === "diamond") {
          drawDiamondNodeHover(
            context,
            data,
            settings,
            tokensRef.current.popover,
            tokensRef.current.isDark ? "#000" : tokensRef.current.border,
          )
        } else {
          drawDiscNodeHover(context, data, settings)
        }
      },
      stagePadding: 40,
      labelRenderedSizeThreshold: 6,
      defaultNodeColor: mutedColor,
      nodeReducer(node, data) {
        const t = tokensRef.current
        const res = { ...data }
        const hov = hoveredNodeRef.current
        const sel = selectedNodeIdRef.current
        if (hov === node) {
          res.color = lightenHex(data.color || t.mutedForeground, 0.4)
          res.size = (data.size || 5) * 1.4
          res.highlighted = true
        } else if (sel === node) {
          res.color = lightenHex(data.color || t.mutedForeground, 0.4)
          res.size = (data.size || 5) * 1.4
          res.highlighted = true
          if (data.type !== "diamond") {
            res.borderColor = t.foreground
            res.borderSize = 3
          }
        } else if (sel && sel !== node) {
          const isNeighbor =
            graph.hasEdge(sel, node) || graph.hasEdge(node, sel)
          if (!isNeighbor) {
            res.color = t.border
            res.label = ""
          }
        }
        return res
      },
      edgeReducer(edge, data) {
        const t = tokensRef.current
        const res = { ...data }
        const hov = hoveredNodeRef.current
        const sel = selectedNodeIdRef.current
        const src = graph.source(edge)
        const tgt = graph.target(edge)

        if (sel) {
          if (src === sel || tgt === sel) {
            res.size = (data.size || 2.5) * 2
            const neighborColor =
              graph.getNodeAttribute(src === sel ? tgt : src, "color") ||
              t.mutedForeground
            res.color = lightenHex(neighborColor, 0.3)
          } else {
            res.color = t.border
            res.size = (data.size || 2.5) * 0.5
          }
        }

        if (hov && (src === hov || tgt === hov)) {
          res.size = (data.size || 2.5) * 2
          const neighborColor =
            graph.getNodeAttribute(src === hov ? tgt : src, "color") ||
            t.mutedForeground
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
        drawHullForSigma(hullCtx, sigmaRef.current, members, color, 0.07, 0.2)
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
      const color = nodeBaseColor(attrs)
      graph.mergeNodeAttributes(id, { color, borderColor: darkenHex(color) })
    })
    graph.forEachEdge((edge, attrs, _s, _t, sAttrs) => {
      const kind = (attrs._edgeKind as string) ?? "memory"
      const srcHex =
        (sAttrs.color as string) ?? tokensRef.current.mutedForeground
      graph.setEdgeAttribute(edge, "color", edgeBaseColor(kind, srcHex))
    })
    sigma.setSetting("labelColor", { color: tokensRef.current.foreground })
    sigma.setSetting("edgeLabelColor", {
      color: tokensRef.current.mutedForeground,
    })
    sigma.setSetting("defaultNodeColor", tokensRef.current.mutedForeground)
    sigma.refresh()
    // Keyed on a primitive theme signature so incidental re-renders don't recolor.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [`${tokens.background}:${tokens.isDark}`])

  return <div ref={containerRef} className="absolute inset-0" />
}
