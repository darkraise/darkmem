import { useRef, useEffect, useCallback } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import { EdgeCurvedArrowProgram, indexParallelEdgesIndex, createDrawCurvedEdgeLabel, DEFAULT_EDGE_CURVE_PROGRAM_OPTIONS } from "@sigma/edge-curve";
import { drawDiscNodeHover, DEFAULT_EDGE_ARROW_HEAD_PROGRAM_OPTIONS } from "sigma/rendering";
import FA2Layout from "graphology-layout-forceatlas2/worker";
import { inferSettings } from "graphology-layout-forceatlas2";
import { entityTypeColor, lightenHex, darkenHex } from "@/lib/graph-colors";

export interface KGSelection {
  kind: "node" | "edge";
  id: string;
  label: string;
  type: string;
  weight?: number;
  source?: string;
  target?: string;
}

interface KnowledgeGraphRendererProps {
  entities: Array<{ id?: string; name: string; entity_type: string }>;
  relations: Array<{ source: string; target: string; type?: string; weight?: number }>;
  selectedId: string | null;
  onSelect: (selected: KGSelection | null) => void;
}

export function KnowledgeGraphRenderer({
  entities,
  relations,
  selectedId,
  onSelect,
}: KnowledgeGraphRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const fa2Ref = useRef<FA2Layout | null>(null);
  const selectedIdRef = useRef(selectedId);
  const hoveredNodeRef = useRef<string | null>(null);

  const buildGraph = useCallback(() => {
    if (!containerRef.current) return;

    if (fa2Ref.current) { fa2Ref.current.kill(); fa2Ref.current = null; }
    if (sigmaRef.current) { sigmaRef.current.kill(); sigmaRef.current = null; graphRef.current = null; }

    const graph = new Graph();
    graphRef.current = graph;

    for (const e of entities) {
      const nodeId = e.id || e.name;
      if (graph.hasNode(nodeId)) continue;
      const color = entityTypeColor(e.entity_type);
      graph.addNode(nodeId, {
        x: (Math.random() - 0.5) * 10,
        y: (Math.random() - 0.5) * 10,
        label: e.name,
        size: 14,
        color,
        borderColor: darkenHex(color),
        _entityType: e.entity_type,
      });
    }

    for (const r of relations) {
      if (!graph.hasNode(r.source) || !graph.hasNode(r.target)) continue;
      try {
        graph.addEdge(r.source, r.target, {
          color: "#58606980",
          size: 1.5,
          label: r.type || "",
          _weight: r.weight ?? 0.5,
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
      defaultNodeColor: "#8b949e",
      nodeReducer(node, data) {
        const res = { ...data };
        const hov = hoveredNodeRef.current;
        const sel = selectedIdRef.current;
        if (hov === node) {
          res.color = lightenHex(data.color || "#8b949e", 0.4);
          res.size = (data.size || 14) * 1.4;
          res.highlighted = true;
        } else if (sel === node) {
          res.color = lightenHex(data.color || "#8b949e", 0.4);
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
            const neighborColor = graph.getNodeAttribute(src === sel ? tgt : src, "color") || "#8b949e";
            res.color = lightenHex(neighborColor, 0.3);
          } else {
            res.color = "#444444";
            res.size = (data.size || 1.5) * 0.5;
          }
        }

        if (hov && (src === hov || tgt === hov)) {
          res.size = (data.size || 1.5) * 2;
          const neighborColor = graph.getNodeAttribute(src === hov ? tgt : src, "color") || "#8b949e";
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
        kind: "node",
        id: node,
        label: attrs.label as string,
        type: attrs._entityType as string,
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
  }, [entities, relations, onSelect]);

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

  return <div ref={containerRef} className="absolute inset-0" />;
}
