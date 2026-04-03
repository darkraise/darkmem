import { useRef, useEffect, useCallback } from "react";
import Graph from "graphology";
import Sigma from "sigma";
import EdgeCurveProgram from "@sigma/edge-curve";
import { NodeDiamondProgram } from "@/lib/node-diamond-program";
import FA2Layout from "graphology-layout-forceatlas2/worker";
import { inferSettings } from "graphology-layout-forceatlas2";
import { computeSize } from "@/lib/graph-utils";
import { computeHullGroups, drawHullForSigma } from "@/lib/graph-geometry";
import type { HullMode } from "@/lib/graph-geometry";
import type { SizeMode } from "@/lib/graph-utils";
import {
  resolveNodeColor,
  resolveGroupColor,
  entityTypeColor,
  lightenHex,
  darkenHex,
} from "@/lib/graph-colors";
import type { ColorMode } from "@/lib/graph-colors";
import type {
  UnifiedMemory,
  UnifiedGraphData,
  GraphEntity,
  EntityRelation,
} from "@/hooks/useApi";

interface Graph2DRendererProps {
  data: UnifiedGraphData;
  filteredMemories: UnifiedMemory[];
  filteredEdges: { source: string; target: string; score: number }[];
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  onReady: () => void;
  sizeMode: SizeMode;
  colorMode: ColorMode;
  spacing: number;
  clusterTightness: number;
  hullMode: HullMode;
  entityLayerEnabled: boolean;
  entities: GraphEntity[];
  entityRelations: EntityRelation[];
  onEntitySelect?: (entityId: string | null) => void;
}

export function Graph2DRenderer({
  filteredMemories,
  filteredEdges,
  selectedNodeId,
  onNodeSelect,
  onReady,
  sizeMode,
  colorMode,
  hullMode,
  entityLayerEnabled,
  entities,
  entityRelations,
  onEntitySelect,
}: Graph2DRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sigmaRef = useRef<Sigma | null>(null);
  const graphRef = useRef<Graph | null>(null);
  const fa2Ref = useRef<FA2Layout | null>(null);
  const selectedNodeIdRef = useRef(selectedNodeId);
  const hoveredNodeRef = useRef<string | null>(null);
  const colorModeRef = useRef(colorMode);
  const hullModeRef = useRef(hullMode);
  const filteredMemoriesRef = useRef(filteredMemories);

  const buildGraph = useCallback(() => {
    if (!containerRef.current) return;

    if (fa2Ref.current) {
      fa2Ref.current.kill();
      fa2Ref.current = null;
    }
    if (sigmaRef.current) {
      sigmaRef.current.kill();
      sigmaRef.current = null;
      graphRef.current = null;
    }

    const graph = new Graph();
    graphRef.current = graph;

    const connMap = new Map<string, number>();
    for (const e of filteredEdges) {
      connMap.set(e.source, (connMap.get(e.source) ?? 0) + 1);
      connMap.set(e.target, (connMap.get(e.target) ?? 0) + 1);
    }

    const allNodeIds = new Set<string>();
    for (const m of filteredMemories) {
      const color = resolveNodeColor(m, colorModeRef.current);
      const conns = connMap.get(m.id) ?? 0;
      const size = computeSize(sizeMode, conns, m.importance);
      allNodeIds.add(m.id);
      graph.addNode(m.id, {
        x: (Math.random() - 0.5) * 10,
        y: (Math.random() - 0.5) * 10,
        label: m.content.slice(0, 30) + (m.content.length > 30 ? "…" : ""),
        size: size * 0.5,
        color,
        borderColor: darkenHex(color),
        _kind: "memory",
      });
    }

    for (const e of filteredEdges) {
      if (graph.hasNode(e.source) && graph.hasNode(e.target)) {
        try {
          const srcColor =
            graph.getNodeAttribute(e.source, "color") || "#8b949e";
          const edgeColor = darkenHex(srcColor, 0.6);
          graph.addEdge(e.source, e.target, {
            color: edgeColor,
            size: 2.5,
          });
        } catch {
          /* duplicate */
        }
      }
    }


    if (entityLayerEnabled) {
      const visibleEntities = entities.filter((ent) =>
        ent.memory_ids.some((mid) => allNodeIds.has(mid)),
      );
      const entityIdSet = new Set(visibleEntities.map((ent) => ent.id));

      for (const ent of visibleEntities) {
        const bg = entityTypeColor(ent.entity_type);
        graph.addNode(`entity:${ent.id}`, {
          x: (Math.random() - 0.5) * 10,
          y: (Math.random() - 0.5) * 10,
          label: ent.name,
          size: 10,
          color: bg,
          borderColor: darkenHex(bg),
          type: "diamond",
          _kind: "entity",
          _entityData: ent,
        });
      }

      for (const r of entityRelations) {
        if (entityIdSet.has(r.source) && entityIdSet.has(r.target)) {
          try {
            graph.addEdge(`entity:${r.source}`, `entity:${r.target}`, {
              color: "#ffa65770",
              size: 2.5,
              label: r.type,
            });
          } catch {
            /* duplicate */
          }
        }
      }

      for (const ent of visibleEntities) {
        for (const mid of ent.memory_ids) {
          if (allNodeIds.has(mid)) {
            try {
              graph.addEdge(`entity:${ent.id}`, mid, {
                color: "#58606920",
                size: 2.5,
              });
            } catch {
              /* duplicate */
            }
          }
        }
      }
    }

    const sigma = new Sigma(graph, containerRef.current, {
      antiAliasingFeather: 2,
      renderLabels: true,
      renderEdgeLabels: false,
      labelSize: 12,
      labelColor: { color: "#c9d1d9" },
      labelFont: "Inter, sans-serif",
      defaultEdgeType: "curve",
      nodeProgramClasses: { diamond: NodeDiamondProgram },
      edgeProgramClasses: { curve: EdgeCurveProgram },
      stagePadding: 40,
      labelRenderedSizeThreshold: 6,
      defaultNodeColor: "#8b949e",
      nodeReducer(node, data) {
        const res = { ...data };
        const hov = hoveredNodeRef.current;
        const sel = selectedNodeIdRef.current;
        if (hov === node) {
          res.color = lightenHex(data.color || "#8b949e", 0.4);
          res.size = (data.size || 5) * 1.4;
          if (data.type !== "diamond") res.highlighted = true;
        } else if (sel === node) {
          if (data.type === "diamond") {
            res.color = "#ffffff";
            res.size = (data.size || 5) * 1.6;
          } else {
            res.color = lightenHex(data.color || "#8b949e", 0.4);
            res.size = (data.size || 5) * 1.4;
            res.highlighted = true;
            res.borderColor = "#ffffff";
            res.borderSize = 3;
          }
        } else if (sel && sel !== node) {
          const isNeighbor =
            graph.hasEdge(sel, node) || graph.hasEdge(node, sel);
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
        const sel = selectedNodeIdRef.current;
        const src = graph.source(edge);
        const tgt = graph.target(edge);

        // Selection dimming applies first as the base state
        if (sel) {
          if (src === sel || tgt === sel) {
            res.size = (data.size || 2.5) * 2;
            const neighborColor =
              graph.getNodeAttribute(src === sel ? tgt : src, "color") ||
              "#8b949e";
            res.color = lightenHex(neighborColor, 0.3);
          } else {
            res.color = "#444444";
            res.size = (data.size || 2.5) * 0.5;
          }
        }

        // Hover highlight overrides for hovered node's edges only
        if (hov && (src === hov || tgt === hov)) {
          res.size = (data.size || 2.5) * 2;
          const neighborColor =
            graph.getNodeAttribute(src === hov ? tgt : src, "color") ||
            "#8b949e";
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
      if (attrs._kind === "entity") {
        onEntitySelect?.(attrs._entityData?.id ?? null);
      } else {
        onNodeSelect(node);
      }
    });
    sigma.on("clickStage", () => {
      onNodeSelect(null);
      onEntitySelect?.(null);
    });

    sigmaRef.current = sigma;

    // Hull canvas: placed on top of sigma with pointer-events: none
    const sigmaContainer = sigma.getContainer();
    const hullCanvas = document.createElement("canvas");
    hullCanvas.style.position = "absolute";
    hullCanvas.style.inset = "0";
    hullCanvas.style.pointerEvents = "none";
    hullCanvas.style.zIndex = "1";
    sigmaContainer.appendChild(hullCanvas);
    const hullCtx = hullCanvas.getContext("2d")!;

    function drawHulls() {
      if (!sigmaRef.current || !containerRef.current) return;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;
      const dpr = window.devicePixelRatio || 1;
      if (hullCanvas.width !== w * dpr || hullCanvas.height !== h * dpr) {
        hullCanvas.width = w * dpr;
        hullCanvas.height = h * dpr;
        hullCanvas.style.width = w + "px";
        hullCanvas.style.height = h + "px";
      }
      hullCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
      hullCtx.clearRect(0, 0, w, h);

      const hullGroups = computeHullGroups(filteredMemoriesRef.current, hullModeRef.current);
      let idx = 0;
      for (const [groupKey, members] of hullGroups) {
        const color = resolveGroupColor(groupKey, idx, colorModeRef.current, hullModeRef.current);
        drawHullForSigma(
          hullCtx,
          sigmaRef.current,
          members,
          color,
          0.07,
          0.2,
        );
        idx++;
      }
    }

    sigma.on("afterRender", drawHulls);
    sigma.on("kill", () => hullCanvas.remove());

    // Let the library infer optimal FA2 settings from the graph structure
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
    setTimeout(() => {
      if (fa2Ref.current) fa2Ref.current.stop();
    }, 8000);

    onReady();
  }, [
    filteredMemories,
    filteredEdges,
    sizeMode,
    colorMode,
    entityLayerEnabled,
    entities,
    entityRelations,
    onNodeSelect,
    onEntitySelect,
    onReady,
  ]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => buildGraph());
    return () => {
      cancelAnimationFrame(frame);
      if (fa2Ref.current) {
        fa2Ref.current.kill();
        fa2Ref.current = null;
      }
      if (sigmaRef.current) {
        sigmaRef.current.kill();
        sigmaRef.current = null;
        graphRef.current = null;
      }
    };
  }, [buildGraph]);

  useEffect(() => {
    selectedNodeIdRef.current = selectedNodeId;
    sigmaRef.current?.refresh();
  }, [selectedNodeId]);

  useEffect(() => {
    colorModeRef.current = colorMode;
    hullModeRef.current = hullMode;
    filteredMemoriesRef.current = filteredMemories;
    sigmaRef.current?.refresh();
  }, [colorMode, hullMode, filteredMemories]);

  return <div ref={containerRef} className="absolute inset-0" />;
}
