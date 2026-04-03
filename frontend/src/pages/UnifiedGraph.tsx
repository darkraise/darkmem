import { useUnifiedGraph } from "@/hooks/useApi";
import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Filter, PanelRightClose } from "lucide-react";
import { GraphSkeleton } from "@/components/graph/GraphSkeleton";
import { MiniGraph } from "@/components/graph/MiniGraph";
import { GraphFilterPanel } from "@/components/graph/GraphFilterPanel";
import { GraphDetailPanel } from "@/components/graph/GraphDetailPanel";
import { Graph2DRenderer } from "@/components/graph/Graph2DRenderer";
import { Graph3DRenderer } from "@/components/graph/Graph3DRenderer";
import { GraphToolbar } from "@/components/graph/GraphToolbar";
import {
  transformToGraphData,
  type SizeMode,
  type FilterState,
} from "@/lib/graph-utils";
import type { ColorMode } from "@/lib/graph-colors";
import type { HullMode } from "@/lib/graph-geometry";

type ViewMode = "2d" | "3d";

function useDebouncedValue<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    if (Object.is(debounced, value)) return;
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay, debounced]);
  return debounced;
}

export default function UnifiedGraph() {
  // View
  const [viewMode, setViewMode] = useState<ViewMode>("2d");
  const [graphReady, setGraphReady] = useState(false);
  const [colorMode, setColorMode] = useState<ColorMode>("type");
  const [showSettings, setShowSettings] = useState(false);

  // API params (shared, debounced)
  const [similarityThreshold, setSimilarityThreshold] = useState(0.5);

  const [minClusterSize, setMinClusterSize] = useState(3);
  const debouncedSimilarity = useDebouncedValue(similarityThreshold, 500);

  const debouncedMinSize = useDebouncedValue(minClusterSize, 500);

  // Entity layer
  const [entityLayerEnabled, setEntityLayerEnabled] = useState(false);
  const [selectedEntityTypes, setSelectedEntityTypes] = useState<Set<string>>(new Set());
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);

  const { data, isLoading } = useUnifiedGraph(
    debouncedSimilarity,
    debouncedMinSize,
    entityLayerEnabled,
  );

  // Layout (shared)
  const [sizeMode, setSizeMode] = useState<SizeMode>("connections");

  // Layout (view-specific)
  const [nodeSpacing, setNodeSpacing] = useState(100);
  const [clusterTightness, setClusterTightness] = useState(300);
  const [hullMode, setHullMode] = useState<HullMode>("none");
  const [spacing3D, setSpacing3D] = useState(50);
  const debouncedTightness = useDebouncedValue(clusterTightness, 500);
  const debouncedSpacing2D = useDebouncedValue(nodeSpacing, 500);

  // Selection & UI
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [showPanel, setShowPanel] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  // Filters
  const [searchText, setSearchText] = useState("");
  const debouncedSearchText = useDebouncedValue(searchText, 1000);
  const [selectedTags, setSelectedTags] = useState<Set<string>>(new Set());
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [selectedSources, setSelectedSources] = useState<Set<string>>(new Set());
  const [selectedClusters, setSelectedClusters] = useState<Set<number>>(new Set());

  // Container dimensions (for 3D renderer)
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number } | null>(null);
  const hasGraphData = (data?.memories.length ?? 0) > 0;

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) {
        setDimensions((prev) =>
          prev && prev.width === width && prev.height === height
            ? prev
            : { width, height },
        );
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasGraphData]);

  const handleGraphReady = useCallback(() => setGraphReady(true), []);

  // Reset ready state on view switch so loading overlay re-appears
  useEffect(() => {
    setGraphReady(false);
  }, [viewMode]);

  function clearFilters() {
    setSearchText("");
    setSelectedTags(new Set());
    setSelectedTypes(new Set());
    setSelectedSources(new Set());
    setSelectedClusters(new Set());
  }

  function handleReset() {
    setSimilarityThreshold(0.5);
    setMinClusterSize(3);
    setClusterTightness(300);
    setNodeSpacing(100);
    setSpacing3D(50);
    setSizeMode("connections");
    setColorMode("type");
    setHullMode("none");
    setShowSettings(false);
    setEntityLayerEnabled(false);
    setSelectedEntityTypes(new Set());
    setSelectedEntityId(null);
    clearFilters();
  }

  const handleNodeSelect = useCallback((id: string | null) => {
    setSelectedNodeId(id);
    setSelectedEntityId(null);
    if (id) setShowPanel(true);
  }, []);

  const handleNavigate = useCallback((id: string) => {
    setSelectedNodeId(id);
    setSelectedEntityId(null);
    setShowPanel(true);
  }, []);

  const handleEntitySelect = useCallback((entityId: string | null) => {
    setSelectedEntityId(entityId);
    setSelectedNodeId(null);
    if (entityId) setShowPanel(true);
  }, []);

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
      if (selectedTypes.size > 0 && (!m.memory_type || !selectedTypes.has(m.memory_type)))
        return false;
      if (selectedSources.size > 0 && !selectedSources.has(m.source))
        return false;
      if (selectedClusters.size > 0 && !selectedClusters.has(m.cluster))
        return false;
      if (
        debouncedSearchText.trim() &&
        !m.content.toLowerCase().includes(debouncedSearchText.trim().toLowerCase())
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

  // Filtered similarity edges (both endpoints must be in filtered set)
  const filteredEdges = useMemo(() => {
    if (!data) return [];
    const filteredIds = new Set(filteredMemories.map((m) => m.id));
    return data.similarity_edges.filter(
      (e) => filteredIds.has(e.source) && filteredIds.has(e.target),
    );
  }, [data, filteredMemories]);

  // Filtered entities (only those linked to visible memories)
  const filteredEntities = useMemo(() => {
    if (!data?.entities || !entityLayerEnabled) return [];
    const memoryIdSet = new Set(filteredMemories.map((m) => m.id));
    return data.entities.filter((e) => {
      if (selectedEntityTypes.size > 0 && !selectedEntityTypes.has(e.entity_type)) return false;
      return e.memory_ids.some((mid) => memoryIdSet.has(mid));
    });
  }, [data, entityLayerEnabled, filteredMemories, selectedEntityTypes]);

  const filteredEntityRelations = useMemo(() => {
    if (!data?.entity_relations || !entityLayerEnabled) return [];
    const entityIdSet = new Set(filteredEntities.map((e) => e.id));
    return data.entity_relations.filter(
      (r) => entityIdSet.has(r.source) && entityIdSet.has(r.target),
    );
  }, [data, entityLayerEnabled, filteredEntities]);

  // All entity types for filter panel counts
  const allEntityTypes = useMemo((): [string, number][] => {
    if (!data?.entities) return [];
    const counts = new Map<string, number>();
    for (const e of data.entities) {
      counts.set(e.entity_type, (counts.get(e.entity_type) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1]);
  }, [data]);

  // 3D graph data (includes filter logic internally via transformToGraphData)
  const graphData3D = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    const filters: FilterState = {
      searchText: debouncedSearchText,
      selectedTags,
      selectedTypes,
      selectedSources,
      selectedClusters,
      selectedEntityTypes,
    };
    return transformToGraphData(
      data, sizeMode, filters, colorMode,
      entityLayerEnabled, filteredEntities, filteredEntityRelations,
    );
  }, [data, sizeMode, debouncedSearchText, selectedTags, selectedTypes, selectedSources, selectedClusters, selectedEntityTypes, colorMode, entityLayerEnabled, filteredEntities, filteredEntityRelations]);

  // Derived totals for filter panel counts (always from full data, not filtered)
  const allTags = useMemo((): [string, number][] => {
    if (!data) return [];
    const counts = new Map<string, number>();
    for (const m of data.memories) {
      for (const t of m.tags) counts.set(t, (counts.get(t) ?? 0) + 1);
    }
    return Array.from(counts.entries()).sort((a, b) => a[0].localeCompare(b[0]));
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

  const tagGroups = useMemo(() => {
    const groups = new Map<string, [string, number][]>();
    for (const [tag, count] of allTags) {
      const slash = tag.indexOf("/");
      const category = slash >= 0 ? tag.slice(0, slash) : "other";
      const arr = groups.get(category) ?? [];
      arr.push([tag, count]);
      groups.set(category, arr);
    }
    return Array.from(groups.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [allTags]);

  const selectedMemory = data?.memories.find((m) => m.id === selectedNodeId) ?? null;
  const selectedEntity = data?.entities?.find((e) => e.id === selectedEntityId) ?? null;
  const memoryCount = data?.memories.length ?? 0;

  return (
    <div className="flex h-full" style={{ minHeight: 0 }}>
      {/* Main graph area */}
      <div className="flex-1 flex flex-col min-w-0">
        {isLoading && <GraphSkeleton />}
        {!isLoading && memoryCount === 0 && (
          <p className="text-muted-foreground p-3">
            No data yet. Create memories with the pipeline running to populate the graph.
          </p>
        )}

        {memoryCount > 0 && (
          <div ref={containerRef} className="relative flex-1 min-h-0">
            <div className="bg-[#0d1117] absolute inset-0">
              {dimensions && viewMode === "2d" && data && (
                <Graph2DRenderer
                  data={data}
                  filteredMemories={filteredMemories}
                  filteredEdges={filteredEdges}
                  selectedNodeId={selectedNodeId}
                  onNodeSelect={handleNodeSelect}
                  onReady={handleGraphReady}
                  sizeMode={sizeMode}
                  colorMode={colorMode}
                  spacing={debouncedSpacing2D}
                  clusterTightness={debouncedTightness}
                  hullMode={hullMode}
                  entityLayerEnabled={entityLayerEnabled}
                  entities={filteredEntities}
                  entityRelations={filteredEntityRelations}
                  onEntitySelect={handleEntitySelect}
                />
              )}
              {dimensions && viewMode === "3d" && (
                <Graph3DRenderer
                  graphData={graphData3D}
                  width={dimensions.width}
                  height={dimensions.height}
                  selectedNodeId={selectedNodeId}
                  onNodeSelect={handleNodeSelect}
                  onReady={handleGraphReady}
                  spacing={spacing3D}
                  colorMode={colorMode}
                  hullMode={hullMode}
                />
              )}
            </div>

            {/* Loading overlay — only during API fetch */}
            {isLoading && (
              <div className="absolute inset-0 z-30 bg-[#0d1117]">
                <GraphSkeleton label="Loading graph data..." />
              </div>
            )}

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
            <GraphToolbar
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              colorMode={colorMode}
              onColorModeChange={setColorMode}
              hullMode={hullMode}
              onHullModeChange={setHullMode}
              entityLayer={entityLayerEnabled}
              onEntityLayerChange={setEntityLayerEnabled}
              showSettings={showSettings}
              onToggleSettings={() => setShowSettings((v) => !v)}
              sizeMode={sizeMode}
              onSizeModeChange={setSizeMode}
              similarityThreshold={similarityThreshold}
              onSimilarityChange={setSimilarityThreshold}
              minClusterSize={minClusterSize}
              onMinClusterSizeChange={setMinClusterSize}
              spacing={viewMode === "2d" ? nodeSpacing : spacing3D}
              onSpacingChange={viewMode === "2d" ? setNodeSpacing : setSpacing3D}
              clusterTightness={clusterTightness}
              onClusterTightnessChange={setClusterTightness}
              onReset={handleReset}
            />

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
                colorMode={colorMode}
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
                entityLayerEnabled={entityLayerEnabled}
                allEntityTypes={allEntityTypes}
                selectedEntityTypes={selectedEntityTypes}
                onEntityTypeToggle={(etype) =>
                  setSelectedEntityTypes((prev) => {
                    const next = new Set(prev);
                    next.has(etype) ? next.delete(etype) : next.add(etype);
                    return next;
                  })
                }
              />
            </div>
          </div>
        )}
      </div>

      {/* Right panel */}
      {showPanel && memoryCount > 0 && (
        <div className="w-[320px] shrink-0 border-l border-border bg-card overflow-auto">
          <GraphDetailPanel
            colorMode={colorMode}
            selectedMemory={selectedMemory}
            clusterName={data?.cluster_names?.[String(selectedMemory?.cluster)] ?? ""}
            memories={filteredMemories}
            clusterNames={data?.cluster_names ?? {}}
            visibleEdgeCount={filteredEdges.length}
            onClose={() => {
              setShowPanel(false);
              setSelectedNodeId(null);
              setSelectedEntityId(null);
            }}
            selectedEntity={selectedEntity}
            entityRelations={filteredEntityRelations}
            allEntities={data?.entities}
            onNavigateToMemory={handleNavigate}
          >
            {selectedMemory && viewMode === "2d" && (
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
