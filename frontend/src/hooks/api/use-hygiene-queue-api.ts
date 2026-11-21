import { useMutation, useQuery, useQueryClient, keepPreviousData } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

export interface HygieneDuplicateItem {
  id: string
  source_memory_id: string
  target_memory_id: string
  rel_type: string
  project: string
  score: number | null
  verdict: string | null
  hygiene_state: string | null
  detected_at: string | null
  created_at: string
  // Which endpoint is older cannot be told from an id and a score alone
  // (T2.87) — a supersede direction needs each side's own preview and
  // created_at, truncated the same way hygiene_queue_memories' is.
  source_content_preview: string
  source_created_at: string
  target_content_preview: string
  target_created_at: string
}

export interface HygieneDuplicateListResponse {
  items: HygieneDuplicateItem[]
  total: number
  limit: number
  offset: number
}

export interface HygieneMemoryItem {
  id: string
  project: string
  content_preview: string
  confidence: number | null
  expires_at: string | null
  status: string
  superseded_by: string | null
  reason: string
  created_at: string
}

export interface HygieneMemoryListResponse {
  items: HygieneMemoryItem[]
  total: number
  limit: number
  offset: number
}

export interface HygieneActionItemResult {
  id: string
  applied: boolean
  event_id: number | null
  reason: string | null
}

/** Every bulk-action door mints one `cycle_id` per request (doc 08 §7) — the
 *  same shape one dreaming tick shares — so the whole batch undoes through
 *  `POST /dream-digest/cycles/{cycle_id}/undo` with no per-item plumbing. */
export interface HygieneBulkActionResponse {
  cycle_id: string
  results: HygieneActionItemResult[]
}

export interface HygieneListParams {
  project?: string
  limit?: number
  offset?: number
}

function hygieneQueryString(params: {
  project?: string
  limit?: number
  offset?: number
  threshold?: number
  within_days?: number
}): string {
  const qs = new URLSearchParams()
  if (params.project) qs.set("project", params.project)
  if (params.limit !== undefined) qs.set("limit", String(params.limit))
  if (params.offset !== undefined) qs.set("offset", String(params.offset))
  if (params.threshold !== undefined) qs.set("threshold", String(params.threshold))
  if (params.within_days !== undefined) qs.set("within_days", String(params.within_days))
  return qs.toString()
}

export function useHygieneDuplicates(
  params: HygieneListParams = {},
  options?: { enabled?: boolean },
) {
  const query = hygieneQueryString(params)
  return useQuery<HygieneDuplicateListResponse>({
    queryKey: ["hygieneQueue", "duplicates", query],
    queryFn: ({ signal }) =>
      apiFetch<HygieneDuplicateListResponse>(
        `/hygiene-queue/duplicates${query ? `?${query}` : ""}`, { signal }),
    enabled: options?.enabled ?? true,
    placeholderData: keepPreviousData,
  })
}

export function useHygieneLowConfidence(
  params: HygieneListParams & { threshold?: number } = {},
  options?: { enabled?: boolean },
) {
  const query = hygieneQueryString(params)
  return useQuery<HygieneMemoryListResponse>({
    queryKey: ["hygieneQueue", "lowConfidence", query],
    queryFn: ({ signal }) =>
      apiFetch<HygieneMemoryListResponse>(
        `/hygiene-queue/low-confidence${query ? `?${query}` : ""}`, { signal }),
    enabled: options?.enabled ?? true,
    placeholderData: keepPreviousData,
  })
}

export function useHygieneExpiringSoon(
  params: HygieneListParams & { within_days?: number } = {},
  options?: { enabled?: boolean },
) {
  const query = hygieneQueryString(params)
  return useQuery<HygieneMemoryListResponse>({
    queryKey: ["hygieneQueue", "expiringSoon", query],
    queryFn: ({ signal }) =>
      apiFetch<HygieneMemoryListResponse>(
        `/hygiene-queue/expiring-soon${query ? `?${query}` : ""}`, { signal }),
    enabled: options?.enabled ?? true,
    placeholderData: keepPreviousData,
  })
}

export function useHygieneSuperseded(
  params: HygieneListParams = {},
  options?: { enabled?: boolean },
) {
  const query = hygieneQueryString(params)
  return useQuery<HygieneMemoryListResponse>({
    queryKey: ["hygieneQueue", "superseded", query],
    queryFn: ({ signal }) =>
      apiFetch<HygieneMemoryListResponse>(
        `/hygiene-queue/superseded${query ? `?${query}` : ""}`, { signal }),
    enabled: options?.enabled ?? true,
    placeholderData: keepPreviousData,
  })
}

function invalidateHygiene(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: ["hygieneQueue"] })
}

/** `POST /hygiene-queue/bulk/confirm-dedup` — the one bulk action with an
 *  unambiguous backend door: it rewrites the existing `near_duplicate`
 *  pass-block, changing only `hygiene_state`. Journalled as `ACTION_ASSOCIATE`
 *  (`app/services/hygiene_queue.py`), so the returned `cycle_id` is undoable
 *  through the dream-digest cycle-undo door. */
export function useBulkConfirmDedup() {
  const qc = useQueryClient()
  return useMutation<HygieneBulkActionResponse, Error, string[]>({
    mutationFn: (relationIds) =>
      apiFetch<HygieneBulkActionResponse>("/hygiene-queue/bulk/confirm-dedup", {
        method: "POST",
        body: JSON.stringify({ relation_ids: relationIds }),
      }),
    onSuccess: () => invalidateHygiene(qc),
  })
}

export interface HygieneSupersedeItem {
  memory_id: string
  superseded_by: string
}

/** `POST /hygiene-queue/bulk/supersede` — the direction-aware duplicate
 *  resolution T2.87 wires up: each item names the older memory
 *  (`memory_id`) and the newer one that replaces it (`superseded_by`).
 *  Reuses `ACTION_SUBSUME` through `supersede()`, so it is undoable the
 *  same way `prune` is. Refuses (per-item) `cross_project`,
 *  `self_reference` or `successor_not_newer` if the caller's chosen
 *  direction does not actually hold — the backend is the final arbiter,
 *  not the row ordering this surface displays. */
export function useBulkSupersede() {
  const qc = useQueryClient()
  return useMutation<HygieneBulkActionResponse, Error, HygieneSupersedeItem[]>({
    mutationFn: (items) =>
      apiFetch<HygieneBulkActionResponse>("/hygiene-queue/bulk/supersede", {
        method: "POST",
        body: JSON.stringify({ items }),
      }),
    onSuccess: () => invalidateHygiene(qc),
  })
}

/** `POST /hygiene-queue/bulk/prune` — retires with no successor
 *  (`deprecate()`), never a hard delete (doc 01 F6). Reuses `ACTION_SUBSUME`,
 *  so it is undoable the same way `supersede` is. Refuses (per-item, not
 *  batch-wide) any memory whose `status` is not `active` — an already
 *  `superseded` row is not a valid target, which is why the Superseded
 *  lineage arm does not offer this action (see `hygiene-queue.tsx`). */
export function useBulkPrune() {
  const qc = useQueryClient()
  return useMutation<HygieneBulkActionResponse, Error, string[]>({
    mutationFn: (memoryIds) =>
      apiFetch<HygieneBulkActionResponse>("/hygiene-queue/bulk/prune", {
        method: "POST",
        body: JSON.stringify({ memory_ids: memoryIds }),
      }),
    onSuccess: () => invalidateHygiene(qc),
  })
}

// The batch's real undo door is `POST /dream-digest/cycles/{cycle_id}/undo`
// (doc 08 §7's intended unification, body-less form) — the exact same door
// the dream-digest surface uses, so it is `useUndoDreamCycle` from
// `use-dream-digest-api.ts`, not a hygiene-owned duplicate. A separate hook
// here previously invalidated only `hygieneQueue`, leaving a dream-digest
// viewer's cache stale after a hygiene-triggered undo (F9).
