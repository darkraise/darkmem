import { useRef, useEffect } from "react";
import { Network, DataSet } from "vis-network/standalone";
import { useMemoryContext } from "@/hooks/useApi";

export interface MiniGraphProps {
  memoryId: string;
  onNavigate: (id: string) => void;
  onEntitySelect?: (entityId: string) => void;
}

export function MiniGraph({ memoryId, onNavigate, onEntitySelect }: MiniGraphProps) {
  const { data, isLoading } = useMemoryContext(memoryId);
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);

  useEffect(() => {
    if (!containerRef.current || !data) return;
    if (networkRef.current) {
      networkRef.current.destroy();
      networkRef.current = null;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const nodes: any[] = [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const edges: any[] = [];
    const neighborIds = new Set<string>();

    // Entity nodes — diamond (deduplicate by name+type)
    const seenEntities = new Set<string>();
    for (const e of data.entities) {
      const entityKey = `${e.name}::${e.entity_type}`;
      if (seenEntities.has(entityKey)) continue;
      seenEntities.add(entityKey);
      nodes.push({
        id: `entity-${e.name}-${e.entity_type}`,
        label: e.name,
        shape: "diamond",
        size: 16,
        color: {
          background: "#ffa657",
          border: "#ffa657",
          highlight: { background: "#ffa657", border: "#fff" },
        },
        font: { color: "#c9d1d9", size: 11, face: "Inter, sans-serif" },
        borderWidth: 2,
        _isEntity: true,
        _entityId: e.id,
      });
    }

    // Neighbor memory nodes — dot (deduplicate by id)
    for (const n of data.neighbors) {
      if (neighborIds.has(n.id)) continue;
      neighborIds.add(n.id);
      nodes.push({
        id: n.id,
        label: n.content.slice(0, 18) + (n.content.length > 18 ? "…" : ""),
        shape: "dot",
        size: 12,
        color: {
          background: "#8b5cf6",
          border: "#a855f7",
          highlight: { background: "#a855f7", border: "#fff" },
        },
        font: { color: "#8b949e", size: 10, face: "Inter, sans-serif" },
        borderWidth: 1,
        _isNeighbor: true,
        _neighborId: n.id,
      });
    }

    // Relation edges — map entity names to node IDs
    const entityNameToId = new Map<string, string>();
    for (const e of data.entities) {
      if (!entityNameToId.has(e.name)) {
        entityNameToId.set(e.name, `entity-${e.name}-${e.entity_type}`);
      }
    }
    const entityNodeIds = new Set(entityNameToId.values());
    for (let i = 0; i < data.relations.length; i++) {
      const r = data.relations[i];
      const src = entityNameToId.get(r.source);
      const tgt = entityNameToId.get(r.target);
      if (src && tgt && entityNodeIds.has(src) && entityNodeIds.has(tgt)) {
        edges.push({
          id: `rel-${i}`,
          from: src!,
          to: tgt!,
          label: r.type,
          arrows: { to: { enabled: true, scaleFactor: 0.5 } },
          color: { color: "#7a8490", highlight: "#4CC9F0", opacity: 0.9 },
          font: { color: "#8b949e", size: 9, strokeWidth: 0 },
          smooth: { type: "continuous", roundness: 0.3 },
          width: 1.5,
        });
      }
    }

    // Entity→memory edges (entity appears in neighbor)
    for (const e of data.entities) {
      const entityId = entityNameToId.get(e.name);
      if (!entityId) continue;
      for (const mid of e.memory_ids) {
        if (neighborIds.has(mid)) {
          edges.push({
            id: `em-${e.name}-${e.entity_type}-${mid}`,
            from: entityId,
            to: mid,
            arrows: {},
            color: { color: "#586069", opacity: 0.7 },
            smooth: { type: "curvedCW", roundness: 0.2 },
            width: 1,
            dashes: [3, 3],
          });
        }
      }
    }

    const nodesDs = new DataSet(nodes);
    const edgesDs = new DataSet(edges);

    const network = new Network(
      containerRef.current,
      { nodes: nodesDs, edges: edgesDs },
      {
        physics: {
          barnesHut: {
            gravitationalConstant: -600,
            springLength: 60,
            springConstant: 0.08,
            damping: 0.5,
            avoidOverlap: 0.4,
          },
          stabilization: { enabled: true, iterations: 150, fit: true },
        },
        interaction: {
          hover: true,
          tooltipDelay: 99999,
          zoomView: true,
          dragView: true,
        },
        edges: {
          color: { color: "#6e7681", opacity: 0.8 },
          smooth: { enabled: true, type: "continuous", roundness: 0.2 },
          length: 60,
        },
        nodes: {
          shape: "dot",
          size: 14,
          font: { color: "#c9d1d9", size: 11 },
          borderWidth: 2,
        },
      },
    );

    network.on("stabilizationIterationsDone", () => {
      network.setOptions({ physics: { enabled: false } });
      network.fit({ animation: { duration: 200, easingFunction: "easeInOutQuad" } });
    });

    // Navigate to neighbor on click
    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0] as string;
        const node = nodes.find((n) => n.id === nodeId);
        if (node?._isNeighbor) {
          onNavigate(node._neighborId as string);
        } else if (node?._isEntity && onEntitySelect) {
          onEntitySelect(node._entityId as string);
        }
      }
    });

    networkRef.current = network;

    return () => {
      network.destroy();
      networkRef.current = null;
    };
  }, [data, onNavigate, onEntitySelect]);

  if (isLoading)
    return (
      <p className="text-xs text-muted-foreground p-2">Loading context…</p>
    );
  if (!data || (data.entities.length === 0 && data.neighbors.length === 0)) {
    return (
      <p className="text-xs text-muted-foreground p-2">
        No entities extracted yet. Run the pipeline with entity extraction enabled to populate this graph.
      </p>
    );
  }

  return (
    <div
      ref={containerRef}
      className="bg-[#0d1117] border border-border rounded"
      style={{ height: 250 }}
    />
  );
}
