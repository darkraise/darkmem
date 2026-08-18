import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"

/** Doc 12 §4's badge object, on the wire exactly as that doc fixes it.
 *
 *  `claim` is the contract: every consumer shows it **verbatim** or not at
 *  all. Nothing here recomputes or softens it, and no renderer may derive a
 *  sentence of its own from the parts — the parts are present so a screen can
 *  lay them out, never so it can rewrite the claim. */
export interface FactBadge {
  verification_status: string | null
  origin_count: number
  origin_kinds: string[]
  as_of: string | null
  contradiction: boolean
  human_ratified: boolean
  stale: boolean
  claim: string
}

/** The belief axis, which is **independent** of the verification axis
 *  (doc 08 §3). A closed window is retained history, not a withdrawn claim;
 *  a withdrawn claim is `expired_at`. A fact can be well-verified and no
 *  longer current, so a UI that collapses these into one status is describing
 *  a model the system does not have. */
export interface BeliefWindow {
  valid_at: string | null
  invalid_at: string | null
  expired_at: string | null
}

export interface AppliesWhenLabel {
  axis: string
  value: string
}

export interface FactListItem {
  id: string
  id_kind: string
  subject_name: string
  object_name: string
  rel_type: string
  fact: string
  project: string
  verification_status: string | null
  lifecycle: string | null
  badge: FactBadge | null
  /** Doc 07 §5's cold-start label (T2.56): the facts list's own door onto
   *  the same `row_labels` tier the composed read's wire carries. */
  unverified: boolean
  /** T2.95: why a promoted rung was withheld for want of its evidence record,
   *  null when nothing was. Without it a suppressed row and a genuine
   *  `candidate` read identically. */
  label_suppressed: string | null
  confidence: number | null
  review_state: string | null
  /** T2.46's `under-sourced` overlay: non-null means a demotion is pending
   *  and the fact is still `corroborated`. It is served, never withheld. */
  demotion_pending_since: string | null
  belief_window: BeliefWindow
  applies_when: Record<string, unknown> | null
  applies_when_labels: AppliesWhenLabel[]
  created_at: string
}

export interface FactListResponse {
  items: FactListItem[]
  total: number
  limit: number
  offset: number
}

export interface FactListParams {
  project?: string
  subject_name?: string
  rel_type?: string
  object_name?: string
  verification_status?: string
  limit?: number
  offset?: number
}

function factsQueryString(params: FactListParams): string {
  const qs = new URLSearchParams()
  if (params.project) qs.set("project", params.project)
  if (params.subject_name) qs.set("subject_name", params.subject_name)
  if (params.rel_type) qs.set("rel_type", params.rel_type)
  if (params.object_name) qs.set("object_name", params.object_name)
  if (params.verification_status)
    qs.set("verification_status", params.verification_status)
  if (params.limit !== undefined) qs.set("limit", String(params.limit))
  if (params.offset !== undefined) qs.set("offset", String(params.offset))
  return qs.toString()
}

export const FACTS_PAGE_SIZE = 25

/** `GET /knowledge/facts` — doc 13 §5.1's Facts tab substrate, page by page.
 *
 *  **Server-paginated and server-filtered.** `total` is the count behind the
 *  filter, not `items.length`, and a caller that counts the page is reporting
 *  the page size as the corpus — the shape invariant 14 exists to prevent.
 *
 *  Paging is an infinite query over `offset`, not a growing `limit` folded
 *  into the key: a growing limit re-keys the query on every page, so the
 *  already-loaded rows drop to `undefined` and the list unmounts under the
 *  reader. Pages accumulate here instead, and each one is fetched once.
 *
 *  Nothing here filters by verification status by default: absent the
 *  parameter, a candidate, a disputed and a corroborated fact are listed
 *  alike and labelled apart (doc 08 §6's never-a-gate rule). */
/** `GET /knowledge/facts?limit=1`, read for its `total` alone. The dashboard
 *  needs a count per verification status, and `useFactPages` would page rows
 *  in only to discard them — a page of one is the cheapest honest count the
 *  contract offers. */
export function useFactCount(
  params: Omit<FactListParams, "limit" | "offset"> = {},
  options?: { enabled?: boolean },
) {
  const query = factsQueryString({ ...params, limit: 1 })
  return useQuery<FactListResponse>({
    queryKey: ["knowledge", "facts", "count", query],
    queryFn: () => apiFetch<FactListResponse>(`/knowledge/facts?${query}`),
    enabled: options?.enabled ?? true,
  })
}

export function useFactPages(
  params: Omit<FactListParams, "limit" | "offset"> = {},
  options?: { enabled?: boolean },
) {
  const base: FactListParams = { ...params, limit: FACTS_PAGE_SIZE }
  return useInfiniteQuery<FactListResponse>({
    queryKey: ["knowledge", "facts", factsQueryString(base)],
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      apiFetch<FactListResponse>(
        `/knowledge/facts?${factsQueryString({
          ...base,
          offset: pageParam as number,
        })}`,
      ),
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((n, page) => n + page.items.length, 0)
      // An empty page terminates regardless of what `total` says: a total
      // that outruns the rows would otherwise refetch the same offset forever.
      if (last.items.length === 0 || loaded >= last.total) return undefined
      return loaded
    },
    enabled: options?.enabled ?? true,
  })
}

/** `POST /knowledge/facts/{id}/ratify` — the single door to `confirmed`
 *  (doc 08 §4.4, T2.05). Authenticated by the session only; never exposed
 *  over MCP (`app/api/routes/ratification.py`). 204 — the durable record is
 *  the human source row and the recomputed badge, not an echo of either. */
export function useRatifyFact() {
  const qc = useQueryClient()
  return useMutation<void, Error, { factId: string; shown?: string; note?: string }>({
    mutationFn: ({ factId, shown, note }) =>
      apiFetch<void>(`/knowledge/facts/${factId}/ratify`, {
        method: "POST",
        body: shown || note ? JSON.stringify({ shown, note }) : undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["knowledge"] })
      qc.invalidateQueries({ queryKey: ["reviewQueue"] })
    },
  })
}

// ───────────────────────── the fact detail door (T2.86) ─────────────────────────

export interface FactSourceRow {
  id: string
  source_kind: string
  source_ref: string
  detail: Record<string, unknown> | null
  created_at: string
}

/** `fact_sources` pre-grouped by ``origin_key`` server-side (T2.36a) — the
 *  badge's ``origin_count`` audited. ``origin_key: null`` is the merged
 *  unknown-identity bucket; ``unknown_origin`` says so in-band.
 *
 *  The audited number is the count of groups where ``stale`` is false, not the
 *  count of groups: a citation whose recorded code address stopped resolving
 *  (doc 10 §6) is retained and served so a downgraded badge has a visible
 *  cause, but it corroborates nothing. */
export interface FactSourceGroup {
  origin_key: string | null
  unknown_origin: boolean
  stale: boolean
  source_kinds: string[]
  first_seen: string
  last_seen: string
  sources: FactSourceRow[]
}

/** One ``events`` row journalled against this fact (``object_type='fact'``),
 *  via the same ``ix_events_object``-backed reader ``GET /events/timeline``
 *  uses. Oldest-to-newest — the ladder history the demo store used to fake. */
export interface FactLadderEvent {
  id: number
  created_at: string
  event_type: string
  actor: string | null
  payload: Record<string, unknown>
}

/** One claim, in the shape both sides of a dispute are rendered in
 *  (backend ``layer_composition._triple``) — neither side privileged. */
export interface FactDisputeTriple {
  subject: string | null
  rel_type: string | null
  object: string | null
  id: string | null
}

/** ``layer_composition.dispute_label``'s output, verbatim. Present only when
 *  ``verification_status`` is currently ``disputed``. ``counterpart`` is
 *  ``null`` when the veto's finding was never journalled against this fact —
 *  ``counterpart_absent`` names that case rather than leaving it
 *  indistinguishable from "no dispute". The two-sided **sentence** is
 *  `badge.claim`, never re-derived from this block. */
export interface FactDispute {
  review_state: string | null
  claim: FactDisputeTriple
  counterpart: FactDisputeTriple | null
  counterpart_absent: string | null
  rule: string | null
  witness_origin: string | null
  enumeration: string | null
}

export interface FactDetailItem extends FactListItem {
  sources: FactSourceGroup[]
  triple_key: string
  learned_in: string[] | null
  source_file: string | null
  reference_time: string | null
  /** The newest `ladder_total <= 50 ? ladder_total : 50` journal rows,
   *  oldest-to-newest — the most recent transitions, not the earliest ones,
   *  when the full history exceeds the cap. */
  ladder: FactLadderEvent[]
  /** The full journalled count behind `ladder`. Compare the two before
   *  claiming the ladder is complete — a capped list presented as complete
   *  is invariant 14's shape. */
  ladder_total: number
  dispute: FactDispute | null
}

/** `GET /knowledge/facts/{id}` — one fact's full detail (T2.36a shipped the
 *  door, T2.86 is the first caller). `retry: false`: a 404 here is a stable,
 *  legitimate outcome ("this fact does not exist"), not a transient fault
 *  worth the global default's one retry. */
export function useFactDetailQuery(
  factId: string,
  options?: { enabled?: boolean },
) {
  return useQuery<FactDetailItem>({
    queryKey: ["knowledge", "facts", "detail", factId],
    queryFn: () => apiFetch<FactDetailItem>(`/knowledge/facts/${factId}`),
    enabled: options?.enabled ?? true,
    retry: false,
  })
}
