import type { UnifiedMemory, UnifiedGraphData } from "@/hooks/useApi";
import { clusterColor, typeColor } from "@/lib/graph-colors";
export { clusterColor, typeColor };
export { CLUSTER_PALETTE, UNCLUSTERED_COLOR } from "@/lib/graph-colors";

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
  hidden?: boolean;
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
    color: typeColor(m.memory_type),
    val: computeNodeVal(sizeMode, edgeCountMap.get(m.id) ?? 0, m.importance),
  }));

  const links: Link3D[] = data.similarity_edges
    .filter((e) => filteredIds.has(e.source) && filteredIds.has(e.target))
    .map((e) => ({ source: e.source, target: e.target, score: e.score }));

  const clusterMembers = new Map<number, string[]>();
  for (const node of nodes) {
    if (node.cluster >= 0) {
      const members = clusterMembers.get(node.cluster) ?? [];
      members.push(node.id);
      clusterMembers.set(node.cluster, members);
    }
  }

  const existingEdges = new Set(links.map((l) => `${l.source}-${l.target}`));
  for (const [, members] of clusterMembers) {
    for (let i = 0; i < members.length; i++) {
      for (let j = i + 1; j < members.length; j++) {
        const key1 = `${members[i]}-${members[j]}`;
        const key2 = `${members[j]}-${members[i]}`;
        if (!existingEdges.has(key1) && !existingEdges.has(key2)) {
          links.push({ source: members[i], target: members[j], score: 0, hidden: true });
        }
      }
    }
  }

  const clusterIdList = [...clusterMembers.keys()];
  for (let i = 0; i < clusterIdList.length; i++) {
    for (let j = i + 1; j < clusterIdList.length; j++) {
      const rep1 = clusterMembers.get(clusterIdList[i])![0];
      const rep2 = clusterMembers.get(clusterIdList[j])![0];
      links.push({ source: rep1, target: rep2, score: 0, hidden: true });
    }
  }

  const clusterIds = clusterIdList;
  const nClusters = clusterIds.length;
  const clusterRadius = 60 + nClusters * 12;
  for (let ci = 0; ci < clusterIds.length; ci++) {
    const theta = (2 * Math.PI * ci) / nClusters;
    const phi = Math.PI / 2 + (Math.random() - 0.5) * 0.5;
    const cx = Math.sin(phi) * Math.cos(theta) * clusterRadius;
    const cy = Math.sin(phi) * Math.sin(theta) * clusterRadius;
    const cz = Math.cos(phi) * clusterRadius * 0.3;
    const spread = 30 + Math.sqrt(nodes.length) * 3;
    const members = clusterMembers.get(clusterIds[ci])!;
    for (const id of members) {
      const node = nodes.find((n) => n.id === id);
      if (node) {
        node.x = cx + (Math.random() - 0.5) * spread;
        node.y = cy + (Math.random() - 0.5) * spread;
        node.z = cz + (Math.random() - 0.5) * spread;
      }
    }
  }

  return { nodes, links };
}
