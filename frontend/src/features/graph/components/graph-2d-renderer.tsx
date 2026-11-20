import { useRef, useEffect, useCallback, useState } from "react"
import Graph from "graphology"
import Sigma from "sigma"
import EdgeCurveProgram from "@sigma/edge-curve"
import { EdgeRectangleProgram } from "sigma/rendering"
import { EmptyState } from "@/components/darkmem"
import { scaleSettings } from "@/features/graph/lib/graph-scale"
import {
  NodeDiamondProgram,
  drawDiamondNodeHover,
} from "@/features/graph/lib/node-diamond-program"
import { drawNodeLabel, drawThemedDiscNodeHover } from "@/features/graph/lib/node-hover"
import type { ChromeKind } from "@/features/graph/lib/node-hover"
import type { NodeDisplayData } from "sigma/types"
import type { Settings } from "sigma/settings"
import {
  focusTier,
  groundEdgeAlpha,
  groundNodeAlpha,
  hoverGroundAlpha,
  hoverGroundEdgeAlpha,
  edgeEmphasis,
  litByHover,
  labelVisible,
  fade,
  recede,
} from "@/features/graph/lib/focus-model"
import { useGraphPrefs } from "@/features/graph/lib/graph-prefs"
import { hoverRepaintSet } from "@/features/graph/lib/hover-repaint"
import { constellationFa2Settings } from "@/features/graph/lib/constellation-runner"
import { createClusterRunner, type ClusterRunner } from "@/features/graph/lib/cluster-runner"
import type { Attachment, ScoredEdge } from "@/features/graph/lib/constellation-layout"
import { topHubs } from "@/features/graph/lib/hubs"
import { memoryEdgeSize, restEdgeSize } from "@/features/graph/lib/memory-edge-width"
import {
  createNodeGlowProgram,
  glowDiscScale,
  trackDensityGain,
  type GlowClock,
} from "@/features/graph/lib/node-glow-program"
import { withStraightAlpha } from "@/features/graph/lib/straight-alpha"
import {
  attachBackdrop,
  coreOnScreen,
  WEBGL_UNAVAILABLE_MESSAGE,
} from "@/features/graph/lib/graph-backdrop"
import { startAmbientMotion } from "@/features/graph/lib/ambient-motion"
import { memorySizes } from "@/features/graph/lib/memory-size"
import {
  islandLabelAlpha,
  islandLabelInputs,
  placeIslandLabels,
} from "@/features/graph/lib/island-labels"
import {
  entityRenderKey,
  layoutSignature,
  relationRenderKey,
} from "@/features/graph/lib/graph-utils"
import {
  computeHullGroups,
  createHullShapeCache,
  drawFramedHull,
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
  restEdgeColor,
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

/** Entity nodes are the overlay, so they must not outweigh the memories they
 *  annotate: 3 sits at the low end of the memories' 2.5-11.5 size range. */
const ENTITY_NODE_SIZE = 3

/** Fewest memory-to-memory edges a hub carries. */
const HUB_DEGREE = 5
const MEMORY_SIZE_SCALE = 0.25
const LIGHT_REST_EDGE_FADE = 0.4

/** Sigma's camera ratio counts down as you move in, so *below* this is
 *  closer. 0.72 is the 1.4x of the spec, inverted. */
const LABEL_ZOOM_RATIO = 0.72

const LABEL_FONT = "Inter, sans-serif"

/** The toolbar row floats over the canvas's top edge (top-3, 32 px buttons);
 *  island names stay below it. */
const TOOLBAR_BAND_PX = 48

/** While the layout runs, hull shapes refresh at most this often; camera
 *  moves never recompute them. */
const HULL_REFRESH_MS = 250

/** The backdrop draws its glow at 2.2x this share of the islands' extent. */
const NEBULA_SHARE = 0.5

export function Graph2DRenderer({
  filteredMemories,
  filteredEdges,
  selectedNodeId,
  onNodeSelect,
  onReady,
  sizeMode,
  colorMode,
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
  const runnerRef = useRef<ClusterRunner | null>(null)
  const clockRef = useRef<GlowClock>({ time: 0 })
  const stopMotionRef = useRef<(() => void) | null>(null)
  const [webglFailed, setWebglFailed] = useState(false)
  // Where every node had settled when the last graph was torn down. A rebuild
  // that re-seeds from scratch throws the layout away and makes the canvas
  // lurch, which is what toggling the entity layer used to do -- twice, once
  // on the switch and again when the new data landed.
  const positionsRef = useRef<Map<string, { x: number; y: number }>>(new Map())
  const islandSigRef = useRef<string | null>(null)
  // What the last layout was computed for. ForceAtlas2 only needs to re-run
  // when this changes; adding or dropping an overlay does not change it.
  const layoutSigRef = useRef<string | null>(null)
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
  const hubsRef = useRef<Set<string>>(new Set())

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
  // An edge rests faded and lifts to its full colour only inside the selected
  // or hovered neighbourhood, so the constellation reads as points, not mesh.
  const edgeColors = (
    kind: string,
    srcHex: string,
  ): { color: string; _fullColor: string } => {
    const full = edgeBaseColor(kind, srcHex)
    const hex = full.startsWith("#")
      ? full.slice(0, 7)
      : srcHex.startsWith("#")
        ? srcHex.slice(0, 7)
        : tokensRef.current.mutedForeground
    return { color: restEdgeColor(hex, tokensRef.current.isDark), _fullColor: full }
  }

  // Empty whenever there is nothing to overlay -- layer off, or layer on with
  // the fetch still in flight. Two renders that would draw the same entities
  // produce the same key, so the effect below does not re-run and no canvas is
  // torn down.
  const entitiesKey = entityRenderKey(entityLayerEnabled, entities)
  const relationsKey = relationRenderKey(entityLayerEnabled, entityRelations)

  const buildGraph = useCallback(() => {
    if (!containerRef.current) return

    stopMotionRef.current?.()
    stopMotionRef.current = null
    if (runnerRef.current) {
      runnerRef.current.kill()
      runnerRef.current = null
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

    // Memories only: entities ride on their memories' centroid and never enter
    // the simulation, so the entity layer arriving is no reason to re-run it.
    const layoutSig = layoutSignature(filteredMemories.map((m) => m.id))
    const layoutChanged = layoutSigRef.current !== layoutSig
    layoutSigRef.current = layoutSig

    const settled = positionsRef.current
    // Every rebuild starts from where the nodes already are, changed layout or
    // not. Only something never seen before is seeded. That is what makes a
    // re-arrangement read as the graph settling rather than as it being thrown
    // across the canvas and reassembling.
    const placeSeeded = (id: string) => ({
      x: (seededUnit(id, 0) - 0.5) * 10,
      y: (seededUnit(id, 1) - 0.5) * 10,
    })
    // A never-seen memory is placed on its island by the runner.
    const fresh = new Set<string>()
    const place = (id: string) => {
      const known = settled.get(id)
      if (known) return known
      fresh.add(id)
      return placeSeeded(id)
    }

    const sizes = memorySizes(sizeMode, filteredMemories, connMap)
    const allNodeIds = new Set<string>()
    for (const m of filteredMemories) {
      const { color, borderColor } = nodeColors({
        _kind: "memory",
        _mem: { cluster: m.cluster, memory_type: m.memory_type, tags: m.tags },
      })
      const conns = connMap.get(m.id) ?? 0
      const size = sizes.get(m.id)!
      allNodeIds.add(m.id)
      graph.addNode(m.id, {
        ...place(m.id),
        label: m.content.slice(0, 30) + (m.content.length > 30 ? "…" : ""),
        size: size * MEMORY_SIZE_SCALE,
        type: "glow",
        _degree: conns,
        color,
        borderColor,
        _kind: "memory",
        _mem: { cluster: m.cluster, memory_type: m.memory_type, tags: m.tags },
      })
    }

    const roleEdges: ScoredEdge[] = []
    const attachments: Attachment[] = []
    for (const e of filteredEdges) {
      if (graph.hasNode(e.source) && graph.hasNode(e.target)) {
        try {
          const srcColor =
            graph.getNodeAttribute(e.source, "color") || mutedColor
          graph.addEdge(e.source, e.target, {
            ...edgeColors("memory", srcColor),
            size: 2.5,
            score: e.score,
            _edgeKind: "memory",
          })
          roleEdges.push({ source: e.source, target: e.target, score: e.score })
        } catch {
          /* duplicate */
        }
      }
    }

    if (entitiesKey !== "") {
      const visibleEntities = entities.filter((ent) =>
        ent.memory_ids.some((mid) => allNodeIds.has(mid)),
      )

      // A first-time entity lands on the centroid of the memories asserting
      // it -- which is roughly where the simulation would have dragged it
      // anyway, so the overlay can appear without one.
      const placeEntity = (ent: { id: string; memory_ids: string[] }) => {
        const known = settled.get(`entity:${ent.id}`)
        if (known) return known
        const anchors = ent.memory_ids
          .filter((mid) => graph.hasNode(mid))
          .map((mid) => ({
            x: graph.getNodeAttribute(mid, "x") as number,
            y: graph.getNodeAttribute(mid, "y") as number,
          }))
        if (anchors.length === 0) return placeSeeded(`entity:${ent.id}`)
        const cx = anchors.reduce((t, a) => t + a.x, 0) / anchors.length
        const cy = anchors.reduce((t, a) => t + a.y, 0) / anchors.length
        // Deterministic jitter: two entities on one memory would otherwise
        // stack exactly, and a stack reads as a single node.
        return {
          x: cx + (seededUnit(`entity:${ent.id}`, 2) - 0.5) * 1.5,
          y: cy + (seededUnit(`entity:${ent.id}`, 3) - 0.5) * 1.5,
        }
      }
      const entityIdSet = new Set(visibleEntities.map((ent) => ent.id))

      for (const ent of visibleEntities) {
        const { color: bg, borderColor } = nodeColors({
          _kind: "entity",
          _entityData: ent,
        })
        graph.addNode(`entity:${ent.id}`, {
          ...placeEntity(ent),
          label: ent.name,
          size: ENTITY_NODE_SIZE,
          _degree: ent.memory_ids.length,
          color: bg,
          borderColor,
          type: "diamond",
          _kind: "entity",
          _entityData: ent,
        })
        attachments.push({
          id: `entity:${ent.id}`,
          linked: ent.memory_ids.filter((mid) => allNodeIds.has(mid)),
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
              ...edgeColors("relation", relSrc),
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
                ...edgeColors(
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

    const memoryDegrees = new Map<string, number>()
    for (const id of allNodeIds) memoryDegrees.set(id, 0)
    for (const e of roleEdges) {
      memoryDegrees.set(e.source, memoryDegrees.get(e.source)! + 1)
      memoryDegrees.set(e.target, memoryDegrees.get(e.target)! + 1)
    }
    hubsRef.current = topHubs(memoryDegrees, 0.02, HUB_DEGREE)

    const scale = scaleSettings(graph.order, graph.size)
    const runner = createClusterRunner(graph, {
      layoutMs: scale.layoutMs,
      // Each island is its own component in the simulation; a weak gravity
      // only stops them drifting apart, since every frame refits them.
      fa2Settings: {
        ...constellationFa2Settings(graph, scale),
        strongGravityMode: false,
        gravity: 0.05,
        edgeWeightInfluence: 1,
      },
      memories: filteredMemories,
      edges: roleEdges,
      attachments,
      fresh,
      onStop: () => {
        hullCache.invalidate()
        sigmaRef.current?.refresh()
      },
    })
    runnerRef.current = runner
    // Islands follow the clusters and edges, so an Edges-threshold change can
    // move memories between islands with the id set unchanged; the islands
    // then have to settle again around their new members.
    // The reference draws no lines across open space: at rest an edge shows
    // only inside one island, and hover or selection lights the rest of a
    // node's links.
    const restGroup = runner.groupOf
    const islandSig = filteredMemories
      .map((m) => `${m.id}=${restGroup.get(m.id)}`)
      .sort()
      .join("\n")
    const islandsChanged = islandSigRef.current !== islandSig
    islandSigRef.current = islandSig
    // The glow program shrinks dense roles' discs on the GPU; the canvas
    // chrome and labels are placed off the disc as drawn.
    const drawnDisc = <T extends { size: number }>(data: T): T => ({
      ...data,
      size:
        data.size *
        glowDiscScale((data as { brightness?: number }).brightness, clockRef.current, {
          additive: tokensRef.current.isDark,
          memoryCanvas: true,
        }),
    })
    const sigmaSettings: Partial<Settings> = {
      antiAliasingFeather: 2,
      // Sorts each program's items by the `zIndex` the reducers emit. Only the
      // edge reducer sets one, so node paint order is unchanged: sigma skips
      // the sort entirely when a category's z-extent is flat.
      zIndex: true,
      renderLabels: true,
      renderEdgeLabels: false,
      // Off at every size: with it on, sigma runs a full refresh after each
      // pan release, which at 20k nodes is a second-long main-thread stall.
      hideEdgesOnMove: false,
      hideLabelsOnMove: scale.hideLabelsOnMove,
      labelSize: 12,
      // Per-node so a grounded label can recede with its node; sigma's
      // label renderer reads this attribute and falls back to `color`.
      labelColor: { attribute: "labelColor", color: labelColorToken },
      labelFont: LABEL_FONT,
      defaultEdgeType: scale.curvedEdges ? "curve" : "line",
      // Order matters and is the whole point: sigma draws program by program
      // in registration order, and zIndex only sorts WITHIN a program. Giving
      // memories their own key after "diamond" is what puts the subject on top
      // of the overlay where they overlap.
      nodeProgramClasses: {
        diamond: NodeDiamondProgram,
        glow: createNodeGlowProgram({
          additive: tokensRef.current.isDark,
          clock: clockRef.current,
          memoryCanvas: true,
        }),
      },
      // Sigma replaces its default program map with this one, so the
      // straight program must be registered here to be usable at all.
      edgeProgramClasses: {
        curve: withStraightAlpha(EdgeCurveProgram),
        line: withStraightAlpha(EdgeRectangleProgram),
      },
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
          drawThemedDiscNodeHover(context, drawnDisc(data), settings, tokensRef.current, color, kind)
        }
      },
      // Keeps the islands clear of the toolbar buttons, which sit up to 44px
      // in from the top edge.
      stagePadding: 64,
      // Memories and the halo draw under sigma's 6px label cull, which runs
      // before the reducer is consulted; the reducer alone decides labels.
      labelRenderedSizeThreshold: 0,
      defaultDrawNodeLabel: (context, data, settings) =>
        drawNodeLabel(context, data.type === "diamond" ? data : drawnDisc(data), settings),
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
          res.color = recede(data.color || t.mutedForeground, t.canvas, alpha)
          res.borderColor = recede(
            (data as { borderColor?: string }).borderColor ||
              data.color ||
              t.mutedForeground,
            t.canvas,
            alpha,
          )
        }
        const litNode = litByHover(node, hov, hoverNeighbour)
        const hoverGround =
          scale.hoverDims && !sel && !!hov && hov !== node && !hoverNeighbour
        if (tier === "ground" && !litNode) {
          dim(groundNodeAlpha(dimUnrelated))
        } else if (hoverGround) {
          // Nothing selected, but the pointer is on something: sort the
          // canvas the same way, half as far.
          dim(hoverGroundAlpha(dimUnrelated))
        }

        // A dimmed node with an undimmed label reads as a label floating over
        // nothing -- the label has to recede with the thing it names.
        if (tier === "ground" && !litNode) {
          res.labelColor = recede(
            t.foreground,
            t.canvas,
            groundNodeAlpha(dimUnrelated),
          )
        } else if (hoverGround) {
          res.labelColor = recede(
            t.foreground,
            t.canvas,
            hoverGroundAlpha(dimUnrelated),
          )
        }

        if (
          !labelVisible({
            tier,
            isHub: hubsRef.current.has(node) && zoomRatioRef.current < LABEL_ZOOM_RATIO,
            // Hubs are memories only; entity names keep the zoomed-in rule.
            zoomedIn: data._kind === "entity" && zoomRatioRef.current < LABEL_ZOOM_RATIO,
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
        res.size = restEdgeSize(data._edgeKind)

        // Emphasis never recolours an edge: its colour is its endpoints', and
        // repainting it the selection colour threw that away exactly when the
        // neighbourhood mattered most.
        const { zIndex, ground, lit } = edgeEmphasis(src, tgt, sel, hov)
        const group = restGroup.get(src)
        if (!lit && (group === undefined || group !== restGroup.get(tgt))) {
          res.hidden = true
          return res
        }
        if (lit && typeof data._fullColor === "string") res.color = data._fullColor
        // On the light canvas a dense core's mesh of grey lines outweighs its
        // small points; at rest it sits further back than in the dark theme.
        else if (!t.isDark && !ground) res.color = fade(data.color || t.border, LIGHT_REST_EDGE_FADE)

        res.size = memoryEdgeSize(data._edgeKind, {
          selected: !!sel && (src === sel || tgt === sel),
          hovered: !!hov && (src === hov || tgt === hov),
        })

        if (ground === "selection" || (ground === "hover" && scale.hoverDims)) {
          res.color = fade(
            data.color || t.border,
            ground === "selection"
              ? groundEdgeAlpha(dimUnrelated)
              : hoverGroundEdgeAlpha(dimUnrelated),
          )
        }

        // Without this the ground is painted in whatever order the graph
        // iterates and crosses over a lit spoke — the neighbourhood is
        // emphasised and then partly painted back out.
        res.zIndex = zIndex

        return res
      },
    }
    let sigma: Sigma
    try {
      sigma = new Sigma(graph, containerRef.current, sigmaSettings)
    } catch (error) {
      // Also how a shader that fails to compile surfaces; log it so it is not
      // mistaken for a browser setting.
      console.error("Memory graph: WebGL renderer failed to start", error)
      runner.kill()
      runnerRef.current = null
      graphRef.current = null
      setWebglFailed(true)
      onReady()
      return
    }
    setWebglFailed(false)

    // Label tiers gate on zoom, so a camera move has to re-run the reducers.
    zoomRatioRef.current = sigma.getCamera().ratio
    const onCameraUpdated = () => {
      const next = sigma.getCamera().ratio
      const crossed =
        next < LABEL_ZOOM_RATIO !== zoomRatioRef.current < LABEL_ZOOM_RATIO
      zoomRatioRef.current = next
      // Only when the threshold is actually crossed: refreshing on every
      // frame of a zoom would re-reduce the whole graph per wheel tick. Labels
      // are node output only, so the edges are left alone.
      if (crossed) {
        sigma.refresh({
          partialGraph: { nodes: graph.nodes() },
          skipIndexation: true,
          schedule: true,
        })
      }
    }
    const camera = sigma.getCamera()
    camera.on("updated", onCameraUpdated)
    // kill() leaves the camera, and an animation still in flight keeps
    // emitting updates to listeners that would refresh a dead instance.
    sigma.on("kill", () => camera.removeListener("updated", onCameraUpdated))

    const setHovered = (next: string | null) => {
      const previous = hoveredNodeRef.current
      hoveredNodeRef.current = next
      if (scale.hoverDims) {
        sigma.refresh()
        return
      }
      sigma.refresh({
        partialGraph: hoverRepaintSet(graph, previous, next),
        skipIndexation: true,
        schedule: true,
      })
    }
    sigma.on("enterNode", ({ node }) => {
      containerRef.current!.style.cursor = "pointer"
      setHovered(node)
    })
    sigma.on("leaveNode", () => {
      containerRef.current!.style.cursor = "default"
      setHovered(null)
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

    // Hull groups change only with the data or the mode, and hull shapes only
    // while the layout moves. Recomputing both on every frame is what made a
    // large graph stutter on pan.
    const hullCache = createHullShapeCache(computeHullGroups, HULL_REFRESH_MS)

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

      const hullGroups = hullCache.update(
        filteredMemoriesRef.current,
        hullModeRef.current,
        sigmaRef.current,
        runnerRef.current?.isRunning() ?? false,
        performance.now(),
      )
      for (const [groupKey, members] of hullGroups) {
        const color = resolveGroupColor(groupKey, paletteRef.current)
        const hull = drawFramedHull(
          hullCtx,
          sigmaRef.current,
          hullCache.shape(groupKey),
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

    // Above the nodes, under sigma's own labels and hover tags, so a memory's
    // name always reads over its island's.
    const islandCanvas = sigma.createCanvas("islandLabels", { beforeLayer: "labels" })
    const islandCtx = islandCanvas.getContext("2d")!
    const textWidths = new Map<string, number>()
    // Widths measured before the label font loaded are a fallback font's.
    const clearTextWidths = () => {
      textWidths.clear()
      sigma.scheduleRender()
    }
    document.fonts?.addEventListener("loadingdone", clearTextWidths)
    sigma.on("kill", () => document.fonts?.removeEventListener("loadingdone", clearTextWidths))
    const measureText = (text: string, fontPx: number) => {
      const key = `${fontPx}|${text}`
      let w = textWidths.get(key)
      if (w === undefined) {
        islandCtx.font = `600 ${fontPx}px ${LABEL_FONT}`
        w = islandCtx.measureText(text).width
        textWidths.set(key, w)
      }
      return w
    }

    function drawIslandLabels() {
      const s = sigmaRef.current
      const r = runnerRef.current
      if (!s || !r) return
      const { width, height } = s.getDimensions()
      const dpr = window.devicePixelRatio || 1
      if (islandCanvas.width !== width * dpr || islandCanvas.height !== height * dpr) {
        islandCanvas.width = width * dpr
        islandCanvas.height = height * dpr
        islandCanvas.style.width = width + "px"
        islandCanvas.style.height = height + "px"
      }
      islandCtx.setTransform(dpr, 0, 0, dpr, 0, 0)
      islandCtx.clearRect(0, 0, width, height)
      const alpha = islandLabelAlpha(selectedNodeIdRef.current !== null)
      const islands = islandLabelInputs(
        r.layout.groups,
        r.layout.centres,
        clusterNamesRef.current,
        (p) => s.graphToViewport(p),
      )
      const tk = tokensRef.current
      islandCtx.save()
      islandCtx.globalAlpha = alpha
      islandCtx.textAlign = "center"
      islandCtx.textBaseline = "middle"
      islandCtx.lineJoin = "round"
      islandCtx.lineWidth = 4
      islandCtx.strokeStyle = hexToRgba(tk.canvas, 0.9)
      islandCtx.fillStyle = tk.foreground
      for (const label of placeIslandLabels(islands, measureText, {
        width,
        height,
        top: TOOLBAR_BAND_PX,
      })) {
        islandCtx.font = `600 ${label.fontPx}px ${LABEL_FONT}`
        islandCtx.strokeText(label.text, label.x, label.y)
        islandCtx.fillText(label.text, label.x, label.y)
      }
      islandCtx.restore()
    }

    sigma.on("afterRender", drawHulls)
    sigma.on("afterRender", drawIslandLabels)
    sigma.on("kill", () => hullCanvas.remove())

    // Entity diamonds draw through their own program, not the glow pass, so
    // counting them in any role's density misreads how dense its glows are.
    const attached = new Set(attachments.map((a) => a.id))
    const glowOnly = (ids: readonly string[]) => ids.filter((id) => !attached.has(id))
    trackDensityGain(
      sigma,
      graph,
      {
        core: glowOnly(runner.classification.core),
        satellites: runner.classification.satellites
          .map(glowOnly)
          .filter((members) => members.length > 0),
        halo: glowOnly(runner.classification.halo),
      },
      clockRef.current,
      runner.outer,
      true,
    )
    // The constructor's synchronous first frame ran before this handler.
    sigma.scheduleRender()

    const detachBackdrop = attachBackdrop(
      sigma,
      // The nebula spans the islands rather than one core.
      () => coreOnScreen(sigma, NEBULA_SHARE * runner.layout.extent),
      {
        canvas: tokensRef.current.canvas,
        nebula: tokensRef.current.nebula,
        isDark: tokensRef.current.isDark,
      },
    )
    sigma.on("kill", detachBackdrop)
    stopMotionRef.current = startAmbientMotion({
      nodeCount: graph.order,
      onFrame: (sec) => {
        clockRef.current.time = sec
        sigma.scheduleRender()
      },
    })

    // Nothing new to arrange -- this is the render that happens while a fetch
    // is in flight, drawing the same nodes as the last one. Re-simulating here
    // is what scattered the canvas the moment the switch was touched.
    if (!layoutChanged && !islandsChanged) {
      onReady()
      return
    }

    // Sigma has drawn the first frame, but the browser shows it only once
    // this task ends, and the core copy in start() costs ~180 ms at 20k
    // nodes. This callback already runs in a frame, so a nested request
    // lands on the next one, after the first paint.
    requestAnimationFrame(() => {
      if (runnerRef.current === runner) runner.start()
    })

    onReady()
    // dispatchers read refs; listing them would rebuild + resettle every render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    filteredMemories,
    filteredEdges,
    sizeMode,
    colorMode,
    // The keys, not the arrays: `filteredEntities` is a fresh array on every
    // data change, and its identity moving is not a reason to rebuild.
    entitiesKey,
    relationsKey,
    onNodeSelect,
    onEntitySelect,
    onReady,
    // The glow program's blending and the backdrop's colours are fixed when
    // sigma is built, so a theme switch has to rebuild; the layout signature
    // is unchanged, so nothing re-simulates.
    tokens.isDark,
    tokens.canvas,
    tokens.nebula,
  ])

  useEffect(() => {
    const frame = requestAnimationFrame(() => buildGraph())
    return () => {
      cancelAnimationFrame(frame)
      // Before anything is torn down: React runs this cleanup ahead of the
      // next buildGraph, so this is the last moment the settled coordinates
      // exist.
      if (graphRef.current) {
        const settled = positionsRef.current
        graphRef.current.forEachNode((id, attrs) => {
          const x = attrs.x as number
          const y = attrs.y as number
          if (Number.isFinite(x) && Number.isFinite(y)) settled.set(id, { x, y })
        })
      }
      stopMotionRef.current?.()
      stopMotionRef.current = null
      if (runnerRef.current) {
        runnerRef.current.kill()
        runnerRef.current = null
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
      graph.mergeEdgeAttributes(
        edge,
        edgeColors(kind, tint ?? tokensRef.current.mutedForeground),
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

  return (
    <>
      <div ref={containerRef} className="absolute inset-0 bg-transparent" />
      {webglFailed && (
        <div className="absolute inset-0 flex items-center justify-center">
          <EmptyState kind="failed" title={WEBGL_UNAVAILABLE_MESSAGE} />
        </div>
      )}
    </>
  )
}
