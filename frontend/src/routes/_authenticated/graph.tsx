import { createFileRoute } from "@tanstack/react-router"
import {
  useFullGraph,
  useKnowledgeEntities,
  useKnowledgeTimeline,
} from "@/hooks/api"
import type { KnowledgeTriple } from "@/hooks/api"
import {
  KnowledgeGraphRenderer,
  type KGSelection,
} from "@/features/graph/components/knowledge-graph-renderer"
import {
  ENTITY_TYPE_COLORS,
  entityTypeColor,
} from "@/features/graph/lib/graph-colors"
import { useState, useMemo } from "react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import {
  Network,
  Clock,
  ArrowRight,
  CalendarDays,
  X,
  Loader2,
} from "lucide-react"

export const Route = createFileRoute("/_authenticated/graph")({
  component: KnowledgeGraphPage,
})

// ── Predicate color palette ───────────────────────────────────

const PREDICATE_COLORS: Record<string, string> = {
  is_a: "#22d3ee",
  uses: "#60a5fa",
  used: "#818cf8",
  depends_on: "#f472b6",
  maintains: "#4ade80",
  maintained_by: "#4ade80",
  runs_on: "#34d399",
  deployed_at: "#2dd4bf",
  version: "#fbbf24",
  replaced: "#fb923c",
  prefers: "#c084fc",
  transport: "#38bdf8",
}

function predicateColor(predicate: string): string {
  return PREDICATE_COLORS[predicate] ?? "#8b949e"
}

// ── Date formatting helpers ───────────────────────────────────

function fmtDate(iso: string | null): string {
  if (!iso) return "present"
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

function isExpired(triple: KnowledgeTriple): boolean {
  return !!triple.valid_to && new Date(triple.valid_to) < new Date()
}

// ── Sub-components ────────────────────────────────────────────

interface TabButtonProps {
  active: boolean
  onClick: () => void
  icon: React.ReactNode
  label: string
}

function TabButton({ active, onClick, icon, label }: TabButtonProps) {
  return (
    <Button
      variant="ghost"
      onClick={onClick}
      className={[
        "flex items-center gap-2 border-b-2 px-4 py-2 text-base font-medium transition-colors",
        active
          ? "border-cyan-400 text-cyan-400"
          : "text-muted-foreground hover:text-foreground hover:border-border border-transparent",
      ].join(" ")}
    >
      {icon}
      {label}
    </Button>
  )
}

interface TripleRowProps {
  triple: KnowledgeTriple
  animate: boolean
}

function TripleRow({ triple, animate }: TripleRowProps) {
  const expired = isExpired(triple)
  const color = predicateColor(triple.predicate)
  const confidencePct = Math.round(triple.confidence * 100)

  return (
    <div
      className={[
        "border-border/50 flex gap-4 border-b px-4 py-3 transition-opacity",
        expired ? "opacity-40" : "opacity-100",
        animate ? "animate-in fade-in slide-in-from-left-2 duration-300" : "",
      ].join(" ")}
    >
      {/* Timeline rail */}
      <div className="flex w-24 shrink-0 flex-col items-center gap-1 text-right">
        <span className="font-mono text-sm leading-tight text-cyan-400/80">
          {fmtDate(triple.valid_from)}
        </span>
        {triple.valid_to && (
          <>
            <div className="bg-border min-h-[8px] w-px flex-1" />
            <span className="text-muted-foreground font-mono text-sm leading-tight line-through">
              {fmtDate(triple.valid_to)}
            </span>
          </>
        )}
      </div>

      {/* Fact card */}
      <div
        className={[
          "flex-1 rounded-lg border px-3 py-2 transition-colors",
          expired ? "bg-card/30 border-border/40" : "bg-card border-border/80",
        ].join(" ")}
        style={
          expired ? undefined : { borderLeftColor: color, borderLeftWidth: 2 }
        }
      >
        <div className="flex flex-wrap items-center gap-2">
          <span
            className="font-mono text-base font-medium"
            style={{ color: expired ? "#8b949e" : "#e2e8f0" }}
          >
            {triple.subject}
          </span>

          <div className="flex items-center gap-1.5">
            <ArrowRight className="text-muted-foreground h-3.5 w-3.5" />
            <Badge
              variant="outline"
              className="rounded border-0 px-1.5 py-0 font-mono text-sm"
              style={{
                backgroundColor: expired
                  ? "rgba(139,148,158,0.1)"
                  : `${color}18`,
                color: expired ? "#8b949e" : color,
              }}
            >
              {triple.predicate}
            </Badge>
            <ArrowRight className="text-muted-foreground h-3.5 w-3.5" />
          </div>

          <span
            className={[
              "font-mono text-base",
              expired
                ? "text-muted-foreground line-through"
                : "text-foreground",
            ].join(" ")}
          >
            {triple.object}
          </span>

          <span
            className="ml-auto shrink-0 font-mono text-sm"
            style={{ color: `rgba(139,148,158,${triple.confidence})` }}
            title={`Confidence: ${confidencePct}%`}
          >
            {confidencePct}%
          </span>
        </div>
      </div>
    </div>
  )
}

// ── Timeline tab ──────────────────────────────────────────────

function KnowledgeTimelineTab() {
  const [selectedEntity, setSelectedEntity] = useState<string>("")
  const [asOfInput, setAsOfInput] = useState("")
  const [asOf, setAsOf] = useState<string | undefined>(undefined)
  const [animateKey, setAnimateKey] = useState(0)

  const { data: entities, isLoading: entitiesLoading } = useKnowledgeEntities()
  const { data: triples, isLoading: triplesLoading } = useKnowledgeTimeline(
    selectedEntity || null,
    asOf,
  )

  const sorted = useMemo(() => {
    if (!triples) return []
    return [...triples].sort((a, b) => {
      const aFrom = a.valid_from ? new Date(a.valid_from).getTime() : 0
      const bFrom = b.valid_from ? new Date(b.valid_from).getTime() : 0
      return aFrom - bFrom
    })
  }, [triples])

  const activeCount = sorted.filter((t) => !isExpired(t)).length
  const expiredCount = sorted.length - activeCount

  function handleApplyAsOf() {
    setAsOf(asOfInput || undefined)
    setAnimateKey((k) => k + 1)
  }

  function handleClearAsOf() {
    setAsOfInput("")
    setAsOf(undefined)
    setAnimateKey((k) => k + 1)
  }

  function handleEntityChange(value: string) {
    setSelectedEntity(value === "__none__" ? "" : value)
    setAnimateKey((k) => k + 1)
  }

  const selectedEntityMeta = entities?.find((e) => e.name === selectedEntity)

  return (
    <div className="flex flex-col gap-4">
      {/* The temporal knowledge-graph backend endpoints aren't implemented yet
          (useKnowledgeEntities/useKnowledgeTimeline are stubs), so the controls
          below can't return data. Say so plainly rather than presenting
          working-looking controls. */}
      <div className="rounded-md border border-amber-400/20 bg-amber-950/30 px-3 py-2 text-base text-amber-300/90">
        The temporal fact timeline is not yet available — the knowledge-graph
        endpoints are still being built, so the controls below won&apos;t return
        data yet.
      </div>

      {/* Controls */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <Label className="text-muted-foreground text-base font-medium tracking-wider uppercase">
            Entity
          </Label>
          <Select
            value={selectedEntity || "__none__"}
            onValueChange={handleEntityChange}
          >
            <SelectTrigger className="h-8 w-52 font-mono text-base">
              <SelectValue placeholder="Select entity…" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">Select entity…</SelectItem>
              {entitiesLoading && (
                <SelectItem value="__loading__" disabled>
                  Loading…
                </SelectItem>
              )}
              {entities?.map((e) => (
                <SelectItem key={e.name} value={e.name}>
                  <span className="font-mono">{e.name}</span>
                  <span className="text-muted-foreground ml-2 text-base">
                    {e.entity_type}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1">
          <Label className="text-muted-foreground flex items-center gap-1.5 text-base font-medium tracking-wider uppercase">
            <CalendarDays className="h-3 w-3" />
            As of date
          </Label>
          <div className="flex gap-2">
            <Input
              type="date"
              value={asOfInput}
              onChange={(e) => setAsOfInput(e.target.value)}
              className="h-8 w-44 font-mono text-base"
            />
            <Button onClick={handleApplyAsOf} disabled={!asOfInput}>
              Apply
            </Button>
            {asOf && (
              <Button
                variant="ghost"
                onClick={handleClearAsOf}
                className="px-2"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            )}
          </div>
        </div>

        {selectedEntity && selectedEntityMeta && (
          <div className="text-muted-foreground ml-auto flex items-center gap-2 text-base">
            <span
              className="h-2.5 w-2.5 shrink-0 rounded-full"
              style={{
                backgroundColor: entityTypeColor(
                  selectedEntityMeta.entity_type,
                ),
              }}
            />
            <span
              style={{ color: entityTypeColor(selectedEntityMeta.entity_type) }}
            >
              {selectedEntityMeta.entity_type}
            </span>
            {!triplesLoading && sorted.length > 0 && (
              <span className="text-muted-foreground">
                · {activeCount} active, {expiredCount} expired
              </span>
            )}
          </div>
        )}
      </div>

      {/* Active date filter indicator */}
      {asOf && (
        <div className="flex w-fit items-center gap-2 rounded-md border border-cyan-400/20 bg-cyan-950/40 px-3 py-1.5 font-mono text-base text-cyan-400/80">
          <Clock className="h-3 w-3" />
          Showing facts valid on {fmtDate(asOf)}
        </div>
      )}

      {/* Empty states */}
      {!selectedEntity && (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <Clock className="text-muted-foreground/30 h-10 w-10" />
          <p className="text-muted-foreground text-base">
            Select an entity to view its temporal fact timeline.
          </p>
        </div>
      )}

      {selectedEntity && triplesLoading && (
        <div className="text-muted-foreground flex items-center justify-center gap-2 py-8 text-base">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading timeline…
        </div>
      )}

      {selectedEntity && !triplesLoading && sorted.length === 0 && (
        <p className="text-muted-foreground py-8 text-center text-base">
          No facts found
          {asOf ? ` valid on ${fmtDate(asOf)}` : ""} for "{selectedEntity}".
        </p>
      )}

      {/* Timeline list */}
      {sorted.length > 0 && (
        <div
          className="border-border overflow-hidden rounded-lg border"
          style={{ background: "rgba(8,8,14,0.6)" }}
        >
          {/* Legend */}
          <div className="border-border/50 bg-card/30 text-muted-foreground flex items-center gap-4 border-b px-4 py-2 text-base">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-cyan-400/80" />
              Active
            </span>
            <span className="flex items-center gap-1.5 opacity-40">
              <span className="bg-muted-foreground h-2 w-2 rounded-full" />
              Expired
            </span>
            <span className="ml-auto">Confidence %</span>
          </div>

          {sorted.map((triple) => (
            <TripleRow
              key={`${triple.id}-${animateKey}`}
              triple={triple}
              animate={animateKey > 0}
            />
          ))}
        </div>
      )}

      {/* Predicate legend */}
      {sorted.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-2">
          {Array.from(new Set(sorted.map((t) => t.predicate))).map((pred) => (
            <span
              key={pred}
              className="border-border/50 rounded border px-2 py-0.5 font-mono text-sm"
              style={{
                color: predicateColor(pred),
                backgroundColor: `${predicateColor(pred)}12`,
              }}
            >
              {pred}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Graph tab ─────────────────────────────────────────────────

interface GraphTabProps {
  data: ReturnType<typeof useFullGraph>["data"]
  isLoading: boolean
}

function GraphTab({ data: graph, isLoading }: GraphTabProps) {
  const [selected, setSelected] = useState<KGSelection | null>(null)

  const entities = useMemo(
    () =>
      (graph?.entities || []) as Array<{
        id?: string
        name: string
        entity_type: string
      }>,
    [graph],
  )
  const relations = useMemo(
    () =>
      (graph?.relations || []) as Array<{
        source: string
        target: string
        type?: string
        weight?: number
      }>,
    [graph],
  )

  const nodeCount = entities.length

  return (
    <>
      {isLoading && <p className="text-muted-foreground">Loading graph…</p>}

      {!isLoading && nodeCount === 0 && (
        <p className="text-muted-foreground">
          No entities in the knowledge graph yet. Create memories with the
          pipeline running to populate it.
        </p>
      )}

      {nodeCount > 0 && (
        <div
          className="bg-card border-border relative overflow-hidden rounded-lg border"
          style={{ height: "70vh" }}
        >
          <KnowledgeGraphRenderer
            entities={entities}
            relations={relations}
            selectedId={selected?.kind === "node" ? selected.id : null}
            onSelect={setSelected}
          />
        </div>
      )}

      {selected && (
        <div className="bg-card border-border mt-4 rounded-lg border p-4">
          {selected.kind === "node" ? (
            <>
              <h3 className="font-medium">{selected.label}</h3>
              <p className="text-muted-foreground text-base">
                Type: {selected.type}
              </p>
            </>
          ) : (
            <>
              <h3 className="font-medium">
                {selected.label || "relationship"}
              </h3>
              <p className="text-muted-foreground text-base">
                {selected.source} → {selected.target}
                {selected.weight && (
                  <span className="ml-2">weight: {selected.weight}</span>
                )}
              </p>
            </>
          )}
        </div>
      )}

      {nodeCount > 0 && (
        <div className="mt-4 flex flex-wrap gap-3">
          {Object.entries(ENTITY_TYPE_COLORS).map(([type, color]) => (
            <div
              key={type}
              className="text-muted-foreground flex items-center gap-1.5 text-base"
            >
              <div
                className="h-3 w-3 rounded-full"
                style={{ backgroundColor: color }}
              />
              {type}
            </div>
          ))}
        </div>
      )}
    </>
  )
}

// ── Page root ─────────────────────────────────────────────────

type Tab = "graph" | "timeline"

function KnowledgeGraphPage() {
  const [tab, setTab] = useState<Tab>("graph")
  const { data: graph, isLoading: graphLoading } = useFullGraph()

  const nodeCount = (graph?.entities || []).length
  const edgeCount = (graph?.relations || []).length

  return (
    <div className="flex flex-col gap-4 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Knowledge Graph</h1>
        {nodeCount > 0 && (
          <span className="text-muted-foreground text-base">
            {nodeCount} entities, {edgeCount} relationships
          </span>
        )}
      </div>

      {/* Tab bar */}
      <div className="border-border -mb-2 flex border-b">
        <TabButton
          active={tab === "graph"}
          onClick={() => setTab("graph")}
          icon={<Network className="h-4 w-4" />}
          label="Entity Graph"
        />
        <TabButton
          active={tab === "timeline"}
          onClick={() => setTab("timeline")}
          icon={<Clock className="h-4 w-4" />}
          label="Knowledge Timeline"
        />
      </div>

      {/* Tab content */}
      {tab === "graph" && <GraphTab data={graph} isLoading={graphLoading} />}
      {tab === "timeline" && <KnowledgeTimelineTab />}
    </div>
  )
}
