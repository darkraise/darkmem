import type { UnifiedMemory, UnifiedGraphData } from "@/hooks/useApi";

export type SizeMode = "connections" | "importance" | "uniform";

export interface Node3D {
  id: string;
  content: string;
  source: string;
  tags: string[];
  memoryType: string | null;
  importance: number;
  cluster: number;
  clusterName: string;
  color: string;
  val: number;
  x?: number;
  y?: number;
  z?: number;
  fx?: number;
  fy?: number;
  fz?: number;
}

export interface Link3D {
  source: string;
  target: string;
  score: number;
}

export interface GraphData3D {
  nodes: Node3D[];
  links: Link3D[];
}

export interface FilterState {
  searchText: string;
  selectedTags: Set<string>;
  selectedTypes: Set<string>;
  selectedSources: Set<string>;
  selectedClusters: Set<number>;
}

export const CLUSTER_PALETTE = [
  "#a855f7", "#3fb950", "#f97316", "#06b6d4",
  "#ec4899", "#eab308", "#6366f1", "#14b8a6",
  "#f43f5e", "#84cc16", "#8b5cf6", "#0ea5e9",
];

export const UNCLUSTERED_COLOR = "#8b949e";

export function clusterColor(clusterId: number): string {
  if (clusterId < 0) return UNCLUSTERED_COLOR;
  return CLUSTER_PALETTE[clusterId % CLUSTER_PALETTE.length];
}

export function computeNodeVal(
  mode: SizeMode,
  connectionCount: number,
  importance: number,
): number {
  if (mode === "uniform") return 2;
  if (mode === "importance") return 1 + importance * 5;
  return 1 + Math.min(5, Math.log1p(connectionCount) * 1.5);
}

function matchesFilter(memory: UnifiedMemory, filters: FilterState): boolean {
  if (filters.searchText) {
    const term = filters.searchText.toLowerCase();
    if (!memory.content.toLowerCase().includes(term)) return false;
  }
  if (filters.selectedTags.size > 0) {
    if (!memory.tags.some((t) => filters.selectedTags.has(t))) return false;
  }
  if (filters.selectedTypes.size > 0) {
    if (!memory.memory_type || !filters.selectedTypes.has(memory.memory_type))
      return false;
  }
  if (filters.selectedSources.size > 0) {
    if (!filters.selectedSources.has(memory.source)) return false;
  }
  if (filters.selectedClusters.size > 0) {
    if (!filters.selectedClusters.has(memory.cluster)) return false;
  }
  return true;
}

export function transformToGraphData(
  data: UnifiedGraphData,
  sizeMode: SizeMode,
  filters: FilterState,
): GraphData3D {
  const edgeCountMap = new Map<string, number>();
  for (const edge of data.similarity_edges) {
    edgeCountMap.set(edge.source, (edgeCountMap.get(edge.source) ?? 0) + 1);
    edgeCountMap.set(edge.target, (edgeCountMap.get(edge.target) ?? 0) + 1);
  }

  const filteredMemories = data.memories.filter((m) =>
    matchesFilter(m, filters),
  );
  const filteredIds = new Set(filteredMemories.map((m) => m.id));

  const nodes: Node3D[] = filteredMemories.map((m) => ({
    id: m.id,
    content: m.content,
    source: m.source,
    tags: m.tags,
    memoryType: m.memory_type,
    importance: m.importance,
    cluster: m.cluster,
    clusterName: data.cluster_names[String(m.cluster)] ?? "",
    color: clusterColor(m.cluster),
    val: computeNodeVal(sizeMode, edgeCountMap.get(m.id) ?? 0, m.importance),
  }));

  const links: Link3D[] = data.similarity_edges
    .filter((e) => filteredIds.has(e.source) && filteredIds.has(e.target))
    .map((e) => ({ source: e.source, target: e.target, score: e.score }));

  return { nodes, links };
}
