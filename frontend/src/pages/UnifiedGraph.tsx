import { useUnifiedGraph, useMemoryContext } from "@/hooks/useApi";
import type { UnifiedMemory } from "@/hooks/useApi";
import { useRef, useEffect, useState, useCallback } from "react";
import { Network, DataSet } from "vis-network/standalone";

// ─── Palettes ────────────────────────────────────────────────────────────────

const CLUSTER_PALETTE = [
  "#a855f7", "#3fb950", "#f97316", "#06b6d4",
  "#ec4899", "#eab308", "#6366f1", "#14b8a6",
  "#f43f5e", "#84cc16", "#8b5cf6", "#0ea5e9",
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

function darkenHex(hex: string, amount = 0.45): string {
  const r = Math.max(0, Math.round(parseInt(hex.slice(1, 3), 16) * (1 - amount)));
  const g = Math.max(0, Math.round(parseInt(hex.slice(3, 5), 16) * (1 - amount)));
  const b = Math.max(0, Math.round(parseInt(hex.slice(5, 7), 16) * (1 - amount)));
  return `#${r.toString(16).padStart(2, "0")}${g.toString(16).padStart(2, "0")}${b.toString(16).padStart(2, "0")}`;
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
  _label?: string,
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

// ─── Memory type colors (pre-assigned + dynamic) ───────────────────────────

const TYPE_COLOR_PREASSIGNED: Record<string, string> = {
  fact: "#58a6ff",
  decision: "#d2a8ff",
  debug: "#f85149",
  architecture: "#3fb950",
  preference: "#ffa657",
  session: "#79c0ff",
  workflow: "#56d364",
};

const TYPE_COLOR_DYNAMIC = [
  "#f778ba", "#bb86fc", "#4fc3f7", "#aed581",
  "#ffb74d", "#ff6b6b", "#22d3ee", "#e879f9",
];

const typeColorAssignments = new Map<string, string>();
let nextDynamicIdx = 0;

function getTypeColor(memoryType: string | null): string {
  if (!memoryType) return "#8b949e";
  if (TYPE_COLOR_PREASSIGNED[memoryType]) return TYPE_COLOR_PREASSIGNED[memoryType];
  if (!typeColorAssignments.has(memoryType)) {
    typeColorAssignments.set(memoryType, TYPE_COLOR_DYNAMIC[nextDynamicIdx % TYPE_COLOR_DYNAMIC.length]);
    nextDynamicIdx++;
  }
  return typeColorAssignments.get(memoryType)!;
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
          color: { color: "#444c56", highlight: "#4CC9F0", opacity: 0.8 },
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
  const [similarityThreshold, setSimilarityThreshold] = useState(0.75);
  const { data, isLoading } = useUnifiedGraph(similarityThreshold);
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
      const color = getTypeColor(m.memory_type);
      const conns = connMap.get(m.id) ?? 0;
      const size = computeSize(sizeMode, conns, m.importance);

      const borderCol = darkenHex(color);
      nodes.push({
        id: m.id,
        label: m.content.slice(0, 25) + (m.content.length > 25 ? "…" : ""),
        shape: "dot",
        size,
        color: {
          background: color,
          border: borderCol,
          highlight: { background: color, border: darkenHex(color) },
        },
        font: { color: "#8b949e", size: 9, face: "Inter, sans-serif" },
        borderWidth: 2,
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
        color: hexToRgba("#21262d", 0.3),
        smooth: { type: "continuous", roundness: 0.2 },
        width: Math.max(0.3, e.score * 0.8),
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
            gravitationalConstant: -4000,
            springLength: 150,
            springConstant: 0.02,
            damping: 0.4,
            avoidOverlap: 1.0,
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
    // Only re-enable physics when dragging a NODE, not when panning the canvas
    network.on("dragStart", (params) => {
      if (params.nodes.length > 0) {
        network.setOptions({ physics: { enabled: true } });
      }
    });
    network.on("dragEnd", (params) => {
      if (params.nodes.length > 0) {
        setTimeout(() => network.setOptions({ physics: { enabled: false } }), 300);
      }
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

    // Focus/dim helpers (data guaranteed non-null here since we checked above)
    const graphData = data!;
    function focusOnNode(nodeId: string) {
      // Only nodes directly connected via similarity edges
      const directNeighbors = new Set<string>();
      const directEdgeIndices = new Set<number>();
      graphData.similarity_edges.forEach((e, i) => {
        if (e.source === nodeId) { directNeighbors.add(e.target); directEdgeIndices.add(i); }
        if (e.target === nodeId) { directNeighbors.add(e.source); directEdgeIndices.add(i); }
      });

      // Update nodes: selected + direct neighbors bright, everything else dimmed
      const nodeUpdates = graphData.memories.map((m) => {
        const color = getTypeColor(m.memory_type);
        if (m.id === nodeId) {
          return { id: m.id, opacity: 1, borderWidth: 5, color: { background: color, border: darkenHex(color), highlight: { background: color, border: darkenHex(color) } } };
        } else if (directNeighbors.has(m.id)) {
          return { id: m.id, opacity: 1, borderWidth: 2, color: { background: color, border: darkenHex(color), highlight: { background: color, border: darkenHex(color) } } };
        } else {
          return { id: m.id, opacity: 0.15, borderWidth: 1, color: { background: hexToRgba(color, 0.15), border: hexToRgba(color, 0.1), highlight: { background: color, border: darkenHex(color) } }, font: { color: hexToRgba("#8b949e", 0.15), size: 9 } };
        }
      });
      nodesDataSet.update(nodeUpdates);

      // Update edges: only edges touching the selected node are highlighted
      const edgeUpdates = graphData.similarity_edges.map((_, i) => {
        if (directEdgeIndices.has(i)) {
          return { id: `sim-${i}`, color: "#4CC9F0", width: 1.5 };
        }
        return { id: `sim-${i}`, color: hexToRgba("#21262d", 0.05), width: 0.2 };
      });
      edgesDataSet.update(edgeUpdates);
    }

    function exitFocusMode() {
      const nodeUpdates = graphData.memories.map((m) => {
        const color = getTypeColor(m.memory_type);
        return { id: m.id, opacity: 1, borderWidth: 2, color: { background: color, border: darkenHex(color), highlight: { background: color, border: darkenHex(color) } }, font: { color: "#8b949e", size: 9 } };
      });
      nodesDataSet.update(nodeUpdates);

      // Restore edges to normal
      const edgeResets = graphData.similarity_edges.map((e, i) => ({
        id: `sim-${i}`,
        color: hexToRgba("#21262d", 0.3),
        width: Math.max(0.3, e.score * 0.8),
      }));
      edgesDataSet.update(edgeResets);
    }

    // Click handling
    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0] as string;
        const node = nodes.find((n: { id: string }) => n.id === nodeId);
        if (node?._memory) {
          setSelectedMemoryId(nodeId);
          focusOnNode(nodeId);
        }
      } else if (params.nodes.length === 0 && params.edges.length === 0) {
        setSelectedMemoryId(null);
        exitFocusMode();
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
      // Trigger focus/dim by simulating click
      (networkRef.current as any).body.emitter.emit("click", { nodes: [id], edges: [], event: {}, pointer: { DOM: { x: 0, y: 0 }, canvas: { x: 0, y: 0 } } });
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

          {/* Similarity threshold */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <label>Similarity</label>
            <input
              type="range" min="0.5" max="0.95" step="0.05"
              value={similarityThreshold}
              onChange={(e) => setSimilarityThreshold(parseFloat(e.target.value))}
              className="w-20"
            />
            <span className="font-mono text-xs w-8">{similarityThreshold}</span>
          </div>

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
            <div className="mt-3 space-y-1.5 text-xs text-muted-foreground">
              <div className="flex gap-4 flex-wrap items-center">
                <span className="font-medium uppercase tracking-wide">Type</span>
                {Object.entries(TYPE_COLOR_PREASSIGNED).map(([type, color]) => (
                  <div key={type} className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                    <span>{type}</span>
                  </div>
                ))}
                {Array.from(typeColorAssignments.entries()).map(([type, color]) => (
                  <div key={type} className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                    <span>{type}</span>
                  </div>
                ))}
              </div>
              <div className="flex gap-4 flex-wrap items-center">
                <span className="font-medium uppercase tracking-wide">Clusters</span>
                {Array.from({ length: Math.min(clusterCount, CLUSTER_PALETTE.length) }, (_, i) => (
                  <div key={i} className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: clusterColor(i), opacity: 0.5 }} />
                    <span>{i}</span>
                  </div>
                ))}
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
