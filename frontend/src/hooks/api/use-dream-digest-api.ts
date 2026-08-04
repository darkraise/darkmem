import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"

/** `GET /dream-digest/cycles` — one row per consolidation cycle. */
export interface DreamCycleSummary {
  cycle_id: string
  started_at: string
  ended_at: string
  projects: string[]
  total: number
  counts: Record<string, number>
  undone_count: number
  // null ⇒ an automated dreaming tick; a value names the human curation
  // surface (e.g. "hygiene_queue") that ran the batch. Homogeneous per cycle.
  origin: string | null
}

export interface DreamCycleListResponse {
  items: DreamCycleSummary[]
  total: number
  limit: number
  offset: number
}

/** One row of `GET /dream-digest/cycles/{cycle_id}`, exactly as the backend
 *  projects it — `app/schemas/dream_digest.py::DreamAction`. Not re-grouped
 *  or re-sorted client-side: journal order is application order. */
export interface DreamAction {
  event_id: number
  created_at: string
  action: string
  object_id: string
  project: string | null
  // Present only for a detector-found action; absent when `origin` is set,
  // because a human curation action is not a detector's finding and
  // rendering "dedup" for it would be a false provenance claim.
  detector: string | null
  origin: string | null
  actor: string | null
  before: Record<string, unknown>
  after: Record<string, unknown>
  detail: Record<string, unknown>
  undone: boolean
  undone_at: string | null
  undone_by: string | null
  undo_batch_id: string | null
  // Advisory only — computed with no locks. The door re-runs the same
  // predicate under its locks and answers 409 on disagreement.
  undoable: boolean
  undo_blocked_reason: string | null
}

export interface DreamObjectGroup {
  object_id: string
  project: string | null
  actions: DreamAction[]
}

export interface DreamCycleDigest {
  cycle_id: string
  started_at: string
  ended_at: string
  counts: Record<string, number>
  undone_count: number
  objects: DreamObjectGroup[]
}

/** Names a subset of a cycle. Whatever set it names is undone in full or not
 *  at all — never silently shrunk to drop an already-undone id. */
export interface UndoRequest {
  action?: string
  event_ids?: number[]
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

export interface DreamCycleListParams {
  project?: string
  since?: string
  until?: string
  limit?: number
  offset?: number
}

function dreamCyclesQueryString(params: DreamCycleListParams): string {
  const qs = new URLSearchParams()
  if (params.project) qs.set("project", params.project)
  if (params.since) qs.set("since", params.since)
  if (params.until) qs.set("until", params.until)
  if (params.limit !== undefined) qs.set("limit", String(params.limit))
  if (params.offset !== undefined) qs.set("offset", String(params.offset))
  return qs.toString()
}

/** `GET /dream-digest/cycles` — doc 13 §6.3's cycle picker substrate. */
export function useDreamCycles(
  params: DreamCycleListParams = {},
  options?: { enabled?: boolean },
) {
  const query = dreamCyclesQueryString(params)
  return useQuery<DreamCycleListResponse>({
    queryKey: ["dreamDigest", "cycles", query],
    queryFn: () =>
      apiFetch<DreamCycleListResponse>(
        `/dream-digest/cycles${query ? `?${query}` : ""}`,
      ),
    enabled: options?.enabled ?? true,
  })
}

/** `GET /dream-digest/cycles/{cycle_id}` — one cycle's actions, grouped by
 *  object, each carrying its own before/after and undo status. */
export function useDreamCycleDigest(
  cycleId: string | null,
  options?: { enabled?: boolean },
) {
  return useQuery<DreamCycleDigest>({
    queryKey: ["dreamDigest", "cycle", cycleId],
    queryFn: () =>
      apiFetch<DreamCycleDigest>(
        `/dream-digest/cycles/${encodeURIComponent(cycleId ?? "")}`,
      ),
    enabled: (options?.enabled ?? true) && cycleId !== null,
  })
}

/** `POST /dream-digest/actions/{event_id}/undo` — the batch of one. There is
 *  no per-action code path behind it; see app/services/dream_undo.py. */
export function useUndoDreamAction() {
  const qc = useQueryClient()
  return useMutation<UndoBatchResponse, Error, number>({
    mutationFn: (eventId) =>
      apiFetch<UndoBatchResponse>(`/dream-digest/actions/${eventId}/undo`, {
        method: "POST",
      }),
    // The backend decides what was and was not restored; re-read rather than
    // patch a local copy, on every settle (success, 409, or anything else) —
    // the caller (use-dream-digest.ts) invalidates unconditionally too, this
    // covers a caller that only awaits the mutateAsync promise.
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["dreamDigest"] })
    },
  })
}

/** `POST /dream-digest/cycles/{cycle_id}/undo` — a named subset (goes
 *  through whole; the primitive decides) or, body-less, whatever is left of
 *  the cycle. */
export function useUndoDreamCycle() {
  const qc = useQueryClient()
  return useMutation<
    UndoBatchResponse,
    Error,
    { cycleId: string; body?: UndoRequest }
  >({
    mutationFn: ({ cycleId, body }) =>
      apiFetch<UndoBatchResponse>(
        `/dream-digest/cycles/${encodeURIComponent(cycleId)}/undo`,
        { method: "POST", body: body ? JSON.stringify(body) : undefined },
      ),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["dreamDigest"] })
    },
  })
}
