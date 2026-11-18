import { useEffect, useLayoutEffect, useRef, useState, type KeyboardEvent } from "react"
import Graph from "graphology"
import Sigma from "sigma"
import type { NodeDisplayData } from "sigma/types"
import { EmptyState } from "@/components/darkmem"
import type {
  CodeNodeKind,
  DemoCodeCommunity,
  DemoCodeEdge,
  DemoCodeGraph,
  DemoCodeNode,
} from "@/features/code/types"
import {
  seededUnit,
  useGraphThemeTokens,
  type GraphThemeTokens,
} from "@/features/graph/lib/code-graph-theme"
import { blendHex, hexToRgba, restEdgeColor } from "@/features/graph/lib/graph-colors"
import { scaleSettings } from "@/features/graph/lib/graph-scale"
import {
  constellationFa2Settings,
  createConstellationRunner,
  type ConstellationRunner,
} from "@/features/graph/lib/constellation-runner"
import {
  createNodeGlowProgram,
  trackDensityGain,
  type GlowClock,
} from "@/features/graph/lib/node-glow-program"
import {
  attachBackdrop,
  coreOnScreen,
  WEBGL_UNAVAILABLE_MESSAGE,
} from "@/features/graph/lib/graph-backdrop"
import { startAmbientMotion } from "@/features/graph/lib/ambient-motion"

export interface CodeGlowCanvasProps {
  graph: DemoCodeGraph
  colorBy: "community" | "kind"
  selectedId: string | null
  onSelect: (id: string | null) => void
  visibleIds: Set<string> | null
  hiddenKinds?: ReadonlySet<CodeNodeKind>
  blastIds: Set<string> | null
  highlightCommunity: string | null
  processIds: Set<string> | null
  zoom: number // 1 = fitted view
}

export type CanvasKeyAction =
  | { type: "zoom"; factor: number }
  | { type: "pan"; dx: number; dy: number }
  | { type: "fit" }
  | { type: "clear" }

const KEY_ACTIONS: Record<string, CanvasKeyAction> = {
  "+": { type: "zoom", factor: 1.25 },
  "=": { type: "zoom", factor: 1.25 },
  "-": { type: "zoom", factor: 0.8 },
  ArrowLeft: { type: "pan", dx: -1, dy: 0 },
  ArrowRight: { type: "pan", dx: 1, dy: 0 },
  ArrowUp: { type: "pan", dx: 0, dy: -1 },
  ArrowDown: { type: "pan", dx: 0, dy: 1 },
  "0": { type: "fit" },
  Escape: { type: "clear" },
}

export function canvasKeyAction(key: string): CanvasKeyAction | null {
  return Object.prototype.hasOwnProperty.call(KEY_ACTIONS, key) ? KEY_ACTIONS[key]! : null
}

// The SVG canvas's tiers (code-canvas.tsx): structural, types, callables.
export const KIND_CHART: Record<CodeNodeKind, 1 | 2 | 3> = {
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

const HUB_DEGREE = 5
const LABEL_ZOOM_RATIO = 0.72
const CAMERA_MS = 400
const SELECTED_RATIO = 0.15
const PAN_FRACTION = 0.1
const DIM_ALPHA = 0.18
const DIM_EDGE_ALPHA = 0.08
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)"

export function drawnGraph(
  graph: DemoCodeGraph,
  hiddenKinds?: ReadonlySet<CodeNodeKind>,
): { nodes: DemoCodeNode[]; edges: DemoCodeEdge[] } {
  if (!hiddenKinds || hiddenKinds.size === 0) {
    return { nodes: graph.nodes, edges: graph.edges }
  }
  const nodes = graph.nodes.filter((n) => !hiddenKinds.has(n.kind))
  const kept = new Set(nodes.map((n) => n.id))
  const edges = graph.edges.filter((e) => kept.has(e.source) && kept.has(e.target))
  return { nodes, edges }
}

export function codeNodeColor(
  node: DemoCodeNode,
  colorBy: "community" | "kind",
  communities: DemoCodeCommunity[],
  chart: string[],
): string {
  if (colorBy === "community") {
    const community = communities.find((c) => c.id === node.community)
    return chart[(community?.chart ?? 1) - 1]!
  }
  return chart[KIND_CHART[node.kind] - 1]!
}

export function isDimmed(
  node: DemoCodeNode,
  visibleIds: Set<string> | null,
  highlightCommunity: string | null,
): boolean {
  if (visibleIds && !visibleIds.has(node.id)) return true
  if (highlightCommunity && node.community !== highlightCommunity) return true
  return false
}

export function showsLabel(o: {
  selected: boolean
  blast: boolean
  process: boolean
  degree: number
  cameraRatio: number
}): boolean {
  if (o.selected || o.blast || o.process) return true
  return o.degree >= HUB_DEGREE && o.cameraRatio < LABEL_ZOOM_RATIO
}

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(REDUCED_MOTION_QUERY).matches
}

function centreOn(sigma: Sigma, id: string) {
  const d = sigma.getNodeDisplayData(id)
  if (!d) return
  const target = { x: d.x, y: d.y, ratio: SELECTED_RATIO }
  if (prefersReducedMotion()) sigma.getCamera().setState(target)
  else void sigma.getCamera().animate(target, { duration: CAMERA_MS })
}

function drawOutlinedText(
  ctx: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  t: GraphThemeTokens,
) {
  ctx.font = `12px ${t.fontMono}`
  ctx.lineJoin = "round"
  ctx.lineWidth = 3
  ctx.strokeStyle = t.canvas
  ctx.strokeText(text, x, y)
  ctx.fillStyle = t.foreground
  ctx.fillText(text, x, y)
}

type CodeDisplayData = Partial<NodeDisplayData> & { _hover?: string }

export function CodeGlowCanvas({
  graph,
  colorBy,
  selectedId,
  onSelect,
  visibleIds,
  hiddenKinds,
  blastIds,
  highlightCommunity,
  processIds,
  zoom,
}: CodeGlowCanvasProps) {
  const tokens = useGraphThemeTokens()
  const containerRef = useRef<HTMLDivElement | null>(null)
  const sigmaRef = useRef<Sigma | null>(null)
  const clockRef = useRef<GlowClock>({ time: 0 })
  const runnerRef = useRef<ConstellationRunner | null>(null)
  // A node chosen while the core still settles keeps moving, so the camera
  // follows it until the run ends or the reader moves the camera.
  const followRef = useRef(false)
  const zoomRef = useRef(zoom)
  const [webglFailed, setWebglFailed] = useState(false)

  const tokensRef = useRef(tokens)
  const onSelectRef = useRef(onSelect)
  const emphasisRef = useRef({ selectedId, visibleIds, blastIds, highlightCommunity, processIds })
  // Layout effects run before this commit's passive effects, so the build and
  // the refresh below read current values.
  useLayoutEffect(() => {
    tokensRef.current = tokens
    onSelectRef.current = onSelect
    emphasisRef.current = { selectedId, visibleIds, blastIds, highlightCommunity, processIds }
  })

  const drawn = drawnGraph(graph, hiddenKinds)
  const themeKey = `${tokens.isDark}:${tokens.canvas}:${tokens.nebula}:${tokens.border}:${tokens.chart.join(",")}`

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const t = tokensRef.current
    const { nodes, edges } = drawnGraph(graph, hiddenKinds)

    const g = new Graph()
    const degree = new Map<string, number>()
    for (const e of edges) {
      degree.set(e.source, (degree.get(e.source) ?? 0) + 1)
      degree.set(e.target, (degree.get(e.target) ?? 0) + 1)
    }
    for (const n of nodes) {
      if (g.hasNode(n.id)) continue
      g.addNode(n.id, {
        x: seededUnit(n.id, 1) * 100,
        y: seededUnit(n.id, 2) * 100,
        size: 3 + 0.5 * Math.min(degree.get(n.id) ?? 0, 12),
        color: codeNodeColor(n, colorBy, graph.communities, t.chart),
        type: "glow",
        label: n.name,
        name: n.name,
        kind: n.kind,
        file: n.file,
        community: n.community,
        degree: degree.get(n.id) ?? 0,
      })
    }
    for (const e of edges) {
      if (e.source === e.target || g.hasEdge(e.source, e.target)) continue
      const sameCommunity =
        g.getNodeAttribute(e.source, "community") === g.getNodeAttribute(e.target, "community")
      const full = sameCommunity ? (g.getNodeAttribute(e.source, "color") as string) : t.border
      g.addEdge(e.source, e.target, { _fullColor: full, color: restEdgeColor(full, t.isDark) })
    }

    const scale = scaleSettings(g.order, g.size)
    const runner: ConstellationRunner = createConstellationRunner(g, {
      layoutMs: scale.layoutMs,
      onStop: () => {
        followRef.current = false
      },
      fa2Settings: constellationFa2Settings(g, scale),
    })

    const nodeOf = (id: string): DemoCodeNode => ({
      id,
      name: g.getNodeAttribute(id, "name") as string,
      kind: g.getNodeAttribute(id, "kind") as CodeNodeKind,
      file: g.getNodeAttribute(id, "file") as string,
      community: g.getNodeAttribute(id, "community") as string,
    })

    let sigma: Sigma
    try {
      sigma = new Sigma(g, container, {
        nodeProgramClasses: {
          glow: createNodeGlowProgram({ additive: t.isDark, clock: clockRef.current }),
        },
        defaultNodeType: "glow",
        renderEdgeLabels: false,
        labelFont: t.fontMono,
        zIndex: true,
        defaultDrawNodeLabel: (ctx, data) => {
          if (!data.label) return
          drawOutlinedText(ctx, data.label, data.x + data.size + 3, data.y + 4, tokensRef.current)
        },
        defaultDrawNodeHover: (ctx, data) => {
          const text = (data as CodeDisplayData)._hover
          if (!text) return
          drawOutlinedText(ctx, text, data.x + data.size + 3, data.y + 4, tokensRef.current)
        },
        nodeReducer: (id, data) => {
          const e = emphasisRef.current
          const tk = tokensRef.current
          const node = nodeOf(id)
          const res: CodeDisplayData = { ...data }
          res._hover = `${node.name} · ${node.kind} · ${node.file}`
          if (isDimmed(node, e.visibleIds, e.highlightCommunity)) {
            res.color = blendHex(tk.canvas, data.color as string, DIM_ALPHA)
          }
          const shown = showsLabel({
            selected: e.selectedId === id,
            blast: e.blastIds?.has(id) ?? false,
            process: e.processIds?.has(id) ?? false,
            degree: g.getNodeAttribute(id, "degree") as number,
            cameraRatio: sigmaRef.current?.getCamera().ratio ?? 1,
          })
          res.label = shown ? node.name : ""
          // Labels follow showsLabel alone, not sigma's size threshold and
          // label grid, which would drop a selected leaf's name.
          res.forceLabel = shown
          return res
        },
        edgeReducer: (edge, data) => {
          const e = emphasisRef.current
          const [s, tg] = g.extremities(edge)
          const res = { ...data }
          if (
            isDimmed(nodeOf(s), e.visibleIds, e.highlightCommunity) ||
            isDimmed(nodeOf(tg), e.visibleIds, e.highlightCommunity)
          ) {
            res.color = hexToRgba(data._fullColor as string, DIM_EDGE_ALPHA)
          } else if (e.selectedId !== null && (s === e.selectedId || tg === e.selectedId)) {
            res.color = data._fullColor as string
            res.zIndex = 1
          }
          return res
        },
      })
    } catch {
      runner.kill()
      sigmaRef.current = null
      setWebglFailed(true)
      return
    }
    setWebglFailed(false)
    sigmaRef.current = sigma

    let belowLabelRatio = sigma.getCamera().ratio < LABEL_ZOOM_RATIO
    const onCameraUpdated = () => {
      const below = sigma.getCamera().ratio < LABEL_ZOOM_RATIO
      if (below === belowLabelRatio) return
      belowLabelRatio = below
      sigma.refresh()
    }
    sigma.getCamera().on("updated", onCameraUpdated)
    sigma.on("clickNode", ({ node }) => onSelectRef.current(node))
    sigma.on("clickStage", () => onSelectRef.current(null))

    const overlay = document.createElement("canvas")
    Object.assign(overlay.style, { position: "absolute", inset: "0", pointerEvents: "none" })
    sigma.getContainer().appendChild(overlay)
    const octx = overlay.getContext("2d")
    const ring = (id: string, color: string, dash: number[]) => {
      if (!octx || !g.hasNode(id)) return
      const d = sigma.getNodeDisplayData(id)
      if (!d) return
      const vp = sigma.framedGraphToViewport(d)
      octx.beginPath()
      octx.arc(vp.x, vp.y, sigma.scaleSize(d.size) + 4, 0, Math.PI * 2)
      octx.setLineDash(dash)
      octx.strokeStyle = color
      octx.lineWidth = 2
      octx.stroke()
    }
    const drawChrome = () => {
      if (!octx) return
      const { width, height } = sigma.getDimensions()
      const dpr = window.devicePixelRatio || 1
      if (overlay.width !== Math.round(width * dpr) || overlay.height !== Math.round(height * dpr)) {
        overlay.width = Math.round(width * dpr)
        overlay.height = Math.round(height * dpr)
        overlay.style.width = `${width}px`
        overlay.style.height = `${height}px`
      }
      octx.setTransform(dpr, 0, 0, dpr, 0, 0)
      octx.clearRect(0, 0, width, height)
      const e = emphasisRef.current
      const tk = tokensRef.current
      for (const id of e.processIds ?? []) ring(id, hexToRgba(tk.foreground, 0.7), [2, 2])
      for (const id of e.blastIds ?? []) ring(id, tk.destructiveSolid, [3, 2])
      if (e.selectedId) ring(e.selectedId, tk.primary, [])
    }
    sigma.on("afterRender", drawChrome)
    sigma.on("kill", () => overlay.remove())

    trackDensityGain(sigma, g, runner.classification, clockRef.current)
    // The constructor's synchronous first frame ran before this handler.
    sigma.scheduleRender()

    const detachBackdrop = attachBackdrop(sigma, () => coreOnScreen(sigma, runner.coreRadius), {
      canvas: t.canvas,
      nebula: t.nebula,
      isDark: t.isDark,
    })
    const stopMotion = startAmbientMotion({
      nodeCount: g.order,
      onFrame: (sec) => {
        clockRef.current.time = sec
        sigma.scheduleRender()
      },
    })
    sigma.on("beforeRender", () => {
      const id = emphasisRef.current.selectedId
      const camera = sigma.getCamera()
      if (!followRef.current || !id || !g.hasNode(id) || camera.isAnimated()) return
      const d = sigma.getNodeDisplayData(id)
      if (d && (Math.abs(d.x - camera.x) > 1e-6 || Math.abs(d.y - camera.y) > 1e-6)) {
        camera.setState({ x: d.x, y: d.y })
      }
    })
    const stopFollowing = () => {
      followRef.current = false
    }
    for (const event of ["wheelStage", "downStage", "wheelNode", "downNode"] as const) {
      sigma.on(event, stopFollowing)
    }
    runnerRef.current = runner
    runner.start()

    return () => {
      stopMotion()
      detachBackdrop()
      runner.kill()
      // kill() leaves the camera, and an animation still in flight keeps
      // emitting updates to listeners that would refresh a dead instance.
      sigma.getCamera().removeListener("updated", onCameraUpdated)
      sigma.kill()
      sigmaRef.current = null
    }
    // Theme is keyed on its primitives: the tokens object is fresh on every
    // style mutation the theme observer sees.
  }, [graph, colorBy, hiddenKinds, themeKey])

  useEffect(() => {
    sigmaRef.current?.refresh()
  }, [visibleIds, blastIds, highlightCommunity, processIds])

  useEffect(() => {
    const sigma = sigmaRef.current
    if (!sigma) return
    sigma.refresh()
    if (!selectedId || !sigma.getGraph().hasNode(selectedId)) return
    centreOn(sigma, selectedId)
    followRef.current = runnerRef.current?.isRunning() ?? false
  }, [selectedId])

  useEffect(() => {
    const sigma = sigmaRef.current
    // Only a change moves the camera: on mount this would cancel the move to
    // a node selected from the start.
    if (!sigma || zoomRef.current === zoom) return
    zoomRef.current = zoom
    const target = { ratio: 1 / zoom }
    if (prefersReducedMotion()) sigma.getCamera().setState(target)
    else void sigma.getCamera().animate(target, { duration: CAMERA_MS })
  }, [zoom])

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const action = canvasKeyAction(event.key)
    if (!action) return
    event.preventDefault()
    followRef.current = false
    if (action.type === "clear") {
      onSelect(null)
      return
    }
    const sigma = sigmaRef.current
    if (!sigma) return
    const camera = sigma.getCamera()
    // sigma's animate divides by the duration, so 0 would yield NaN; reduced
    // motion sets the end state directly instead.
    const instant = prefersReducedMotion()
    const move = (state: { x?: number; y?: number; ratio?: number; angle?: number }) => {
      if (instant) camera.setState(state)
      else void camera.animate(state, { duration: CAMERA_MS })
    }
    if (action.type === "zoom") {
      if (instant) camera.setState({ ratio: camera.ratio / action.factor })
      else if (action.factor > 1)
        void camera.animatedZoom({ factor: action.factor, duration: CAMERA_MS })
      else void camera.animatedUnzoom({ factor: 1 / action.factor, duration: CAMERA_MS })
    } else if (action.type === "pan") {
      const { width, height } = sigma.getDimensions()
      const centre = sigma.viewportToFramedGraph({
        x: width / 2 + action.dx * PAN_FRACTION * width,
        y: height / 2 + action.dy * PAN_FRACTION * height,
      })
      move({ x: centre.x, y: centre.y })
    } else if (instant) {
      camera.setState({ x: 0.5, y: 0.5, ratio: 1, angle: 0 })
    } else {
      void camera.animatedReset({ duration: CAMERA_MS })
    }
  }

  return (
    <div
      role="group"
      tabIndex={0}
      aria-label={`Code graph — ${drawn.nodes.length} nodes, ${drawn.edges.length} edges`}
      onKeyDown={onKeyDown}
      className="focus-visible:ring-ring relative h-full w-full outline-none focus-visible:ring-2"
    >
      <div ref={containerRef} className="absolute inset-0 bg-transparent" />
      {webglFailed && (
        <div className="absolute inset-0 flex items-center justify-center">
          <EmptyState kind="failed" title={WEBGL_UNAVAILABLE_MESSAGE} />
        </div>
      )}
    </div>
  )
}
