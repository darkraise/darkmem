import { useRef, useEffect, useCallback } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import { EdgeCurvedArrowProgram, indexParallelEdgesIndex, createDrawCurvedEdgeLabel, DEFAULT_EDGE_CURVE_PROGRAM_OPTIONS } from "@sigma/edge-curve";
import { drawDiscNodeHover, DEFAULT_EDGE_ARROW_HEAD_PROGRAM_OPTIONS } from "sigma/rendering";
import FA2Layout from "graphology-layout-forceatlas2/worker";
import { inferSettings } from "graphology-layout-forceatlas2";
import { lightenHex, darkenHex } from "@/lib/graph-colors";

const KIND_COLORS: Record<string, string> = {
  function: "#58a6ff",
  class: "#4ade80",
  interface: "#c084fc",
  struct: "#fb923c",
  method: "#38bdf8",
  trait: "#f472b6",
  enum: "#fbbf24",
  namespace: "#8b949e",
};

const LANGUAGE_COLORS: Record<string, string> = {
  python: "#3fb950",
  typescript: "#58a6ff",
  javascript: "#fbbf24",
  go: "#00ADD8",
  rust: "#fb923c",
};

const DEFAULT_COLOR = "#8b949e";

function nodeColor(kind?: string, language?: string): string {
  if (kind) return KIND_COLORS[kind] ?? DEFAULT_COLOR;
  if (language) return LANGUAGE_COLORS[language.toLowerCase()] ?? DEFAULT_COLOR;
  return DEFAULT_COLOR;
}

interface CodeGraphRendererProps {
  nodes: Array<{ id: string; label: string; kind?: string; language?: string; file_path?: string }>;
  edges: Array<{ source: string; target: string; type: string }>;
  selectedId: string | null;
  onSelect: (node: { id: string; label: string; kind?: string; file_path?: string } | null) => void;
  highlightedIds?: Set<string>;
}

export function CodeGraphRenderer({
  nodes,
  edges,
  selectedId,
  onSelect,
  highlightedIds,
}: CodeGraphRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const fa2Ref = useRef<FA2Layout | null>(null);
  const selectedIdRef = useRef(selectedId);
  const hoveredNodeRef = useRef<string | null>(null);
  const highlightedIdsRef = useRef(highlightedIds);

  const buildGraph = useCallback(() => {
    if (!containerRef.current) return;

    if (fa2Ref.current) { fa2Ref.current.kill(); fa2Ref.current = null; }
    if (sigmaRef.current) { sigmaRef.current.kill(); sigmaRef.current = null; graphRef.current = null; }

    const graph = new Graph();
    graphRef.current = graph;

    for (const n of nodes) {
      if (graph.hasNode(n.id)) continue;
      const color = nodeColor(n.kind, n.language);
      graph.addNode(n.id, {
        x: (Math.random() - 0.5) * 10,
        y: (Math.random() - 0.5) * 10,
        label: n.label,
        size: 14,
        color,
        borderColor: darkenHex(color),
        _kind: n.kind,
        _filePath: n.file_path,
      });
    }

    for (const e of edges) {
      if (!graph.hasNode(e.source) || !graph.hasNode(e.target)) continue;
      try {
        graph.addEdge(e.source, e.target, {
          color: "#58606980",
          size: 1.5,
          label: e.type || "",
        });
      } catch { /* duplicate edge */ }
    }

    indexParallelEdgesIndex(graph, {
      edgeIndexAttribute: "parallelIndex",
      edgeMaxIndexAttribute: "parallelMaxIndex",
    });

    const sigma = new Sigma(graph, containerRef.current, {
      antiAliasingFeather: 2,
      renderLabels: true,
      renderEdgeLabels: true,
      labelSize: 12,
      labelColor: { color: "#c9d1d9" },
      labelFont: "Inter, sans-serif",
      edgeLabelSize: 10,
      edgeLabelColor: { color: "#6e7681" },
      defaultEdgeType: "curvedArrow",
      edgeProgramClasses: { curvedArrow: EdgeCurvedArrowProgram },
      defaultDrawEdgeLabel: createDrawCurvedEdgeLabel({
        ...DEFAULT_EDGE_CURVE_PROGRAM_OPTIONS,
        arrowHead: DEFAULT_EDGE_ARROW_HEAD_PROGRAM_OPTIONS,
      }),
      defaultDrawNodeHover: drawDiscNodeHover,
      stagePadding: 40,
      labelRenderedSizeThreshold: 6,
      defaultNodeColor: DEFAULT_COLOR,
      nodeReducer(node, data) {
        const res = { ...data };
        const hl = highlightedIdsRef.current;

        if (hl && hl.size > 0) {
          if (hl.has(node)) {
            res.color = "#f87171";
            res.size = (data.size || 14) * 1.3;
          } else {
            res.color = "#333333";
            res.label = "";
          }
          return res;
        }

        const hov = hoveredNodeRef.current;
        const sel = selectedIdRef.current;
        if (hov === node) {
          res.color = lightenHex(data.color || DEFAULT_COLOR, 0.4);
          res.size = (data.size || 14) * 1.4;
          res.highlighted = true;
        } else if (sel === node) {
          res.color = lightenHex(data.color || DEFAULT_COLOR, 0.4);
          res.size = (data.size || 14) * 1.4;
          res.highlighted = true;
          res.borderColor = "#ffffff";
          res.borderSize = 3;
        } else if (sel && sel !== node) {
          const isNeighbor = graph.hasEdge(sel, node) || graph.hasEdge(node, sel);
          if (!isNeighbor) {
            res.color = "#444444";
            res.label = "";
          }
        }
        return res;
      },
      edgeReducer(edge, data) {
        const res = { ...data };
        const hov = hoveredNodeRef.current;
        const sel = selectedIdRef.current;
        const src = graph.source(edge);
        const tgt = graph.target(edge);

        if (sel) {
          if (src === sel || tgt === sel) {
            res.size = (data.size || 1.5) * 2;
            const neighborColor = graph.getNodeAttribute(src === sel ? tgt : src, "color") || DEFAULT_COLOR;
            res.color = lightenHex(neighborColor, 0.3);
          } else {
            res.color = "#444444";
            res.size = (data.size || 1.5) * 0.5;
          }
        }

        if (hov && (src === hov || tgt === hov)) {
          res.size = (data.size || 1.5) * 2;
          const neighborColor = graph.getNodeAttribute(src === hov ? tgt : src, "color") || DEFAULT_COLOR;
          res.color = lightenHex(neighborColor, 0.3);
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
        gravity: 1,
        slowDown: 12,
      },
    });
    fa2Ref.current = fa2;
    fa2.start();
    setTimeout(() => { if (fa2Ref.current) fa2Ref.current.stop(); }, 5000);
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

  return <div ref={containerRef} className="absolute inset-0" />;
}
