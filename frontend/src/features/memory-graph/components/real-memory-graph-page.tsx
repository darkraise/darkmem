import { useUnifiedGraph } from "@/hooks/api"
import { EmptyState } from "@/components/darkmem"
import { useFullBleedContent } from "@/hooks/use-full-bleed-content"
import { useEffect, useRef, useState, useCallback, useMemo } from "react"
import { Button } from "darkraise-ui/components/button"
import { Filter, PanelRightClose, Waypoints } from "lucide-react"
import { useSetPageChrome } from "@/components/app-chrome"
import { GraphSkeleton } from "@/features/graph/components/graph-skeleton"
import { Spinner } from "darkraise-ui/components/spinner"
import { MiniGraph } from "@/features/graph/components/mini-graph"
import { GraphFilterPanel } from "@/features/graph/components/graph-filter-panel"
import { GraphDetailPanel } from "@/features/graph/components/graph-detail-panel"
import { Graph2DRenderer } from "@/features/graph/components/graph-2d-renderer"
import { Graph3DRenderer } from "@/features/graph/components/graph-3d-renderer"
import { GraphToolbar } from "@/features/graph/components/graph-toolbar"
import { ChatOverlay } from "@/features/chat/components/chat-overlay"
import {
  transformToGraphData,
  DEFAULT_SIZE_MODE,
  type FilterState,
} from "@/features/graph/lib/graph-utils"
import {
  DEFAULT_COLOR_MODE,
  type ColorMode,
} from "@/features/graph/lib/graph-colors"
import { DEFAULT_HULL_MODE } from "@/features/graph/lib/graph-geometry"
import { useDebouncedValue } from "@/features/graph/hooks/use-debounced-value"
import { useGraphFilters } from "@/features/graph/hooks/use-graph-filters"
import { useGraphLayout } from "@/features/graph/hooks/use-graph-layout"
import { useGraphSelection } from "@/features/graph/hooks/use-graph-selection"
import { useMemoryGraphTheme } from "@/features/graph/lib/memory-graph-theme"
import { useGraphPrefs } from "@/features/graph/lib/graph-prefs"
import { PanelResizeHandle } from "@/features/graph/components/panel-resize-handle"
import {
  panelLayout,
  widthFromPointer,
  DETAIL_PANEL_MIN_WIDTH,
  GRAPH_MIN_WIDTH,
} from "@/features/graph/lib/panel-resize"

type ViewMode = "2d" | "3d"

/**
 * The real-backend counterpart of the demo `MemoryGraphExplorer` (Ruling 5's
 * DEMO ? demo : real split). Relocated here from the orphaned
 * `/unified-graph` route (T1.60, Step 1) — the sidebar nav already pointed
 * at `/memory-graph`, which served only demo data before this move.
 */
export function RealMemoryGraphPage() {
  useFullBleedContent()
  useSetPageChrome({
    icon: Waypoints,
    title: "Memory Graph",
    description:
      "The L1 candidate entity graph and its detected topics — a browsing surface; retrieval does not consult it.",
  })
  const { tokens, palette } = useMemoryGraphTheme()
  const [viewMode, setViewMode] = useState<ViewMode>("2d")
  const [, setGraphReady] = useState(false)
  const [colorMode, setColorMode] = useState<ColorMode>(DEFAULT_COLOR_MODE)

  const [similarityThreshold, setSimilarityThreshold] = useState(0.5)
  const [minClusterSize, setMinClusterSize] = useState(3)
  const debouncedSimilarity = useDebouncedValue(similarityThreshold, 500)
  const debouncedMinSize = useDebouncedValue(minClusterSize, 500)

  const [entityLayerEnabled, setEntityLayerEnabled] = useState(false)
  const [selectedEntityTypes, setSelectedEntityTypes] = useState<Set<string>>(
    new Set(),
  )

  const { data, isLoading, isFetching } = useUnifiedGraph(
    debouncedSimilarity,
    debouncedMinSize,
    entityLayerEnabled,
  )

  // `placeholderData: keepPreviousData` deliberately keeps the graph on screen
  // when the entity toggle changes the query key, so `isLoading` stays false
  // and the fetch was previously invisible. This is that fetch, and the only
  // thing it drives is an affordance -- the graph, its camera and its layout
  // all stay put.
  const isRefetching = isFetching && !isLoading

  const layout = useGraphLayout()
  const filters = useGraphFilters(data, entityLayerEnabled, selectedEntityTypes)
  const selection = useGraphSelection()

  const storedPanelWidth = useGraphPrefs((s) => s.detailPanelWidth)
  const [draggedPanelWidth, setDraggedPanelWidth] = useState<number | null>(
    null,
  )
  const splitRef = useRef<HTMLDivElement>(null)
  const [splitWidth, setSplitWidth] = useState(0)

  const { width: panelWidth, floating: panelFloating } = panelLayout(
    draggedPanelWidth ?? storedPanelWidth,
    // Before the split is measured, honour the stored width rather than
    // clamping against a zero container and collapsing the panel.
    splitWidth || Number.POSITIVE_INFINITY,
  )

  const widthAt = useCallback((clientX: number) => {
    const box = splitRef.current?.getBoundingClientRect()
    if (!box) return DETAIL_PANEL_MIN_WIDTH
    return widthFromPointer(clientX, box.right, box.width)
  }, [])

  const commitPanelWidth = useCallback((px: number) => {
    setDraggedPanelWidth(null)
    useGraphPrefs.getState().setDetailPanelWidth(px)
  }, [])

  // The canvas floor is a fact about the split's own width, so a narrowing
  // window has to squeeze the panel rather than the graph.
  useEffect(() => {
    const el = splitRef.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      const next = entries[0]?.contentRect.width
      if (next && next > 0) setSplitWidth(next)
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState<{
    width: number
    height: number
  } | null>(null)
  const hasGraphData = (data?.memories.length ?? 0) > 0

  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) return
      const { width, height } = entry.contentRect
      if (width > 0 && height > 0) {
        setDimensions((prev) =>
          prev && prev.width === width && prev.height === height
            ? prev
            : { width, height },
        )
      }
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [hasGraphData])

  const handleGraphReady = useCallback(() => setGraphReady(true), [])

  useEffect(() => {
    setGraphReady(false)
  }, [viewMode])

  function handleReset() {
    setSimilarityThreshold(0.5)
    setMinClusterSize(3)
    layout.setClusterTightness(300)
    layout.setNodeSpacing(100)
    layout.setSpacing3D(50)
    layout.setSizeMode(DEFAULT_SIZE_MODE)
    setColorMode(DEFAULT_COLOR_MODE)
    layout.setHullMode(DEFAULT_HULL_MODE)
    setEntityLayerEnabled(false)
    setSelectedEntityTypes(new Set())
    selection.setSelectedEntityId(null)
    filters.clearFilters()
  }

  const graphData3D = useMemo(
    () => {
      if (!data) return { nodes: [], links: [] }
      const graphFilters: FilterState = {
        searchText: filters.debouncedSearchText,
        selectedTags: filters.selectedTags,
        selectedTypes: filters.selectedTypes,
        selectedSources: filters.selectedSources,
        selectedClusters: filters.selectedClusters,
        selectedEntityTypes,
      }
      return transformToGraphData(
        data,
        layout.sizeMode,
        graphFilters,
        colorMode,
        entityLayerEnabled,
        filters.filteredEntities,
        filters.filteredEntityRelations,
        palette,
      )
    },
    // palette intentionally excluded from deps: the renderer recolors node
    // materials in place so a theme flip preserves 3D positions. colorMode (a dep)
    // still recomputes with the current palette.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
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
    ],
  )

  const selectedMemory =
    data?.memories.find((m) => m.id === selection.selectedNodeId) ?? null
  const selectedEntity =
    data?.entities?.find((e) => e.id === selection.selectedEntityId) ?? null
  const memoryCount = data?.memories.length ?? 0

  return (
    <div
      ref={splitRef}
      className="relative flex h-full overflow-hidden"
      style={{ minHeight: 0 }}
      data-testid="graph-split"
    >
      <h1 className="sr-only">Memory Graph</h1>
      <div className="flex min-w-0 flex-1 flex-col">
        {isLoading && <GraphSkeleton />}
        {!isLoading && memoryCount === 0 && (
          <EmptyState
            kind="empty"
            icon={Waypoints}
            scope="page"
            title="No graph yet"
            description="The graph is built from entities extracted on ingest. Capture memories with the pipeline running and nodes appear here."
          />
        )}

        {memoryCount > 0 && (
          <div ref={containerRef} className="relative min-h-0 flex-1">
            <div className="bg-background absolute inset-0">
              {dimensions && viewMode === "2d" && data && (
                <Graph2DRenderer
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
                  tokens={tokens}
                  palette={palette}
                  clusterNames={data?.cluster_names ?? {}}
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
                  tokens={tokens}
                  palette={palette}
                />
              )}
            </div>

            {isLoading && (
              <div className="bg-background absolute inset-0 z-30">
                <GraphSkeleton />
              </div>
            )}

            {isRefetching && (
              <div
                className="bg-card/90 border-border text-muted-foreground absolute top-3 left-1/2 z-30 flex -translate-x-1/2 items-center gap-2 rounded-md border px-3 py-1.5 text-sm shadow-sm"
                role="status"
              >
                <Spinner size="sm" />
                {entityLayerEnabled ? "Loading entities" : "Updating graph"}
              </div>
            )}

            <div className="absolute top-3 left-3 z-30">
              <Button
                variant="outline"
                size="icon"
                aria-label="Filters"
                title="Filters"
                className={`h-8 w-8 rounded-md shadow-lg ${filters.showFilters ? "bg-primary/20 border-primary text-primary hover:bg-primary/30 hover:text-primary" : "bg-card/80 backdrop-blur-sm"}`}
                onClick={() => filters.setShowFilters((v) => !v)}
              >
                <Filter className="h-4 w-4" />
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
              entityLayerLoading={isRefetching}
              sharedEntitiesOnly={filters.sharedEntitiesOnly}
              onSharedEntitiesOnlyChange={filters.setSharedEntitiesOnly}
              onEntityLayerChange={setEntityLayerEnabled}
              sizeMode={layout.sizeMode}
              onSizeModeChange={layout.setSizeMode}
              similarityThreshold={similarityThreshold}
              onSimilarityChange={setSimilarityThreshold}
              minClusterSize={minClusterSize}
              onMinClusterSizeChange={setMinClusterSize}
              spacing={
                viewMode === "2d" ? layout.nodeSpacing : layout.spacing3D
              }
              onSpacingChange={
                viewMode === "2d" ? layout.setNodeSpacing : layout.setSpacing3D
              }
              clusterTightness={layout.clusterTightness}
              onClusterTightnessChange={layout.setClusterTightness}
              onReset={handleReset}
              trailing={
                !selection.showPanel && (
                  <Button
                    variant="outline"
                    size="icon"
                    aria-label="Show details panel"
                    title="Show details panel"
                    className="bg-card/80 pointer-events-auto h-8 w-8 rounded-md border shadow-lg backdrop-blur-sm"
                    onClick={() => selection.setShowPanel(true)}
                  >
                    <PanelRightClose className="h-4 w-4" />
                  </Button>
                )
              }
            />

            {entityLayerEnabled && (
              <div className="pointer-events-none absolute top-16 right-0 left-0 z-20 flex flex-col items-center gap-1.5 px-3">
                {/* The standing "entities are not project-scoped" caption was
                    removed on the owner's instruction. The truncation banner
                    below is a different thing and stays: it reports that this
                    view is missing data, which nothing else on the page says. */}
                {data?.entities_truncated && (
                  <p className="bg-warning/12 border-warning/55 text-warning rounded-md border px-2.5 py-1 text-sm shadow-lg backdrop-blur-sm">
                    Entity overlay truncated — showing a partial view.
                  </p>
                )}
              </div>
            )}

            <div
              className={`border-border bg-card absolute top-14 left-3 z-[25] flex origin-top flex-col overflow-clip rounded-lg border shadow-xl transition-all duration-200 ease-out ${filters.showFilters ? "scale-y-100 opacity-100" : "pointer-events-none scale-y-0 opacity-0"}`}
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
                    const next = new Set(prev)
                    if (next.has(tag)) next.delete(tag)
                    else next.add(tag)
                    return next
                  })
                }
                onTypeToggle={(type) =>
                  filters.setSelectedTypes((prev) => {
                    const next = new Set(prev)
                    if (next.has(type)) next.delete(type)
                    else next.add(type)
                    return next
                  })
                }
                onSourceToggle={(src) =>
                  filters.setSelectedSources((prev) => {
                    const next = new Set(prev)
                    if (next.has(src)) next.delete(src)
                    else next.add(src)
                    return next
                  })
                }
                onClusterToggle={(cid) =>
                  filters.setSelectedClusters((prev) => {
                    const next = new Set(prev)
                    if (next.has(cid)) next.delete(cid)
                    else next.add(cid)
                    return next
                  })
                }
                onShowAll={filters.clearFilters}
                entityLayerEnabled={entityLayerEnabled}
                allEntityTypes={filters.allEntityTypes}
                selectedEntityTypes={selectedEntityTypes}
                onEntityTypeToggle={(etype) =>
                  setSelectedEntityTypes((prev) => {
                    const next = new Set(prev)
                    if (next.has(etype)) next.delete(etype)
                    else next.add(etype)
                    return next
                  })
                }
              />
            </div>

            <ChatOverlay
              selectedNodeId={selection.selectedNodeId}
              selectedEntityId={selection.selectedEntityId}
              onNodeSelect={(type, id) => {
                if (type === "entity") {
                  selection.setSelectedEntityId(id)
                  selection.setSelectedNodeId(`entity:${id}`)
                } else {
                  selection.setSelectedNodeId(id)
                  selection.setSelectedEntityId(null)
                }
              }}
            />
          </div>
        )}
      </div>

      {selection.showPanel && memoryCount > 0 && (
        <>
          {/* Resizing an overlay against a canvas floor that no longer
              constrains it is meaningless, so the handle only exists for the
              split layout. */}
          {!panelFloating && (
            <PanelResizeHandle
              width={panelWidth}
              onResize={setDraggedPanelWidth}
              onCommit={commitPanelWidth}
              widthAt={widthAt}
              min={DETAIL_PANEL_MIN_WIDTH}
              max={Math.max(
                DETAIL_PANEL_MIN_WIDTH,
                splitWidth - GRAPH_MIN_WIDTH,
              )}
            />
          )}
          <div
            data-testid="graph-detail-panel"
            data-floating={panelFloating}
            className={
              panelFloating
                ? "bg-card border-border absolute inset-y-0 right-0 z-30 flex flex-col overflow-hidden border-l shadow-2xl"
                : "bg-card flex shrink-0 flex-col overflow-hidden"
            }
            style={{ width: panelWidth }}
          >
            <GraphDetailPanel
              colorMode={colorMode}
              selectedMemory={selectedMemory}
              clusterName={
                data?.cluster_names?.[String(selectedMemory?.cluster)] ?? ""
              }
              memories={filters.filteredMemories}
              clusterNames={data?.cluster_names ?? {}}
              visibleEdges={filters.filteredEdges}
              onClose={() => {
                selection.setShowPanel(false)
                selection.setSelectedNodeId(null)
                selection.setSelectedEntityId(null)
              }}
              selectedEntity={selectedEntity}
              entityRelations={filters.filteredEntityRelations}
              allEntities={data?.entities}
              visibleEntities={filters.filteredEntities}
              onNavigateToMemory={selection.handleNavigate}
            >
              {/* Gated on the entity layer, not merely on the 2D view: this
                section counts memories sharing an entity while the canvas
                draws cosine edges, and shown beside a graph carrying no
                entities at all its smaller count reads as the canvas being
                wrong rather than as a second relation. */}
              {selectedMemory && viewMode === "2d" && entityLayerEnabled && (
                <MiniGraph
                  memoryId={selectedMemory.id}
                  onNavigate={selection.handleNavigate}
                  onEntitySelect={selection.handleEntitySelect}
                />
              )}
            </GraphDetailPanel>
          </div>
        </>
      )}
    </div>
  )
}
