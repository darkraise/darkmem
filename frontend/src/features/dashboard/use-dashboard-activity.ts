import { DEMO } from "@/lib/demo-flag"
import { useDemoEvents } from "@/demo/hooks"
import type {
  ActivityEvent,
  ActivityEventKind,
} from "@/features/dashboard/types"
import type { FeedCategory } from "@/features/activity/types"
import { categoryOfEventType } from "@/features/activity/event-taxonomy"
import { useEvents, type EventLogEntry } from "@/hooks/api"
import { shortId } from "@/lib/short-id"
import { useProjectStore } from "@/stores/project-store"

const FEED_LIMIT = 8
/** Read past the sign-ins so eight vault events usually remain after them. */
const FETCH_LIMIT = 50

/** Sign-in and setup rows say who reached the instance, not what the vault
 *  learned or did; they have their own reader (`GET /auth/audit`, Settings ->
 *  Security) and the Activity feed's "all" view. On the dashboard they
 *  crowded out every capture after a few failed logins. */
function isVaultEvent(entry: EventLogEntry): boolean {
  return !/^(auth|setup)_/.test(entry.event_type)
}

/** The dashboard's icon set is keyed by `ActivityEventKind`, the feed's
 *  taxonomy by `FeedCategory`. Deriving one from the other keeps
 *  `event-taxonomy.ts` the single place an event type is classified — a
 *  second parallel map here would drift the moment a type is added there. */
const KIND_BY_CATEGORY: Record<FeedCategory, ActivityEventKind> = {
  capture: "memory",
  pipeline: "pipeline",
  verification: "fact",
  consolidation: "job",
  code: "pipeline",
}

/** `KIND_ICONS` is a total Record, so an unmapped kind resolves to
 *  `undefined` and throws when rendered as a component. An event type the
 *  taxonomy does not know yet must therefore still land on a real kind. */
const FALLBACK_KIND: ActivityEventKind = "job"

function humanise(eventType: string): string {
  const spaced = eventType.replace(/_/g, " ")
  return spaced.charAt(0).toUpperCase() + spaced.slice(1)
}

function fromEventLog(entry: EventLogEntry): ActivityEvent {
  const category = categoryOfEventType(entry.event_type)
  const outcome =
    typeof entry.payload?.outcome === "string" ? entry.payload.outcome : null
  const detail = [
    entry.object_type,
    entry.object_id ? shortId(entry.object_id) : null,
    entry.project ? `· project ${entry.project}` : null,
    outcome,
  ]
    .filter(Boolean)
    .join(" ")
  return {
    id: String(entry.id),
    kind: category ? KIND_BY_CATEGORY[category] : FALLBACK_KIND,
    title: humanise(entry.event_type),
    detail: detail || undefined,
    object:
      entry.object_type && entry.object_id
        ? { type: entry.object_type, id: entry.object_id }
        : undefined,
    at: entry.created_at,
  }
}

export interface DashboardActivityState {
  events: ActivityEvent[]
  isLoading: boolean
  isError: boolean
}

/**
 * Binds the dashboard's Recent Activity card to `/events` outside demo mode.
 * The route used to call `useDemoEvents()` unconditionally, so the card
 * listed fixture activity on a system that had none.
 *
 * Deliberately no `verification` or `layer`: the real `/events` payload does
 * not carry either for most event types, and inferring a badge from an event
 * type would put a second verification opinion on a read surface.
 */
export function useDashboardActivity(): DashboardActivityState {
  const demo = useDemoEvents()
  const project = useProjectStore((s) => s.activeProject) ?? undefined
  const query = useEvents({ project, limit: FETCH_LIMIT }, { enabled: !DEMO })

  if (DEMO) {
    return { events: demo, isLoading: false, isError: false }
  }

  return {
    events: (query.data?.items ?? [])
      .filter(isVaultEvent)
      .slice(0, FEED_LIMIT)
      .map(fromEventLog),
    isLoading: query.isLoading,
    isError: query.isError,
  }
}
