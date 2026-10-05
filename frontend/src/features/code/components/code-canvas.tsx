import { useMemo } from "react"
import { cn } from "darkraise-ui/lib"
import { layoutGraph, type GraphLayoutMode, type Point } from "@/demo/explore"
import type { CodeNodeKind, DemoCodeGraph } from "@/features/code/types"

export const CANVAS_W = 640
export const CANVAS_H = 400

// The same accent-anchored tiering code-graph-theme.ts uses: structural,
// types, callables, entrypoints, data — all from the --chart ramp. Kinds
// beyond the original demo five (widened for the real backend's vocabulary,
// T1.59) slot into the nearest existing tier rather than adding new colours
// the bottom-of-canvas legend does not explain.
const KIND_CHART: Record<CodeNodeKind, number> = {
  file: 1,
  module: 1,
  class: 2,
  struct: 2,
  interface: 2,
  trait: 2,
  enum: 2,
  namespace: 2,
  impl: 2,
  type: 2,
  property: 2,
  method: 3,
  function: 3,
  route: 3,
  tool: 3,
}

export const chartVar = (n: number) => `var(--chart-${n})`

/** Approximate advance of one 10px monospace glyph, in SVG units. */
const LABEL_CHAR_W = 6.1
const RIGHT_LABEL = { x: 12, y: 4, anchor: "start" } as const
const ABOVE_LABEL = { x: 0, y: -15, anchor: "middle" } as const
const BELOW_LABEL = { x: 0, y: 22, anchor: "middle" } as const

export interface CodeCanvasProps {
  graph: DemoCodeGraph
  layout: GraphLayoutMode
  colorBy: "community" | "kind"
  selectedId: string | null
  onSelect: (id: string | null) => void
  /** Depth filter — ids to keep prominent; null = no filter. */
  visibleIds: Set<string> | null
  /** Node kinds the Filters tab has switched off — removed, not dimmed. */
  hiddenKinds?: ReadonlySet<CodeNodeKind>
  /** Blast-radius affected ids — dashed destructive rings. */
  blastIds: Set<string> | null
  highlightCommunity: string | null
  /** Active-process step ids, emphasised. */
  processIds: Set<string> | null
  playing: boolean
  zoom: number
  center: Point | null
}

export function CodeCanvas({
  graph,
  layout,
  colorBy,
  selectedId,
  onSelect,
  visibleIds,
  hiddenKinds,
  blastIds,
  highlightCommunity,
  processIds,
  playing,
  zoom,
  center,
}: CodeCanvasProps) {
  const positions = useMemo(
    () =>
      layoutGraph(
        graph.nodes.map((n) => ({ id: n.id, group: n.community })),
        graph.edges,
        layout,
        CANVAS_W,
        CANVAS_H,
      ),
    [graph, layout],
  )

  const communityChart = useMemo(() => {
    const map = new Map<string, number>()
    for (const c of graph.communities) map.set(c.id, c.chart)
    return map
  }, [graph])

  const isKindHidden = (kind: CodeNodeKind) => hiddenKinds?.has(kind) ?? false

  const nodeColor = (community: string, kind: CodeNodeKind) =>
    colorBy === "community"
      ? chartVar(communityChart.get(community) ?? 1)
      : chartVar(KIND_CHART[kind])

  const dimmed = (id: string, community: string) => {
    if (visibleIds && !visibleIds.has(id)) return true
    if (highlightCommunity && community !== highlightCommunity) return true
    return false
  }

  // Labels are drawn only for emphasised nodes. To the node's right is the
  // default spot; when another node sits in that strip the label moves above
  // the node (or below, if above is taken too), so a label never runs
  // through a neighbour.
  const labelSpot = (id: string, name: string) => {
    const pos = positions[id]
    if (!pos) return RIGHT_LABEL
    const width = name.length * LABEL_CHAR_W
    const occupied = (x0: number, x1: number, y0: number, y1: number) =>
      graph.nodes.some((other) => {
        if (other.id === id || isKindHidden(other.kind)) return false
        const o = positions[other.id]
        if (!o) return false
        const dx = o.x - pos.x
        const dy = o.y - pos.y
        return dx + 8 > x0 && dx - 8 < x1 && dy + 8 > y0 && dy - 8 < y1
      })
    if (!occupied(10, 12 + width, -6, 6)) return RIGHT_LABEL
    if (!occupied(-width / 2, width / 2, -22, -10)) return ABOVE_LABEL
    if (!occupied(-width / 2, width / 2, 10, 22)) return BELOW_LABEL
    return ABOVE_LABEL
  }

  const vw = CANVAS_W / zoom
  const vh = CANVAS_H / zoom
  const cx = center?.x ?? CANVAS_W / 2
  const cy = center?.y ?? CANVAS_H / 2
  const viewBox = `${cx - vw / 2} ${cy - vh / 2} ${vw} ${vh}`

  return (
    <svg
      viewBox={viewBox}
      className="bg-background block h-full w-full"
      role="group"
      aria-label={`Code graph — ${graph.nodes.length} nodes, ${graph.edges.length} edges, ${layout} layout`}
      onClick={() => onSelect(null)}
    >
      {graph.edges.map((edge, i) => {
        const from = positions[edge.source]
        const to = positions[edge.target]
        const a = graph.nodes.find((n) => n.id === edge.source)
        const b = graph.nodes.find((n) => n.id === edge.target)
        if (!from || !to || !a || !b) return null
        if (isKindHidden(a.kind) || isKindHidden(b.kind)) return null
        const sameCommunity = a.community === b.community
        const hidden =
          (visibleIds &&
            (!visibleIds.has(edge.source) || !visibleIds.has(edge.target))) ||
          (highlightCommunity &&
            (a.community !== highlightCommunity ||
              b.community !== highlightCommunity))
        return (
          <line
            key={i}
            x1={from.x}
            y1={from.y}
            x2={to.x}
            y2={to.y}
            stroke={
              sameCommunity
                ? nodeColor(a.community, a.kind)
                : "hsl(var(--border))"
            }
            strokeWidth={1.3}
            opacity={hidden ? 0.08 : sameCommunity ? 0.65 : 0.9}
            style={{ transition: "opacity 300ms" }}
          />
        )
      })}
      {graph.nodes.map((node) => {
        const pos = positions[node.id]
        if (!pos || isKindHidden(node.kind)) return null
        const isSelected = node.id === selectedId
        const isBlast = blastIds?.has(node.id) ?? false
        const inProcess = processIds?.has(node.id) ?? false
        const isDim = dimmed(node.id, node.community)
        return (
          <g
            key={node.id}
            role="button"
            tabIndex={0}
            aria-label={`${node.name} (${node.kind})`}
            className={cn(
              "group cursor-pointer focus-visible:outline-none",
              playing && "dm-graph-drift",
            )}
            style={{
              transform: `translate(${pos.x}px, ${pos.y}px)`,
              transition: "transform 400ms ease, opacity 300ms",
              opacity: isDim ? 0.18 : 1,
              animationDelay: playing
                ? `${(node.id.length % 5) * -1.3}s`
                : undefined,
            }}
            onClick={(e) => {
              e.stopPropagation()
              onSelect(node.id)
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault()
                onSelect(node.id)
              }
            }}
          >
            <title>{`${node.name} · ${node.kind} · ${node.file}`}</title>
            <circle
              data-focus-ring
              r={15}
              strokeWidth={2}
              className="stroke-ring fill-none opacity-0 group-focus-visible:opacity-100"
            />
            {isSelected && (
              <circle
                r={13}
                fill="none"
                stroke="hsl(var(--primary))"
                strokeWidth={1.6}
              />
            )}
            {isBlast && (
              <circle
                r={12}
                fill="none"
                stroke="hsl(var(--destructive))"
                strokeWidth={1.6}
                strokeDasharray="3 2"
              />
            )}
            {inProcess && !isSelected && (
              <circle
                r={11}
                fill="none"
                stroke="hsl(var(--foreground))"
                strokeWidth={1.2}
                strokeDasharray="2 2"
                opacity={0.7}
              />
            )}
            <circle
              r={8}
              fill={nodeColor(node.community, node.kind)}
              stroke="hsl(var(--card))"
              strokeWidth={2}
            />
            {(isSelected || isBlast || inProcess) &&
              (() => {
                const spot = labelSpot(node.id, node.name)
                return (
                  <text
                    x={spot.x}
                    y={spot.y}
                    textAnchor={spot.anchor}
                    className="font-mono"
                    fontSize={10}
                    fill="hsl(var(--foreground))"
                    // A halo in the canvas colour keeps the label legible
                    // where it crosses an edge or another node's ring.
                    stroke="hsl(var(--background))"
                    strokeWidth={3}
                    strokeLinejoin="round"
                    paintOrder="stroke"
                  >
                    {node.name}
                  </text>
                )
              })()}
          </g>
        )
      })}
    </svg>
  )
}
