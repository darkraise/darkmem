import {
  useQuery,
  useMutation,
  keepPreviousData,
} from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { useProjectScopedKey } from "@/lib/query-keys"
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"

export interface UnifiedMemory {
  id: string
  content: string
  source: string
  tags: string[]
  memory_type: string | null
  importance: number
  cluster: number
  /** Lifecycle rung. `/graph/unified` has always sent this; the type dropped
   *  it, so no surface could report it. Optional because a node whose payload
   *  predates the field must render as unknown rather than as active. */
  status?: string | null
}

export interface GraphEntity {
  id: string
  name: string
  entity_type: string
  properties: Record<string, unknown>
  memory_ids: string[]
}

export interface EntityRelation {
  source: string
  target: string
  type: string
  weight: number
}

export interface SimilarityEdge {
  source: string
  target: string
  score: number
}

export interface UnifiedGraphData {
  memories: UnifiedMemory[]
  clusters: Record<string, string[]>
  cluster_names: Record<string, string>
  similarity_edges: SimilarityEdge[]
  entities?: GraphEntity[]
  entity_relations?: EntityRelation[]
  /** True when the entity overlay's unscoped, 500-row fetch hit its limit
   *  before the membership filter ran — some relevant entities may be
   *  missing from `entities`/`entity_relations` with no other signal
   *  (F10). Present only when `include_entities` was requested. */
  entities_truncated?: boolean
}

export interface MemoryContextData {
  entities: {
    id: string
    name: string
    entity_type: string
    properties: Record<string, unknown>
    memory_ids: string[]
  }[]
  relations: { source: string; target: string; type: string; weight: number }[]
  neighbors: {
    id: string
    content: string
    source: string
    memory_type: string | null
  }[]
}

// Project-scoped via the query-key layer (src/lib/query-keys.ts, Ruling 1):
// the active project rides both the query key and the request URL, so
// switching projects addresses a fresh cache entry instead of continuing
// to show the previous project's rows while the new project's fetch is
// in flight. The entity-overlay path is not scoped by this same SQL
// pushdown — see app/services/graph.py's _fetch_entity_overlay.
export function useUnifiedGraph(
  similarityThreshold = 0.75,
  minClusterSize = 3,
  includeEntities = false,
) {
  const queryKey = useProjectScopedKey(
    "unifiedGraph",
    similarityThreshold,
    minClusterSize,
    includeEntities,
  )
  const project = useProjectStore((s) => s.activeProject)
  return useQuery<UnifiedGraphData>({
    queryKey,
    // `includeEntities` is part of the key, so toggling the entity layer asks
    // for a different cache entry and `isLoading` would flip true -- swapping
    // the whole page for a skeleton to add an overlay to a graph already on
    // screen. Holding the previous data keeps the graph up while the new
    // shape arrives.
    placeholderData: keepPreviousData,
    queryFn: () =>
      apiFetch(
        `/graph/unified?similarity_threshold=${similarityThreshold}&min_cluster_size=${minClusterSize}&include_entities=${includeEntities}` +
          // Omitted, never sent empty: `project=` would ask for a project
          // *named* the empty string, while an absent param is what the route
          // reads as every project.
          (project === ALL_PROJECTS
            ? ""
            : `&project=${encodeURIComponent(project)}`),
      ),
  })
}

export function useMemoryContext(memoryId: string | null) {
  return useQuery<MemoryContextData>({
    queryKey: ["memoryContext", memoryId],
    queryFn: () =>
      apiFetch<MemoryContextData>(`/graph/memory-context/${memoryId}`),
    enabled: !!memoryId,
  })
}

export function useFullGraph() {
  return useQuery({
    queryKey: ["fullGraph"],
    queryFn: () =>
      apiFetch<{ entities: unknown[]; relations: unknown[] }>("/graph/full"),
  })
}

export function useGraphEntities(type?: string) {
  return useQuery({
    queryKey: ["graphEntities", type],
    queryFn: () =>
      apiFetch(`/graph/entities${type ? `?entity_type=${type}` : ""}`),
  })
}

export function useVectorProjection() {
  return useQuery({
    queryKey: ["vectorProjection"],
    queryFn: () =>
      apiFetch<{
        points: {
          memory_id: string
          x: number
          y: number
          content: string
          source: string
          tags: string[]
          memory_type: string | null
        }[]
      }>("/vectors/projection"),
  })
}

export function useReason() {
  return useMutation({
    mutationFn: (data: { question: string; limit?: number }) =>
      apiFetch<{ answer: string; sources: unknown[] }>("/memories/reason", {
        method: "POST",
        body: JSON.stringify(data),
      }),
  })
}

// ── Knowledge Timeline ────────────────────────────────────────

export interface KnowledgeEntity {
  name: string
  entity_type: string
}

export interface KnowledgeTriple {
  id: string
  subject: string
  predicate: string
  object: string
  valid_from: string | null
  valid_to: string | null
  confidence: number
}

// TODO: wire up once GET /api/v1/graph/knowledge/entities is implemented in the backend
export function useKnowledgeEntities() {
  return useQuery<KnowledgeEntity[]>({
    queryKey: ["knowledgeEntities"],
    queryFn: () => Promise.resolve([] as KnowledgeEntity[]),
    staleTime: 30_000,
  })
}

// TODO: wire up once GET /api/v1/graph/knowledge/timeline is implemented in the backend.
// Key on (entity, asOf) so distinct selections don't collide on one cache entry
// once the queryFn returns real data.
export function useKnowledgeTimeline(entity: string | null, asOf?: string) {
  return useQuery<KnowledgeTriple[]>({
    queryKey: ["knowledgeTimeline", entity, asOf ?? null],
    queryFn: () => Promise.resolve([] as KnowledgeTriple[]),
    enabled: false,
    staleTime: 30_000,
  })
}
