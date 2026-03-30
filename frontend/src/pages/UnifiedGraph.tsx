import { useUnifiedGraph } from "@/hooks/useApi";
// eslint-disable-next-line @typescript-eslint/no-explicit-any
import CytoscapeComp from "react-cytoscapejs";
const CytoscapeComponent = CytoscapeComp as any;
import { useRef, useMemo, useCallback, useReducer } from "react";

const ENTITY_COLORS: Record<string, string> = {
  person: "#58a6ff",
  service: "#3fb950",
  project: "#d2a8ff",
  technology: "#ffa657",
  concept: "#8b949e",
  organization: "#f778ba",
};

const CLUSTER_PALETTE = [
  "#58a6ff", "#3fb950", "#ffa657", "#d2a8ff",
  "#f778ba", "#79c0ff", "#56d364", "#ffb74d",
  "#bb86fc", "#ff6b6b", "#4fc3f7", "#aed581",
];

function clusterColor(id: number): string {
  return CLUSTER_PALETTE[id % CLUSTER_PALETTE.length];
}

function clusterBg(id: number): string {
  // Translucent version for compound node background
  const hex = CLUSTER_PALETTE[id % CLUSTER_PALETTE.length];
  return hex + "18"; // ~10% opacity
}

const stylesheet = [
  // Cluster compound nodes (parent)
  {
    selector: "node[nodeType = 'cluster']",
    style: {
      "background-color": "data(bgColor)",
      "background-opacity": 0.6,
      "border-width": 1.5,
      "border-color": "data(color)",
      "border-opacity": 0.4,
      shape: "round-rectangle" as const,
      label: "data(label)",
      "text-valign": "top" as const,
      "text-halign": "center" as const,
      "text-margin-y": 10,
      "font-size": 10,
      color: "data(color)",
      "padding": "20px",
    },
  },
  // Entity nodes
  {
    selector: "node[nodeType = 'entity']",
    style: {
      label: "data(label)",
      "background-color": "data(color)",
      color: "#c9d1d9",
      "text-valign": "bottom" as const,
      "text-margin-y": 6,
      "font-size": 10,
      width: 30,
      height: 30,
      "border-width": 2,
      "border-color": "#30363d",
      shape: "diamond" as const,
    },
  },
  // Memory nodes
  {
    selector: "node[nodeType = 'memory']",
    style: {
      label: "data(label)",
      "background-color": "data(color)",
      color: "#c9d1d9",
      "text-valign": "bottom" as const,
      "text-margin-y": 5,
      "font-size": 8,
      width: 22,
      height: 22,
      "border-width": 1.5,
      "border-color": "#21262d",
      shape: "round-rectangle" as const,
      "text-max-width": "80px",
      "text-wrap": "ellipsis" as const,
    },
  },
  // Entity–entity relation edges
  {
    selector: "edge[edgeType = 'relation']",
    style: {
      width: 2,
      "line-color": "#444c56",
      "target-arrow-color": "#444c56",
      "target-arrow-shape": "triangle" as const,
      "curve-style": "bezier" as const,
      label: "data(label)",
      "font-size": 8,
      color: "#6e7681",
      "text-rotation": "autorotate" as const,
      "text-margin-y": -10,
    },
  },
  // Memory→entity mention edges
  {
    selector: "edge[edgeType = 'mention']",
    style: {
      width: 0.8,
      "line-color": "#30363d",
      "line-style": "dashed" as const,
      "target-arrow-color": "#30363d",
      "target-arrow-shape": "vee" as const,
      "curve-style": "bezier" as const,
    },
  },
  {
    selector: "node:selected",
    style: { "border-color": "#58a6ff", "border-width": 3 },
  },
];

const layout = {
  name: "cose",
  animate: true,
  animationDuration: 800,
  nodeRepulsion: () => 10000,
  idealEdgeLength: () => 100,
  gravity: 0.2,
  numIter: 800,
  padding: 30,
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Selected = { kind: "node" | "edge"; [key: string]: any } | null;

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

    // Create cluster compound (parent) nodes
    for (const [clusterId, memberIds] of Object.entries(data.clusters)) {
      const cid = parseInt(clusterId);
      nodes.push({
        data: {
          id: `cluster-${clusterId}`,
          label: `Cluster ${clusterId} (${memberIds.length})`,
          nodeType: "cluster",
          color: clusterColor(cid),
          bgColor: clusterBg(cid),
        },
      });
    }

    // Entity nodes (no parent — float freely)
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

    // Memory nodes — assigned to cluster parent if clustered
    for (const m of data.memories) {
      const color = m.cluster >= 0 ? clusterColor(m.cluster) : "#484f58";
      const nodeData: Record<string, unknown> = {
        id: m.id,
        label: m.content.slice(0, 30) + (m.content.length > 30 ? "..." : ""),
        fullContent: m.content,
        source: m.source,
        tags: m.tags,
        memoryType: m.memory_type,
        cluster: m.cluster,
        nodeType: "memory",
        color,
      };
      // Assign parent compound node for clustered memories
      if (m.cluster >= 0) {
        nodeData.parent = `cluster-${m.cluster}`;
      }
      nodes.push({ data: nodeData });
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
    const allNodeIds = new Set([...data.memories.map((m) => m.id), ...data.entities.map((e) => e.id)]);
    for (let i = 0; i < data.mentions.length; i++) {
      const m = data.mentions[i];
      if (allNodeIds.has(m.source) && allNodeIds.has(m.target)) {
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
      const d = evt.target.data();
      if (d.nodeType === "cluster") return; // don't select cluster backgrounds
      selectedRef.current = { ...d, kind: "node" };
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
  const selected = selectedRef.current;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Unified Graph</h2>
        {(entityCount > 0 || memoryCount > 0) && (
          <span className="text-sm text-muted-foreground">
            {entityCount} entities · {memoryCount} memories · {clusterCount} clusters
          </span>
        )}
      </div>

      {isLoading && <p className="text-muted-foreground">Loading...</p>}
      {!isLoading && entityCount === 0 && memoryCount === 0 && (
        <p className="text-muted-foreground">
          No data yet. Create memories with the pipeline running to populate the graph.
        </p>
      )}

      {(entityCount > 0 || memoryCount > 0) && (
        <div className="bg-card border border-border rounded-lg overflow-hidden" style={{ height: "70vh" }}>
          <CytoscapeComponent
            elements={elements}
            stylesheet={stylesheet}
            layout={layout}
            style={{ width: "100%", height: "100%" }}
            cy={handleCy}
          />
        </div>
      )}

      {selected && (
        <div className="mt-4 bg-card border border-border rounded-lg p-4">
          {selected.kind === "node" && selected.nodeType === "entity" && (
            <>
              <h3 className="font-medium">{selected.label}</h3>
              <p className="text-sm text-muted-foreground">Entity type: {selected.entityType}</p>
            </>
          )}
          {selected.kind === "node" && selected.nodeType === "memory" && (
            <>
              <p className="text-sm text-foreground leading-relaxed">{selected.fullContent}</p>
              <div className="flex gap-1 mt-2 flex-wrap">
                {(selected.tags as string[])?.map((t) => (
                  <span key={t} className="text-xs px-1.5 py-0.5 rounded bg-accent text-primary">{t}</span>
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {selected.source}{selected.memoryType && ` | ${selected.memoryType}`}
                {selected.cluster >= 0 && ` | cluster ${selected.cluster}`}
              </p>
            </>
          )}
          {selected.kind === "edge" && selected.edgeType === "relation" && (
            <p className="text-sm text-muted-foreground">
              <span className="text-foreground font-medium">{selected.label}</span>
              {" "}{selected.source} → {selected.target}
            </p>
          )}
          {selected.kind === "edge" && selected.edgeType === "mention" && (
            <p className="text-sm text-muted-foreground">
              Memory mentions entity <span className="font-medium text-foreground">{selected.target}</span>
            </p>
          )}
        </div>
      )}

      {(entityCount > 0 || memoryCount > 0) && (
        <div className="mt-4 space-y-2 text-xs text-muted-foreground">
          <div className="flex gap-4 flex-wrap items-center">
            <span className="font-medium uppercase tracking-wide">Entities</span>
            {Object.entries(ENTITY_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-1">
                <div className="w-3 h-3 rotate-45" style={{ backgroundColor: color }} />
                <span>{type}</span>
              </div>
            ))}
          </div>
          <div className="flex gap-4 flex-wrap items-center">
            <span className="font-medium uppercase tracking-wide">Clusters</span>
            {Array.from({ length: clusterCount }, (_, i) => (
              <div key={i} className="flex items-center gap-1">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: clusterColor(i) }} />
                <span>{i}</span>
              </div>
            ))}
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded" style={{ backgroundColor: "#484f58" }} />
              <span>unclustered</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
