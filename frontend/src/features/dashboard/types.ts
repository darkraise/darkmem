import type { KnowledgeLayer, VerificationStatus } from "@/components/darkmem"

// Relocated out of src/demo/types.ts by T1.68: real data populates these
// (fillCalendarDays in ./calendar.ts builds ContributionDay[] straight from
// GET /events/calendar in real mode), so they are not demo fixture shapes —
// see the task's report for the full per-type evidence trail.

export interface ContributionTypeCount {
  label: string
  count: number
}

export interface ContributionDay {
  /** Local calendar day, YYYY-MM-DD. */
  date: string
  count: number
  /** Per-memory_type breakdown, count desc — popover detail. Always empty
   *  in real mode: /events/calendar carries no per-type breakdown. */
  types: ContributionTypeCount[]
  /** Rows carrying a corroborated/confirmed verification badge. */
  verified: number
  /** Inject records journalled on this day (T3.20, doc 13 §6.5). A separate
   *  server-side series rather than a slice of `count`: the human can always
   *  see what the agent was told, and the calendar is the entry point to the
   *  day where it is shown in full. */
  injects: number
}

// Relocated out of src/demo/types.ts on 2026-08-18, on T1.68's own rule:
// real code is load-bearing on these now. `use-dashboard-stats.ts` and
// `use-dashboard-activity.ts` build both shapes straight from the API, so
// they stopped being demo fixture shapes the moment the dashboard stopped
// reading the fixture store.

export interface DashboardStats {
  totalMemories: number
  verifiedFacts: number
  liveArticles: number
  pendingReview: number
  disputedFacts: number
}

export type ActivityEventKind =
  | "memory"
  | "fact"
  | "article"
  | "pipeline"
  | "job"
  | "review"

export interface ActivityEvent {
  id: string
  kind: ActivityEventKind
  title: string
  detail?: string
  /** Demo-only today: the real /events payload carries no badge. */
  verification?: VerificationStatus
  /** Demo-only today, for the same reason. */
  layer?: KnowledgeLayer
  /** The journalled object, when the event names one (`/events` rows carry
   *  `object_type` + `object_id`); lets the feed item open it. */
  object?: { type: string; id: string }
  at: string
}
