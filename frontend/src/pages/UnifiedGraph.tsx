import { useUnifiedGraph } from "@/hooks/useApi";
// eslint-disable-next-line @typescript-eslint/no-explicit-any
import CytoscapeComp from "react-cytoscapejs";
const CytoscapeComponent = CytoscapeComp as any;
import { useRef, useMemo, useCallback, useReducer } from "react";

// ── Colour palettes ──────────────────────────────────────────────────────────

const ENTITY_COLORS: Record<string, string> = {
  person: "#58a6ff",
  service: "#3fb950",
  project: "#d2a8ff",
  technology: "#ffa657",
  concept: "#8b949e",
  organization: "#f778ba",
};

// 12 visually-distinct cluster colours (cycling when > 12 clusters)
const CLUSTER_PALETTE = [
  "#58a6ff", "#3fb950", "#ffa657", "#d2a8ff",
  "#f778ba", "#79c0ff", "#56d364", "#ffb74d",
  "#bb86fc", "#ff6b6b", "#4fc3f7", "#aed581",
];

function clusterColor(id: number): string {
  return CLUSTER_PALETTE[id % CLUSTER_PALETTE.length];
}

// ── Cytoscape stylesheet ──────────────────────────────────────────────────────

const stylesheet = [
  // Entity nodes
  {
    selector: "node[nodeType = 'entity']",
    style: {
      label: "data(label)",
      "background-color": "data(color)",
      color: "#c9d1d9",
      "text-valign": "bottom" as const,
      "text-margin-y": 6,
      "font-size": 9,
      width: 26,
      height: 26,
      "border-width": 2,
      "border-color": "#30363d",
      shape: "ellipse" as const,
    },
  },
  // Memory nodes
  {
    selector: "node[nodeType = 'memory']",
    style: {
      label: "data(label)",
      "background-color": "data(color)",
      color: "#8b949e",
      "text-valign": "bottom" as const,
      "text-margin-y": 5,
      "font-size": 8,
      width: 18,
      height: 18,
      "border-width": 1.5,
      "border-color": "#21262d",
      shape: "round-rectangle" as const,
    },
  },
  // Entity–entity relation edges
  {
    selector: "edge[edgeType = 'relation']",
    style: {
      width: 1.5,
      "line-color": "#444c56",
      "target-arrow-color": "#444c56",
      "target-arrow-shape": "triangle" as const,
      "curve-style": "bezier" as const,
      label: "data(label)",
      "font-size": 7,
      color: "#484f58",
      "text-rotation": "autorotate" as const,
      "text-margin-y": -8,
    },
  },
  // Memory→entity mention edges
  {
    selector: "edge[edgeType = 'mention']",
    style: {
      width: 1,
      "line-color": "#2d3138",
      "line-style": "dashed" as const,
      "target-arrow-color": "#2d3138",
      "target-arrow-shape": "vee" as const,
      "curve-style": "bezier" as const,
    },
  },
  // Selected
  {
    selector: "node:selected",
    style: { "border-color": "#58a6ff", "border-width": 3 },
  },
  {
    selector: "edge:selected",
    style: { "line-color": "#58a6ff", "target-arrow-color": "#58a6ff", width: 2.5 },
  },
];

const layout = {
  name: "cose",
  animate: false,
  nodeRepulsion: () => 6000,
  idealEdgeLength: () => 80,
  edgeElasticity: () => 100,
  gravity: 0.25,
  numIter: 1000,
};

// ── Types ─────────────────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Selected = { kind: "node" | "edge"; [key: string]: any } | null;

// ── Component ─────────────────────────────────────────────────────────────────

export default function UnifiedGraph() {
  const { data, isLoading } = useUnifiedGraph();
  const cyRef = useRef<unknown>(null);
  const listenersAttached = useRef(false);
  const [, forceUpdate] = useReducer((x: number) => x + 1, 0);
  const selectedRef = useRef<Selected>(null);

  const elements = useMemo(() => {
    if (!data) return [];

    const nodes: object[] = [];
    const edges: object[] = [];

    // Entity nodes
    for (const e of data.entities) {
      nodes.push({
        data: {
          id: e.id,
          label: e.name,
          entityType: e.entity_type,
          nodeType: "entity",
          color: ENTITY_COLORS[e.entity_type] || "#8b949e",
        },
      });
    }

    // Memory nodes
    for (const m of data.memories) {
      const color = m.cluster >= 0 ? clusterColor(m.cluster) : "#484f58";
      nodes.push({
        data: {
          id: m.id,
          label: m.content.slice(0, 30) + (m.content.length > 30 ? "…" : ""),
          fullContent: m.content,
          source: m.source,
          tags: m.tags,
          memoryType: m.memory_type,
          cluster: m.cluster,
          nodeType: "memory",
          color,
        },
      });
    }

    // Entity–entity relation edges
    const entityIds = new Set(data.entities.map((e) => e.id));
    for (let i = 0; i < data.relations.length; i++) {
      const r = data.relations[i];
      if (entityIds.has(r.source) && entityIds.has(r.target)) {
        edges.push({
          data: {
            id: `rel-${i}`,
            source: r.source,
            target: r.target,
            label: r.type || "",
            weight: r.weight ?? 0.5,
            edgeType: "relation",
          },
        });
      }
    }

    // Memory→entity mention edges
    const memoryIds = new Set(data.memories.map((m) => m.id));
    for (let i = 0; i < data.mentions.length; i++) {
      const m = data.mentions[i];
      if (memoryIds.has(m.source) && entityIds.has(m.target)) {
        edges.push({
          data: {
            id: `mention-${i}`,
            source: m.source,
            target: m.target,
            edgeType: "mention",
          },
        });
      }
    }

    return [...nodes, ...edges];
  }, [data]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleCy = useCallback((cy: any) => {
    cyRef.current = cy;
    if (listenersAttached.current) return;
    listenersAttached.current = true;

    cy.on("tap", "node", (evt: any) => {
      selectedRef.current = { ...evt.target.data(), kind: "node" };
      forceUpdate();
    });
    cy.on("tap", "edge", (evt: any) => {
      selectedRef.current = { ...evt.target.data(), kind: "edge" };
      forceUpdate();
    });
    cy.on("tap", (evt: any) => {
      if (evt.target === cy) {
        selectedRef.current = null;
        forceUpdate();
      }
    });
  }, []);

  const entityCount = data?.entities.length ?? 0;
  const memoryCount = data?.memories.length ?? 0;
  const clusterCount = Object.keys(data?.clusters ?? {}).length;
  const mentionCount = data?.mentions.length ?? 0;
  const selected = selectedRef.current;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Unified Graph</h2>
        {elements.length > 0 && (
          <span className="text-sm text-muted-foreground">
            {entityCount} entities · {memoryCount} memories · {clusterCount} clusters · {mentionCount} mentions
          </span>
        )}
      </div>

      {/* States */}
      {isLoading && <p className="text-muted-foreground">Loading unified graph...</p>}
      {!isLoading && entityCount === 0 && memoryCount === 0 && (
        <p className="text-muted-foreground">
          No data yet. Create memories with the pipeline running to populate the graph.
        </p>
      )}

      {/* Graph canvas */}
      {elements.length > 0 && (
        <div
          className="bg-card border border-border rounded-lg overflow-hidden"
          style={{ height: "68vh" }}
        >
          <CytoscapeComponent
            elements={elements}
            stylesheet={stylesheet}
            layout={layout}
            style={{ width: "100%", height: "100%" }}
            cy={handleCy}
          />
        </div>
      )}

      {/* Detail panel */}
      {selected && (
        <div className="mt-4 bg-card border border-border rounded-lg p-4">
          {selected.kind === "node" && selected.nodeType === "entity" && (
            <>
              <h3 className="font-medium">{selected.label}</h3>
              <p className="text-sm text-muted-foreground">Type: {selected.entityType}</p>
            </>
          )}
          {selected.kind === "node" && selected.nodeType === "memory" && (
            <>
              <p className="text-sm text-foreground leading-relaxed">{selected.fullContent}</p>
              <div className="flex gap-1 mt-2 flex-wrap">
                {(selected.tags as string[])?.map((t) => (
                  <span key={t} className="text-xs px-1.5 py-0.5 rounded bg-accent text-primary">
                    {t}
                  </span>
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {selected.source}
                {selected.memoryType && ` | ${selected.memoryType}`}
                {selected.cluster >= 0 && ` | cluster ${selected.cluster}`}
              </p>
            </>
          )}
          {selected.kind === "edge" && selected.edgeType === "relation" && (
            <>
              <h3 className="font-medium">{selected.label || "relationship"}</h3>
              <p className="text-sm text-muted-foreground">
                {selected.source} → {selected.target}
                {selected.weight != null && <span className="ml-2">weight: {selected.weight}</span>}
              </p>
            </>
          )}
          {selected.kind === "edge" && selected.edgeType === "mention" && (
            <p className="text-sm text-muted-foreground">
              memory <span className="font-mono text-xs">{selected.source.slice(0, 8)}…</span> mentions entity{" "}
              <span className="font-medium text-foreground">{selected.target}</span>
            </p>
          )}
        </div>
      )}

      {/* Legend */}
      {elements.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="flex gap-4 flex-wrap">
            <span className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Entities</span>
            {Object.entries(ENTITY_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                {type}
              </div>
            ))}
          </div>
          {clusterCount > 0 && (
            <div className="flex gap-4 flex-wrap">
              <span className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Clusters</span>
              {Array.from({ length: Math.min(clusterCount, CLUSTER_PALETTE.length) }, (_, i) => (
                <div key={i} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <div className="w-3 h-3 rounded" style={{ backgroundColor: clusterColor(i) }} />
                  {i}
                </div>
              ))}
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: "#484f58" }} />
                noise
              </div>
            </div>
          )}
          <div className="flex gap-6 flex-wrap">
            <span className="text-xs text-muted-foreground font-medium uppercase tracking-wide">Edges</span>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <div className="h-px w-6 bg-[#444c56]" />
              entity relation
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <div className="h-px w-6 border-t border-dashed border-[#444c56]" />
              memory mention
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
