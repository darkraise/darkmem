import { useUnifiedGraph } from "@/hooks/useApi";
import { useEffect, useState, useCallback, useMemo } from "react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Filter, PanelRightClose } from "lucide-react";
import { GraphSkeleton } from "@/components/graph/GraphSkeleton";
import { MiniGraph } from "@/components/graph/MiniGraph";
import { GraphFilterPanel } from "@/components/graph/GraphFilterPanel";
import { GraphDetailPanel } from "@/components/graph/GraphDetailPanel";
import { Graph2DRenderer } from "@/components/graph/Graph2DRenderer";
import type { SizeMode } from "@/lib/graph-utils";

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

  const handleNavigate = useCallback((id: string) => {
    setSelectedMemoryId(id);
    setShowPanel(true);
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
            <div className="bg-[#0d1117] absolute inset-0">
              <Graph2DRenderer
                data={data!}
                filteredMemories={filteredMemories}
                filteredClusters={filteredClusters}
                filteredEdges={filteredEdges}
                selectedNodeId={selectedMemoryId}
                onNodeSelect={(id) => {
                  setSelectedMemoryId(id);
                  if (id) setShowPanel(true);
                }}
                onReady={() => {}}
                sizeMode={sizeMode}
                spacing={debouncedSpacing}
                clusterTightness={debouncedTightness}
                showTagOverlay={showTagOverlay}
              />
            </div>

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
