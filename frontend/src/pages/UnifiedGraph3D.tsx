import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { GraphSkeleton } from "@/components/graph/GraphSkeleton";
import { useNavigate } from "react-router-dom";
import { PanelRightClose, Hexagon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUnifiedGraph } from "@/hooks/useApi";
import { Graph3DRenderer } from "@/components/graph/Graph3DRenderer";
import { Graph3DDetailPanel } from "@/components/graph3d/Graph3DDetailPanel";
import { Graph3DToolbar } from "@/components/graph3d/Graph3DToolbar";
import {
  transformToGraphData,
  type Node3D,
  type SizeMode,
  type FilterState,
} from "@/lib/graph-utils";

export default function UnifiedGraph3D() {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState<{
    width: number;
    height: number;
  } | null>(null);

  const [sizeMode, setSizeMode] = useState<SizeMode>("connections");
  const [spacing, setSpacing] = useState(50);
  const [selectedNode, setSelectedNode] = useState<Node3D | null>(null);
  const [showPanel, setShowPanel] = useState(false);
  const [graphReady, setGraphReady] = useState(false);

  const [filters] = useState<FilterState>({
    searchText: "",
    selectedTags: new Set(),
    selectedTypes: new Set(),
    selectedSources: new Set(),
    selectedClusters: new Set(),
  });

  const { data, isLoading, error } = useUnifiedGraph(0.5, 0.2, 3);

  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    return transformToGraphData(data, sizeMode, filters);
  }, [data, sizeMode, filters]);

  const handleNodeSelect = useCallback((nodeId: string | null) => {
    const node = nodeId ? graphData.nodes.find(n => n.id === nodeId) ?? null : null;
    setSelectedNode(node);
    if (node) setShowPanel(true);
  }, [graphData.nodes]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) setDimensions({ width, height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="relative flex h-full">
      <div
        ref={containerRef}
        className="relative flex-1 min-w-0 overflow-hidden"
      >
        {dimensions && (
          <Graph3DRenderer
            graphData={graphData}
            width={dimensions.width}
            height={dimensions.height}
            spacing={spacing}
            selectedNodeId={selectedNode?.id ?? null}
            onNodeSelect={handleNodeSelect}
            onReady={() => setGraphReady(true)}
          />
        )}

        {(!graphReady || error) && (
          <div className="absolute inset-0 z-20 overflow-hidden bg-[#0d1117]">
            {error ? (
              <div className="flex h-full items-center justify-center">
                <div className="text-destructive">
                  Failed to load graph: {(error as Error).message}
                </div>
              </div>
            ) : (
              <GraphSkeleton label={isLoading ? "Loading graph data..." : "Rendering graph..."} />
            )}
          </div>
        )}

        {graphReady && !error && (
          <>
            <Graph3DToolbar
              sizeMode={sizeMode}
              onSizeModeChange={setSizeMode}
              spacing={spacing}
              onSpacingChange={setSpacing}
            />

            <div className="absolute top-3 left-3 z-10 flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs"
                onClick={() => navigate("/unified-graph")}
                title="Switch to 2D view"
              >
                <Hexagon className="mr-1.5 h-3.5 w-3.5" />
                2D View
              </Button>
            </div>

            <div className="absolute top-3 right-3 z-10">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setShowPanel((p) => !p)}
              >
                <PanelRightClose className="h-4 w-4" />
              </Button>
            </div>
          </>
        )}
      </div>

      {showPanel && (
        <div className="w-72 shrink-0 overflow-y-auto border-l border-border bg-card">
          <Graph3DDetailPanel
            selectedNode={selectedNode}
            graphData={graphData}
            onClose={() => {
              setSelectedNode(null);
              setShowPanel(false);
            }}
          />
        </div>
      )}
    </div>
  );
}

