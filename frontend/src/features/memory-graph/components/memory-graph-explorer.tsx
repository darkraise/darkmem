import { useEffect, useMemo, useState } from "react"
import {
  Crosshair,
  ListTree,
  Orbit,
  Search,
  Share2,
  Waypoints,
} from "lucide-react"
import { Input } from "darkraise-ui/components/input"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
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

const W = 680
const H = 400
const LAYOUTS: GraphLayoutMode[] = ["force", "tree", "circles"]

// The four non-caution chart members (S17): a topic halo or entity dot is
// never misreadable as the language's caution colour, so --chart-4 is out.
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
  const graph = useDemoMemoryGraph()
  const project = useProjectStore((s) => s.activeProject)
  const [layout, setLayout] = useState<GraphLayoutMode>("force")
  const [query, setQuery] = useState("")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [focusTopic, setFocusTopic] = useState<string | null>(null)

  useEffect(() => {
    setSelectedId(null)
    setFocusTopic(null)
  }, [project])

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
    [scoped, layout],
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
              direction: r.source === selected.id ? "→" : "←",
              other,
            }
          : null
      })
      .filter((r): r is NonNullable<typeof r> => r !== null)
  }, [scoped, selected])

  const topicChart = useMemo(() => {
    const map = new Map<string, number>()
    for (const t of scoped.topics) map.set(t.id, t.chart)
    return map
  }, [scoped])

  const dimmed = (topicId: string) =>
    focusTopic !== null && topicId !== focusTopic

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* toolbar strip */}
      <div className="border-border bg-card flex flex-wrap items-center gap-2.5 border-b px-4 py-2.5">
        <Input
          prefix={<Search aria-hidden className="h-4 w-4" />}
          placeholder="Search entities & relations…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          groupClassName="w-64"
          aria-label="Search entities"
        />
        {query.trim() !== "" && (
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
        <div className="relative min-h-72 min-w-0 flex-1">
          {scoped.entities.length === 0 ? (
            <div className="flex h-full items-center justify-center p-6">
              <EmptyState
                kind="empty"
                icon={Waypoints}
                title="No entity graph yet"
                description={`${project === ALL_PROJECTS ? "No project" : `Project ${project}`} has no memories yet, so nothing has been extracted into entities or relations. The graph populates automatically as memories are captured; topic communities appear after the next clustering pass runs over it.`}
              />
            </div>
          ) : (
            <>
              <svg
                viewBox={`0 0 ${W} ${H}`}
                className="h-full w-full"
                role="img"
                aria-label={`Entity graph for ${project === ALL_PROJECTS ? projectLabel(project) : `project ${project}`}: ${scoped.entities.length} entities in ${scoped.topics.length} topic clusters, ${layout} layout`}
                onClick={() => setSelectedId(null)}
              >
                {halos.map(({ topic, cx, cy, rx, ry }) => (
                  <ellipse
                    key={topic.id}
                    cx={cx}
                    cy={cy}
                    rx={rx}
                    ry={ry}
                    fill={chartVar(topic.chart)}
                    fillOpacity={dimmed(topic.id) ? 0.04 : 0.13}
                    stroke={chartVar(topic.chart)}
                    strokeOpacity={dimmed(topic.id) ? 0.15 : 0.55}
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
                  const dim = dimmed(entity.topic)
                  return (
                    <g
                      key={entity.id}
                      role="button"
                      tabIndex={0}
                      aria-label={`${entity.name} (${entity.entity_type})`}
                      className="cursor-pointer outline-none"
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
                    >
                      <title>{`${entity.name} · ${entity.entity_type}`}</title>
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
                      <text
                        x={12}
                        y={4}
                        fontSize={10.5}
                        className="font-mono"
                        fill="hsl(var(--foreground))"
                      >
                        {entity.name}
                      </text>
                    </g>
                  )
                })}
              </svg>
              <div className="bg-background/75 text-muted-foreground absolute inset-x-0 bottom-0 flex flex-wrap gap-x-4 gap-y-1 px-4 py-2 text-sm backdrop-blur-sm">
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
              </div>
            </>
          )}
        </div>

        {/* inspector + community navigator — full-height side column */}
        <div className="border-border bg-card min-h-0 shrink-0 overflow-y-auto border-t lg:w-72 lg:border-t-0 lg:border-l">
          <div className="border-border border-b">
            <div className="border-border bg-muted/30 flex items-center gap-2 border-b px-3 py-2">
              <Crosshair
                aria-hidden
                className="text-muted-foreground h-3.5 w-3.5"
              />
              <span className="text-sm font-semibold">Inspector</span>
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
                <p className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
                  relations ({selectedRelations.length})
                </p>
                <div className="space-y-1">
                  {selectedRelations.map((rel, i) => (
                    <button
                      key={i}
                      type="button"
                      className="hover:bg-muted/50 flex w-full items-center gap-1.5 rounded-sm px-1 py-0.5 text-left text-sm"
                      onClick={() => setSelectedId(rel.other.id)}
                    >
                      <span className="text-muted-foreground font-mono text-[10px]">
                        {rel.direction} {rel.rel_type}
                      </span>
                      <span className="min-w-0 flex-1 truncate font-mono">
                        {rel.other.name}
                      </span>
                    </button>
                  ))}
                </div>
                <p className="text-muted-foreground text-sm">
                  L1 carries no verification rung — these are pre-corroboration
                  entities and relations straight from extraction; the ladder
                  applies to L2 facts in the Knowledge vault.
                </p>
              </div>
            ) : (
              <p className="text-muted-foreground p-3 text-sm">
                Click an entity node to inspect its type, topic, and relations.
              </p>
            )}
          </div>

          <div>
            <div className="border-border bg-muted/30 flex items-center gap-2 border-b px-3 py-2">
              <Waypoints
                aria-hidden
                className="text-muted-foreground h-3.5 w-3.5"
              />
              <span className="text-sm font-semibold">Community navigator</span>
              <span className="text-muted-foreground ml-auto font-mono text-sm">
                {scoped.topics.length} topics
              </span>
            </div>
            <div className="space-y-2 p-3">
              {scoped.topics.length === 0 ? (
                <p className="text-muted-foreground text-sm">
                  No communities detected yet — clustering runs over the entity
                  graph once one exists.
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
                      <span
                        className="mt-1 h-2.5 w-2.5 shrink-0 rounded-[3px]"
                        style={{
                          background: chartVar(topicChart.get(topic.id) ?? 1),
                        }}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block text-sm font-semibold">
                          {topic.label}
                        </span>
                        <span className="text-muted-foreground block font-mono text-[10px]">
                          {members} entities · detected {topic.detected}
                        </span>
                      </span>
                      <button
                        type="button"
                        className={cn(
                          "inline-flex shrink-0 items-center gap-1 font-mono text-[10px]",
                          focusTopic === topic.id
                            ? "text-primary"
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
              <p className="border-border text-muted-foreground border-t border-dashed pt-2 text-sm">
                Topics are read-only labels from a clustering pass over the
                entity graph — browsing them here does not feed ranking.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
