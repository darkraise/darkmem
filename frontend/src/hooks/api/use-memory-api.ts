import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

// Mirrors backend MEMORY_STATUS_VALUES (app/models/memory.py). Archival is a
// separate `is_archived` boolean, not a status.
export type MemoryStatus = "active" | "superseded" | "deprecated"

export interface Memory {
  id: string
  content: string
  source: string
  source_agent: string | null
  memory_type: string | null
  importance: number
  metadata: Record<string, unknown>
  technologies?: string[]
  tags: string[]
  created_at: string
  updated_at: string
  expires_at: string | null
  is_archived: boolean
  classified_type?: string | null
  classified_confidence?: number | null
  llm_classified_type?: string | null
  llm_summary?: string | null
  llm_emotions?: string[]
  llm_flags?: string[]
  related_memories?: { memory_id: string; score: number }[]
  rrf_score?: number
  status?: MemoryStatus
  superseded_by?: string | null
}

export interface Tag {
  id: number
  name: string
  category: string | null
  memory_count: number
}

export function useMemories() {
  return useQuery<Memory[]>({
    queryKey: ["memories"],
    queryFn: () =>
      apiFetch("/memories/search", {
        method: "POST",
        body: JSON.stringify({ limit: 50 }),
      }),
  })
}

export function useMemory(id: string) {
  return useQuery<Memory>({
    queryKey: ["memory", id],
    queryFn: () => apiFetch(`/memories/${id}`),
    enabled: !!id,
  })
}

export function useCreateMemory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: {
      content: string
      tags?: string[]
      source?: string
      memory_type?: string
    }) =>
      apiFetch<Memory>("/memories", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memories"] })
      qc.invalidateQueries({ queryKey: ["memoriesPaginated"] })
    },
  })
}

export function useDeleteMemory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/memories/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["memories"] }),
  })
}

export function useSearchMemories() {
  return useMutation({
    mutationFn: (params: {
      query?: string
      tags_any?: string[]
      limit?: number
    }) =>
      apiFetch<Memory[]>("/memories/search", {
        method: "POST",
        body: JSON.stringify(params),
      }),
  })
}

export function useTags() {
  return useQuery<Tag[]>({
    queryKey: ["tags"],
    queryFn: () => apiFetch("/tags"),
  })
}

export interface PaginatedSearchParams {
  query?: string
  tags_any?: string[]
  source?: string
  memory_type?: string
  source_any?: string[]
  memory_type_any?: string[]
  status?: MemoryStatus[]
  limit?: number
  offset?: number
  semantic_weight?: number
}

export interface PaginatedMemories {
  items: Memory[]
  total: number
  limit: number
  offset: number
}

export function usePaginatedSearch(params: PaginatedSearchParams) {
  return useQuery<PaginatedMemories>({
    queryKey: ["memoriesPaginated", params],
    queryFn: () =>
      apiFetch("/memories/search/paginated", {
        method: "POST",
        body: JSON.stringify({
          query: params.query || undefined,
          tags_any: params.tags_any?.length ? params.tags_any : undefined,
          source: params.source || undefined,
          memory_type: params.memory_type || undefined,
          source_any: params.source_any?.length ? params.source_any : undefined,
          memory_type_any: params.memory_type_any?.length
            ? params.memory_type_any
            : undefined,
          // Default to showing both active and superseded so the
          // Memories page doesn't silently hide memories after a
          // REPLACES-supersession runs (the status default on the
          // server is `["active"]`).
          status: params.status ?? ["active", "superseded"],
          limit: params.limit ?? 50,
          offset: params.offset ?? 0,
          semantic_weight: params.semantic_weight,
        }),
      }),
  })
}
