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

export interface HygieneCountsResponse {
  duplicates: number
  low_confidence: number
  expiring_soon: number
  superseded: number
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
    queryFn: () =>
      apiFetch<HygieneDuplicateListResponse>(
        `/hygiene-queue/duplicates${query ? `?${query}` : ""}`,
      ),
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
    queryFn: () =>
      apiFetch<HygieneMemoryListResponse>(
        `/hygiene-queue/low-confidence${query ? `?${query}` : ""}`,
      ),
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
    queryFn: () =>
      apiFetch<HygieneMemoryListResponse>(
        `/hygiene-queue/expiring-soon${query ? `?${query}` : ""}`,
      ),
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
    queryFn: () =>
      apiFetch<HygieneMemoryListResponse>(
        `/hygiene-queue/superseded${query ? `?${query}` : ""}`,
      ),
    enabled: options?.enabled ?? true,
    placeholderData: keepPreviousData,
  })
}

export function useHygieneCounts(
  params: { project?: string; threshold?: number; within_days?: number } = {},
  options?: { enabled?: boolean },
) {
  const query = hygieneQueryString(params)
  return useQuery<HygieneCountsResponse>({
    queryKey: ["hygieneQueue", "counts", query],
    queryFn: () =>
      apiFetch<HygieneCountsResponse>(
        `/hygiene-queue/counts${query ? `?${query}` : ""}`,
      ),
    enabled: options?.enabled ?? true,
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

export interface UndoneAction {
  event_id: number
  action: string
  object_id: string
  restored: string[]
  not_restored: string[]
}

export interface UndoBatchResponse {
  undo_batch_id: string
  undone: UndoneAction[]
}

/** `POST /dream-digest/cycles/{cycle_id}/undo`, body-less form — undoes every
 *  not-yet-undone action in the named cycle (`app/api/routes/dream_digest.py`).
 *  A hygiene bulk action's own `cycle_id` is exactly such a cycle (doc 08 §7's
 *  intended unification), so this is the batch's real undo door — not a new
 *  one invented for this surface. */
export function useUndoCycle() {
  const qc = useQueryClient()
  return useMutation<UndoBatchResponse, Error, string>({
    mutationFn: (cycleId) =>
      apiFetch<UndoBatchResponse>(`/dream-digest/cycles/${cycleId}/undo`, {
        method: "POST",
      }),
    onSuccess: () => invalidateHygiene(qc),
  })
}
