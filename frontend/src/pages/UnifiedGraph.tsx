import { useUnifiedGraph, useMemoryContext } from "@/hooks/useApi";
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
import { X, Filter, PanelRightClose } from "lucide-react";
import { Network, DataSet } from "vis-network/standalone";

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

// ─── Mini sub-graph component ─────────────────────────────────────────────────

// ─── Graph Loading Skeleton ──────────────────────────────────────────────────

interface SkelCluster {
  color: string;
  hull: { cx: string; cy: string; rx: string; ry: string; rotate: string };
  nodes: { top: string; left: string; size: string; delay: string }[];
}

const SKEL_CLUSTERS: SkelCluster[] = [
  {
    // Purple cluster (left)
    color: "168,85,247",
    hull: { cx: "22%", cy: "38%", rx: "14%", ry: "18%", rotate: "-10deg" },
    nodes: [
      { top: "32%", left: "18%", size: "44px", delay: "0s" },
      { top: "24%", left: "26%", size: "34px", delay: "0.3s" },
      { top: "44%", left: "28%", size: "28px", delay: "0.6s" },
      { top: "28%", left: "12%", size: "26px", delay: "0.9s" },
      { top: "40%", left: "14%", size: "22px", delay: "0.4s" },
      { top: "48%", left: "22%", size: "20px", delay: "0.7s" },
      { top: "36%", left: "30%", size: "24px", delay: "0.2s" },
    ],
  },
  {
    // Green cluster (right)
    color: "63,185,80",
    hull: { cx: "65%", cy: "42%", rx: "15%", ry: "16%", rotate: "8deg" },
    nodes: [
      { top: "38%", left: "62%", size: "42px", delay: "0.2s" },
      { top: "30%", left: "72%", size: "32px", delay: "0.5s" },
      { top: "48%", left: "68%", size: "28px", delay: "0.8s" },
      { top: "46%", left: "56%", size: "30px", delay: "0.4s" },
      { top: "36%", left: "76%", size: "22px", delay: "0.1s" },
      { top: "52%", left: "60%", size: "20px", delay: "0.6s" },
      { top: "42%", left: "74%", size: "24px", delay: "0.3s" },
    ],
  },
  {
    // Blue cluster (top-center)
    color: "88,166,255",
    hull: { cx: "46%", cy: "20%", rx: "13%", ry: "12%", rotate: "5deg" },
    nodes: [
      { top: "16%", left: "44%", size: "36px", delay: "0.1s" },
      { top: "12%", left: "36%", size: "26px", delay: "0.7s" },
      { top: "22%", left: "52%", size: "28px", delay: "0.4s" },
      { top: "18%", left: "56%", size: "22px", delay: "0.8s" },
      { top: "10%", left: "46%", size: "20px", delay: "0.5s" },
      { top: "24%", left: "40%", size: "24px", delay: "0.2s" },
    ],
  },
  {
    // Orange cluster (bottom)
    color: "255,166,87",
    hull: { cx: "42%", cy: "68%", rx: "14%", ry: "13%", rotate: "-5deg" },
    nodes: [
      { top: "64%", left: "38%", size: "38px", delay: "0.3s" },
      { top: "70%", left: "48%", size: "30px", delay: "0.6s" },
      { top: "58%", left: "46%", size: "26px", delay: "0.1s" },
      { top: "72%", left: "36%", size: "22px", delay: "0.5s" },
      { top: "66%", left: "52%", size: "24px", delay: "0.8s" },
      { top: "60%", left: "32%", size: "20px", delay: "0.4s" },
    ],
  },
  {
    // Cyan cluster (far right, smaller)
    color: "6,182,212",
    hull: { cx: "84%", cy: "24%", rx: "10%", ry: "11%", rotate: "12deg" },
    nodes: [
      { top: "20%", left: "82%", size: "32px", delay: "0.2s" },
      { top: "14%", left: "88%", size: "24px", delay: "0.6s" },
      { top: "28%", left: "86%", size: "22px", delay: "0.9s" },
      { top: "22%", left: "78%", size: "20px", delay: "0.4s" },
    ],
  },
];

const SKEL_EDGES: { top: string; left: string; width: string; rotate: string; delay: string }[] = [
  // Intra-cluster edges (purple)
  { top: "34%", left: "20%", width: "70px", rotate: "-12deg", delay: "0.2s" },
  { top: "30%", left: "16%", width: "55px", rotate: "35deg", delay: "0.5s" },
  { top: "42%", left: "18%", width: "60px", rotate: "15deg", delay: "0.8s" },
  // Intra-cluster edges (green)
  { top: "40%", left: "60%", width: "80px", rotate: "18deg", delay: "0.3s" },
  { top: "44%", left: "58%", width: "55px", rotate: "-25deg", delay: "0.7s" },
  { top: "36%", left: "70%", width: "50px", rotate: "30deg", delay: "0.1s" },
  // Intra-cluster edges (blue)
  { top: "18%", left: "40%", width: "65px", rotate: "8deg", delay: "0.4s" },
  { top: "14%", left: "44%", width: "50px", rotate: "-18deg", delay: "0.6s" },
  // Intra-cluster edges (orange)
  { top: "66%", left: "36%", width: "70px", rotate: "12deg", delay: "0.5s" },
  { top: "62%", left: "42%", width: "50px", rotate: "-20deg", delay: "0.3s" },
  // Cross-cluster edges
  { top: "46%", left: "32%", width: "120px", rotate: "5deg", delay: "0.6s" },
  { top: "26%", left: "30%", width: "90px", rotate: "-8deg", delay: "0.4s" },
  { top: "54%", left: "48%", width: "60px", rotate: "35deg", delay: "0.2s" },
];

const SKEL_BARS = ["64px", "80px", "56px", "48px"];

function GraphSkeleton() {
  return (
    <div className="relative flex-1 min-h-0">
      <div className="bg-[#0d1117] absolute inset-0 overflow-hidden">
        {/* Toolbar skeleton */}
        <div className="absolute top-3 left-1/2 -translate-x-1/2 flex gap-2 px-3 py-1.5 bg-card/70 rounded-md border border-border z-10">
          {SKEL_BARS.map((w, i) => (
            <div
              key={i}
              className="h-2 rounded-full bg-[#21262d] animate-pulse"
              style={{ width: w, animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </div>

        {/* Cluster hulls */}
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

        {/* Skeleton edges */}
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

        {/* Skeleton nodes */}
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

        {/* Loading text */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-xs text-muted-foreground tracking-wide animate-pulse">
          Loading graph data...
        </div>
      </div>
    </div>
  );
}

// ─── Mini Graph ──────────────────────────────────────────────────────────────

interface MiniGraphProps {
  memoryId: string;
  onNavigate: (id: string) => void;
}

function MiniGraph({ memoryId, onNavigate }: MiniGraphProps) {
  const { data, isLoading } = useMemoryContext(memoryId);
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);

  useEffect(() => {
    if (!containerRef.current || !data) return;
    if (networkRef.current) {
      networkRef.current.destroy();
      networkRef.current = null;
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const nodes: any[] = [];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const edges: any[] = [];
    const neighborIds = new Set<string>();

    // Entity nodes — diamond (deduplicate by name+type)
    const seenEntities = new Set<string>();
    for (const e of data.entities) {
      const entityKey = `${e.name}::${e.entity_type}`;
      if (seenEntities.has(entityKey)) continue;
      seenEntities.add(entityKey);
      nodes.push({
        id: `entity-${e.name}-${e.entity_type}`,
        label: e.name,
        shape: "diamond",
        size: 16,
        color: {
          background: "#ffa657",
          border: "#ffa657",
          highlight: { background: "#ffa657", border: "#fff" },
        },
        font: { color: "#c9d1d9", size: 11, face: "Inter, sans-serif" },
        borderWidth: 2,
      });
    }

    // Neighbor memory nodes — dot (deduplicate by id)
    for (const n of data.neighbors) {
      if (neighborIds.has(n.id)) continue;
      neighborIds.add(n.id);
      nodes.push({
        id: n.id,
        label: n.content.slice(0, 18) + (n.content.length > 18 ? "…" : ""),
        shape: "dot",
        size: 12,
        color: {
          background: "#8b5cf6",
          border: "#a855f7",
          highlight: { background: "#a855f7", border: "#fff" },
        },
        font: { color: "#8b949e", size: 10, face: "Inter, sans-serif" },
        borderWidth: 1,
        _isNeighbor: true,
        _neighborId: n.id,
      });
    }

    // Relation edges — map entity names to node IDs
    const entityNameToId = new Map<string, string>();
    for (const e of data.entities) {
      if (!entityNameToId.has(e.name)) {
        entityNameToId.set(e.name, `entity-${e.name}-${e.entity_type}`);
      }
    }
    const entityNodeIds = new Set(entityNameToId.values());
    for (let i = 0; i < data.relations.length; i++) {
      const r = data.relations[i];
      const src = entityNameToId.get(r.source);
      const tgt = entityNameToId.get(r.target);
      if (src && tgt && entityNodeIds.has(src) && entityNodeIds.has(tgt)) {
        edges.push({
          id: `rel-${i}`,
          from: src!,
          to: tgt!,
          label: r.type,
          arrows: { to: { enabled: true, scaleFactor: 0.5 } },
          color: { color: "#7a8490", highlight: "#4CC9F0", opacity: 0.9 },
          font: { color: "#8b949e", size: 9, strokeWidth: 0 },
          smooth: { type: "continuous", roundness: 0.3 },
          width: 1.5,
        });
      }
    }

    // Entity→memory edges (entity appears in neighbor)
    for (const e of data.entities) {
      const entityId = entityNameToId.get(e.name);
      if (!entityId) continue;
      for (const mid of e.memory_ids) {
        if (neighborIds.has(mid)) {
          edges.push({
            id: `em-${e.name}-${e.entity_type}-${mid}`,
            from: entityId,
            to: mid,
            arrows: {},
            color: { color: "#586069", opacity: 0.7 },
            smooth: { type: "curvedCW", roundness: 0.2 },
            width: 1,
            dashes: [3, 3],
          });
        }
      }
    }

    const nodesDs = new DataSet(nodes);
    const edgesDs = new DataSet(edges);

    const network = new Network(
      containerRef.current,
      { nodes: nodesDs, edges: edgesDs },
      {
        physics: {
          barnesHut: {
            gravitationalConstant: -600,
            springLength: 60,
            springConstant: 0.08,
            damping: 0.5,
            avoidOverlap: 0.4,
          },
          stabilization: { enabled: true, iterations: 150, fit: true },
        },
        interaction: {
          hover: true,
          tooltipDelay: 99999,
          zoomView: true,
          dragView: true,
        },
        edges: {
          color: { color: "#6e7681", opacity: 0.8 },
          smooth: { enabled: true, type: "continuous", roundness: 0.2 },
          length: 60,
        },
        nodes: {
          shape: "dot",
          size: 14,
          font: { color: "#c9d1d9", size: 11 },
          borderWidth: 2,
        },
      },
    );

    network.on("stabilizationIterationsDone", () => {
      network.setOptions({ physics: { enabled: false } });
      network.fit({ animation: { duration: 200, easingFunction: "easeInOutQuad" } });
    });

    // Navigate to neighbor on click
    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0] as string;
        const node = nodes.find((n) => n.id === nodeId);
        if (node?._isNeighbor) {
          onNavigate(node._neighborId as string);
        }
      }
    });

    networkRef.current = network;

    return () => {
      network.destroy();
      networkRef.current = null;
    };
  }, [data, onNavigate]);

  if (isLoading)
    return (
      <p className="text-xs text-muted-foreground p-2">Loading context…</p>
    );
  if (!data || (data.entities.length === 0 && data.neighbors.length === 0)) {
    return (
      <p className="text-xs text-muted-foreground p-2">
        No entities extracted yet. Run the pipeline with entity extraction enabled to populate this graph.
      </p>
    );
  }

  return (
    <div
      ref={containerRef}
      className="bg-[#0d1117] border border-border rounded"
      style={{ height: 250 }}
    />
  );
}

// ─── Filter Panel ────────────────────────────────────────────────────────────

interface FilterPanelProps {
  tagGroups: [string, [string, number][]][];
  allTypes: [string, number][];
  allSources: [string, number][];
  allClusters: [number, number][];
  clusterNames: Record<string, string>;
  selectedTags: Set<string>;
  selectedTypes: Set<string>;
  selectedSources: Set<string>;
  selectedClusters: Set<number>;
  searchText: string;
  onSearchChange: (v: string) => void;
  onTagToggle: (tag: string) => void;
  onTypeToggle: (type: string) => void;
  onSourceToggle: (src: string) => void;
  onClusterToggle: (cid: number) => void;
  onShowAll: () => void;
}

function FilterPanel({
  tagGroups,
  allTypes,
  allSources,
  allClusters,
  clusterNames,
  selectedTags,
  selectedTypes,
  selectedSources,
  selectedClusters,
  searchText,
  onSearchChange,
  onTagToggle,
  onTypeToggle,
  onSourceToggle,
  onClusterToggle,
  onShowAll,
}: FilterPanelProps) {
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(
    new Set(),
  );

  function toggleGroup(group: string) {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      next.has(group) ? next.delete(group) : next.add(group);
      return next;
    });
  }

  const hasFilters =
    searchText.trim() !== "" ||
    selectedTags.size > 0 ||
    selectedTypes.size > 0 ||
    selectedSources.size > 0 ||
    selectedClusters.size > 0;

  return (
    <div className="flex flex-col flex-1 min-h-0" style={{ width: 280 }}>
      {/* Fixed search header */}
      <div className="p-3 pb-2 border-b border-border shrink-0">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
          Search
        </p>
        <input
          type="text"
          placeholder="Filter by content…"
          value={searchText}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full text-sm bg-background border border-border rounded px-2 py-1.5 text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-primary"
        />
      </div>

      {/* Scrollable filter sections */}
      <div className="flex-1 min-h-0 overflow-y-auto scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent">
        <div className="p-3 space-y-4">
          {/* Tags */}
          {tagGroups.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Tags
              </p>
              <div className="space-y-2">
                {tagGroups.map(([category, tags]) => (
                  <div key={category}>
                    <button
                      className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground w-full text-left mb-1"
                      onClick={() => toggleGroup(category)}
                    >
                      <span className="font-medium capitalize">{category}</span>
                      <span className="ml-auto opacity-60">
                        {collapsedGroups.has(category) ? "▶" : "▼"}
                      </span>
                    </button>
                    {!collapsedGroups.has(category) && (
                      <div className="space-y-0.5 pl-1">
                        {tags.map(([tag, count]) => (
                          <label
                            key={tag}
                            className="flex items-center gap-2 text-sm cursor-pointer py-0.5 group"
                          >
                            <input
                              type="checkbox"
                              checked={selectedTags.has(tag)}
                              onChange={() => onTagToggle(tag)}
                              className="accent-primary w-3.5 h-3.5"
                            />
                            <span
                              className={`flex-1 truncate ${
                                selectedTags.has(tag)
                                  ? "text-foreground"
                                  : "text-muted-foreground group-hover:text-foreground"
                              }`}
                              title={tag}
                            >
                              {tag.includes("/")
                                ? tag.split("/").slice(1).join("/")
                                : tag}
                            </span>
                            <span className="opacity-40 text-xs">{count}</span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Types */}
          {allTypes.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Types
              </p>
              <div className="space-y-0.5">
                {allTypes.map(([type, count]) => {
                  const realType = type === "(none)" ? null : type;
                  const color = typeColor(realType);
                  return (
                    <label
                      key={type}
                      className="flex items-center gap-2 text-sm cursor-pointer py-0.5 group"
                    >
                      <input
                        type="checkbox"
                        checked={selectedTypes.has(type)}
                        onChange={() => onTypeToggle(type)}
                        className="accent-primary w-3.5 h-3.5"
                      />
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: color }}
                      />
                      <span
                        className={`flex-1 truncate ${
                          selectedTypes.has(type)
                            ? "text-foreground"
                            : "text-muted-foreground group-hover:text-foreground"
                        }`}
                      >
                        {type}
                      </span>
                      <span className="opacity-40 text-xs">{count}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}

          {/* Sources */}
          {allSources.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Sources
              </p>
              <div className="space-y-0.5">
                {allSources.map(([src, count]) => (
                  <label
                    key={src}
                    className="flex items-center gap-2 text-sm cursor-pointer py-0.5 group"
                  >
                    <input
                      type="checkbox"
                      checked={selectedSources.has(src)}
                      onChange={() => onSourceToggle(src)}
                      className="accent-primary w-3.5 h-3.5"
                    />
                    <span
                      className={`flex-1 truncate ${
                        selectedSources.has(src)
                          ? "text-foreground"
                          : "text-muted-foreground group-hover:text-foreground"
                      }`}
                      title={src}
                    >
                      {src}
                    </span>
                    <span className="opacity-40 text-xs">{count}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {/* Clusters */}
          {allClusters.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                Clusters
              </p>
              <div className="space-y-0.5">
                {allClusters.map(([cid, count]) => {
                  const color = clusterColor(cid);
                  return (
                    <label
                      key={cid}
                      className="flex items-center gap-2 text-sm cursor-pointer py-0.5 group"
                    >
                      <input
                        type="checkbox"
                        checked={selectedClusters.has(cid)}
                        onChange={() => onClusterToggle(cid)}
                        className="accent-primary w-3.5 h-3.5"
                      />
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0 opacity-70"
                        style={{ backgroundColor: color }}
                      />
                      <span
                        className={`flex-1 ${
                          selectedClusters.has(cid)
                            ? "text-foreground"
                            : "text-muted-foreground group-hover:text-foreground"
                        }`}
                      >
                        {clusterNames[String(cid)] || `Cluster ${cid}`}
                      </span>
                      <span className="opacity-40 text-xs">{count}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Fixed Show All button */}
      <div className="p-3 border-t border-border shrink-0">
        <button
          className={`w-full text-sm py-1.5 rounded border transition-colors ${
            hasFilters
              ? "border-primary text-primary hover:bg-primary/10"
              : "border-border text-muted-foreground cursor-default opacity-50"
          }`}
          onClick={onShowAll}
          disabled={!hasFilters}
        >
          Show All
        </button>
      </div>
    </div>
  );
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
  const filteredCount = filteredMemories.length;
  const clusterCount = Object.keys(data?.clusters ?? {}).length;

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
              <FilterPanel
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
          {/* Panel header */}
          <div className="flex items-center justify-between px-4 pt-3 pb-2 border-b border-border">
            <span className="text-sm font-medium">
              {selectedMemory ? "Memory Detail" : "Graph Summary"}
            </span>
            <button
              className="text-muted-foreground hover:text-foreground rounded-sm p-1"
              onClick={() => {
                setShowPanel(false);
                if (selectedMemory) {
                  setSelectedMemoryId(null);
                  exitFocusModeRef.current?.();
                  networkRef.current?.unselectAll();
                  networkRef.current?.redraw();
                }
              }}
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Memory detail */}
          {selectedMemory ? (
            <div className="p-4 space-y-3">
              <p className="text-sm text-foreground leading-relaxed">
                {selectedMemory.content}
              </p>

              {selectedMemory.tags.length > 0 && (
                <div className="flex gap-1 flex-wrap">
                  {selectedMemory.tags.map((t) => (
                    <span
                      key={t}
                      className="text-xs px-1.5 py-0.5 rounded bg-accent text-primary"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}

              <div className="text-xs text-muted-foreground space-y-0.5">
                <div>
                  Source:{" "}
                  <span className="text-foreground">
                    {selectedMemory.source}
                  </span>
                </div>
                {selectedMemory.memory_type && (
                  <div>
                    Type:{" "}
                    <span className="text-foreground">
                      {selectedMemory.memory_type}
                    </span>
                  </div>
                )}
                <div>
                  Importance:{" "}
                  <span className="text-foreground">
                    {selectedMemory.importance.toFixed(2)}
                  </span>
                </div>
                {selectedMemory.cluster >= 0 && (
                  <div className="flex items-center gap-1">
                    Cluster:{" "}
                    <span className="inline-flex items-center gap-1 text-foreground">
                      <span
                        className="inline-block w-2 h-2 rounded-full"
                        style={{
                          backgroundColor: clusterColor(selectedMemory.cluster),
                        }}
                      />
                      {data?.cluster_names?.[String(selectedMemory.cluster)] ||
                        `Cluster ${selectedMemory.cluster}`}
                    </span>
                  </div>
                )}
              </div>

              <div className="pt-2 border-t border-border">
                <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                  Entity Context
                </p>
                <MiniGraph
                  memoryId={selectedMemory.id}
                  onNavigate={handleNavigate}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Click a neighbor node to navigate.
                </p>
              </div>
            </div>
          ) : (
            /* Graph summary */
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-background rounded-lg p-3">
                  <p className="text-2xl font-bold">{filteredCount}</p>
                  <p className="text-xs text-muted-foreground">Memories</p>
                </div>
                <div className="bg-background rounded-lg p-3">
                  <p className="text-2xl font-bold">{clusterCount}</p>
                  <p className="text-xs text-muted-foreground">Clusters</p>
                </div>
                <div className="bg-background rounded-lg p-3">
                  <p className="text-2xl font-bold">{filteredEdges.length}</p>
                  <p className="text-xs text-muted-foreground">Edges</p>
                </div>
                <div className="bg-background rounded-lg p-3">
                  <p className="text-2xl font-bold">{allTypes.length}</p>
                  <p className="text-xs text-muted-foreground">Types</p>
                </div>
              </div>

              {/* Clusters list */}
              {allClusters.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                    Clusters
                  </p>
                  <div className="space-y-1.5">
                    {allClusters.map(([cid, count]) => (
                      <div
                        key={cid}
                        className="flex items-center gap-2 text-sm"
                      >
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: clusterColor(cid) }}
                        />
                        <span className="flex-1 truncate text-foreground">
                          {data?.cluster_names?.[String(cid)] ||
                            `Cluster ${cid}`}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {count}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Types breakdown */}
              {allTypes.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                    Types
                  </p>
                  <div className="space-y-1.5">
                    {allTypes.map(([type, count]) => {
                      const color = typeColor(
                        type === "(none)" ? null : type,
                      );
                      return (
                        <div
                          key={type}
                          className="flex items-center gap-2 text-sm"
                        >
                          <span
                            className="w-2.5 h-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: color }}
                          />
                          <span className="flex-1 text-foreground">{type}</span>
                          <span className="text-xs text-muted-foreground">
                            {count}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Sources breakdown */}
              {allSources.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                    Sources
                  </p>
                  <div className="space-y-1.5">
                    {allSources.map(([src, count]) => (
                      <div
                        key={src}
                        className="flex items-center gap-2 text-sm"
                      >
                        <span className="flex-1 text-foreground">{src}</span>
                        <span className="text-xs text-muted-foreground">
                          {count}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
