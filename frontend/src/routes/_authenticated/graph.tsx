import { createFileRoute } from "@tanstack/react-router";
import { useFullGraph, useKnowledgeEntities, useKnowledgeTimeline } from "@/hooks/api";
import type { KnowledgeTriple } from "@/hooks/api";
import { KnowledgeGraphRenderer, type KGSelection } from "@/features/graph/components/knowledge-graph-renderer";
import { ENTITY_TYPE_COLORS, entityTypeColor } from "@/features/graph/lib/graph-colors";
import { useState, useMemo } from "react";
import { Badge } from "darkraise-ui/components/badge";
import { Button } from "darkraise-ui/components/button";
import { Input } from "darkraise-ui/components/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select";
import {
  Network,
  Clock,
  ArrowRight,
  CalendarDays,
  X,
  Loader2,
} from "lucide-react";

export const Route = createFileRoute("/_authenticated/graph")({
  component: KnowledgeGraphPage,
});

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
};

function predicateColor(predicate: string): string {
  return PREDICATE_COLORS[predicate] ?? "#8b949e";
}

// ── Date formatting helpers ───────────────────────────────────

function fmtDate(iso: string | null): string {
  if (!iso) return "present";
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function isExpired(triple: KnowledgeTriple): boolean {
  return !!triple.valid_to && new Date(triple.valid_to) < new Date();
}

// ── Sub-components ────────────────────────────────────────────

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}

function TabButton({ active, onClick, icon, label }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={[
        "flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors",
        active
          ? "border-cyan-400 text-cyan-400"
          : "border-transparent text-muted-foreground hover:text-foreground hover:border-border",
      ].join(" ")}
    >
      {icon}
      {label}
    </button>
  );
}

interface TripleRowProps {
  triple: KnowledgeTriple;
  animate: boolean;
}

function TripleRow({ triple, animate }: TripleRowProps) {
  const expired = isExpired(triple);
  const color = predicateColor(triple.predicate);
  const confidencePct = Math.round(triple.confidence * 100);

  return (
    <div
      className={[
        "flex gap-4 px-4 py-3 border-b border-border/50 transition-opacity",
        expired ? "opacity-40" : "opacity-100",
        animate ? "animate-in fade-in slide-in-from-left-2 duration-300" : "",
      ].join(" ")}
    >
      {/* Timeline rail */}
      <div className="flex flex-col items-center gap-1 shrink-0 w-24 text-right">
        <span className="text-[11px] font-mono text-cyan-400/80 leading-tight">
          {fmtDate(triple.valid_from)}
        </span>
        {triple.valid_to && (
          <>
            <div className="w-px flex-1 min-h-[8px] bg-border" />
            <span className="text-[11px] font-mono text-muted-foreground leading-tight line-through">
              {fmtDate(triple.valid_to)}
            </span>
          </>
        )}
      </div>

      {/* Fact card */}
      <div
        className={[
          "flex-1 rounded-lg px-3 py-2 border transition-colors",
          expired
            ? "bg-card/30 border-border/40"
            : "bg-card border-border/80",
        ].join(" ")}
        style={expired ? undefined : { borderLeftColor: color, borderLeftWidth: 2 }}
      >
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className="text-sm font-mono font-medium"
            style={{ color: expired ? "#8b949e" : "#e2e8f0" }}
          >
            {triple.subject}
          </span>

          <div className="flex items-center gap-1.5">
            <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />
            <Badge
              variant="outline"
              className="text-[11px] px-1.5 py-0 font-mono border-0 rounded"
              style={{
                backgroundColor: expired ? "rgba(139,148,158,0.1)" : `${color}18`,
                color: expired ? "#8b949e" : color,
              }}
            >
              {triple.predicate}
            </Badge>
            <ArrowRight className="w-3.5 h-3.5 text-muted-foreground" />
          </div>

          <span
            className={[
              "text-sm font-mono",
              expired ? "line-through text-muted-foreground" : "text-foreground",
            ].join(" ")}
          >
            {triple.object}
          </span>

          <span
            className="ml-auto text-[11px] font-mono shrink-0"
            style={{ color: `rgba(139,148,158,${triple.confidence})` }}
            title={`Confidence: ${confidencePct}%`}
          >
            {confidencePct}%
          </span>
        </div>
      </div>
    </div>
  );
}

// ── Timeline tab ──────────────────────────────────────────────

function KnowledgeTimelineTab() {
  const [selectedEntity, setSelectedEntity] = useState<string>("");
  const [asOfInput, setAsOfInput] = useState("");
  const [asOf, setAsOf] = useState<string | undefined>(undefined);
  const [animateKey, setAnimateKey] = useState(0);

  const { data: entities, isLoading: entitiesLoading } = useKnowledgeEntities();
  const { data: triples, isLoading: triplesLoading } = useKnowledgeTimeline(
    selectedEntity || null,
    asOf,
  );

  const sorted = useMemo(() => {
    if (!triples) return [];
    return [...triples].sort((a, b) => {
      const aFrom = a.valid_from ? new Date(a.valid_from).getTime() : 0;
      const bFrom = b.valid_from ? new Date(b.valid_from).getTime() : 0;
      return aFrom - bFrom;
    });
  }, [triples]);

  const activeCount = sorted.filter((t) => !isExpired(t)).length;
  const expiredCount = sorted.length - activeCount;

  function handleApplyAsOf() {
    setAsOf(asOfInput || undefined);
    setAnimateKey((k) => k + 1);
  }

  function handleClearAsOf() {
    setAsOfInput("");
    setAsOf(undefined);
    setAnimateKey((k) => k + 1);
  }

  function handleEntityChange(value: string) {
    setSelectedEntity(value === "__none__" ? "" : value);
    setAnimateKey((k) => k + 1);
  }

  const selectedEntityMeta = entities?.find((e) => e.name === selectedEntity);

  return (
    <div className="flex flex-col gap-4">
      {/* Controls */}
      <div className="flex flex-wrap gap-3 items-end">
        <div className="flex flex-col gap-1">
          <label className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
            Entity
          </label>
          <Select
            value={selectedEntity || "__none__"}
            onValueChange={handleEntityChange}
          >
            <SelectTrigger className="h-8 w-52 font-mono text-sm">
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
                  <span className="ml-2 text-xs text-muted-foreground">
                    {e.entity_type}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs uppercase tracking-wider text-muted-foreground font-medium flex items-center gap-1.5">
            <CalendarDays className="w-3 h-3" />
            As of date
          </label>
          <div className="flex gap-2">
            <Input
              type="date"
              value={asOfInput}
              onChange={(e) => setAsOfInput(e.target.value)}
              className="h-8 w-44 font-mono text-sm"
            />
            <Button size="sm" onClick={handleApplyAsOf} disabled={!asOfInput}>
              Apply
            </Button>
            {asOf && (
              <Button
                size="sm"
                variant="ghost"
                onClick={handleClearAsOf}
                className="px-2"
              >
                <X className="w-3.5 h-3.5" />
              </Button>
            )}
          </div>
        </div>

        {selectedEntity && selectedEntityMeta && (
          <div className="ml-auto flex items-center gap-2 text-sm text-muted-foreground">
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{
                backgroundColor: entityTypeColor(selectedEntityMeta.entity_type),
              }}
            />
            <span style={{ color: entityTypeColor(selectedEntityMeta.entity_type) }}>
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
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-cyan-950/40 border border-cyan-400/20 text-xs font-mono text-cyan-400/80 w-fit">
          <Clock className="w-3 h-3" />
          Showing facts valid on {fmtDate(asOf)}
        </div>
      )}

      {/* Empty states */}
      {!selectedEntity && (
        <div className="flex flex-col items-center justify-center py-16 text-center gap-3">
          <Clock className="w-10 h-10 text-muted-foreground/30" />
          <p className="text-muted-foreground text-sm">
            Select an entity to view its temporal fact timeline.
          </p>
        </div>
      )}

      {selectedEntity && triplesLoading && (
        <div className="flex items-center gap-2 text-muted-foreground text-sm py-8 justify-center">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading timeline…
        </div>
      )}

      {selectedEntity && !triplesLoading && sorted.length === 0 && (
        <p className="text-muted-foreground text-sm py-8 text-center">
          No facts found
          {asOf ? ` valid on ${fmtDate(asOf)}` : ""} for "{selectedEntity}".
        </p>
      )}

      {/* Timeline list */}
      {sorted.length > 0 && (
        <div
          className="rounded-lg border border-border overflow-hidden"
          style={{ background: "rgba(8,8,14,0.6)" }}
        >
          {/* Legend */}
          <div className="flex items-center gap-4 px-4 py-2 border-b border-border/50 bg-card/30 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-cyan-400/80" />
              Active
            </span>
            <span className="flex items-center gap-1.5 opacity-40">
              <span className="w-2 h-2 rounded-full bg-muted-foreground" />
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
        <div className="flex gap-2 flex-wrap mt-1">
          {Array.from(new Set(sorted.map((t) => t.predicate))).map((pred) => (
            <span
              key={pred}
              className="text-[11px] font-mono px-2 py-0.5 rounded border border-border/50"
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
  );
}

// ── Graph tab ─────────────────────────────────────────────────

interface GraphTabProps {
  data: ReturnType<typeof useFullGraph>["data"];
  isLoading: boolean;
}

function GraphTab({ data: graph, isLoading }: GraphTabProps) {
  const [selected, setSelected] = useState<KGSelection | null>(null);

  const entities = useMemo(
    () => (graph?.entities || []) as Array<{ id?: string; name: string; entity_type: string }>,
    [graph],
  );
  const relations = useMemo(
    () =>
      (graph?.relations || []) as Array<{
        source: string;
        target: string;
        type?: string;
        weight?: number;
      }>,
    [graph],
  );

  const nodeCount = entities.length;
  const edgeCount = relations.length;

  return (
    <>
      {isLoading && <p className="text-muted-foreground">Loading graph…</p>}

      {!isLoading && nodeCount === 0 && (
        <p className="text-muted-foreground">
          No entities in the knowledge graph yet. Create memories with the pipeline
          running to populate it.
        </p>
      )}

      {nodeCount > 0 && (
        <div
          className="relative bg-card border border-border rounded-lg overflow-hidden"
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
        <div className="mt-4 bg-card border border-border rounded-lg p-4">
          {selected.kind === "node" ? (
            <>
              <h3 className="font-medium">{selected.label}</h3>
              <p className="text-sm text-muted-foreground">Type: {selected.type}</p>
            </>
          ) : (
            <>
              <h3 className="font-medium">{selected.label || "relationship"}</h3>
              <p className="text-sm text-muted-foreground">
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
        <div className="mt-4 flex gap-3 flex-wrap">
          {Object.entries(ENTITY_TYPE_COLORS).map(([type, color]) => (
            <div
              key={type}
              className="flex items-center gap-1.5 text-xs text-muted-foreground"
            >
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
              {type}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

// ── Page root ─────────────────────────────────────────────────

type Tab = "graph" | "timeline";

function KnowledgeGraphPage() {
  const [tab, setTab] = useState<Tab>("graph");
  const { data: graph, isLoading: graphLoading } = useFullGraph();

  const nodeCount = (graph?.entities || []).length;
  const edgeCount = (graph?.relations || []).length;

  return (
    <div className="p-6 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Knowledge Graph</h2>
        {nodeCount > 0 && (
          <span className="text-sm text-muted-foreground">
            {nodeCount} entities, {edgeCount} relationships
          </span>
        )}
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-border -mb-2">
        <TabButton
          active={tab === "graph"}
          onClick={() => setTab("graph")}
          icon={<Network className="w-4 h-4" />}
          label="Entity Graph"
        />
        <TabButton
          active={tab === "timeline"}
          onClick={() => setTab("timeline")}
          icon={<Clock className="w-4 h-4" />}
          label="Knowledge Timeline"
        />
      </div>

      {/* Tab content */}
      {tab === "graph" && <GraphTab data={graph} isLoading={graphLoading} />}
      {tab === "timeline" && <KnowledgeTimelineTab />}
    </div>
  );
}
