import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react"
import { Link } from "@tanstack/react-router"
import {
  ArrowRight,
  Crosshair,
  ListTree,
  Maximize,
  Minus,
  Orbit,
  Plus,
  Search,
  SearchX,
  Share2,
  Waypoints,
  X,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import { useSetPageChrome } from "@/components/app-chrome"
import { EmptyState, listItemClass } from "@/components/darkmem"
import { cn } from "darkraise-ui/lib"
import { useDemoMemoryGraph } from "@/demo/hooks"
import {
  ALL_PROJECTS,
  projectLabel,
  useProjectStore,
} from "@/stores/project-store"
import {
  layoutGraph,
  matchEntities,
  scopeMemoryGraph,
  type GraphLayoutMode,
} from "@/demo/explore"
import type { MemoryEntityType } from "@/demo/types"
import { LABEL_OFFSET_X, labelSide, placeLabels } from "../lib/label-placement"
import {
  panView,
  viewBoxAttr,
  zoomViewAt,
  zoomViewCentered,
  type ViewBox,
} from "../lib/viewbox"

// Layout canvases in viewBox units: landscape for wide panes, portrait for
// a phone-width pane, so a narrow screen does not shrink a landscape layout
// to a sliver (labels rendered at ~5px at 390px wide).
const LANDSCAPE = { w: 680, h: 400 }
const PORTRAIT = { w: 420, h: 600 }
const ZOOM_STEP = 1.25
const LAYOUTS: GraphLayoutMode[] = ["force", "tree", "circles"]

// The four non-caution chart members (S17): an entity dot is never
// misreadable as the language's caution colour, so --chart-4 is out. Colour
// encodes entity type only; topic halos are a neutral tint, so a cluster is
// never read as "all tools" because its halo shares the tool colour.
const TYPE_CHART: Record<MemoryEntityType, number> = {
  tool: 1,
  database: 2,
  concept: 3,
  algorithm: 5,
}

const chartVar = (n: number) => `var(--chart-${n})`

/**
 * Full-bleed explorer: a toolbar strip on top, the canvas filling the rest
 * of the content area edge-to-edge (legend as a bottom overlay), and the
 * inspector + community navigator as a full-height side column.
 */
export function MemoryGraphExplorer() {
  useSetPageChrome({
    icon: Waypoints,
    title: "Memory Graph",
  })
  const graph = useDemoMemoryGraph()
  const project = useProjectStore((s) => s.activeProject)
  const [layout, setLayout] = useState<GraphLayoutMode>("force")
  const [query, setQuery] = useState("")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [focusTopic, setFocusTopic] = useState<string | null>(null)
  const [revealedId, setRevealedId] = useState<string | null>(null)
  const [portrait, setPortrait] = useState(false)
  const canvasRef = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const { w: W, h: H } = portrait ? PORTRAIT : LANDSCAPE
  const base = useMemo<ViewBox>(() => ({ x: 0, y: 0, w: W, h: H }), [W, H])
  // The zoom/pan view belongs to one canvas + layout + scope; a change of
  // any of them starts again from the whole graph.
  const viewKey = `${W}x${H}:${layout}:${project ?? ""}`
  const [viewState, setViewState] = useState<{ key: string; view: ViewBox }>({
    key: viewKey,
    view: base,
  })
  const view = viewState.key === viewKey ? viewState.view : base
  const setView = (next: ViewBox | ((current: ViewBox) => ViewBox)) =>
    setViewState((s) => {
      const current = s.key === viewKey ? s.view : base
      return {
        key: viewKey,
        view: typeof next === "function" ? next(current) : next,
      }
    })

  useEffect(() => {
    setSelectedId(null)
    setFocusTopic(null)
  }, [project])

  // Pick the layout canvas from the pane's shape.
  useEffect(() => {
    const node = canvasRef.current
    if (!node || typeof ResizeObserver === "undefined") return
    const observer = new ResizeObserver(([entry]) => {
      if (!entry) return
      const { width, height } = entry.contentRect
      if (width > 0 && height > 0) setPortrait(width / height < 0.9)
    })
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  // Escape clears the selection unless it was meant for a field or overlay.
  useEffect(() => {
    if (!selectedId) return
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape" || event.defaultPrevented) return
      const target = event.target
      if (
        target instanceof HTMLElement &&
        target.closest("input, textarea, select, [role=dialog], [role=listbox]")
      )
        return
      setSelectedId(null)
    }
    document.addEventListener("keydown", onKeyDown)
    return () => document.removeEventListener("keydown", onKeyDown)
  }, [selectedId])

  // Wheel zoom about the cursor. Registered natively: React's wheel
  // listener is passive and cannot stop the page from scrolling.
  useEffect(() => {
    const svg = svgRef.current
    if (!svg) return
    const onWheel = (event: WheelEvent) => {
      event.preventDefault()
      const point = toUserPoint(svg, event.clientX, event.clientY)
      if (!point) return
      const factor = Math.exp(event.deltaY * 0.0015)
      setView((v) => zoomViewAt(v, base, factor, point.x, point.y))
    }
    svg.addEventListener("wheel", onWheel, { passive: false })
    return () => svg.removeEventListener("wheel", onWheel)
  })

  // Drag to pan, two fingers to pinch. A drag that moved suppresses the
  // background click that would otherwise clear the selection.
  const pointers = useRef(new Map<number, { x: number; y: number }>())
  const dragged = useRef(false)
  const onPointerDown = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (event.pointerType === "mouse" && event.button !== 0) return
    pointers.current.set(event.pointerId, {
      x: event.clientX,
      y: event.clientY,
    })
    dragged.current = false
  }
  const onPointerMove = (event: ReactPointerEvent<SVGSVGElement>) => {
    const svg = svgRef.current
    const previous = pointers.current.get(event.pointerId)
    if (!svg || !previous) return
    const current = { x: event.clientX, y: event.clientY }
    const others = [...pointers.current.entries()].filter(
      ([id]) => id !== event.pointerId,
    )
    const scale = userUnitsPerPixel(svg)
    if (others.length === 0) {
      const dx = current.x - previous.x
      const dy = current.y - previous.y
      if (!dragged.current && Math.hypot(dx, dy) < 3) return
      if (!dragged.current) svg.setPointerCapture(event.pointerId)
      dragged.current = true
      setView((v) => panView(v, dx * scale, dy * scale))
    } else {
      const other = others[0]![1]
      const before = Math.hypot(previous.x - other.x, previous.y - other.y)
      const after = Math.hypot(current.x - other.x, current.y - other.y)
      const mid = toUserPoint(
        svg,
        (current.x + other.x) / 2,
        (current.y + other.y) / 2,
      )
      dragged.current = true
      if (before > 0 && after > 0 && mid) {
        setView((v) => zoomViewAt(v, base, before / after, mid.x, mid.y))
      }
    }
    pointers.current.set(event.pointerId, current)
  }
  const onPointerEnd = (event: ReactPointerEvent<SVGSVGElement>) => {
    pointers.current.delete(event.pointerId)
  }

  const scoped = useMemo(
    () => (project === ALL_PROJECTS ? graph : scopeMemoryGraph(graph, project)),
    [graph, project],
  )
  const matched = useMemo(() => matchEntities(scoped, query), [scoped, query])
  const positions = useMemo(
    () =>
      layoutGraph(
        scoped.entities.map((e) => ({ id: e.id, group: e.topic })),
        scoped.relations,
        layout,
        W,
        H,
      ),
    [scoped, layout, W, H],
  )
  const labelled = useMemo(
    () =>
      placeLabels(
        scoped.entities.flatMap((e) => {
          const pos = positions[e.id]
          return pos ? [{ id: e.id, x: pos.x, y: pos.y, text: e.name }] : []
        }),
        W,
      ),
    [scoped, positions, W],
  )

  // Topic halos: centroid + spread of each topic's members. Communities
  // render as halos behind the cluster, never as clickable nodes.
  const halos = useMemo(() => {
    if (layout === "tree") return []
    return scoped.topics.flatMap((topic) => {
      const points = scoped.entities
        .filter((e) => e.topic === topic.id)
        .map((e) => positions[e.id])
        .filter((p): p is { x: number; y: number } => p !== undefined)
      if (points.length === 0) return []
      const cx = points.reduce((s, p) => s + p.x, 0) / points.length
      const cy = points.reduce((s, p) => s + p.y, 0) / points.length
      const rx = Math.max(...points.map((p) => Math.abs(p.x - cx)), 34) + 30
      const ry = Math.max(...points.map((p) => Math.abs(p.y - cy)), 30) + 26
      return [{ topic, cx, cy, rx, ry }]
    })
  }, [scoped, positions, layout])

  const searchActive = query.trim() !== ""

  const selected = scoped.entities.find((e) => e.id === selectedId)
  const selectedRelations = useMemo(() => {
    if (!selected) return []
    return scoped.relations
      .filter((r) => r.source === selected.id || r.target === selected.id)
      .map((r) => {
        const otherId = r.source === selected.id ? r.target : r.source
        const other = scoped.entities.find((e) => e.id === otherId)
        return other
          ? {
              rel_type: r.rel_type,
              outgoing: r.source === selected.id,
              other,
            }
          : null
      })
      .filter((r): r is NonNullable<typeof r> => r !== null)
  }, [scoped, selected])

  const dimmed = (topicId: string) =>
    focusTopic !== null && topicId !== focusTopic

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* toolbar strip */}
      <div className="border-border bg-card flex flex-wrap items-center gap-2.5 border-b px-4 py-2.5">
        <Input
          prefix={<Search aria-hidden className="h-4 w-4" />}
          placeholder="Search entities…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          groupClassName="w-64"
          aria-label="Search entities"
        />
        {searchActive && (
          <span className="text-muted-foreground font-mono text-sm whitespace-nowrap">
            {matched.size} {matched.size === 1 ? "entity" : "entities"} matched
          </span>
        )}
        <ToggleGroup
          type="single"
          size="sm"
          value={layout}
          onValueChange={(value) => {
            if (LAYOUTS.includes(value as GraphLayoutMode))
              setLayout(value as GraphLayoutMode)
          }}
          aria-label="Graph layout"
        >
          <ToggleGroupItem value="force">
            <Share2 aria-hidden className="mr-1 h-3.5 w-3.5" />
            Force
          </ToggleGroupItem>
          <ToggleGroupItem value="tree">
            <ListTree aria-hidden className="mr-1 h-3.5 w-3.5" />
            Tree
          </ToggleGroupItem>
          <ToggleGroupItem value="circles">
            <Orbit aria-hidden className="mr-1 h-3.5 w-3.5" />
            Community
          </ToggleGroupItem>
        </ToggleGroup>
        <span className="text-muted-foreground ml-auto font-mono text-sm whitespace-nowrap">
          {scoped.entities.length} entities · {scoped.relations.length}{" "}
          relations · {scoped.topics.length} topics
        </span>
      </div>

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        {/* canvas — edge-to-edge, legend overlaid at the bottom */}
        <div className="relative flex min-w-0 flex-1 flex-col">
          <div
            ref={canvasRef}
            className="relative min-h-[60vh] min-w-0 flex-1 lg:min-h-72"
          >
            {scoped.entities.length === 0 ? (
              <div className="flex h-full items-center justify-center p-6">
                <EmptyState
                  kind="empty"
                  icon={Waypoints}
                  title="No entity graph yet"
                  description={`${project === ALL_PROJECTS ? "No project" : `Project ${project}`} has no memories yet. The graph fills in as memories are captured.`}
                />
              </div>
            ) : (
              <>
                <svg
                  ref={svgRef}
                  viewBox={viewBoxAttr(view)}
                  className="absolute inset-0 h-full w-full cursor-grab touch-none select-none active:cursor-grabbing"
                  role="group"
                  aria-label={`Entity graph for ${project === ALL_PROJECTS ? projectLabel(project) : `project ${project}`}: ${scoped.entities.length} entities in ${scoped.topics.length} topic clusters, ${layout} layout`}
                  onPointerDown={onPointerDown}
                  onPointerMove={onPointerMove}
                  onPointerUp={onPointerEnd}
                  onPointerCancel={onPointerEnd}
                  onClick={() => {
                    if (dragged.current) {
                      dragged.current = false
                      return
                    }
                    setSelectedId(null)
                  }}
                >
                  {halos.map(({ topic, cx, cy, rx, ry }) => (
                    <ellipse
                      key={topic.id}
                      cx={cx}
                      cy={cy}
                      rx={rx}
                      ry={ry}
                      fill="hsl(var(--muted-foreground))"
                      fillOpacity={dimmed(topic.id) ? 0.02 : 0.07}
                      stroke="hsl(var(--muted-foreground))"
                      strokeOpacity={dimmed(topic.id) ? 0.15 : 0.5}
                      strokeWidth={1.3}
                      strokeDasharray="4 3"
                      style={{
                        transition: "fill-opacity 300ms, stroke-opacity 300ms",
                      }}
                    />
                  ))}
                  {scoped.relations.map((rel, i) => {
                    const from = positions[rel.source]
                    const to = positions[rel.target]
                    const a = scoped.entities.find((e) => e.id === rel.source)
                    const b = scoped.entities.find((e) => e.id === rel.target)
                    if (!from || !to || !a || !b) return null
                    const cross = a.topic !== b.topic
                    const dim = dimmed(a.topic) || dimmed(b.topic)
                    return (
                      <line
                        key={i}
                        x1={from.x}
                        y1={from.y}
                        x2={to.x}
                        y2={to.y}
                        stroke={
                          cross
                            ? "hsl(var(--foreground))"
                            : "hsl(var(--muted-foreground))"
                        }
                        strokeOpacity={dim ? 0.1 : cross ? 0.55 : 0.6}
                        strokeWidth={cross ? 1.5 : 1.3}
                        strokeDasharray={cross ? "5 3" : undefined}
                        style={{ transition: "stroke-opacity 300ms" }}
                      >
                        <title>{`${a.name} ${rel.rel_type} ${b.name}`}</title>
                      </line>
                    )
                  })}
                  {scoped.entities.map((entity) => {
                    const pos = positions[entity.id]
                    if (!pos) return null
                    const isMatch = matched.has(entity.id)
                    const isSelected = entity.id === selectedId
                    // A live query dims every non-match, like a topic focus.
                    const dim =
                      dimmed(entity.topic) ||
                      (searchActive && !isMatch && !isSelected)
                    const placedSide = labelled.get(entity.id)
                    const showLabel =
                      placedSide !== undefined ||
                      (searchActive && isMatch) ||
                      revealedId === entity.id ||
                      isSelected
                    const side =
                      placedSide ??
                      labelSide(
                        {
                          id: entity.id,
                          x: pos.x,
                          y: pos.y,
                          text: entity.name,
                        },
                        W,
                      )
                    return (
                      <g
                        key={entity.id}
                        role="button"
                        tabIndex={0}
                        aria-label={`${entity.name} (${entity.entity_type})`}
                        className="group cursor-pointer focus-visible:outline-none [&:focus:not(:focus-visible)]:outline-none"
                        style={{
                          transform: `translate(${pos.x}px, ${pos.y}px)`,
                          transition: "transform 400ms ease, opacity 300ms",
                          opacity: dim ? 0.25 : 1,
                        }}
                        onClick={(e) => {
                          e.stopPropagation()
                          setSelectedId(entity.id)
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault()
                            setSelectedId(entity.id)
                          }
                        }}
                        onMouseEnter={() => setRevealedId(entity.id)}
                        onMouseLeave={() => setRevealedId(null)}
                        onFocus={() => setRevealedId(entity.id)}
                        onBlur={() => setRevealedId(null)}
                      >
                        <title>{`${entity.name} · ${entity.entity_type}`}</title>
                        <circle
                          data-focus-ring
                          r={16}
                          strokeWidth={2}
                          className="stroke-ring fill-none opacity-0 group-focus-visible:opacity-100"
                        />
                        {isSelected && (
                          <circle
                            r={14}
                            fill="none"
                            stroke="hsl(var(--primary))"
                            strokeWidth={1.6}
                          />
                        )}
                        <circle
                          r={9}
                          fill={chartVar(TYPE_CHART[entity.entity_type])}
                          stroke={
                            isMatch ? "hsl(var(--ring))" : "hsl(var(--card))"
                          }
                          strokeWidth={isMatch ? 3 : 2}
                        />
                        {showLabel && (
                          <text
                            x={
                              side === "right"
                                ? LABEL_OFFSET_X
                                : -LABEL_OFFSET_X
                            }
                            y={4}
                            textAnchor={side === "right" ? "start" : "end"}
                            fontSize={10.5}
                            fontWeight={
                              searchActive && isMatch ? 600 : undefined
                            }
                            className="font-mono"
                            fill="hsl(var(--foreground))"
                          >
                            {entity.name}
                          </text>
                        )}
                      </g>
                    )
                  })}
                </svg>
                <div
                  role="toolbar"
                  aria-label="Zoom"
                  className="bg-background/80 border-border absolute top-2 right-2 flex flex-col gap-1 rounded-md border p-1 backdrop-blur-sm"
                >
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Zoom in"
                    onClick={() =>
                      setView((v) => zoomViewCentered(v, base, 1 / ZOOM_STEP))
                    }
                  >
                    <Plus aria-hidden className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Zoom out"
                    onClick={() =>
                      setView((v) => zoomViewCentered(v, base, ZOOM_STEP))
                    }
                  >
                    <Minus aria-hidden className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Fit graph"
                    onClick={() => setView(base)}
                  >
                    <Maximize aria-hidden className="h-4 w-4" />
                  </Button>
                </div>
                {searchActive && matched.size === 0 && (
                  <div className="pointer-events-none absolute inset-x-0 top-3 flex justify-center px-14">
                    <p
                      role="status"
                      className="bg-background/90 border-border text-muted-foreground inline-flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm shadow-sm"
                    >
                      <SearchX aria-hidden className="h-4 w-4 shrink-0" />
                      No entity matches &ldquo;{query.trim()}&rdquo;
                    </p>
                  </div>
                )}
              </>
            )}
          </div>
          {scoped.entities.length > 0 && (
            <div className="bg-background/75 text-muted-foreground border-border flex flex-wrap gap-x-4 gap-y-1 border-t px-4 py-2 text-sm backdrop-blur-sm lg:absolute lg:inset-x-0 lg:bottom-0 lg:border-t-0">
              {(Object.keys(TYPE_CHART) as MemoryEntityType[]).map((type) => (
                <span key={type} className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2.5 w-2.5 rounded-full"
                    style={{ background: chartVar(TYPE_CHART[type]) }}
                  />
                  {type}
                </span>
              ))}
              <span className="inline-flex items-center gap-1.5">
                <span className="border-muted-foreground/70 w-4 border-t-[1.4px]" />
                relation, within topic
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="border-foreground/70 w-4 border-t-[1.6px] border-dashed" />
                relation, cross-topic
              </span>
              <span className="inline-flex items-center gap-1.5">
                <TopicHaloGlyph />
                topic cluster
              </span>
            </div>
          )}
        </div>

        {/* inspector + community navigator — full-height side column */}
        <div className="border-border bg-card min-h-0 shrink-0 overflow-y-auto border-t lg:w-80 lg:border-t-0 lg:border-l">
          <div className="border-border border-b">
            <div className="border-border bg-muted/30 flex min-h-10 items-center gap-2 border-b px-3 py-1">
              <Crosshair
                aria-hidden
                className="text-muted-foreground h-3.5 w-3.5"
              />
              <span className="text-sm font-semibold">Inspector</span>
              {selected && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="ml-auto h-7 w-7"
                  aria-label="Deselect entity"
                  title="Deselect (Esc)"
                  onClick={() => setSelectedId(null)}
                >
                  <X aria-hidden className="h-4 w-4" />
                </Button>
              )}
            </div>
            {selected ? (
              <div className="space-y-2 p-3">
                <p className="font-mono text-sm font-semibold">
                  {selected.name}
                </p>
                <p className="text-muted-foreground text-sm">
                  type:{" "}
                  <span className="font-mono">{selected.entity_type}</span>
                  <br />
                  topic:{" "}
                  {scoped.topics.find((t) => t.id === selected.topic)?.label ??
                    selected.topic}
                </p>
                <Link
                  to="/memories"
                  search={{ q: selected.name }}
                  className="text-primary-text focus-visible:ring-ring inline-flex items-center gap-1 rounded-sm text-sm underline-offset-4 hover:underline focus-visible:ring-2 focus-visible:outline-none"
                >
                  Search memories mentioning {selected.name}
                  <ArrowRight aria-hidden className="h-3.5 w-3.5" />
                </Link>
                <p className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
                  relations ({selectedRelations.length})
                </p>
                <ul className="space-y-1">
                  {selectedRelations.map((rel, i) => (
                    <li key={i}>
                      <button
                        type="button"
                        aria-label={`${rel.outgoing ? selected.name : rel.other.name} ${rel.rel_type} ${rel.outgoing ? rel.other.name : selected.name}; inspect ${rel.other.name}`}
                        className="hover:bg-muted/50 border-border focus-visible:ring-ring flex w-full flex-wrap items-center gap-x-1.5 gap-y-0.5 rounded-sm border px-2 py-1 text-left font-mono text-sm focus-visible:ring-2 focus-visible:outline-none"
                        onClick={() => setSelectedId(rel.other.id)}
                      >
                        <span
                          className={cn(
                            "min-w-0 truncate",
                            rel.outgoing && "text-muted-foreground",
                          )}
                        >
                          {rel.outgoing ? "this" : rel.other.name}
                        </span>
                        <span className="text-muted-foreground text-xs">
                          → {rel.rel_type} →
                        </span>
                        <span
                          className={cn(
                            "min-w-0 truncate",
                            !rel.outgoing && "text-muted-foreground",
                          )}
                        >
                          {rel.outgoing ? rel.other.name : "this"}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-muted-foreground p-3 text-sm">
                Click an entity node to inspect its type, topic, and relations.
                Drag to pan; scroll or pinch to zoom.
              </p>
            )}
          </div>

          <div>
            <div className="border-border bg-muted/30 flex items-center gap-1.5 border-b px-3 py-2">
              <Waypoints
                aria-hidden
                className="text-muted-foreground h-3.5 w-3.5 shrink-0"
              />
              <span className="min-w-0 text-sm leading-tight font-semibold">
                Community navigator
              </span>
              <span className="text-muted-foreground ml-auto font-mono text-xs whitespace-nowrap">
                {scoped.topics.length} topics
              </span>
            </div>
            <div className="space-y-2 p-3">
              {scoped.topics.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  No communities detected yet.
                </p>
              ) : (
                scoped.topics.map((topic) => {
                  const members = scoped.entities.filter(
                    (e) => e.topic === topic.id,
                  ).length
                  return (
                    <div
                      key={topic.id}
                      className={listItemClass({
                        className: cn(
                          "flex items-start gap-2 p-2",
                          focusTopic === topic.id &&
                            "border-primary/45 bg-primary/5",
                        ),
                      })}
                    >
                      <TopicHaloGlyph className="mt-1" />
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm font-semibold">
                          {topic.label}
                        </span>
                        <span className="text-muted-foreground block font-mono text-xs">
                          {members} entities · detected {topic.detected}
                        </span>
                      </span>
                      <button
                        type="button"
                        className={cn(
                          "inline-flex shrink-0 items-center gap-1 font-mono text-xs",
                          focusTopic === topic.id
                            ? "text-primary-text"
                            : "text-muted-foreground hover:text-foreground",
                        )}
                        onClick={() =>
                          setFocusTopic((cur) =>
                            cur === topic.id ? null : topic.id,
                          )
                        }
                      >
                        <Crosshair aria-hidden className="h-3 w-3" />
                        {focusTopic === topic.id ? "Unfocus" : "Focus"}
                      </button>
                    </div>
                  )
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/** The legend/navigator mark for a topic: the halo's dashed neutral ellipse. */
function TopicHaloGlyph({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden
      viewBox="0 0 16 10"
      className={cn("h-2.5 w-4 shrink-0", className)}
    >
      <ellipse
        cx={8}
        cy={5}
        rx={7}
        ry={4}
        fill="hsl(var(--muted-foreground))"
        fillOpacity={0.12}
        stroke="hsl(var(--muted-foreground))"
        strokeWidth={1.2}
        strokeDasharray="2.5 1.5"
      />
    </svg>
  )
}

function toUserPoint(
  svg: SVGSVGElement,
  clientX: number,
  clientY: number,
): { x: number; y: number } | null {
  const ctm = svg.getScreenCTM()
  if (!ctm) return null
  const point = new DOMPoint(clientX, clientY).matrixTransform(ctm.inverse())
  return { x: point.x, y: point.y }
}

function userUnitsPerPixel(svg: SVGSVGElement): number {
  const ctm = svg.getScreenCTM()
  return ctm && ctm.a !== 0 ? 1 / ctm.a : 1
}
