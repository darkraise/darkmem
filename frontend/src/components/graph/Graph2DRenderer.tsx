import { useRef, useEffect, useCallback } from "react";
import { Network, DataSet } from "vis-network/standalone";
import { computeSize } from "@/lib/graph-utils";
import type { SizeMode } from "@/lib/graph-utils";
import {
  clusterColor,
  tagColor,
  typeColor,
  hexToRgba,
  lightenHex,
  darkenHex,
} from "@/lib/graph-colors";
import { drawHullForGroup } from "@/lib/graph-geometry";
import type { UnifiedMemory, UnifiedGraphData } from "@/hooks/useApi";

interface Graph2DRendererProps {
  data: UnifiedGraphData;
  filteredMemories: UnifiedMemory[];
  filteredClusters: Record<string, string[]>;
  filteredEdges: { source: string; target: string; score: number }[];
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  onReady: () => void;
  sizeMode: SizeMode;
  spacing: number;
  clusterTightness: number;
  showTagOverlay: boolean;
}

export function Graph2DRenderer({
  data,
  filteredMemories,
  filteredClusters,
  filteredEdges,
  selectedNodeId,
  onNodeSelect,
  onReady,
  sizeMode,
  spacing,
  clusterTightness,
  showTagOverlay,
}: Graph2DRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodesDataSetRef = useRef<DataSet<any> | null>(null);
  const tagColorMap = useRef<Map<string, string>>(new Map());

  // Keep latest showTagOverlay accessible in afterDrawing without rebuilding
  const showTagOverlayRef = useRef(showTagOverlay);
  useEffect(() => {
    showTagOverlayRef.current = showTagOverlay;
    if (networkRef.current) {
      networkRef.current.redraw();
    }
  }, [showTagOverlay]);

  // Keep latest filtered state accessible in focusOnNode/exitFocusMode closures
  const filteredMemoriesRef = useRef(filteredMemories);
  const filteredEdgesRef = useRef(filteredEdges);
  useEffect(() => {
    filteredMemoriesRef.current = filteredMemories;
  }, [filteredMemories]);
  useEffect(() => {
    filteredEdgesRef.current = filteredEdges;
  }, [filteredEdges]);

  // Exposed focus handles so selectedNodeId effect can trigger them
  const focusOnNodeRef = useRef<((id: string) => void) | null>(null);
  const exitFocusModeRef = useRef<(() => void) | null>(null);

  const buildGraph = useCallback(() => {
    if (!containerRef.current) return;

    if (networkRef.current) {
      networkRef.current.destroy();
      networkRef.current = null;
    }

    const connMap = new Map<string, number>();
    for (const e of filteredEdges) {
      connMap.set(e.source, (connMap.get(e.source) ?? 0) + 1);
      connMap.set(e.target, (connMap.get(e.target) ?? 0) + 1);
    }

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

    for (const m of filteredMemories) {
      const color = typeColor(m.memory_type);
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
          hover: { background: lightenHex(color), border: color },
          highlight: { background: color, border: darkenHex(color) },
        },
        font: { color: "#c9d1d9", size: 13, face: "Inter, sans-serif" },
        borderWidth: 2,
        shadow: { enabled: true, color: color + "30", size: 8, x: 0, y: 1 },
        mass: 0.5 + Math.min(2.5, Math.log1p(conns) * 0.8),
        _memory: m,
      });
    }

    for (let i = 0; i < filteredEdges.length; i++) {
      const e = filteredEdges[i];
      edges.push({
        id: `sim-${i}`,
        from: e.source,
        to: e.target,
        color: {
          color: "#30363d",
          hover: "#78a6e0b4",
          highlight: "#4CC9F0",
          inherit: false,
        },
        hoverWidth: 1.5,
        smooth: { type: "continuous", roundness: 0.2 },
        width: 1,
      });
    }

    const allNodeIds = new Set(nodes.map((n: { id: string }) => n.id));
    for (const [clusterId, memberIds] of Object.entries(filteredClusters)) {
      const members = (memberIds as string[]).filter((id) =>
        allNodeIds.has(id),
      );
      for (let i = 0; i < members.length; i++) {
        for (let j = i + 1; j < members.length; j++) {
          edges.push({
            id: `cluster-${clusterId}-${i}-${j}`,
            from: members[i],
            to: members[j],
            hidden: true,
            physics: true,
            width: 0,
            length: clusterTightness,
          });
        }
      }
    }

    const clusterIds = Object.keys(filteredClusters);
    const nClusters = clusterIds.length;
    const clusterRadius = 80 + nClusters * 15;
    const clusterCenters: Record<string, { x: number; y: number }> = {};
    clusterIds.forEach((cid, i) => {
      const angle = (2 * Math.PI * i) / nClusters;
      clusterCenters[cid] = {
        x: Math.cos(angle) * clusterRadius,
        y: Math.sin(angle) * clusterRadius,
      };
    });
    const spread = 60 + Math.sqrt(nodes.length) * 5;
    for (const node of nodes) {
      const m: UnifiedMemory = node._memory;
      if (m.cluster >= 0) {
        const cid = String(m.cluster);
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
            gravitationalConstant: -3000,
            springLength: spacing,
            springConstant: 0.02,
            damping: 0.3,
            avoidOverlap: 0.5,
          },
          stabilization: { enabled: false },
        },
        interaction: {
          hover: true,
          hoverConnectedEdges: true,
          tooltipDelay: 99999,
          zoomView: true,
          dragView: true,
        },
        edges: {
          smooth: { enabled: true, type: "continuous", roundness: 0.2 },
          hoverWidth: 1.5,
          color: { hover: "#78a6e0b4" },
        },
      },
    );

    setTimeout(() => {
      if (networkRef.current) {
        networkRef.current.setOptions({ physics: { enabled: false } });
        networkRef.current.fit({
          animation: { duration: 300, easingFunction: "easeInOutQuad" },
        });
        onReady();
      }
    }, 1500);

    network.on("dragStart", (params) => {
      if (params.nodes.length > 0) {
        network.setOptions({ physics: { enabled: true } });
      }
    });
    network.on("dragEnd", (params) => {
      if (params.nodes.length > 0) {
        setTimeout(
          () => network.setOptions({ physics: { enabled: false } }),
          300,
        );
      }
    });

    network.on("afterDrawing", (ctx: CanvasRenderingContext2D) => {
      for (const [clusterId, memberIds] of Object.entries(filteredClusters)) {
        const cid = parseInt(clusterId);
        const color = clusterColor(cid);
        drawHullForGroup(
          ctx,
          network,
          memberIds as string[],
          color,
          0.07,
          0.3,
          `Cluster ${clusterId}`,
        );
      }

      if (showTagOverlayRef.current) {
        const tagGroups = new Map<string, string[]>();
        for (const m of filteredMemoriesRef.current) {
          for (const tag of m.tags) {
            const arr = tagGroups.get(tag) ?? [];
            arr.push(m.id);
            tagGroups.set(tag, arr);
          }
        }
        let tagIdx = 0;
        for (const [tag, memberIds] of tagGroups.entries()) {
          if (memberIds.length < 2) {
            tagIdx++;
            continue;
          }
          const color = tagColorMap.current.get(tag) ?? tagColor(tagIdx);
          drawHullForGroup(
            ctx,
            network,
            memberIds,
            color,
            0.05,
            0.25,
            `#${tag}`,
          );
          tagIdx++;
        }
      }
    });

    function focusOnNode(nodeId: string) {
      const directNeighbors = new Set<string>();
      const directEdgeIndices = new Set<number>();
      filteredEdgesRef.current.forEach((e, i) => {
        if (e.source === nodeId) {
          directNeighbors.add(e.target);
          directEdgeIndices.add(i);
        }
        if (e.target === nodeId) {
          directNeighbors.add(e.source);
          directEdgeIndices.add(i);
        }
      });

      const nodeUpdates = filteredMemoriesRef.current.map((m) => {
        const color = typeColor(m.memory_type);
        if (m.id === nodeId) {
          return {
            id: m.id,
            opacity: 1,
            borderWidth: 5,
            color: {
              background: color,
              border: darkenHex(color),
              highlight: { background: color, border: darkenHex(color) },
            },
          };
        } else if (directNeighbors.has(m.id)) {
          return {
            id: m.id,
            opacity: 1,
            borderWidth: 2,
            color: {
              background: color,
              border: darkenHex(color),
              highlight: { background: color, border: darkenHex(color) },
            },
          };
        } else {
          return {
            id: m.id,
            opacity: 0.15,
            borderWidth: 1,
            color: {
              background: hexToRgba(color, 0.15),
              border: hexToRgba(color, 0.1),
              highlight: { background: color, border: darkenHex(color) },
            },
            font: { color: hexToRgba("#c9d1d9", 0.15), size: 13 },
          };
        }
      });
      nodesDataSet.update(nodeUpdates);

      const edgeUpdates = filteredEdgesRef.current.map((_, i) => {
        if (directEdgeIndices.has(i)) {
          return {
            id: `sim-${i}`,
            color: {
              color: "#4CC9F0",
              hover: "#4CC9F0",
              highlight: "#4CC9F0",
              inherit: false,
            },
            width: 2.5,
          };
        }
        return {
          id: `sim-${i}`,
          color: {
            color: hexToRgba("#21262d", 0.05),
            hover: hexToRgba("#21262d", 0.05),
            highlight: hexToRgba("#21262d", 0.05),
            inherit: false,
          },
          width: 0.2,
        };
      });
      edgesDataSet.update(edgeUpdates);
    }

    function exitFocusMode() {
      const nodeUpdates = filteredMemoriesRef.current.map((m) => {
        const color = typeColor(m.memory_type);
        return {
          id: m.id,
          opacity: 1,
          borderWidth: 2,
          color: {
            background: color,
            border: darkenHex(color),
            highlight: { background: color, border: darkenHex(color) },
          },
          font: { color: "#c9d1d9", size: 13 },
        };
      });
      nodesDataSet.update(nodeUpdates);

      const edgeResets = filteredEdgesRef.current.map((_, i) => ({
        id: `sim-${i}`,
        color: {
          color: "#30363d",
          hover: "#78a6e0b4",
          highlight: "#4CC9F0",
          inherit: false,
        },
        width: 1,
      }));
      edgesDataSet.update(edgeResets);
    }

    focusOnNodeRef.current = focusOnNode;
    exitFocusModeRef.current = exitFocusMode;

    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0] as string;
        const node = nodes.find((n: { id: string }) => n.id === nodeId);
        if (node?._memory) {
          onNodeSelect(nodeId);
          focusOnNode(nodeId);
          network.focus(nodeId, {
            scale: network.getScale(),
            animation: { duration: 400, easingFunction: "easeInOutQuad" },
          });
        }
      } else if (params.nodes.length === 0 && params.edges.length === 0) {
        onNodeSelect(null);
        exitFocusMode();
      }
    });

    networkRef.current = network;
  // showTagOverlay intentionally excluded — tag overlay is drawn live via ref in afterDrawing
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    data,
    sizeMode,
    clusterTightness,
    spacing,
    filteredMemories,
    filteredEdges,
    filteredClusters,
    onNodeSelect,
    onReady,
  ]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      buildGraph();
    });
    return () => {
      cancelAnimationFrame(frame);
      if (networkRef.current) {
        networkRef.current.destroy();
        networkRef.current = null;
      }
    };
  }, [buildGraph]);

  // Respond to external selectedNodeId changes (e.g. MiniGraph navigation)
  useEffect(() => {
    if (selectedNodeId) {
      focusOnNodeRef.current?.(selectedNodeId);
      if (networkRef.current) {
        networkRef.current.focus(selectedNodeId, {
          animation: { duration: 600, easingFunction: "easeInOutQuad" },
          scale: networkRef.current.getScale(),
        });
      }
    } else {
      exitFocusModeRef.current?.();
      networkRef.current?.unselectAll();
      networkRef.current?.redraw();
    }
  }, [selectedNodeId]);

  return <div ref={containerRef} className="absolute inset-0" />;
}
