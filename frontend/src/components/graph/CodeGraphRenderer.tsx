import { useRef, useEffect, useCallback } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import EdgeCurveProgram, { indexParallelEdgesIndex } from "@sigma/edge-curve";
import FA2Layout from "graphology-layout-forceatlas2/worker";
import { inferSettings } from "graphology-layout-forceatlas2";
import { lightenHex } from "@/lib/graph-colors";

const NODE_SIZES: Record<string, number> = {
  file: 12,
  module: 10,
  namespace: 9,
  class: 8,
  struct: 8,
  interface: 7,
  trait: 7,
  enum: 6,
  function: 4,
  method: 3,
  type: 2,
  impl: 2,
};
const DEFAULT_NODE_SIZE = 3;

const NODE_COLORS: Record<string, string> = {
  module: "#8b5cf6",
  namespace: "#6366f1",
  class: "#f59e0b",
  struct: "#fb923c",
  interface: "#ec4899",
  trait: "#f472b6",
  enum: "#f97316",
  function: "#10b981",
  method: "#14b8a6",
  type: "#64748b",
  impl: "#7c3aed",
  file: "#3b82f6",
};
const DEFAULT_NODE_COLOR = "#6b7280";

const EDGE_COLORS: Record<string, string> = {
  calls: "#7c3aed",
  imports: "#1d4ed8",
  contains: "#2d5a3d",
  defines: "#0e7490",
  extends: "#c2410c",
  implements: "#be185d",
};
const DEFAULT_EDGE_COLOR = "#2a2a3a";

const EDGE_SIZES: Record<string, number> = {
  calls: 0.8,
  imports: 0.6,
  defines: 0.5,
  contains: 0.4,
};
const DEFAULT_EDGE_SIZE = 0.5;

const NODE_MASS: Record<string, number> = {
  file: 30,
  module: 15,
  namespace: 12,
  class: 6,
  struct: 6,
  interface: 5,
  trait: 5,
  enum: 4,
  function: 2,
  method: 1,
};

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

    // Pre-position nodes hierarchically: files in a wide ring, symbols near their parent file
    const fileNodes = nodes.filter((n) => n.kind === "file");
    const moduleNodes = nodes.filter((n) => n.kind === "module");
    const symbolNodes = nodes.filter((n) => n.kind !== "file" && n.kind !== "module");

    const filePositions: Record<string, { x: number; y: number }> = {};
    const goldenAngle = Math.PI * (3 - Math.sqrt(5));
    const fileRadius = Math.max(50, Math.sqrt(fileNodes.length) * 12);

    fileNodes.forEach((f, i) => {
      const angle = i * goldenAngle;
      const r = fileRadius * Math.sqrt((i + 1) / fileNodes.length);
      filePositions[f.id] = { x: Math.cos(angle) * r, y: Math.sin(angle) * r };
    });

    const moduleRadius = fileRadius * 1.3;
    moduleNodes.forEach((m, i) => {
      const angle = i * goldenAngle * 1.5;
      const r = moduleRadius + Math.random() * 20;
      filePositions[m.id] = { x: Math.cos(angle) * r, y: Math.sin(angle) * r };
    });

    for (const n of nodes) {
      if (graph.hasNode(n.id)) continue;
      const kind = n.kind?.toLowerCase() ?? "";
      const color = NODE_COLORS[kind] ?? DEFAULT_NODE_COLOR;
      const size = NODE_SIZES[kind] ?? DEFAULT_NODE_SIZE;

      let x: number, y: number;
      if (filePositions[n.id]) {
        x = filePositions[n.id].x;
        y = filePositions[n.id].y;
      } else if (n.file_path && filePositions[n.file_path]) {
        x = filePositions[n.file_path].x + (Math.random() - 0.5) * 8;
        y = filePositions[n.file_path].y + (Math.random() - 0.5) * 8;
      } else {
        x = (Math.random() - 0.5) * fileRadius;
        y = (Math.random() - 0.5) * fileRadius;
      }

      graph.addNode(n.id, {
        x,
        y,
        label: n.label,
        size,
        color,
        mass: NODE_MASS[kind] ?? 1,
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
          size: EDGE_SIZES[edgeType] || DEFAULT_EDGE_SIZE,
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

    const nodeCount = graph.order;
    const gravity = nodeCount < 500 ? 0.8 : nodeCount < 2000 ? 0.5 : 0.3;
    const scalingRatio = nodeCount < 500 ? 15 : nodeCount < 2000 ? 30 : 60;
    const slowDown = nodeCount < 500 ? 1 : nodeCount < 2000 ? 2 : 3;
    const layoutTimeout = nodeCount < 500 ? 5000 : 15000;

    const sigma = new Sigma(graph, containerRef.current, {
      allowInvalidContainer: true,
      renderLabels: true,
      renderEdgeLabels: false,
      labelSize: 11,
      labelWeight: "500",
      labelFont: "JetBrains Mono, monospace",
      labelColor: { color: "#e4e4ed" },
      labelRenderedSizeThreshold: 12,
      defaultEdgeType: "curve",
      edgeProgramClasses: { curve: EdgeCurveProgram },
      stagePadding: 60,
      defaultNodeColor: DEFAULT_NODE_COLOR,
      defaultEdgeColor: DEFAULT_EDGE_COLOR,
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
        linLogMode: true,
        outboundAttractionDistribution: false,
        strongGravityMode: true,
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
