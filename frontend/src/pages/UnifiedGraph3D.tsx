import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { PanelRightClose, Hexagon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUnifiedGraph } from "@/hooks/useApi";
import { ForceGraph3DWrapper } from "@/components/graph3d/ForceGraph3DWrapper";
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

  const handleNodeSelect = useCallback((node: Node3D | null) => {
    setSelectedNode(node);
    if (node) setShowPanel(true);
  }, []);

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
          <ForceGraph3DWrapper
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

const SKEL_CLUSTERS = [
  {
    color: "168,85,247",
    hull: { cx: "22%", cy: "38%", rx: "14%", ry: "18%", rotate: "-10deg" },
    nodes: [
      { top: "32%", left: "18%", size: "44px", delay: "0s" },
      { top: "24%", left: "26%", size: "34px", delay: "0.3s" },
      { top: "44%", left: "28%", size: "28px", delay: "0.6s" },
      { top: "28%", left: "12%", size: "26px", delay: "0.9s" },
      { top: "40%", left: "14%", size: "22px", delay: "0.4s" },
    ],
  },
  {
    color: "63,185,80",
    hull: { cx: "65%", cy: "42%", rx: "15%", ry: "16%", rotate: "8deg" },
    nodes: [
      { top: "38%", left: "62%", size: "42px", delay: "0.2s" },
      { top: "30%", left: "72%", size: "32px", delay: "0.5s" },
      { top: "48%", left: "68%", size: "28px", delay: "0.8s" },
      { top: "46%", left: "56%", size: "30px", delay: "0.4s" },
      { top: "36%", left: "76%", size: "22px", delay: "0.1s" },
    ],
  },
  {
    color: "88,166,255",
    hull: { cx: "46%", cy: "20%", rx: "13%", ry: "12%", rotate: "5deg" },
    nodes: [
      { top: "16%", left: "44%", size: "36px", delay: "0.1s" },
      { top: "12%", left: "36%", size: "26px", delay: "0.7s" },
      { top: "22%", left: "52%", size: "28px", delay: "0.4s" },
      { top: "18%", left: "56%", size: "22px", delay: "0.8s" },
    ],
  },
  {
    color: "255,166,87",
    hull: { cx: "42%", cy: "68%", rx: "14%", ry: "13%", rotate: "-5deg" },
    nodes: [
      { top: "64%", left: "38%", size: "38px", delay: "0.3s" },
      { top: "70%", left: "48%", size: "30px", delay: "0.6s" },
      { top: "58%", left: "46%", size: "26px", delay: "0.1s" },
      { top: "72%", left: "36%", size: "22px", delay: "0.5s" },
    ],
  },
];

const SKEL_EDGES = [
  { top: "34%", left: "20%", width: "70px", rotate: "-12deg", delay: "0.2s" },
  { top: "30%", left: "16%", width: "55px", rotate: "35deg", delay: "0.5s" },
  { top: "40%", left: "60%", width: "80px", rotate: "18deg", delay: "0.3s" },
  { top: "44%", left: "58%", width: "55px", rotate: "-25deg", delay: "0.7s" },
  { top: "18%", left: "40%", width: "65px", rotate: "8deg", delay: "0.4s" },
  { top: "66%", left: "36%", width: "70px", rotate: "12deg", delay: "0.5s" },
  { top: "46%", left: "32%", width: "120px", rotate: "5deg", delay: "0.6s" },
  { top: "26%", left: "30%", width: "90px", rotate: "-8deg", delay: "0.4s" },
];

function GraphSkeleton({ label }: { label: string }) {
  return (
    <>
      <div className="absolute top-3 left-1/2 -translate-x-1/2 flex gap-2 px-3 py-1.5 bg-card/70 rounded-md border border-border z-10">
        {["64px", "80px", "56px", "48px"].map((w, i) => (
          <div
            key={i}
            className="h-2 rounded-full bg-[#21262d] animate-pulse"
            style={{ width: w, animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>

      {SKEL_CLUSTERS.map((c, ci) => (
        <div
          key={`hull-${ci}`}
          className="absolute rounded-[50%] animate-pulse"
          style={{
            left: c.hull.cx,
            top: c.hull.cy,
            width: `calc(${c.hull.rx} * 2)`,
            height: `calc(${c.hull.ry} * 2)`,
            transform: `translate(-50%, -50%) rotate(${c.hull.rotate})`,
            background: `radial-gradient(ellipse at center, rgba(${c.color},0.06) 0%, rgba(${c.color},0.02) 70%, transparent 100%)`,
            border: `1px solid rgba(${c.color},0.08)`,
            animationDelay: `${ci * 0.2}s`,
          }}
        />
      ))}

      {SKEL_EDGES.map((e, i) => (
        <div
          key={`e-${i}`}
          className="absolute h-px animate-pulse"
          style={{
            top: e.top,
            left: e.left,
            width: e.width,
            transform: `rotate(${e.rotate})`,
            transformOrigin: "0 0",
            background: "rgba(139,148,158,0.15)",
            animationDelay: e.delay,
          }}
        />
      ))}

      {SKEL_CLUSTERS.map((c, ci) =>
        c.nodes.map((n, ni) => (
          <div
            key={`n-${ci}-${ni}`}
            className="absolute rounded-full animate-pulse"
            style={{
              top: n.top,
              left: n.left,
              width: n.size,
              height: n.size,
              background: `rgba(${c.color},0.25)`,
              boxShadow: `0 0 16px rgba(${c.color},0.15)`,
              animationDelay: n.delay,
            }}
          />
        )),
      )}

      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-xs text-muted-foreground tracking-wide animate-pulse">
        {label}
      </div>
    </>
  );
}
