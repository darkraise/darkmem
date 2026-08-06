import { useMutation, useQuery, useQueryClient, keepPreviousData } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

/** T2.24's per-item ranking rationale (doc 08 §6). Structural, not decorative
 *  — the score is the sum of the two arms' `component` values, so a reader
 *  can reproduce the total from the parts. No prose field rides the wire
 *  here; any sentence a consumer shows is that consumer's own readout of
 *  these numbers, never a second copy of a backend-authored claim (there is
 *  none to duplicate). */
export interface ConsequenceFrequency {
  source_memories: number
  peak_access_count: number
  last_accessed: string | null
  decayed_access: number
  half_life_days: number
  weight: number
  component: number
}

export interface ConsequenceSalience {
  neighbour_count: number
  weight: number
  component: number
}

export interface ConsequenceStaleness {
  stale: boolean
  label: string
  dispute_opened_at: string | null
  dispute_age_days: number | null
  threshold_days: number
}

export interface ConsequenceExplanation {
  score: number
  tier: number
  retrieval_frequency: ConsequenceFrequency
  subject_salience: ConsequenceSalience
  staleness: ConsequenceStaleness
}

/** The counterpart triple a contradiction veto turned on (T2.64). Names the
 *  finding that decided the verdict, never the complete set of contradictions
 *  standing against the fact — `enumeration` says so in-band. */
export interface VerifiedEvidenceContradiction {
  counterpart_id: string
  counterpart_subject: string
  counterpart_rel_type: string
  counterpart_object: string
  rule: string
  witness_origin: string
  enumeration: string
}

/** The `verified` journal payload, best-effort (doc 07 §5, T2.43). Absent
 *  fields mean "this transition did not carry that evidence", not "unknown
 *  value" — see `app/repositories/knowledge_triples.py`'s conditional
 *  payload assembly. */
// `label_suppressed` rides inside the transition objects rather than beside
// them: the backend gates each embedded rung independently, so a payload can
// carry a withheld `after` next to a `before` that needed no gating. Reading
// it at the payload level would flatten that apart.
export interface VerifiedEvidenceTransition {
  verification_status: string | null
  label_suppressed?: string | null
}

export interface VerifiedEvidencePayload {
  before?: VerifiedEvidenceTransition
  after?: VerifiedEvidenceTransition
  outcome?: string
  origin_count?: number
  required_n?: number
  gate_fired?: string | null
  source_kinds?: string[]
  contradiction_blocked?: boolean
  supersession_blocked?: boolean
  confidence?: number | null
  contradiction?: VerifiedEvidenceContradiction | null
}

export interface VerifiedEvidence {
  payload: VerifiedEvidencePayload
  recorded_at: string
}

export interface ReviewQueueFactItem {
  id: string
  subject_name: string
  object_name: string
  rel_type: string
  fact: string
  project: string
  valid_at: string | null
  invalid_at: string | null
  expired_at: string | null
  verification_status: string
  /** T2.95: why a promoted rung was withheld for want of its evidence record,
   *  null when nothing was. The queue serves the gated rung like every other
   *  labelled door. */
  label_suppressed: string | null
  confidence: number | null
  review_state: string | null
  demotion_pending_since: string | null
  reason: string
  evidence: VerifiedEvidence | null
  consequence: ConsequenceExplanation | null
  created_at: string
}

export interface ReviewQueueFactListResponse {
  items: ReviewQueueFactItem[]
  total: number
  limit: number
  offset: number
}

export interface ReviewQueueArticleItem {
  id: string
  subject_key: string
  project: string
  title: string | null
  status: string
  confidence: number | null
  fact_set_hash: string | null
  review_state: string | null
  reason: string
  content_preview: string | null
  synthesized_at: string | null
  created_at: string
}

export interface ReviewQueueArticleListResponse {
  items: ReviewQueueArticleItem[]
  total: number
  limit: number
  offset: number
}

export interface ReviewQueueCountsResponse {
  facts: number
  articles: number
}

export interface ReviewQueueListParams {
  project?: string
  limit?: number
  offset?: number
}

function reviewQueueQueryString(params: ReviewQueueListParams): string {
  const qs = new URLSearchParams()
  if (params.project) qs.set("project", params.project)
  if (params.limit !== undefined) qs.set("limit", String(params.limit))
  if (params.offset !== undefined) qs.set("offset", String(params.offset))
  return qs.toString()
}

export function useReviewQueueFacts(
  params: ReviewQueueListParams = {},
  options?: { enabled?: boolean },
) {
  const query = reviewQueueQueryString(params)
  return useQuery<ReviewQueueFactListResponse>({
    queryKey: ["reviewQueue", "facts", query],
    queryFn: () =>
      apiFetch<ReviewQueueFactListResponse>(
        `/review-queue/facts${query ? `?${query}` : ""}`,
      ),
    enabled: options?.enabled ?? true,
    placeholderData: keepPreviousData,
  })
}

export function useReviewQueueArticles(
  params: ReviewQueueListParams = {},
  options?: { enabled?: boolean },
) {
  const query = reviewQueueQueryString(params)
  return useQuery<ReviewQueueArticleListResponse>({
    queryKey: ["reviewQueue", "articles", query],
    queryFn: () =>
      apiFetch<ReviewQueueArticleListResponse>(
        `/review-queue/articles${query ? `?${query}` : ""}`,
      ),
    enabled: options?.enabled ?? true,
    placeholderData: keepPreviousData,
  })
}

export function useReviewQueueCounts(
  params: { project?: string } = {},
  options?: { enabled?: boolean },
) {
  const query = reviewQueueQueryString(params)
  return useQuery<ReviewQueueCountsResponse>({
    queryKey: ["reviewQueue", "counts", query],
    queryFn: () =>
      apiFetch<ReviewQueueCountsResponse>(
        `/review-queue/counts${query ? `?${query}` : ""}`,
      ),
    enabled: options?.enabled ?? true,
  })
}

/** `POST /review-queue/facts/{id}/reject` — the review queue's one action
 *  door (T2.63). 204: the durable record is the journal entry, not an echo.
 *  Withdraws belief; touches neither `verification_status` nor
 *  `review_state` (see `app/services/human_adjudication.py`). */
export function useRejectFact() {
  const qc = useQueryClient()
  return useMutation<void, Error, { factId: string; note?: string }>({
    mutationFn: ({ factId, note }) =>
      apiFetch<void>(`/review-queue/facts/${factId}/reject`, {
        method: "POST",
        body: note ? JSON.stringify({ note }) : undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["reviewQueue"] })
      qc.invalidateQueries({ queryKey: ["knowledge"] })
    },
  })
}
