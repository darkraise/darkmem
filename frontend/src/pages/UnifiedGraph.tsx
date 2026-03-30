import { useUnifiedGraph, useMemoryContext } from "@/hooks/useApi";
import type { UnifiedMemory } from "@/hooks/useApi";
import { useRef, useEffect, useState, useCallback } from "react";
import { Network, DataSet } from "vis-network/standalone";

// ─── Palettes ────────────────────────────────────────────────────────────────

const CLUSTER_PALETTE = [
  "#a855f7", "#c084fc", "#d8b4fe", "#9333ea",
  "#7c3aed", "#8b5cf6", "#a78bfa", "#c4b5fd",
];

const TAG_PALETTE = [
  "#22d3ee", "#2dd4bf", "#4ade80", "#a3e635", "#facc15", "#fb923c",
];

function clusterColor(id: number): string {
  return CLUSTER_PALETTE[((id % CLUSTER_PALETTE.length) + CLUSTER_PALETTE.length) % CLUSTER_PALETTE.length];
}

function tagColor(idx: number): string {
  return TAG_PALETTE[idx % TAG_PALETTE.length];
}

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// ─── Geometry helpers ─────────────────────────────────────────────────────────

function convexHull(pts: { x: number; y: number }[]): { x: number; y: number }[] {
  if (pts.length < 3) return pts;
  const sorted = [...pts].sort((a, b) => a.x - b.x || a.y - b.y);
  const cross = (o: { x: number; y: number }, a: { x: number; y: number }, b: { x: number; y: number }) =>
    (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
  const lower: { x: number; y: number }[] = [];
  for (const p of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper: { x: number; y: number }[] = [];
  for (const p of [...sorted].reverse()) {
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }
  upper.pop();
  lower.pop();
  return lower.concat(upper);
}

function expandHull(hull: { x: number; y: number }[], padding: number): { x: number; y: number }[] {
  if (hull.length === 0) return hull;
  const cx = hull.reduce((s, p) => s + p.x, 0) / hull.length;
  const cy = hull.reduce((s, p) => s + p.y, 0) / hull.length;
  return hull.map((p) => {
    const dx = p.x - cx;
    const dy = p.y - cy;
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    return { x: p.x + (dx / dist) * padding, y: p.y + (dy / dist) * padding };
  });
}

function drawSmoothClosed(ctx: CanvasRenderingContext2D, hull: { x: number; y: number }[]) {
  const n = hull.length;
  if (n < 3) return;
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const p0 = hull[(i - 1 + n) % n];
    const p1 = hull[i];
    const p2 = hull[(i + 1) % n];
    const p3 = hull[(i + 2) % n];
    const tension = 6;
    const cp1x = p1.x + (p2.x - p0.x) / tension;
    const cp1y = p1.y + (p2.y - p0.y) / tension;
    const cp2x = p2.x - (p3.x - p1.x) / tension;
    const cp2y = p2.y - (p3.y - p1.y) / tension;
    if (i === 0) ctx.moveTo(p1.x, p1.y);
    ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y);
  }
  ctx.closePath();
}

function drawHullForGroup(
  ctx: CanvasRenderingContext2D,
  network: Network,
  memberIds: string[],
  color: string,
  fillAlpha: number,
  strokeAlpha: number,
  label: string,
) {
  const positions: { x: number; y: number }[] = [];
  for (const id of memberIds) {
    try {
      const pos = network.getPosition(id);
      if (pos) positions.push(pos);
    } catch {
      // node not yet rendered
    }
  }
  if (positions.length < 2) return;

  if (positions.length === 2) {
    const cx = (positions[0].x + positions[1].x) / 2;
    const cy = (positions[0].y + positions[1].y) / 2;
    const dx = positions[1].x - positions[0].x;
    const dy = positions[1].y - positions[0].y;
    const dist = Math.sqrt(dx * dx + dy * dy) / 2 + 50;
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(cx, cy, dist, dist * 0.6, Math.atan2(dy, dx), 0, Math.PI * 2);
    ctx.fillStyle = hexToRgba(color, fillAlpha);
    ctx.fill();
    ctx.strokeStyle = hexToRgba(color, strokeAlpha);
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();
    return;
  }

  const hull = expandHull(convexHull(positions), 45);
  ctx.save();
  drawSmoothClosed(ctx, hull);
  ctx.fillStyle = hexToRgba(color, fillAlpha);
  ctx.fill();
  ctx.strokeStyle = hexToRgba(color, strokeAlpha);
  ctx.lineWidth = 2;
  ctx.stroke();

  const topPt = hull.reduce((min, p) => (p.y < min.y ? p : min), hull[0]);
  ctx.fillStyle = hexToRgba(color, 0.45);
  ctx.font = "10px Inter, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(label, topPt.x, topPt.y - 8);
  ctx.restore();
}

// ─── Size computation ─────────────────────────────────────────────────────────

type SizeMode = "connections" | "importance" | "uniform";

function computeSize(mode: SizeMode, connections: number, importance: number): number {
  if (mode === "uniform") return 14;
  if (mode === "importance") return 8 + importance * 18;
  // connections (default)
  return 8 + Math.min(18, Math.log2(connections + 1) * 6);
}

// ─── Primary cluster color for a memory ──────────────────────────────────────

function primaryClusterColor(mem: UnifiedMemory): string {
  if (mem.clusters.length === 0) return "#484f58";
  // pick cluster with highest membership score
  let best = mem.clusters[0];
  let bestScore = mem.memberships[String(best)] ?? 0;
  for (const c of mem.clusters) {
    const s = mem.memberships[String(c)] ?? 0;
    if (s > bestScore) { best = c; bestScore = s; }
  }
  return clusterColor(best);
}

// ─── Mini sub-graph component ─────────────────────────────────────────────────

interface MiniGraphProps {
  memoryId: string;
  onNavigate: (id: string) => void;
}

function MiniGraph({ memoryId, onNavigate }: MiniGraphProps) {
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

    // Entity nodes — diamond
    for (const e of data.entities) {
      nodes.push({
        id: `entity-${e.name}`,
        label: e.name,
        shape: "diamond",
        size: 14,
        color: { background: "#ffa657", border: "#ffa657", highlight: { background: "#ffa657", border: "#fff" } },
        font: { color: "#c9d1d9", size: 10, face: "Inter, sans-serif" },
        borderWidth: 1.5,
      });
    }

    // Neighbor memory nodes — dot
    for (const n of data.neighbors) {
      neighborIds.add(n.id);
      nodes.push({
        id: n.id,
        label: n.content.slice(0, 20) + (n.content.length > 20 ? "…" : ""),
        shape: "dot",
        size: 10,
        color: { background: "#8b5cf6", border: "#a855f7", highlight: { background: "#a855f7", border: "#fff" } },
        font: { color: "#8b949e", size: 9, face: "Inter, sans-serif" },
        borderWidth: 1,
        _isNeighbor: true,
        _neighborId: n.id,
      });
    }

    // Relation edges
    const entityNodeIds = new Set(data.entities.map((e) => `entity-${e.name}`));
    for (let i = 0; i < data.relations.length; i++) {
      const r = data.relations[i];
      const src = `entity-${r.source}`;
      const tgt = `entity-${r.target}`;
      if (entityNodeIds.has(src) && entityNodeIds.has(tgt)) {
        edges.push({
          id: `rel-${i}`,
          from: src,
          to: tgt,
          label: r.type,
          arrows: { to: { enabled: true, scaleFactor: 0.4 } },
          color: { color: "#444c56", highlight: "#58a6ff", opacity: 0.8 },
          font: { color: "#6e7681", size: 8, strokeWidth: 0 },
          smooth: { type: "continuous", roundness: 0.3 },
          width: 1,
        });
      }
    }

    // Entity→memory edges (entity appears in neighbor)
    for (const e of data.entities) {
      for (const mid of e.memory_ids) {
        if (neighborIds.has(mid)) {
          edges.push({
            id: `em-${e.name}-${mid}`,
            from: `entity-${e.name}`,
            to: mid,
            arrows: {},
            color: { color: "#21262d", opacity: 0.5 },
            smooth: { type: "curvedCW", roundness: 0.2 },
            width: 0.5,
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
            gravitationalConstant: -1500,
            springLength: 70,
            springConstant: 0.05,
            damping: 0.4,
            avoidOverlap: 0.8,
          },
          stabilization: { enabled: true, iterations: 200, fit: true },
        },
        interaction: { hover: true, tooltipDelay: 99999, zoomView: true, dragView: true },
        edges: { smooth: { enabled: true, type: "continuous", roundness: 0.2 } },
      }
    );

    network.on("stabilizationIterationsDone", () => {
      network.setOptions({ physics: { enabled: false } });
    });

    // Navigate to neighbor on click
    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0] as string;
        const node = nodes.find((n) => n.id === nodeId);
        if (node?._isNeighbor) {
          onNavigate(node._neighborId as string);
        }
      }
    });

    networkRef.current = network;

    return () => {
      network.destroy();
      networkRef.current = null;
    };
  }, [data, onNavigate]);

  if (isLoading) return <p className="text-xs text-muted-foreground p-2">Loading context…</p>;
  if (!data || (data.entities.length === 0 && data.neighbors.length === 0)) {
    return <p className="text-xs text-muted-foreground p-2">No entity context available.</p>;
  }

  return (
    <div
      ref={containerRef}
      className="bg-[#0d1117] border border-border rounded"
      style={{ height: 250 }}
    />
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function UnifiedGraph() {
  const { data, isLoading } = useUnifiedGraph();
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodesDataSetRef = useRef<DataSet<any> | null>(null);
  const connectionsMapRef = useRef<Map<string, number>>(new Map());

  const [selectedMemoryId, setSelectedMemoryId] = useState<string | null>(null);
  const [sizeMode, setSizeMode] = useState<SizeMode>("connections");
  const [showTagOverlay, setShowTagOverlay] = useState(false);

  // Derive selected memory object
  const selectedMemory = data?.memories.find((m) => m.id === selectedMemoryId) ?? null;

  // Build a stable tag→color map
  const tagColorMap = useRef<Map<string, string>>(new Map());

  const buildGraph = useCallback(() => {
    if (!containerRef.current || !data) return;

    if (networkRef.current) {
      networkRef.current.destroy();
      networkRef.current = null;
    }

    // Build connections count
    const connMap = new Map<string, number>();
    for (const e of data.similarity_edges) {
      connMap.set(e.source, (connMap.get(e.source) ?? 0) + 1);
      connMap.set(e.target, (connMap.get(e.target) ?? 0) + 1);
    }
    connectionsMapRef.current = connMap;

    // Build tag→color map (stable order)
    const allTags = Array.from(new Set(data.memories.flatMap((m) => m.tags)));
    allTags.forEach((tag, i) => {
      if (!tagColorMap.current.has(tag)) {
        tagColorMap.current.set(tag, tagColor(i));
      }
    });

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const nodes: any[] = [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const edges: any[] = [];

    for (const m of data.memories) {
      const color = primaryClusterColor(m);
      const conns = connMap.get(m.id) ?? 0;
      const size = computeSize(sizeMode, conns, m.importance);

      // Multi-cluster indicator: if memory belongs to >1 cluster, use a brighter border
      const isMultiCluster = m.clusters.length > 1;
      const borderColor = isMultiCluster ? "#ffffff" : color;
      const borderWidth = isMultiCluster ? 2.5 : 1.5;

      nodes.push({
        id: m.id,
        label: m.content.slice(0, 25) + (m.content.length > 25 ? "…" : ""),
        shape: "dot",
        size,
        color: {
          background: color,
          border: borderColor,
          highlight: { background: color, border: "#ffffff" },
        },
        font: { color: "#8b949e", size: 9, face: "Inter, sans-serif" },
        borderWidth,
        shadow: { enabled: true, color: color + "30", size: 8, x: 0, y: 1 },
        mass: m.clusters.length > 0 ? 1.5 : 0.8,
        _memory: m,
      });
    }

    // Similarity edges
    for (let i = 0; i < data.similarity_edges.length; i++) {
      const e = data.similarity_edges[i];
      edges.push({
        id: `sim-${i}`,
        from: e.source,
        to: e.target,
        color: { color: "#30363d", highlight: "#8b5cf6", opacity: 0.5 },
        smooth: { type: "continuous", roundness: 0.2 },
        width: Math.max(0.5, e.score * 2),
      });
    }

    // Hidden cluster attraction edges
    const allNodeIds = new Set(nodes.map((n: { id: string }) => n.id));
    for (const [clusterId, memberIds] of Object.entries(data.clusters)) {
      const members = (memberIds as string[]).filter((id) => allNodeIds.has(id));
      for (let i = 0; i < members.length; i++) {
        for (let j = i + 1; j < members.length; j++) {
          edges.push({
            id: `cluster-${clusterId}-${i}-${j}`,
            from: members[i],
            to: members[j],
            hidden: true,
            physics: true,
            width: 0,
            length: 50,
          });
        }
      }
    }

    // Seed positions in cluster circles
    const clusterIds = Object.keys(data.clusters);
    const nClusters = clusterIds.length;
    const clusterRadius = 250 + nClusters * 40;
    const clusterCenters: Record<string, { x: number; y: number }> = {};
    clusterIds.forEach((cid, i) => {
      const angle = (2 * Math.PI * i) / nClusters;
      clusterCenters[cid] = { x: Math.cos(angle) * clusterRadius, y: Math.sin(angle) * clusterRadius };
    });
    // Use strongest cluster for seeding
    const spread = 80 + Math.sqrt(nodes.length) * 8;
    for (const node of nodes) {
      const m: UnifiedMemory = node._memory;
      if (m.clusters.length > 0) {
        const primaryCluster = m.clusters.reduce((best, c) => {
          return (m.memberships[String(c)] ?? 0) > (m.memberships[String(best)] ?? 0) ? c : best;
        }, m.clusters[0]);
        const cid = String(primaryCluster);
        if (clusterCenters[cid]) {
          node.x = clusterCenters[cid].x + (Math.random() - 0.5) * spread;
          node.y = clusterCenters[cid].y + (Math.random() - 0.5) * spread;
        }
      }
    }

    const nodesDataSet = new DataSet(nodes);
    const edgesDataSet = new DataSet(edges);
    nodesDataSetRef.current = nodesDataSet;

    const network = new Network(
      containerRef.current!,
      { nodes: nodesDataSet, edges: edgesDataSet },
      {
        physics: {
          barnesHut: {
            gravitationalConstant: -2000,
            springLength: 80,
            springConstant: 0.04,
            damping: 0.3,
            avoidOverlap: 0.8,
          },
          stabilization: { enabled: true, iterations: 400, fit: true },
          maxVelocity: 30,
          minVelocity: 0.5,
        },
        interaction: { hover: true, tooltipDelay: 99999, zoomView: true, dragView: true },
        edges: { smooth: { enabled: true, type: "continuous", roundness: 0.2 } },
      }
    );

    network.on("stabilizationIterationsDone", () => {
      network.setOptions({ physics: { enabled: false } });
    });
    network.on("dragStart", () => {
      network.setOptions({ physics: { enabled: true } });
    });
    network.on("dragEnd", () => {
      setTimeout(() => network.setOptions({ physics: { enabled: false } }), 500);
    });

    // afterDrawing: fuzzy cluster hulls + optional tag overlay
    network.on("afterDrawing", (ctx: CanvasRenderingContext2D) => {
      // Cluster hulls (drawn first, lower z)
      for (const [clusterId, memberIds] of Object.entries(data.clusters)) {
        const cid = parseInt(clusterId);
        const color = clusterColor(cid);
        drawHullForGroup(ctx, network, memberIds as string[], color, 0.07, 0.3, `Cluster ${clusterId}`);
      }

      // Tag overlay hulls (drawn on top if enabled)
      if (showTagOverlay) {
        const tagGroups = new Map<string, string[]>();
        for (const m of data.memories) {
          for (const tag of m.tags) {
            const arr = tagGroups.get(tag) ?? [];
            arr.push(m.id);
            tagGroups.set(tag, arr);
          }
        }
        let tagIdx = 0;
        for (const [tag, memberIds] of tagGroups.entries()) {
          if (memberIds.length < 2) { tagIdx++; continue; }
          const color = tagColorMap.current.get(tag) ?? tagColor(tagIdx);
          drawHullForGroup(ctx, network, memberIds, color, 0.05, 0.25, `#${tag}`);
          tagIdx++;
        }
      }
    });

    // Click handling
    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0] as string;
        const node = nodes.find((n: { id: string }) => n.id === nodeId);
        if (node?._memory) {
          setSelectedMemoryId(nodeId);
        }
      } else if (params.nodes.length === 0 && params.edges.length === 0) {
        setSelectedMemoryId(null);
      }
    });

    networkRef.current = network;
  // showTagOverlay intentionally excluded — tag overlay is drawn live in afterDrawing
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  // Rebuild when data changes
  useEffect(() => {
    buildGraph();
    return () => {
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, [buildGraph]);

  // Tag overlay toggle: just redraw without full rebuild
  useEffect(() => {
    if (networkRef.current) {
      networkRef.current.redraw();
    }
  }, [showTagOverlay]);

  // Size mode change: update nodes in-place without full rebuild
  useEffect(() => {
    if (!nodesDataSetRef.current || !data) return;
    const connMap = connectionsMapRef.current;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const updates: any[] = data.memories.map((m) => {
      const conns = connMap.get(m.id) ?? 0;
      return { id: m.id, size: computeSize(sizeMode, conns, m.importance) };
    });
    nodesDataSetRef.current.update(updates);
    if (networkRef.current) networkRef.current.redraw();
  // buildGraph triggers on data change so we only re-run when sizeMode changes
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sizeMode]);

  // Navigate from mini-graph neighbor click
  const handleNavigate = useCallback((id: string) => {
    setSelectedMemoryId(id);
    if (networkRef.current) {
      networkRef.current.selectNodes([id]);
      networkRef.current.focus(id, { animation: { duration: 600, easingFunction: "easeInOutQuad" }, scale: 1.2 });
    }
  }, []);

  const memoryCount = data?.memories.length ?? 0;
  const clusterCount = Object.keys(data?.clusters ?? {}).length;

  return (
    <div className="flex h-full" style={{ minHeight: 0 }}>
      {/* Main graph area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center gap-3 mb-3 flex-wrap">
          <h2 className="text-xl font-semibold">Unified Graph</h2>

          {/* Node size dropdown */}
          <select
            className="text-sm bg-card border border-border rounded px-2 py-1 text-foreground"
            value={sizeMode}
            onChange={(e) => setSizeMode(e.target.value as SizeMode)}
          >
            <option value="connections">Size: Connections</option>
            <option value="importance">Size: Importance</option>
            <option value="uniform">Size: Uniform</option>
          </select>

          {/* Tag overlay toggle */}
          <button
            className={`text-sm px-3 py-1 rounded border transition-colors ${
              showTagOverlay
                ? "bg-cyan-500/20 border-cyan-500 text-cyan-400"
                : "bg-card border-border text-muted-foreground hover:text-foreground"
            }`}
            onClick={() => setShowTagOverlay((v) => !v)}
          >
            Tag Overlay
          </button>

          {memoryCount > 0 && (
            <span className="text-sm text-muted-foreground ml-auto">
              {memoryCount} memories · {clusterCount} clusters
            </span>
          )}
        </div>

        {isLoading && <p className="text-muted-foreground">Loading…</p>}
        {!isLoading && memoryCount === 0 && (
          <p className="text-muted-foreground">
            No data yet. Create memories with the pipeline running to populate the graph.
          </p>
        )}

        {memoryCount > 0 && (
          <>
            <div
              ref={containerRef}
              className="bg-[#0d1117] border border-border rounded-lg flex-1"
              style={{ height: "calc(70vh - 50px)", minHeight: 300 }}
            />

            {/* Legend */}
            <div className="mt-3 flex gap-4 flex-wrap items-center text-xs text-muted-foreground">
              <span className="font-medium uppercase tracking-wide">Clusters</span>
              {Array.from({ length: Math.min(clusterCount, CLUSTER_PALETTE.length) }, (_, i) => (
                <div key={i} className="flex items-center gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: clusterColor(i) }} />
                  <span>{i}</span>
                </div>
              ))}
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-[#484f58]" />
                <span>unclustered</span>
              </div>
              <div className="flex items-center gap-1.5 ml-4">
                <div className="w-2.5 h-2.5 rounded-full border border-white bg-transparent" />
                <span>multi-cluster</span>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Right sidebar */}
      {selectedMemory && (
        <div
          className="w-[350px] border-l border-border overflow-auto flex-shrink-0 bg-card"
          style={{ maxHeight: "calc(70vh + 50px)" }}
        >
          {/* Close button */}
          <div className="flex items-center justify-between px-4 pt-3 pb-2 border-b border-border">
            <span className="text-sm font-medium">Memory Detail</span>
            <button
              className="text-muted-foreground hover:text-foreground text-lg leading-none"
              onClick={() => setSelectedMemoryId(null)}
            >
              ×
            </button>
          </div>

          <div className="p-4 space-y-3">
            {/* Full content */}
            <p className="text-sm text-foreground leading-relaxed">{selectedMemory.content}</p>

            {/* Tags */}
            {selectedMemory.tags.length > 0 && (
              <div className="flex gap-1 flex-wrap">
                {selectedMemory.tags.map((t) => (
                  <span key={t} className="text-xs px-1.5 py-0.5 rounded bg-accent text-primary">
                    {t}
                  </span>
                ))}
              </div>
            )}

            {/* Meta */}
            <div className="text-xs text-muted-foreground space-y-0.5">
              <div>Source: <span className="text-foreground">{selectedMemory.source}</span></div>
              {selectedMemory.memory_type && (
                <div>Type: <span className="text-foreground">{selectedMemory.memory_type}</span></div>
              )}
              <div>
                Importance: <span className="text-foreground">{selectedMemory.importance.toFixed(2)}</span>
              </div>
              {selectedMemory.clusters.length > 0 && (
                <div className="flex items-center gap-1">
                  Clusters:{" "}
                  {selectedMemory.clusters.map((c) => (
                    <span
                      key={c}
                      className="inline-flex items-center gap-1 text-foreground"
                    >
                      <span
                        className="inline-block w-2 h-2 rounded-full"
                        style={{ backgroundColor: clusterColor(c) }}
                      />
                      {c} ({((selectedMemory.memberships[String(c)] ?? 0) * 100).toFixed(0)}%)
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Mini sub-graph */}
            <div className="pt-2 border-t border-border">
              <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                Entity Context
              </p>
              <MiniGraph memoryId={selectedMemory.id} onNavigate={handleNavigate} />
              <p className="text-xs text-muted-foreground mt-1">
                Click a neighbor node to navigate.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
