import { useUnifiedGraph } from "@/hooks/useApi";
import { useRef, useEffect, useState, useCallback } from "react";
import { Network, DataSet } from "vis-network/standalone";

const ENTITY_COLORS: Record<string, string> = {
  person: "#58a6ff",
  service: "#3fb950",
  project: "#d2a8ff",
  technology: "#ffa657",
  concept: "#8b949e",
  organization: "#f778ba",
};

const CLUSTER_PALETTE = [
  "#a855f7", "#c084fc", "#d8b4fe", "#9333ea",
  "#7c3aed", "#8b5cf6", "#a78bfa", "#c4b5fd",
  "#e879f9", "#f0abfc", "#6366f1", "#818cf8",
];

function clusterColor(id: number): string {
  return CLUSTER_PALETTE[id % CLUSTER_PALETTE.length];
}

function clusterBg(id: number): string {
  const hex = CLUSTER_PALETTE[id % CLUSTER_PALETTE.length];
  // Convert hex to rgba with low opacity
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},0.08)`;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Selected = { type: "node" | "edge"; data: any } | null;

export default function UnifiedGraph() {
  const { data, isLoading } = useUnifiedGraph();
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const [selected, setSelected] = useState<Selected>(null);

  const buildGraph = useCallback(() => {
    if (!containerRef.current || !data) return;

    // Destroy previous network
    if (networkRef.current) {
      networkRef.current.destroy();
      networkRef.current = null;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const nodes: any[] = [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const edges: any[] = [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const nodeDataMap: Record<string, any> = {};

    // Entity nodes — diamond shape, larger, bold
    for (const e of data.entities) {
      const color = ENTITY_COLORS[e.entity_type] || "#8b949e";
      const node = {
        id: e.id,
        label: e.name,
        shape: "diamond",
        size: 18,
        color: {
          background: color,
          border: color,
          highlight: { background: color, border: "#ffffff" },
        },
        font: { color: "#c9d1d9", size: 11, face: "Inter, sans-serif" },
        borderWidth: 2,
        shadow: { enabled: true, color: color + "40", size: 12, x: 0, y: 2 },
      };
      nodes.push(node);
      nodeDataMap[e.id] = { ...e, nodeType: "entity" };
    }

    // Memory nodes — dot shape, colored by cluster
    for (const m of data.memories) {
      const color = m.cluster >= 0 ? clusterColor(m.cluster) : "#484f58";
      const borderColor = m.cluster >= 0 ? clusterColor(m.cluster) : "#30363d";
      const connections = data.mentions.filter((mt) => mt.source === m.id).length;
      const size = Math.max(8, Math.min(20, 8 + Math.log2(connections + 1) * 4));

      const node = {
        id: m.id,
        label: m.content.slice(0, 25) + (m.content.length > 25 ? "..." : ""),
        shape: "dot",
        size,
        color: {
          background: color,
          border: borderColor,
          highlight: { background: color, border: "#ffffff" },
        },
        font: { color: "#8b949e", size: 9, face: "Inter, sans-serif" },
        borderWidth: 1.5,
        shadow: { enabled: true, color: color + "30", size: 8, x: 0, y: 1 },
        mass: m.cluster >= 0 ? 1.5 : 0.8,
      };
      nodes.push(node);
      nodeDataMap[m.id] = { ...m, nodeType: "memory" };
    }

    // Entity-entity relation edges — solid, curved
    const entityIds = new Set(data.entities.map((e) => e.id));
    for (let i = 0; i < data.relations.length; i++) {
      const r = data.relations[i];
      if (entityIds.has(r.source) && entityIds.has(r.target)) {
        edges.push({
          id: `rel-${i}`,
          from: r.source,
          to: r.target,
          label: r.type || "",
          arrows: { to: { enabled: true, scaleFactor: 0.5 } },
          color: { color: "#444c56", highlight: "#58a6ff", opacity: 0.7 },
          font: { color: "#6e7681", size: 8, strokeWidth: 0, align: "top" },
          smooth: { type: "continuous", roundness: 0.3 },
          width: 1.5,
          _edgeType: "relation",
          _data: r,
        });
      }
    }

    // Memory→entity mention edges — dashed, thinner
    const allNodeIds = new Set(nodes.map((n) => n.id));
    for (let i = 0; i < data.mentions.length; i++) {
      const m = data.mentions[i];
      if (allNodeIds.has(m.source) && allNodeIds.has(m.target)) {
        edges.push({
          id: `mention-${i}`,
          from: m.source,
          to: m.target,
          arrows: { to: { enabled: true, scaleFactor: 0.3 } },
          color: { color: "#21262d", highlight: "#58a6ff", opacity: 0.4 },
          smooth: { type: "curvedCW", roundness: 0.15 + Math.random() * 0.15 },
          width: 0.5,
          dashes: [4, 4],
          _edgeType: "mention",
          _data: m,
        });
      }
    }

    // Build cluster groups for physics — add hidden edges between cluster members for attraction
    for (const [clusterId, memberIds] of Object.entries(data.clusters)) {
      const members = memberIds.filter((id: string) => allNodeIds.has(id));
      // Add soft attraction edges between cluster members (hidden)
      for (let i = 0; i < members.length; i++) {
        for (let j = i + 1; j < members.length; j++) {
          edges.push({
            id: `cluster-${clusterId}-${i}-${j}`,
            from: members[i],
            to: members[j],
            hidden: true,
            physics: true,
            width: 0,
            length: 50, // short = tight clustering
          });
        }
      }
    }

    const nodesDataSet = new DataSet(nodes);
    const edgesDataSet = new DataSet(edges);

    const network = new Network(
      containerRef.current,
      { nodes: nodesDataSet, edges: edgesDataSet },
      {
        physics: {
          enabled: true,
          solver: "forceAtlas2Based",
          forceAtlas2Based: {
            gravitationalConstant: -80,
            centralGravity: 0.008,
            springLength: 120,
            springConstant: 0.06,
            damping: 0.4,
            avoidOverlap: 0.5,
          },
          stabilization: {
            enabled: true,
            iterations: 300,
            fit: true,
          },
          maxVelocity: 30,
          minVelocity: 0.5,
        },
        interaction: {
          hover: true,
          tooltipDelay: 200,
          zoomView: true,
          dragView: true,
        },
        layout: {
          improvedLayout: true,
        },
        edges: {
          smooth: {
            enabled: true,
            type: "continuous",
            roundness: 0.2,
          },
        },
      }
    );

    // Custom cluster background drawing
    network.on("afterDrawing", (ctx: CanvasRenderingContext2D) => {
      for (const [clusterId, memberIds] of Object.entries(data.clusters)) {
        const cid = parseInt(clusterId);
        const positions: { x: number; y: number }[] = [];
        for (const id of memberIds as string[]) {
          try {
            const pos = network.getPosition(id);
            if (pos) positions.push(pos);
          } catch {
            // Node might not be rendered
          }
        }
        if (positions.length < 2) continue;

        // Compute bounding circle with padding
        const cx = positions.reduce((s, p) => s + p.x, 0) / positions.length;
        const cy = positions.reduce((s, p) => s + p.y, 0) / positions.length;
        const maxDist = Math.max(
          ...positions.map((p) => Math.sqrt((p.x - cx) ** 2 + (p.y - cy) ** 2))
        );
        const radius = maxDist + 60;

        // Draw soft blob
        ctx.save();
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.fillStyle = clusterBg(cid);
        ctx.fill();
        ctx.strokeStyle = clusterColor(cid) + "25";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Cluster label
        ctx.fillStyle = clusterColor(cid) + "60";
        ctx.font = "10px Inter, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(`Cluster ${clusterId}`, cx, cy - radius + 14);
        ctx.restore();
      }
    });

    // Click handling
    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const nodeData = nodeDataMap[nodeId];
        if (nodeData) {
          setSelected({ type: "node", data: nodeData });
        }
      } else if (params.edges.length > 0) {
        const edgeId = params.edges[0];
        const edge = edges.find((e) => e.id === edgeId);
        if (edge && !edge.hidden) {
          setSelected({
            type: "edge",
            data: { edgeType: edge._edgeType, label: edge.label, ...edge._data },
          });
        }
      } else {
        setSelected(null);
      }
    });

    networkRef.current = network;
  }, [data]);

  useEffect(() => {
    buildGraph();
    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, [buildGraph]);

  const entityCount = data?.entities.length ?? 0;
  const memoryCount = data?.memories.length ?? 0;
  const clusterCount = Object.keys(data?.clusters ?? {}).length;

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
        <div
          ref={containerRef}
          className="bg-[#0d1117] border border-border rounded-lg"
          style={{ height: "70vh" }}
        />
      )}

      {selected && (
        <div className="mt-4 bg-card border border-border rounded-lg p-4">
          {selected.type === "node" && selected.data.nodeType === "entity" && (
            <>
              <h3 className="font-medium">{selected.data.name}</h3>
              <p className="text-sm text-muted-foreground">Entity type: {selected.data.entity_type}</p>
            </>
          )}
          {selected.type === "node" && selected.data.nodeType === "memory" && (
            <>
              <p className="text-sm text-foreground leading-relaxed">{selected.data.content}</p>
              <div className="flex gap-1 mt-2 flex-wrap">
                {(selected.data.tags as string[])?.map((t) => (
                  <span key={t} className="text-xs px-1.5 py-0.5 rounded bg-accent text-primary">{t}</span>
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {selected.data.source}
                {selected.data.memory_type && ` | ${selected.data.memory_type}`}
                {selected.data.cluster >= 0 && ` | cluster ${selected.data.cluster}`}
              </p>
            </>
          )}
          {selected.type === "edge" && selected.data.edgeType === "relation" && (
            <p className="text-sm text-muted-foreground">
              <span className="text-foreground font-medium">{selected.data.label || selected.data.type}</span>
              {" "}{selected.data.source} → {selected.data.target}
            </p>
          )}
          {selected.type === "edge" && selected.data.edgeType === "mention" && (
            <p className="text-sm text-muted-foreground">
              Memory mentions entity <span className="font-medium text-foreground">{selected.data.target}</span>
            </p>
          )}
        </div>
      )}

      {(entityCount > 0 || memoryCount > 0) && (
        <div className="mt-4 space-y-2 text-xs text-muted-foreground">
          <div className="flex gap-4 flex-wrap items-center">
            <span className="font-medium uppercase tracking-wide">Entities</span>
            {Object.entries(ENTITY_COLORS).map(([type, color]) => (
              <div key={type} className="flex items-center gap-1.5">
                <div className="w-3 h-3 rotate-45" style={{ backgroundColor: color }} />
                <span>{type}</span>
              </div>
            ))}
          </div>
          <div className="flex gap-4 flex-wrap items-center">
            <span className="font-medium uppercase tracking-wide">Clusters</span>
            {Array.from({ length: clusterCount }, (_, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: clusterColor(i) }} />
                <span>{i}</span>
              </div>
            ))}
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: "#484f58" }} />
              <span>unclustered</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
