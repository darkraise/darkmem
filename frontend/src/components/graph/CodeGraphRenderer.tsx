import { useRef, useEffect, useCallback } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import EdgeCurveProgram, { indexParallelEdgesIndex } from "@sigma/edge-curve";
import FA2Layout from "graphology-layout-forceatlas2/worker";
import { inferSettings } from "graphology-layout-forceatlas2";
import { lightenHex } from "@/lib/graph-colors";

// Exact GitNexus node sizes
const NODE_SIZES: Record<string, number> = {
  project: 20, package: 16, module: 13, folder: 10,
  file: 6, class: 8, struct: 8, record: 8,
  function: 4, method: 3, constructor: 4,
  interface: 7, trait: 7, enum: 5,
  variable: 2, import: 1.5, decorator: 2,
  type: 3, impl: 3, namespace: 13,
  property: 2, const: 2, static: 2,
};
const DEFAULT_NODE_SIZE = 3;

// Exact GitNexus node colors
const NODE_COLORS: Record<string, string> = {
  project: "#a855f7", package: "#8b5cf6", module: "#7c3aed",
  folder: "#6366f1", file: "#3b82f6",
  class: "#f59e0b", struct: "#f59e0b", record: "#f59e0b",
  function: "#10b981", method: "#14b8a6", constructor: "#10b981",
  variable: "#64748b", import: "#475569", decorator: "#eab308",
  interface: "#ec4899", trait: "#ec4899",
  enum: "#f97316", type: "#a78bfa", impl: "#14b8a6",
  namespace: "#7c3aed", property: "#64748b",
};
const DEFAULT_NODE_COLOR = "#6b7280";

// Exact GitNexus edge styles
const EDGE_COLORS: Record<string, string> = {
  contains: "#2d5a3d", defines: "#0e7490",
  imports: "#1d4ed8", calls: "#7c3aed",
  extends: "#c2410c", implements: "#be185d",
};
const DEFAULT_EDGE_COLOR = "#2a2a3a";

const EDGE_SIZE_MULTIPLIERS: Record<string, number> = {
  contains: 0.4, defines: 0.5, imports: 0.6, calls: 0.8,
  extends: 1.0, implements: 0.9,
};
const DEFAULT_EDGE_SIZE = 0.5;

// Exact GitNexus mass values
function getNodeMass(kind: string, nodeCount: number): number {
  const m = nodeCount > 5000 ? 2 : nodeCount > 1000 ? 1.5 : 1;
  switch (kind) {
    case "project": return 50 * m;
    case "package": return 30 * m;
    case "module": return 20 * m;
    case "folder": return 15 * m;
    case "namespace": return 20 * m;
    case "class": case "interface": return 5 * m;
    case "file": return 3 * m;
    case "function": case "method": return 2 * m;
    default: return 1;
  }
}

// Exact GitNexus size scaling for large graphs
function getScaledNodeSize(baseSize: number, nodeCount: number): number {
  if (nodeCount > 50000) return Math.max(1, baseSize * 0.4);
  if (nodeCount > 20000) return Math.max(1.5, baseSize * 0.5);
  if (nodeCount > 5000) return Math.max(2, baseSize * 0.65);
  if (nodeCount > 1000) return Math.max(2.5, baseSize * 0.8);
  return baseSize;
}

interface CodeGraphRendererProps {
  nodes: Array<{ id: string; label: string; kind?: string; language?: string; file_path?: string }>;
  edges: Array<{ source: string; target: string; type: string }>;
  selectedId: string | null;
  onSelect: (node: { id: string; label: string; kind?: string; file_path?: string } | null) => void;
  highlightedIds?: Set<string>;
  visibleEdgeTypes?: Set<string>;
}

export function CodeGraphRenderer({
  nodes,
  edges,
  selectedId,
  onSelect,
  highlightedIds,
  visibleEdgeTypes,
}: CodeGraphRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const fa2Ref = useRef<FA2Layout | null>(null);
  const selectedIdRef = useRef(selectedId);
  const hoveredNodeRef = useRef<string | null>(null);
  const highlightedIdsRef = useRef(highlightedIds);
  const visibleEdgeTypesRef = useRef(visibleEdgeTypes);

  const buildGraph = useCallback(() => {
    if (!containerRef.current) return;

    if (fa2Ref.current) { fa2Ref.current.kill(); fa2Ref.current = null; }
    if (sigmaRef.current) { sigmaRef.current.kill(); sigmaRef.current = null; graphRef.current = null; }

    const graph = new Graph();
    graphRef.current = graph;

    const spread = Math.max(100, Math.sqrt(nodes.length) * 10);

    const nodeCount = nodes.length;
    const edgeBaseSize = nodeCount > 20000 ? 0.4 : nodeCount > 5000 ? 0.6 : 1.0;

    for (const n of nodes) {
      if (graph.hasNode(n.id)) continue;
      const kind = n.kind?.toLowerCase() ?? "";
      const color = NODE_COLORS[kind] ?? DEFAULT_NODE_COLOR;
      const baseSize = NODE_SIZES[kind] ?? DEFAULT_NODE_SIZE;
      const size = getScaledNodeSize(baseSize, nodeCount);

      graph.addNode(n.id, {
        x: (Math.random() - 0.5) * spread,
        y: (Math.random() - 0.5) * spread,
        label: n.label,
        size,
        color,
        mass: getNodeMass(kind, nodeCount),
        _kind: n.kind,
        _filePath: n.file_path,
        _baseSize: size,
      });
    }

    for (const e of edges) {
      if (!graph.hasNode(e.source) || !graph.hasNode(e.target)) continue;
      try {
        const edgeType = e.type?.toLowerCase() ?? "";
        graph.addEdge(e.source, e.target, {
          color: EDGE_COLORS[edgeType] || DEFAULT_EDGE_COLOR,
          size: edgeBaseSize * (EDGE_SIZE_MULTIPLIERS[edgeType] || DEFAULT_EDGE_SIZE),
          type: "curve",
          curvature: 0.12 + Math.random() * 0.08,
          _relType: edgeType,
        });
      } catch { /* duplicate edge */ }
    }

    indexParallelEdgesIndex(graph, {
      edgeIndexAttribute: "parallelIndex",
      edgeMaxIndexAttribute: "parallelMaxIndex",
    });

    const gravity = nodeCount < 500 ? 0.8 : nodeCount < 2000 ? 0.5 : nodeCount < 10000 ? 0.3 : 0.15;
    const scalingRatio = nodeCount < 500 ? 15 : nodeCount < 2000 ? 30 : nodeCount < 10000 ? 60 : 100;
    const slowDown = nodeCount < 500 ? 1 : nodeCount < 2000 ? 2 : nodeCount < 10000 ? 3 : 5;
    const layoutTimeout = nodeCount < 500 ? 8000 : nodeCount < 2000 ? 20000 : 30000;

    const sigma = new Sigma(graph, containerRef.current, {
      allowInvalidContainer: true,
      renderLabels: true,
      renderEdgeLabels: false,
      labelSize: 11,
      labelWeight: "500",
      labelFont: "JetBrains Mono, monospace",
      labelColor: { color: "#e4e4ed" },
      labelRenderedSizeThreshold: 8,
      labelDensity: 0.1,
      defaultEdgeType: "curve",
      edgeProgramClasses: { curve: EdgeCurveProgram },
      stagePadding: 60,
      defaultNodeColor: DEFAULT_NODE_COLOR,
      defaultEdgeColor: DEFAULT_EDGE_COLOR,
      minCameraRatio: 0.002,
      maxCameraRatio: 50,
      hideEdgesOnMove: true,
      zIndex: true,
      nodeReducer(node, data) {
        const res = { ...data };
        const baseSize = (data._baseSize as number) || DEFAULT_NODE_SIZE;
        const hl = highlightedIdsRef.current;

        if (hl && hl.size > 0) {
          if (hl.has(node)) {
            res.color = "#ef4444";
            res.size = baseSize * 1.8;
            res.zIndex = 2;
          } else {
            res.color = "#333333";
            res.size = baseSize * 0.3;
            res.label = "";
            res.zIndex = 0;
          }
          return res;
        }

        const hov = hoveredNodeRef.current;
        const sel = selectedIdRef.current;
        const active = hov || sel;

        if (active) {
          const isNeighbor = graph.hasEdge(active, node) || graph.hasEdge(node, active);

          if (node === active) {
            res.color = lightenHex(data.color || DEFAULT_NODE_COLOR, 0.4);
            res.size = baseSize * 1.8;
            res.zIndex = 2;
            res.highlighted = true;
          } else if (isNeighbor) {
            res.size = baseSize * 1.3;
            res.zIndex = 1;
          } else {
            res.color = "#333333";
            res.size = baseSize * 0.6;
            res.label = "";
            res.zIndex = 0;
          }
        }

        return res;
      },
      edgeReducer(edge, data) {
        const res = { ...data };
        const edgeType = (graph.getEdgeAttribute(edge, "_relType") as string) || "";

        if (visibleEdgeTypesRef.current && !visibleEdgeTypesRef.current.has(edgeType)) {
          res.hidden = true;
          return res;
        }

        const hl = highlightedIdsRef.current;
        if (hl && hl.size > 0) {
          const src = graph.source(edge);
          const tgt = graph.target(edge);
          if (!hl.has(src) || !hl.has(tgt)) {
            res.hidden = true;
          }
          return res;
        }

        const hov = hoveredNodeRef.current;
        const sel = selectedIdRef.current;
        const active = hov || sel;

        if (active) {
          const src = graph.source(edge);
          const tgt = graph.target(edge);
          if (src === active || tgt === active) {
            res.size = (data.size || DEFAULT_EDGE_SIZE) * 2;
            const neighborNode = src === active ? tgt : src;
            res.color = lightenHex(
              (graph.getNodeAttribute(neighborNode, "color") as string) || DEFAULT_NODE_COLOR,
              0.3,
            );
          } else {
            res.color = "#1a1a24";
            res.size = (data.size || DEFAULT_EDGE_SIZE) * 0.3;
          }
        }

        return res;
      },
    });

    sigma.on("enterNode", ({ node }) => {
      hoveredNodeRef.current = node;
      containerRef.current!.style.cursor = "pointer";
      sigma.refresh();
    });
    sigma.on("leaveNode", () => {
      hoveredNodeRef.current = null;
      containerRef.current!.style.cursor = "default";
      sigma.refresh();
    });
    sigma.on("clickNode", ({ node }) => {
      const attrs = graph.getNodeAttributes(node);
      onSelect({
        id: node,
        label: attrs.label as string,
        kind: attrs._kind as string | undefined,
        file_path: attrs._filePath as string | undefined,
      });
    });
    sigma.on("clickStage", () => onSelect(null));

    sigmaRef.current = sigma;

    const fa2 = new FA2Layout(graph, {
      settings: {
        ...inferSettings(graph),
        linLogMode: false,
        outboundAttractionDistribution: true,
        strongGravityMode: false,
        adjustSizes: true,
        edgeWeightInfluence: 1,
        barnesHutOptimize: nodeCount > 200,
        barnesHutTheta: nodeCount >= 2000 ? 0.8 : 0.6,
        gravity,
        scalingRatio,
        slowDown,
      },
    });
    fa2Ref.current = fa2;
    fa2.start();
    setTimeout(() => { if (fa2Ref.current) fa2Ref.current.stop(); }, layoutTimeout);
  }, [nodes, edges, onSelect]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => buildGraph());
    return () => {
      cancelAnimationFrame(frame);
      if (fa2Ref.current) { fa2Ref.current.kill(); fa2Ref.current = null; }
      if (sigmaRef.current) { sigmaRef.current.kill(); sigmaRef.current = null; graphRef.current = null; }
    };
  }, [buildGraph]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver(() => sigmaRef.current?.refresh());
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    selectedIdRef.current = selectedId;
    sigmaRef.current?.refresh();
  }, [selectedId]);

  useEffect(() => {
    highlightedIdsRef.current = highlightedIds;
    sigmaRef.current?.refresh();
  }, [highlightedIds]);

  useEffect(() => {
    visibleEdgeTypesRef.current = visibleEdgeTypes;
    sigmaRef.current?.refresh();
  }, [visibleEdgeTypes]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0"
      style={{ background: "linear-gradient(135deg, #06060a 0%, #0a0a10 50%, #0d0b1a 100%)" }}
    />
  );
}
