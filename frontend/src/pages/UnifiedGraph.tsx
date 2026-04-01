import { useUnifiedGraph } from "@/hooks/useApi";
import type { UnifiedMemory } from "@/hooks/useApi";
import { useRef, useEffect, useState, useCallback, useMemo } from "react";
import {
  clusterColor, tagColor, typeColor, hexToRgba, lightenHex, darkenHex,
} from "@/lib/graph-colors";
import { drawHullForGroup } from "@/lib/graph-geometry";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Filter, PanelRightClose } from "lucide-react";
import { Network, DataSet } from "vis-network/standalone";
import { GraphSkeleton } from "@/components/graph/GraphSkeleton";
import { MiniGraph } from "@/components/graph/MiniGraph";
import { GraphFilterPanel } from "@/components/graph/GraphFilterPanel";
import { GraphDetailPanel } from "@/components/graph/GraphDetailPanel";

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    if (Object.is(debounced, value)) return;
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay, debounced]);
  return debounced;
}

// ─── Size computation ─────────────────────────────────────────────────────────

type SizeMode = "connections" | "importance" | "uniform";

function computeSize(
  mode: SizeMode,
  connections: number,
  importance: number,
): number {
  if (mode === "uniform") return 18;
  if (mode === "importance") return 12 + importance * 28;
  return 12 + Math.min(28, Math.log1p(connections) * 8);
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function UnifiedGraph() {
  const [similarityThreshold, setSimilarityThreshold] = useState(0.5);
  const [clusterMinScore, setClusterMinScore] = useState(0.2);
  const [minClusterSize, setMinClusterSize] = useState(3);
  const debouncedSimilarity = useDebouncedValue(similarityThreshold, 500);
  const debouncedClusterScore = useDebouncedValue(clusterMinScore, 500);
  const debouncedMinSize = useDebouncedValue(minClusterSize, 500);
  const { data, isLoading } = useUnifiedGraph(
    debouncedSimilarity,
    debouncedClusterScore,
    debouncedMinSize,
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const nodesDataSetRef = useRef<DataSet<any> | null>(null);
  const connectionsMapRef = useRef<Map<string, number>>(new Map());
  const exitFocusModeRef = useRef<(() => void) | null>(null);
  const focusOnNodeRef = useRef<((id: string) => void) | null>(null);

  const [selectedMemoryId, setSelectedMemoryId] = useState<string | null>(null);
  const [sizeMode, setSizeMode] = useState<SizeMode>("connections");
  const [showTagOverlay, setShowTagOverlay] = useState(false);
  const [clusterTightness, setClusterTightness] = useState(300);
  const [nodeSpacing, setNodeSpacing] = useState(100);
  const debouncedTightness = useDebouncedValue(clusterTightness, 500);
  const debouncedSpacing = useDebouncedValue(nodeSpacing, 500);

  const [showPanel, setShowPanel] = useState(false);

  // Filter state
  const [showFilters, setShowFilters] = useState(false);
  const [searchText, setSearchText] = useState("");
  const debouncedSearchText = useDebouncedValue(searchText, 1000);
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [selectedSources, setSelectedSources] = useState<Set<string>>(
    new Set(),
  );
  const [selectedClusters, setSelectedClusters] = useState<Set<number>>(
    new Set(),
  );

  function clearFilters() {
    setSearchText("");
    setSelectedTags(new Set());
    setSelectedTypes(new Set());
    setSelectedSources(new Set());
    setSelectedClusters(new Set());
  }

  // Filtered memories
  const filteredMemories = useMemo(() => {
    if (!data) return [];
    const hasFilter =
      debouncedSearchText.trim() !== "" ||
      selectedTags.size > 0 ||
      selectedTypes.size > 0 ||
      selectedSources.size > 0 ||
      selectedClusters.size > 0;
    if (!hasFilter) return data.memories;
    return data.memories.filter((m) => {
      if (selectedTags.size > 0 && !m.tags.some((t) => selectedTags.has(t)))
        return false;
      if (
        selectedTypes.size > 0 &&
        (!m.memory_type || !selectedTypes.has(m.memory_type))
      )
        return false;
      if (selectedSources.size > 0 && !selectedSources.has(m.source))
        return false;
      if (selectedClusters.size > 0 && !selectedClusters.has(m.cluster))
        return false;
      if (
        debouncedSearchText.trim() &&
        !m.content
          .toLowerCase()
          .includes(debouncedSearchText.trim().toLowerCase())
      )
        return false;
      return true;
    });
  }, [
    data,
    debouncedSearchText,
    selectedTags,
    selectedTypes,
    selectedSources,
    selectedClusters,
  ]);

  // Filtered clusters (only include clusters that still have members after filtering)
  const filteredClusters = useMemo(() => {
    if (!data) return {} as Record<string, string[]>;
    const filteredIds = new Set(filteredMemories.map((m) => m.id));
    const result: Record<string, string[]> = {};
    for (const [cid, members] of Object.entries(data.clusters)) {
      const kept = (members as string[]).filter((id) => filteredIds.has(id));
      if (kept.length > 0) result[cid] = kept;
    }
    return result;
  }, [data, filteredMemories]);

  // Filtered similarity edges (both endpoints must be in filtered set)
  const filteredEdges = useMemo(() => {
    if (!data) return [];
    const filteredIds = new Set(filteredMemories.map((m) => m.id));
    return data.similarity_edges.filter(
      (e) => filteredIds.has(e.source) && filteredIds.has(e.target),
    );
  }, [data, filteredMemories]);

  // Derive selected memory object
  const selectedMemory =
    data?.memories.find((m) => m.id === selectedMemoryId) ?? null;

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
    for (const e of filteredEdges) {
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

    // Similarity edges
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

    // Hidden cluster attraction edges
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
            length: debouncedTightness,
          });
        }
      }
    }

    // Seed positions — clusters close together so hulls can overlap naturally
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
            springLength: debouncedSpacing,
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

    // Let physics run visibly, then stop after 1.5s and fit view
    setTimeout(() => {
      if (networkRef.current) {
        networkRef.current.setOptions({ physics: { enabled: false } });
        networkRef.current.fit({
          animation: { duration: 300, easingFunction: "easeInOutQuad" },
        });
      }
    }, 1500);
    // Only re-enable physics when dragging a NODE, not when panning the canvas
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

    // afterDrawing: fuzzy cluster hulls + optional tag overlay
    network.on("afterDrawing", (ctx: CanvasRenderingContext2D) => {
      // Cluster hulls (drawn first, lower z)
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

      // Tag overlay hulls (drawn on top if enabled)
      if (showTagOverlay) {
        const tagGroups = new Map<string, string[]>();
        for (const m of filteredMemories) {
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

    // Focus/dim helpers
    function focusOnNode(nodeId: string) {
      // Only nodes directly connected via similarity edges
      const directNeighbors = new Set<string>();
      const directEdgeIndices = new Set<number>();
      filteredEdges.forEach((e, i) => {
        if (e.source === nodeId) {
          directNeighbors.add(e.target);
          directEdgeIndices.add(i);
        }
        if (e.target === nodeId) {
          directNeighbors.add(e.source);
          directEdgeIndices.add(i);
        }
      });

      // Update nodes: selected + direct neighbors bright, everything else dimmed
      const nodeUpdates = filteredMemories.map((m) => {
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

      // Update edges: only edges touching the selected node are highlighted
      const edgeUpdates = filteredEdges.map((_, i) => {
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
      const nodeUpdates = filteredMemories.map((m) => {
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

      // Restore edges to normal
      const edgeResets = filteredEdges.map((_, i) => ({
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

    exitFocusModeRef.current = exitFocusMode;
    focusOnNodeRef.current = focusOnNode;

    // Click handling
    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0] as string;
        const node = nodes.find((n: { id: string }) => n.id === nodeId);
        if (node?._memory) {
          setSelectedMemoryId(nodeId);
          setShowPanel(true);
          focusOnNode(nodeId);
          network.focus(nodeId, {
            scale: network.getScale(),
            animation: { duration: 400, easingFunction: "easeInOutQuad" },
          });
        }
      } else if (params.nodes.length === 0 && params.edges.length === 0) {
        setSelectedMemoryId(null);
        exitFocusMode();
      }
    });

    networkRef.current = network;
    // showTagOverlay intentionally excluded — tag overlay is drawn live in afterDrawing
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    data,
    sizeMode,
    debouncedTightness,
    debouncedSpacing,
    filteredMemories,
    filteredEdges,
    filteredClusters,
  ]);

  // Rebuild when data changes (rAF prevents StrictMode double-build)
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

  // Tag overlay toggle: just redraw without full rebuild
  useEffect(() => {
    if (networkRef.current) {
      networkRef.current.redraw();
    }
  }, [showTagOverlay]);

  // Navigate from mini-graph neighbor click
  const handleNavigate = useCallback((id: string) => {
    setSelectedMemoryId(id);
    setShowPanel(true);
    focusOnNodeRef.current?.(id);
    if (networkRef.current) {
      networkRef.current.focus(id, {
        animation: { duration: 600, easingFunction: "easeInOutQuad" },
        scale: networkRef.current.getScale(),
      });
    }
  }, []);

  const memoryCount = data?.memories.length ?? 0;

  // Derived totals for filter panel counts (always from full data, not filtered)
  const allTags = useMemo((): [string, number][] => {
    if (!data) return [];
    const counts = new Map<string, number>();
    for (const m of data.memories) {
      for (const t of m.tags) counts.set(t, (counts.get(t) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) =>
      a[0].localeCompare(b[0]),
    );
  }, [data]);

  const allTypes = useMemo(() => {
    if (!data) return [] as [string, number][];
    const counts = new Map<string, number>();
    for (const m of data.memories) {
      const t = m.memory_type ?? "(none)";
      counts.set(t, (counts.get(t) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [data]);

  const allSources = useMemo(() => {
    if (!data) return [] as [string, number][];
    const counts = new Map<string, number>();
    for (const m of data.memories)
      counts.set(m.source, (counts.get(m.source) ?? 0) + 1);
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [data]);

  const allClusters = useMemo(() => {
    if (!data) return [] as [number, number][];
    const counts = new Map<number, number>();
    for (const m of data.memories) {
      if (m.cluster >= 0)
        counts.set(m.cluster, (counts.get(m.cluster) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => a[0] - b[0]);
  }, [data]);

  // Tag groups: group by category prefix (part before first "/")
  const tagGroups = useMemo(() => {
    const groups = new Map<string, [string, number][]>();
    for (const [tag, count] of allTags) {
      const slash = tag.indexOf("/");
      const category = slash >= 0 ? tag.slice(0, slash) : "other";
      const arr = groups.get(category) ?? [];
      arr.push([tag, count]);
      groups.set(category, arr);
    }
    return Array.from(groups.entries()).sort((a, b) =>
      a[0].localeCompare(b[0]),
    );
  }, [allTags]);

  return (
    <div className="flex h-full" style={{ minHeight: 0 }}>
      {/* Main graph area */}
      <div className="flex-1 flex flex-col min-w-0">
        {isLoading && <GraphSkeleton />}
        {!isLoading && memoryCount === 0 && (
          <p className="text-muted-foreground p-3">
            No data yet. Create memories with the pipeline running to populate
            the graph.
          </p>
        )}

        {memoryCount > 0 && (
          <div className="relative flex-1 min-h-0">
            <div ref={containerRef} className="bg-[#0d1117] absolute inset-0" />

            {/* Floating toolbar */}
            {/* Filter button — top left */}
            <div className="absolute top-3 left-3 z-20">
              <Button
                variant="outline"
                size="sm"
                className={`shadow-lg ${showFilters ? "bg-primary/20 border-primary text-primary hover:bg-primary/30 hover:text-primary" : "bg-card/80 backdrop-blur-sm"}`}
                onClick={() => setShowFilters((v) => !v)}
              >
                <Filter className="w-4 h-4 mr-1.5" />
                Filters
              </Button>
            </div>

            {/* Centered toolbar */}
            <div className="absolute top-3 left-0 right-0 z-10 flex justify-center pointer-events-none">
              {/* Controls */}
              <div className="flex items-center gap-2 bg-card/80 backdrop-blur-sm rounded-md border border-border shadow-lg px-3 py-1.5 pointer-events-auto flex-wrap">
                <Select
                  value={sizeMode}
                  onValueChange={(v) => setSizeMode(v as SizeMode)}
                >
                  <SelectTrigger className="w-36 h-7 text-xs border-0 bg-transparent p-0 pr-2">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="connections">
                      Size: Connections
                    </SelectItem>
                    <SelectItem value="importance">Size: Importance</SelectItem>
                    <SelectItem value="uniform">Size: Uniform</SelectItem>
                  </SelectContent>
                </Select>

                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <label>Edges</label>
                  <input
                    type="range"
                    min="0.3"
                    max="0.95"
                    step="0.05"
                    value={similarityThreshold}
                    onChange={(e) =>
                      setSimilarityThreshold(parseFloat(e.target.value))
                    }
                    className="w-14"
                  />
                  <span className="font-mono w-5">{similarityThreshold}</span>
                </div>

                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <label>Cluster</label>
                  <input
                    type="range"
                    min="0.2"
                    max="0.8"
                    step="0.05"
                    value={clusterMinScore}
                    onChange={(e) =>
                      setClusterMinScore(parseFloat(e.target.value))
                    }
                    className="w-14"
                  />
                  <span className="font-mono w-5">{clusterMinScore}</span>
                </div>

                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <label>Min</label>
                  <input
                    type="range"
                    min="2"
                    max="10"
                    step="1"
                    value={minClusterSize}
                    onChange={(e) =>
                      setMinClusterSize(parseInt(e.target.value))
                    }
                    className="w-10"
                  />
                  <span className="font-mono w-3">{minClusterSize}</span>
                </div>

                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <label>Tight</label>
                  <input
                    type="range"
                    min="30"
                    max="300"
                    step="10"
                    value={clusterTightness}
                    onChange={(e) =>
                      setClusterTightness(parseInt(e.target.value))
                    }
                    className="w-14"
                  />
                  <span className="font-mono w-5">{clusterTightness}</span>
                </div>

                <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <label>Space</label>
                  <input
                    type="range"
                    min="100"
                    max="500"
                    step="25"
                    value={nodeSpacing}
                    onChange={(e) => setNodeSpacing(parseInt(e.target.value))}
                    className="w-14"
                  />
                  <span className="font-mono w-5">{nodeSpacing}</span>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  className={`h-7 text-xs ${showTagOverlay ? "text-cyan-400" : "text-muted-foreground"}`}
                  onClick={() => setShowTagOverlay((v) => !v)}
                >
                  Tags
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs text-muted-foreground"
                  onClick={() => {
                    setSimilarityThreshold(0.5);
                    setClusterMinScore(0.2);
                    setMinClusterSize(3);
                    setClusterTightness(300);
                    setNodeSpacing(100);
                    setSizeMode("connections");
                    setShowTagOverlay(false);
                    clearFilters();
                  }}
                >
                  Reset
                </Button>
              </div>
            </div>

            {/* Panel toggle — top right */}
            {!showPanel && (
              <div className="absolute top-3 right-3 z-10">
                <Button
                  variant="outline"
                  size="sm"
                  className="shadow-lg bg-card/80 backdrop-blur-sm"
                  onClick={() => setShowPanel(true)}
                >
                  <PanelRightClose className="w-4 h-4" />
                </Button>
              </div>
            )}

            {/* Floating filter panel */}
            <div
              className={`absolute top-14 left-3 z-20 rounded-lg border border-border shadow-xl bg-card overflow-clip flex flex-col transition-all duration-200 ease-out origin-top ${showFilters ? "opacity-100 scale-y-100" : "opacity-0 scale-y-0 pointer-events-none"}`}
              style={{ maxHeight: "calc(100% - 68px)" }}
            >
              <GraphFilterPanel
                tagGroups={tagGroups}
                allTypes={allTypes}
                allSources={allSources}
                allClusters={allClusters}
                clusterNames={data?.cluster_names ?? {}}
                selectedTags={selectedTags}
                selectedTypes={selectedTypes}
                selectedSources={selectedSources}
                selectedClusters={selectedClusters}
                searchText={searchText}
                onSearchChange={setSearchText}
                onTagToggle={(tag) =>
                  setSelectedTags((prev) => {
                    const next = new Set(prev);
                    next.has(tag) ? next.delete(tag) : next.add(tag);
                    return next;
                  })
                }
                onTypeToggle={(type) =>
                  setSelectedTypes((prev) => {
                    const next = new Set(prev);
                    next.has(type) ? next.delete(type) : next.add(type);
                    return next;
                  })
                }
                onSourceToggle={(src) =>
                  setSelectedSources((prev) => {
                    const next = new Set(prev);
                    next.has(src) ? next.delete(src) : next.add(src);
                    return next;
                  })
                }
                onClusterToggle={(cid) =>
                  setSelectedClusters((prev) => {
                    const next = new Set(prev);
                    next.has(cid) ? next.delete(cid) : next.add(cid);
                    return next;
                  })
                }
                onShowAll={clearFilters}
              />
            </div>
          </div>
        )}
      </div>

      {/* Right panel */}
      {showPanel && memoryCount > 0 && (
        <div className="w-[320px] shrink-0 border-l border-border bg-card overflow-auto">
          <GraphDetailPanel
            selectedMemory={selectedMemory}
            clusterName={data?.cluster_names?.[String(selectedMemory?.cluster)] ?? ""}
            memories={filteredMemories}
            clusterNames={data?.cluster_names ?? {}}
            visibleEdgeCount={filteredEdges.length}
            onClose={() => {
              setShowPanel(false);
              if (selectedMemory) {
                setSelectedMemoryId(null);
                exitFocusModeRef.current?.();
                networkRef.current?.unselectAll();
                networkRef.current?.redraw();
              }
            }}
          >
            {selectedMemory && (
              <MiniGraph
                memoryId={selectedMemory.id}
                onNavigate={handleNavigate}
              />
            )}
          </GraphDetailPanel>
        </div>
      )}
    </div>
  );
}
