import type { FeedCategory } from "@/features/activity/types"

/**
 * Display-only grouping of the closed `event_type` vocabulary
 * (`app/services/events.py` EVENT_TYPES) into the feed's five filter tabs.
 * This is a UI convenience, not a taxonomy the backend enforces — an
 * event_type absent from every bucket below still shows under "all", it
 * just has no dedicated tab (inject/inject_curbed/setup_completed/
 * auth_lockout: none of capture/pipeline/verification/consolidation/code
 * fits them cleanly, and inventing a sixth tab is a design call this task
 * does not own).
 *
 * T2.102 (2026-08-07) closed the gap that let three straight rounds each
 * find one value missing here and fix only that one (`contradiction_scanned`
 * T2.11, `citation_stale` T2.48): every EVENT_TYPES value with a live
 * `record_event` call site is now covered, either by a tab below or by an
 * explicit entry in `EVENT_TYPES_WITHOUT_TAB`. A value with no emitter yet
 * (landed taxonomy-first, ahead of its feature — inject/inject_curbed/
 * setup_completed/auth_lockout today) owes neither, since punishing that
 * discipline is worse than the gap it closes.
 * `backend/tests/test_event_taxonomy_map.py` scans `backend/app` for live
 * emitters and fails the build the moment a value has one but lands in
 * neither list — that test, not this comment, is what keeps this true.
 */
const EVENT_TYPE_CATEGORY: Record<string, FeedCategory> = {
  created: "capture",
  document_filed: "capture",
  extracted: "pipeline",
  sources_changed: "pipeline",
  verified: "verification",
  contradiction_scanned: "verification",
  citation_stale: "verification",
  human_verdict: "verification",
  consolidated: "consolidation",
  superseded: "consolidation",
  deprecated: "consolidation",
  expired: "consolidation",
  invalidated: "consolidation",
  undone: "consolidation",
  repo_registered: "code",
  repo_synced: "code",
  repo_indexed: "code",
  repo_hint_rejected: "code",
}

/**
 * EVENT_TYPES values with a live emitter that deliberately get no tab —
 * recorded here rather than left as a silent absence from
 * EVENT_TYPE_CATEGORY, so the next reader can tell "considered and
 * excluded" from "missed" (that ambiguity is what T2.102 was minted to
 * close). Each reason is why it does not fit one of the five tabs, not why
 * it lacks an emitter — all four below are emitted for real.
 */
const EVENT_TYPES_WITHOUT_TAB = new Set<string>([
  // Generic system housekeeping (re-embed sweeps, maintenance jobs) —
  // not a memory/fact/repo lifecycle step any of the five tabs models.
  "maintenance_run",
  // A human accepting/dismissing a topic pin suggestion — curation on a
  // subject, not a memory or fact transition; no tab covers that surface
  // yet and T2.53's scheduler that would drive it hasn't landed.
  "pin_decision",
  // memory_buffer poison-row triage (requeue/discard), surfaced by the
  // buffer monitor rather than the feed's capture tab, which is about
  // completed captures, not the retry queue behind them.
  "buffer_requeued",
  "buffer_discarded",
])

export function categoryOfEventType(eventType: string): FeedCategory | null {
  return EVENT_TYPE_CATEGORY[eventType] ?? null
}

export function isDeliberatelyUntabbed(eventType: string): boolean {
  return EVENT_TYPES_WITHOUT_TAB.has(eventType)
}
