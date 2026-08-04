import { useQuery } from "@tanstack/react-query"

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

/** `GET /knowledge/facts` — doc 13 §5.1's Facts tab substrate.
 *
 *  **Server-paginated and server-filtered.** `total` is the count behind the
 *  filter, not `items.length`, and a caller that counts the page is reporting
 *  the page size as the corpus — the shape invariant 14 exists to prevent.
 *
 *  Nothing here filters by verification status by default: absent the
 *  parameter, a candidate, a disputed and a corroborated fact are listed
 *  alike and labelled apart (doc 08 §6's never-a-gate rule). */
export function useFacts(
  params: FactListParams = {},
  options?: { enabled?: boolean },
) {
  const query = factsQueryString(params)
  return useQuery<FactListResponse>({
    queryKey: ["knowledge", "facts", query],
    queryFn: () =>
      // No `/api/v1` here: `apiFetch` prepends the base itself, and a path
      // that spells it resolves to `/api/v1/api/v1/...` — every request 404s.
      apiFetch<FactListResponse>(
        `/knowledge/facts${query ? `?${query}` : ""}`,
      ),
    enabled: options?.enabled ?? true,
  })
}
