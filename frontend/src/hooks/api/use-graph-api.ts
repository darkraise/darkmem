import { useQuery, useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface UnifiedMemory {
  id: string;
  content: string;
  source: string;
  tags: string[];
  memory_type: string | null;
  importance: number;
  cluster: number;
}

export interface GraphEntity {
  id: string;
  name: string;
  entity_type: string;
  properties: Record<string, unknown>;
  memory_ids: string[];
}

export interface EntityRelation {
  source: string;
  target: string;
  type: string;
  weight: number;
}

export interface UnifiedGraphData {
  memories: UnifiedMemory[];
  clusters: Record<string, string[]>;
  cluster_names: Record<string, string>;
  similarity_edges: { source: string; target: string; score: number }[];
  entities?: GraphEntity[];
  entity_relations?: EntityRelation[];
}

export interface MemoryContextData {
  entities: { id: string; name: string; entity_type: string; properties: string; memory_ids: string[] }[];
  relations: { source: string; target: string; type: string; weight: number }[];
  neighbors: { id: string; content: string; source: string; memory_type: string | null }[];
}

export function useUnifiedGraph(similarityThreshold = 0.75, minClusterSize = 3, includeEntities = false) {
  return useQuery<UnifiedGraphData>({
    queryKey: ["unifiedGraph", similarityThreshold, minClusterSize, includeEntities],
    queryFn: () => apiFetch(`/graph/unified?similarity_threshold=${similarityThreshold}&min_cluster_size=${minClusterSize}&include_entities=${includeEntities}`),
  });
}

export function useMemoryContext(memoryId: string | null) {
  return useQuery<MemoryContextData>({
    queryKey: ["memoryContext", memoryId],
    queryFn: () => apiFetch<MemoryContextData>(`/graph/memory-context/${memoryId}`),
    enabled: !!memoryId,
  });
}

export function useFullGraph() {
  return useQuery({
    queryKey: ["fullGraph"],
    queryFn: () => apiFetch<{ entities: unknown[]; relations: unknown[] }>("/graph/full"),
  });
}

export function useGraphEntities(type?: string) {
  return useQuery({
    queryKey: ["graphEntities", type],
    queryFn: () => apiFetch(`/graph/entities${type ? `?entity_type=${type}` : ""}`),
  });
}

export function useVectorProjection() {
  return useQuery({
    queryKey: ["vectorProjection"],
    queryFn: () => apiFetch<{ points: { memory_id: string; x: number; y: number; content: string; source: string; tags: string[]; memory_type: string | null }[] }>("/vectors/projection"),
  });
}

export function useReason() {
  return useMutation({
    mutationFn: (data: { question: string; limit?: number }) =>
      apiFetch<{ answer: string; sources: unknown[] }>("/memories/reason", { method: "POST", body: JSON.stringify(data) }),
  });
}

// ── Knowledge Timeline ────────────────────────────────────────

export interface KnowledgeEntity {
  name: string;
  entity_type: string;
}

export interface KnowledgeTriple {
  id: string;
  subject: string;
  predicate: string;
  object: string;
  valid_from: string | null;
  valid_to: string | null;
  confidence: number;
}

// TODO: wire up once GET /api/v1/graph/knowledge/entities is implemented in the backend
export function useKnowledgeEntities() {
  return useQuery<KnowledgeEntity[]>({
    queryKey: ["knowledgeEntities"],
    queryFn: () => Promise.resolve([] as KnowledgeEntity[]),
    staleTime: 30_000,
  });
}

// TODO: wire up once GET /api/v1/graph/knowledge/timeline is implemented in the backend
export function useKnowledgeTimeline(_entity: string | null, _asOf?: string) {
  return useQuery<KnowledgeTriple[]>({
    queryKey: ["knowledgeTimeline"],
    queryFn: () => Promise.resolve([] as KnowledgeTriple[]),
    enabled: false,
    staleTime: 30_000,
  });
}
