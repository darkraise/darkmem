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
 */
const EVENT_TYPE_CATEGORY: Record<string, FeedCategory> = {
  created: "capture",
  document_filed: "capture",
  extracted: "pipeline",
  sources_changed: "pipeline",
  verified: "verification",
  contradiction_scanned: "verification",
  citation_stale: "verification",
  consolidated: "consolidation",
  superseded: "consolidation",
  deprecated: "consolidation",
  expired: "consolidation",
  repo_registered: "code",
  repo_synced: "code",
  repo_indexed: "code",
  repo_hint_rejected: "code",
}

export function categoryOfEventType(eventType: string): FeedCategory | null {
  return EVENT_TYPE_CATEGORY[eventType] ?? null
}
