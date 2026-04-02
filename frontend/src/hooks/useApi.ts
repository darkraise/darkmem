import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface Memory {
  id: string;
  content: string;
  source: string;
  source_agent: string | null;
  memory_type: string | null;
  importance: number;
  metadata: Record<string, unknown>;
  tags: string[];
  created_at: string;
  updated_at: string;
  expires_at: string | null;
  is_archived: boolean;
}

export interface Tag {
  id: number;
  name: string;
  category: string | null;
  memory_count: number;
}

export interface Stats {
  memories: number;
  tags: number;
  entities: number | null;
  relationships: number | null;
  sources: string[];
}

export interface LlmPurposeConfig {
  provider: string;
  base_url: string;
  model: string;
  api_key: string | null;
  dimensions: number | null;
  params: Record<string, unknown>;
}

export interface LlmConfigResponse {
  embedding?: LlmPurposeConfig;
  extraction?: LlmPurposeConfig;
  reasoning?: LlmPurposeConfig;
  summarization?: LlmPurposeConfig;
}

export interface SystemPromptProfile {
  name: string;
  display_name: string;
  is_default: boolean;
  extraction_depth: string;
}

export function useMemories() {
  return useQuery<Memory[]>({
    queryKey: ["memories"],
    queryFn: () => apiFetch("/memories/search", { method: "POST", body: JSON.stringify({ limit: 50 }) }),
  });
}

export function useMemory(id: string) {
  return useQuery<Memory>({
    queryKey: ["memory", id],
    queryFn: () => apiFetch(`/memories/${id}`),
    enabled: !!id,
  });
}

export function useCreateMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { content: string; tags?: string[]; source?: string }) =>
      apiFetch<Memory>("/memories", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["memories"] }),
  });
}

export function useDeleteMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch(`/memories/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["memories"] }),
  });
}

export function useSearchMemories() {
  return useMutation({
    mutationFn: (params: { query?: string; tags_any?: string[]; limit?: number }) =>
      apiFetch<Memory[]>("/memories/search", { method: "POST", body: JSON.stringify(params) }),
  });
}

export function useTags() {
  return useQuery<Tag[]>({ queryKey: ["tags"], queryFn: () => apiFetch("/tags") });
}

export function useStats() {
  return useQuery<Stats>({ queryKey: ["stats"], queryFn: () => apiFetch("/analytics/stats") });
}

export interface HealthStatus {
  status: string;
  pipeline: boolean;
  services: { qdrant: boolean; neo4j: boolean; llm: boolean };
}

export interface PipelineLog {
  id: number;
  memory_id: string | null;
  details: Record<string, unknown>;
  timestamp: string;
}

export function useHealth() {
  return useQuery<HealthStatus>({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/health");
      return res.json();
    },
    refetchInterval: 30000,
  });
}

export function usePipelineLogs(limit = 10) {
  return useQuery<PipelineLog[]>({
    queryKey: ["pipelineLogs", limit],
    queryFn: () => apiFetch(`/analytics/pipeline-logs?limit=${limit}`),
  });
}

export function useReprocessAll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<{ processed: number; errors: number; total: number }>("/analytics/reprocess", { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipelineLogs"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });
}

export function useReprocessFailed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<{ processed: number; errors: number; total: number }>("/analytics/reprocess-failed", { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipelineLogs"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });
}

export function useLlmConfig() {
  return useQuery<LlmConfigResponse>({
    queryKey: ["llmConfig"],
    queryFn: () => apiFetch<LlmConfigResponse>("/config/llm"),
  });
}

export function useUpdateLlmConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      apiFetch("/config/llm", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["llmConfig"] }),
  });
}

export function useSystemPrompts() {
  return useQuery<SystemPromptProfile[]>({
    queryKey: ["systemPrompts"],
    queryFn: () => apiFetch<SystemPromptProfile[]>("/config/system-prompt/list"),
  });
}

export function useGraphEntities(type?: string) {
  return useQuery({
    queryKey: ["graphEntities", type],
    queryFn: () => apiFetch(`/graph/entities${type ? `?entity_type=${type}` : ""}`),
  });
}

export function useFullGraph() {
  return useQuery({
    queryKey: ["fullGraph"],
    queryFn: () => apiFetch<{ entities: unknown[]; relations: unknown[] }>("/graph/full"),
  });
}

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

export function useUnifiedGraph(similarityThreshold = 0.75, clusterMinScore = 0.5, minClusterSize = 3, includeEntities = false) {
  return useQuery<UnifiedGraphData>({
    queryKey: ["unifiedGraph", similarityThreshold, clusterMinScore, minClusterSize, includeEntities],
    queryFn: () => apiFetch(`/graph/unified?similarity_threshold=${similarityThreshold}&cluster_min_score=${clusterMinScore}&min_cluster_size=${minClusterSize}&include_entities=${includeEntities}`),
  });
}

export interface MemoryContextData {
  entities: { id: string; name: string; entity_type: string; properties: string; memory_ids: string[] }[];
  relations: { source: string; target: string; type: string; weight: number }[];
  neighbors: { id: string; content: string; source: string; memory_type: string | null }[];
}

export function useMemoryContext(memoryId: string | null) {
  return useQuery<MemoryContextData>({
    queryKey: ["memoryContext", memoryId],
    queryFn: () => apiFetch<MemoryContextData>(`/graph/memory-context/${memoryId}`),
    enabled: !!memoryId,
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
