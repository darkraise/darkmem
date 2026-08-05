import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"

/** The topics read surface and the pin-suggestion door (doc 09 §3, T2.39a's
 *  routes). Every shape here mirrors `app/schemas/topics.py` exactly; nothing
 *  is composed or renamed on the way in. */

export interface TopicItem {
  project: string
  label: string
  dominant_entities: Array<Record<string, unknown>>
  impact_rating: number | null
  member_count: number
  /** `ready` | `pending` | `failed` | `skipped`. Never collapsed into
   *  `report != null`: the backend distinguishes "not generated yet" from
   *  "will never be generated" from "an attempt failed", and a surface that
   *  re-derives the state from the text loses two of the four. */
  report_status: string
  report: string | null
}

export interface TopicListResponse {
  items: TopicItem[]
}

/** One entry of the cross-run diff. `status` is `new` | `grown` | `stable` |
 *  `decayed`; since T2.91 all four are reachable, because the detector
 *  persists its pre-rewrite census and the door diffs against it. */
export interface TopicDiffItem {
  project: string
  label: string
  status: string
  dominant_name: string | null
  dominant_entity_type: string | null
  member_count: number
  prior_member_count: number | null
}

export interface PinSuggestionItem {
  project: string
  subject_key: string
  dominant_name: string
  dominant_entity_type: string
  label: string
  why: string
  member_count: number
  verified_fact_count: number
}

export interface PinSuggestionsResponse {
  diff: TopicDiffItem[]
  suggestions: PinSuggestionItem[]
  pinned_subject_keys: string[]
  dismissed_subject_keys: string[]
}

export function useTopicsQuery(project: string, options?: { enabled?: boolean }) {
  return useQuery<TopicListResponse>({
    queryKey: ["knowledge", "topics", project],
    queryFn: () =>
      apiFetch<TopicListResponse>(
        `/knowledge/topics?project=${encodeURIComponent(project)}`,
      ),
    enabled: options?.enabled ?? true,
  })
}

export function usePinSuggestionsQuery(
  project: string,
  options?: { enabled?: boolean },
) {
  return useQuery<PinSuggestionsResponse>({
    queryKey: ["knowledge", "topics", "pin-suggestions", project],
    queryFn: () =>
      apiFetch<PinSuggestionsResponse>(
        `/knowledge/topics/pin-suggestions?project=${encodeURIComponent(project)}`,
      ),
    enabled: options?.enabled ?? true,
  })
}

/** Accept and dismiss are one hook parameterised by the verb, not two
 *  copies. Both are 204 doors taking the same body, and the only thing that
 *  differs is which durable list the subject joins — writing them twice is
 *  how the two drift into different invalidation sets. */
function usePinDecision(verb: "accept" | "dismiss") {
  const qc = useQueryClient()
  return useMutation<void, Error, { project: string; subjectKey: string; label?: string }>({
    mutationFn: ({ project, subjectKey, label }) =>
      apiFetch<void>(`/knowledge/topics/pin-suggestions/${verb}`, {
        method: "POST",
        body: JSON.stringify({
          project,
          subject_key: subjectKey,
          ...(label ? { label } : {}),
        }),
      }),
    // The decision changes what the *next* read of the suggestion list
    // returns — the gate reads the durable pinned/dismissed sets — so the
    // list is refetched rather than patched locally. A local patch would
    // show a decision the server may not have recorded.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["knowledge", "topics"] })
    },
  })
}

export function useAcceptPinSuggestion() {
  return usePinDecision("accept")
}

export function useDismissPinSuggestion() {
  return usePinDecision("dismiss")
}
