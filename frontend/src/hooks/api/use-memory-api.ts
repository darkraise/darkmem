import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { useProjectScopedKey } from "@/lib/query-keys"
import { useProjectStore } from "@/stores/project-store"

// Mirrors backend MEMORY_STATUS_VALUES (app/models/memory.py). Archival is a
// separate `is_archived` boolean, not a status.
export type MemoryStatus = "active" | "superseded" | "deprecated"

// Mirrors backend RetrievalEnvelope / MemoryResultTrace (app/schemas/retrieval_trace.py,
// T1.33, doc 07 §8). Transient — populated only when a search request sets
// `with_trace: true`, `undefined` otherwise.
export interface ChannelStatus {
  ran: boolean
  failed?: boolean
}

export interface RetrievalEnvelope {
  query: string
  channels: Record<string, ChannelStatus>
  reranked: boolean
  weights: Record<string, number>
  // Real key set is filter-name-shaped (memory_type, source, technologies,
  // tags, not_found) — never by_project/by_status, which SQL pushdown moved
  // out of this code path before it can count them (T1.33 amendment log).
  excluded: Record<string, number>
}

export interface MemoryResultTrace {
  // rrf_score is the sole ordering signal; semantic/keyword/rerank_score are
  // each channel's own raw contribution and must never be read as "the
  // score" (doc 07 §3's trap).
  scores: Record<string, number | null>
  rank_fusion_factor: number
  rank_fusion_breakdown: Record<string, number>
}

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
  summary?: string | null
  emotions?: string[]
  flags?: string[]
  related_memories?: { memory_id: string; score: number }[]
  rrf_score?: number
  status?: MemoryStatus
  superseded_by?: string | null
  // Mirrors backend MemoryResponse.predecessors (T1.47) — the reverse of
  // `superseded_by`: memories this one directly replaced, newest first,
  // bounded server-side. Populated (possibly `[]`, never `null`) only by
  // the single-get doors (GET /memories/{id}); every other reader (search,
  // create, update, batch) leaves this `undefined` — "not computed for
  // this read," a distinct state from "computed, replaced nothing."
  predecessors?: MemoryLineageEntry[]
  // Populated only when the request set `with_trace: true` (T1.33/T1.44).
  trace?: MemoryResultTrace
}

export interface MemoryLineageEntry {
  id: string
  content: string
  created_at: string
  status: MemoryStatus
}

export interface Tag {
  id: number
  name: string
  category: string | null
  memory_count: number
}

// Project-scoped via the query-key layer (src/lib/query-keys.ts, Ruling 1):
// the active project rides both the query key and the request body, so
// switching projects addresses a fresh cache entry instead of continuing
// to show the previous project's rows while the new project's fetch is
// in flight.
export function useMemories() {
  const queryKey = useProjectScopedKey("memories")
  const project = useProjectStore((s) => s.activeProject)
  return useQuery<Memory[]>({
    queryKey,
    queryFn: () =>
      apiFetch("/memories/search", {
        method: "POST",
        // `project: null` is the wire spelling of every project —
        // `MemorySearchRequest.project` is `str | None` and None applies no
        // scope filter, so this needs no special case.
        body: JSON.stringify({ limit: 50, project }),
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

// Mirrors backend CaptureAck (app/schemas/memory.py) — the default 202
// response. `id` is the pre-minted memory id, resolvable once the buffer
// flush lands it; the row is durably buffered whether or not the caller
// waited for it.
export interface CaptureAck {
  schema_version: number
  id: string
  status: "accepted"
  // One warning line naming the signals capture_lint matched; empty for a
  // clean capture. A flagged capture is stored all the same.
  warnings: string[]
}

// POST /memories returns CaptureAck (202) by default, or a full Memory
// (201) when wait_process=true settles inline within the server's
// buffer_wait_timeout_seconds — otherwise it degrades to the plain ack,
// so the row is never lost even when this union resolves to CaptureAck.
export function useCreateMemory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: {
      content: string
      tags?: string[]
      source?: string
      memory_type?: string
      waitProcess?: boolean
    }) => {
      const { waitProcess, ...body } = data
      const query = waitProcess ? "?wait_process=true" : ""
      return apiFetch<CaptureAck | Memory>(`/memories${query}`, {
        method: "POST",
        body: JSON.stringify(body),
      })
    },
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
    // Invalidate both keys here so callers never need a second manual
    // invalidate (a duplicate invalidate of the same key = a duplicate refetch).
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memories"] })
      qc.invalidateQueries({ queryKey: ["memoriesPaginated"] })
    },
  })
}

export interface BulkDeleteResult {
  deleted: number
  not_found: string[]
}

// Deletes many memories in ONE request. The server processes them in series so
// concurrent graph cleanups don't deadlock on shared entity rows — which is why
// looping the single-delete endpoint client-side failed.
export function useBulkDeleteMemory() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ids: string[]) =>
      apiFetch<BulkDeleteResult>("/memories/delete", {
        method: "POST",
        body: JSON.stringify({ ids }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memories"] })
      qc.invalidateQueries({ queryKey: ["memoriesPaginated"] })
    },
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
  project?: string
  tags_any?: string[]
  source?: string
  memory_type?: string
  source_any?: string[]
  memory_type_any?: string[]
  status?: MemoryStatus[]
  limit?: number
  offset?: number
  semantic_weight?: number
  // Attaches the retrieval trace envelope and a per-row trace (T1.33/T1.44).
  // Structurally zero-cost when unset — the caller never pays for it.
  with_trace?: boolean
}

export interface PaginatedMemories {
  items: Memory[]
  total: number
  limit: number
  offset: number
  // Present only when the request set `with_trace: true`.
  envelope?: RetrievalEnvelope
}

export function usePaginatedSearch(
  params: PaginatedSearchParams,
  options?: { enabled?: boolean },
) {
  return useQuery<PaginatedMemories>({
    enabled: options?.enabled ?? true,
    queryKey: ["memoriesPaginated", params],
    queryFn: () =>
      apiFetch("/memories/search/paginated", {
        method: "POST",
        body: JSON.stringify({
          query: params.query || undefined,
          project: params.project || undefined,
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
          with_trace: params.with_trace ?? false,
        }),
      }),
  })
}
