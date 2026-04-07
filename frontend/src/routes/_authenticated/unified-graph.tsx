import { createFileRoute } from "@tanstack/react-router";
import { useUnifiedGraph } from "@/hooks/api";
import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { Button } from "darkraise-ui/components/button";
import { Filter, PanelRightClose } from "lucide-react";
import { GraphSkeleton } from "@/features/graph/components/graph-skeleton";
import { MiniGraph } from "@/features/graph/components/mini-graph";
import { GraphFilterPanel } from "@/features/graph/components/graph-filter-panel";
import { GraphDetailPanel } from "@/features/graph/components/graph-detail-panel";
import { Graph2DRenderer } from "@/features/graph/components/graph-2d-renderer";
import { Graph3DRenderer } from "@/features/graph/components/graph-3d-renderer";
import { GraphToolbar } from "@/features/graph/components/graph-toolbar";
import { ChatOverlay } from "@/features/chat/components/chat-overlay";
import {
  transformToGraphData,
  type FilterState,
} from "@/features/graph/lib/graph-utils";
import type { ColorMode } from "@/features/graph/lib/graph-colors";
import { useDebouncedValue } from "@/features/graph/hooks/use-debounced-value";
import { useGraphFilters } from "@/features/graph/hooks/use-graph-filters";
import { useGraphLayout } from "@/features/graph/hooks/use-graph-layout";
import { useGraphSelection } from "@/features/graph/hooks/use-graph-selection";

export const Route = createFileRoute("/_authenticated/unified-graph")({
  component: UnifiedGraphPage,
});

type ViewMode = "2d" | "3d";

function UnifiedGraphPage() {
  const [viewMode, setViewMode] = useState<ViewMode>("2d");
  const [graphReady, setGraphReady] = useState(false);
  const [colorMode, setColorMode] = useState<ColorMode>("type");
  const [showSettings, setShowSettings] = useState(false);

  const [similarityThreshold, setSimilarityThreshold] = useState(0.5);
  const [minClusterSize, setMinClusterSize] = useState(3);
  const debouncedSimilarity = useDebouncedValue(similarityThreshold, 500);
  const debouncedMinSize = useDebouncedValue(minClusterSize, 500);

  const [entityLayerEnabled, setEntityLayerEnabled] = useState(false);
  const [selectedEntityTypes, setSelectedEntityTypes] = useState<Set<string>>(new Set());

  const { data, isLoading } = useUnifiedGraph(
    debouncedSimilarity,
    debouncedMinSize,
    entityLayerEnabled,
  );

  const layout = useGraphLayout();
  const filters = useGraphFilters(data, entityLayerEnabled, selectedEntityTypes);
  const selection = useGraphSelection();

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

  useEffect(() => {
    setGraphReady(false);
  }, [viewMode]);

  function handleReset() {
    setSimilarityThreshold(0.5);
    setMinClusterSize(3);
    layout.setClusterTightness(300);
    layout.setNodeSpacing(100);
    layout.setSpacing3D(50);
    layout.setSizeMode("connections");
    setColorMode("type");
    layout.setHullMode("none");
    setShowSettings(false);
    setEntityLayerEnabled(false);
    setSelectedEntityTypes(new Set());
    selection.setSelectedEntityId(null);
    filters.clearFilters();
  }

  const graphData3D = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    const graphFilters: FilterState = {
      searchText: filters.debouncedSearchText,
      selectedTags: filters.selectedTags,
      selectedTypes: filters.selectedTypes,
      selectedSources: filters.selectedSources,
      selectedClusters: filters.selectedClusters,
      selectedEntityTypes,
    };
    return transformToGraphData(
      data, layout.sizeMode, graphFilters, colorMode,
      entityLayerEnabled, filters.filteredEntities, filters.filteredEntityRelations,
    );
  }, [
    data,
    layout.sizeMode,
    filters.debouncedSearchText,
    filters.selectedTags,
    filters.selectedTypes,
    filters.selectedSources,
    filters.selectedClusters,
    selectedEntityTypes,
    colorMode,
    entityLayerEnabled,
    filters.filteredEntities,
    filters.filteredEntityRelations,
  ]);

  const selectedMemory = data?.memories.find((m) => m.id === selection.selectedNodeId) ?? null;
  const selectedEntity = data?.entities?.find((e) => e.id === selection.selectedEntityId) ?? null;
  const memoryCount = data?.memories.length ?? 0;

  return (
    <div className="flex h-full" style={{ minHeight: 0 }}>
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
                  filteredMemories={filters.filteredMemories}
                  filteredEdges={filters.filteredEdges}
                  selectedNodeId={selection.selectedNodeId}
                  onNodeSelect={selection.handleNodeSelect}
                  onReady={handleGraphReady}
                  sizeMode={layout.sizeMode}
                  colorMode={colorMode}
                  spacing={layout.debouncedSpacing2D}
                  clusterTightness={layout.debouncedTightness}
                  hullMode={layout.hullMode}
                  entityLayerEnabled={entityLayerEnabled}
                  entities={filters.filteredEntities}
                  entityRelations={filters.filteredEntityRelations}
                  onEntitySelect={selection.handleEntitySelect}
                />
              )}
              {dimensions && viewMode === "3d" && (
                <Graph3DRenderer
                  graphData={graphData3D}
                  width={dimensions.width}
                  height={dimensions.height}
                  selectedNodeId={selection.selectedNodeId}
                  onNodeSelect={selection.handleNodeSelect}
                  onReady={handleGraphReady}
                  spacing={layout.spacing3D}
                  colorMode={colorMode}
                  hullMode={layout.hullMode}
                />
              )}
            </div>

            {isLoading && (
              <div className="absolute inset-0 z-30 bg-[#0d1117]">
                <GraphSkeleton label="Loading graph data..." />
              </div>
            )}

            <div className="absolute top-3 left-3 z-30">
              <Button
                variant="outline"
                size="sm"
                className={`shadow-lg ${filters.showFilters ? "bg-primary/20 border-primary text-primary hover:bg-primary/30 hover:text-primary" : "bg-card/80 backdrop-blur-sm"}`}
                onClick={() => filters.setShowFilters((v) => !v)}
              >
                <Filter className="w-4 h-4 mr-1.5" />
                Filters
              </Button>
            </div>

            <GraphToolbar
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              colorMode={colorMode}
              onColorModeChange={setColorMode}
              hullMode={layout.hullMode}
              onHullModeChange={layout.setHullMode}
              entityLayer={entityLayerEnabled}
              onEntityLayerChange={setEntityLayerEnabled}
              showSettings={showSettings}
              onToggleSettings={setShowSettings}
              sizeMode={layout.sizeMode}
              onSizeModeChange={layout.setSizeMode}
              similarityThreshold={similarityThreshold}
              onSimilarityChange={setSimilarityThreshold}
              minClusterSize={minClusterSize}
              onMinClusterSizeChange={setMinClusterSize}
              spacing={viewMode === "2d" ? layout.nodeSpacing : layout.spacing3D}
              onSpacingChange={viewMode === "2d" ? layout.setNodeSpacing : layout.setSpacing3D}
              clusterTightness={layout.clusterTightness}
              onClusterTightnessChange={layout.setClusterTightness}
              onReset={handleReset}
            />

            {!selection.showPanel && (
              <div className="absolute top-3 right-3 z-30">
                <Button
                  variant="outline"
                  size="sm"
                  className="shadow-lg bg-card/80 backdrop-blur-sm"
                  onClick={() => selection.setShowPanel(true)}
                >
                  <PanelRightClose className="w-4 h-4" />
                </Button>
              </div>
            )}

            <div
              className={`absolute top-14 left-3 z-[25] rounded-lg border border-border shadow-xl bg-card overflow-clip flex flex-col transition-all duration-200 ease-out origin-top ${filters.showFilters ? "opacity-100 scale-y-100" : "opacity-0 scale-y-0 pointer-events-none"}`}
              style={{ maxHeight: "calc(100% - 68px)" }}
            >
              <GraphFilterPanel
                colorMode={colorMode}
                tagGroups={filters.tagGroups}
                allTypes={filters.allTypes}
                allSources={filters.allSources}
                allClusters={filters.allClusters}
                clusterNames={data?.cluster_names ?? {}}
                selectedTags={filters.selectedTags}
                selectedTypes={filters.selectedTypes}
                selectedSources={filters.selectedSources}
                selectedClusters={filters.selectedClusters}
                searchText={filters.searchText}
                onSearchChange={filters.setSearchText}
                onTagToggle={(tag) =>
                  filters.setSelectedTags((prev) => {
                    const next = new Set(prev);
                    next.has(tag) ? next.delete(tag) : next.add(tag);
                    return next;
                  })
                }
                onTypeToggle={(type) =>
                  filters.setSelectedTypes((prev) => {
                    const next = new Set(prev);
                    next.has(type) ? next.delete(type) : next.add(type);
                    return next;
                  })
                }
                onSourceToggle={(src) =>
                  filters.setSelectedSources((prev) => {
                    const next = new Set(prev);
                    next.has(src) ? next.delete(src) : next.add(src);
                    return next;
                  })
                }
                onClusterToggle={(cid) =>
                  filters.setSelectedClusters((prev) => {
                    const next = new Set(prev);
                    next.has(cid) ? next.delete(cid) : next.add(cid);
                    return next;
                  })
                }
                onShowAll={filters.clearFilters}
                entityLayerEnabled={entityLayerEnabled}
                allEntityTypes={filters.allEntityTypes}
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

            <ChatOverlay
              selectedNodeId={selection.selectedNodeId}
              selectedEntityId={selection.selectedEntityId}
              onNodeSelect={(type, id) => {
                if (type === "entity") {
                  selection.setSelectedEntityId(id);
                  selection.setSelectedNodeId(`entity:${id}`);
                } else {
                  selection.setSelectedNodeId(id);
                  selection.setSelectedEntityId(null);
                }
              }}
            />
          </div>
        )}
      </div>

      {selection.showPanel && memoryCount > 0 && (
        <div className="w-[320px] shrink-0 border-l border-border bg-card flex flex-col overflow-hidden">
          <GraphDetailPanel
            colorMode={colorMode}
            selectedMemory={selectedMemory}
            clusterName={data?.cluster_names?.[String(selectedMemory?.cluster)] ?? ""}
            memories={filters.filteredMemories}
            clusterNames={data?.cluster_names ?? {}}
            visibleEdgeCount={filters.filteredEdges.length}
            onClose={() => {
              selection.setShowPanel(false);
              selection.setSelectedNodeId(null);
              selection.setSelectedEntityId(null);
            }}
            selectedEntity={selectedEntity}
            entityRelations={filters.filteredEntityRelations}
            allEntities={data?.entities}
            onNavigateToMemory={selection.handleNavigate}
          >
            {selectedMemory && viewMode === "2d" && (
              <MiniGraph
                memoryId={selectedMemory.id}
                onNavigate={selection.handleNavigate}
                onEntitySelect={entityLayerEnabled ? selection.handleEntitySelect : undefined}
              />
            )}
          </GraphDetailPanel>
        </div>
      )}
    </div>
  );
}
