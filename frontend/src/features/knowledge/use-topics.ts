import { useCallback, useMemo } from "react"

import { DEMO } from "@/lib/demo-flag"
import {
  useDemoCommunities,
  useDemoLastDetectionRun,
  useDemoPinSuggestions,
} from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type { DemoCommunity, DemoPinSuggestion } from "@/demo/types"
import {
  useAcceptPinSuggestion,
  useDismissPinSuggestion,
  usePinSuggestionsQuery,
  useTopicsQuery,
  type PinSuggestionItem,
  type TopicDiffItem,
  type TopicItem,
} from "@/hooks/api"

/** The one row shape the Topics tab renders, whichever source fed it —
 *  the same two-producers-one-shape discipline `use-facts.ts` carries, so
 *  the surface has a single render path and a demo-only field cannot
 *  quietly become load-bearing. */
export interface TopicRowData {
  /** The label *is* the identity. Community ids churn on every detection
   *  rewrite (doc 06 §7), so nothing here — key, decision, or diff lookup —
   *  may key on one. */
  label: string
  memberCount: number
  dominantEntities: string[]
  /** Carried verbatim from the backend's four-value classification. */
  reportStatus: string
  report: string | null
  impact: string | null
}

export interface PinSuggestionRowData {
  subjectKey: string
  subject: string
  supportingCommunity: string
  why: string
  memberCount: number
  anchoredFactCount: number
  decision: "accepted" | "dismissed" | null
}

/** What changed between the last two detection runs, per label. Empty until
 *  a project has been detected twice — which is a statement about that
 *  project, not a permanent property of the door (T2.91). */
export interface TopicDiffRowData {
  label: string
  status: string
  memberCount: number
  priorMemberCount: number | null
}

function entityNames(entities: Array<Record<string, unknown>>): string[] {
  return entities
    .map((entity) => {
      const display = entity.display_name ?? entity.name
      return typeof display === "string" ? display : ""
    })
    .filter(Boolean)
}

/** `impact_rating` is a number the backend computed; the tab shows a word.
 *  The banding lives here rather than in the component so both producers
 *  render one vocabulary, and a null rating stays null rather than becoming
 *  a band it did not earn. */
export function impactBand(rating: number | null): string | null {
  if (rating == null) return null
  if (rating >= 0.66) return "high"
  if (rating >= 0.33) return "medium"
  return "low"
}

function fromApiTopic(item: TopicItem): TopicRowData {
  return {
    label: item.label,
    memberCount: item.member_count,
    dominantEntities: entityNames(item.dominant_entities),
    reportStatus: item.report_status,
    report: item.report,
    impact: impactBand(item.impact_rating),
  }
}

function fromDemoTopic(community: DemoCommunity): TopicRowData {
  return {
    label: community.label,
    memberCount: community.member_count,
    dominantEntities: community.dominant_entities,
    reportStatus: community.report ? "ready" : "pending",
    report: community.report,
    impact: community.impact,
  }
}

function fromApiSuggestion(
  item: PinSuggestionItem,
  pinned: Set<string>,
  dismissed: Set<string>,
): PinSuggestionRowData {
  return {
    subjectKey: item.subject_key,
    subject: item.dominant_name,
    supportingCommunity: item.label,
    why: item.why,
    memberCount: item.member_count,
    anchoredFactCount: item.verified_fact_count,
    decision: pinned.has(item.subject_key)
      ? "accepted"
      : dismissed.has(item.subject_key)
        ? "dismissed"
        : null,
  }
}

function fromDemoSuggestion(
  suggestion: DemoPinSuggestion,
): PinSuggestionRowData {
  return {
    subjectKey: suggestion.id,
    subject: suggestion.subject,
    supportingCommunity: suggestion.supporting_community,
    why: suggestion.reason,
    memberCount: suggestion.member_count,
    anchoredFactCount: suggestion.anchored_fact_count,
    decision: suggestion.decision,
  }
}

function fromApiDiff(item: TopicDiffItem): TopicDiffRowData {
  return {
    label: item.label,
    status: item.status,
    memberCount: item.member_count,
    priorMemberCount: item.prior_member_count,
  }
}

export interface TopicsView {
  topics: TopicRowData[]
  suggestions: PinSuggestionRowData[]
  diff: TopicDiffRowData[]
  lastRun: string | null
  loading: boolean
  error: Error | null
  decide: (subjectKey: string, decision: "accepted" | "dismissed") => void
}

export function useTopics(project: string): TopicsView {
  const demoCommunities = useDemoCommunities()
  const demoSuggestions = useDemoPinSuggestions()
  const demoLastRun = useDemoLastDetectionRun()
  const demoDecide = useDemoStore((s) => s.decidePinSuggestion)

  const topicsApi = useTopicsQuery(project, { enabled: !DEMO })
  const pinsApi = usePinSuggestionsQuery(project, { enabled: !DEMO })
  const accept = useAcceptPinSuggestion()
  const dismiss = useDismissPinSuggestion()

  const topics = useMemo(
    () =>
      DEMO
        ? demoCommunities.map(fromDemoTopic)
        : (topicsApi.data?.items ?? []).map(fromApiTopic),
    [demoCommunities, topicsApi.data],
  )

  const suggestions = useMemo(() => {
    if (DEMO) return demoSuggestions.map(fromDemoSuggestion)
    const body = pinsApi.data
    if (!body) return []
    const pinned = new Set(body.pinned_subject_keys)
    const dismissed = new Set(body.dismissed_subject_keys)
    return body.suggestions.map((item) =>
      fromApiSuggestion(item, pinned, dismissed),
    )
  }, [demoSuggestions, pinsApi.data])

  const diff = useMemo(
    () => (DEMO ? [] : (pinsApi.data?.diff ?? []).map(fromApiDiff)),
    [pinsApi.data],
  )

  const decide = useCallback(
    (subjectKey: string, decision: "accepted" | "dismissed") => {
      if (DEMO) {
        demoDecide(subjectKey, decision)
        return
      }
      const mutation = decision === "accepted" ? accept : dismiss
      mutation.mutate({ project, subjectKey })
    },
    [accept, demoDecide, dismiss, project],
  )

  return {
    topics,
    suggestions,
    diff,
    // The demo fixture states a last-run timestamp; the live doors do not
    // serve one, and inventing a plausible time is exactly the kind of thing
    // this epic's honesty rule forbids. Null renders as "not reported".
    lastRun: DEMO ? demoLastRun : null,
    loading: DEMO ? false : topicsApi.isLoading || pinsApi.isLoading,
    error: DEMO ? null : ((topicsApi.error ?? pinsApi.error) as Error | null),
    decide,
  }
}
