import type { KnowledgeLayer, VerificationStatus } from "@/components/darkmem"
import { DEMO } from "@/demo/flag"
import { useDemoFeedEvents } from "@/demo/hooks"
import type { DemoFeedEvent, FeedCategory } from "@/demo/types"
import { relativeTime } from "@/lib/format"
import { useEvents, type EventLogEntry } from "@/hooks/api"
import { categoryOfEventType } from "./event-taxonomy"

/** The one row shape FeedTab renders, whichever source fed it. `layer` and
 *  `transition` stay optional because the real /events payload does not
 *  carry them for every event_type — only the demo fixture models the
 *  fully-dressed case today. */
export interface FeedRowData {
  id: string
  type: string
  category: FeedCategory | null
  text: string
  timeLabel: string
  layer?: KnowledgeLayer
  transition?: { from: VerificationStatus; to: VerificationStatus }
  badge?: VerificationStatus
  toast?: boolean
}

function fromDemo(event: DemoFeedEvent): FeedRowData {
  return {
    id: event.id,
    type: event.type,
    category: event.category,
    text: event.text,
    timeLabel: event.time_label,
    layer: event.layer,
    transition: event.transition,
    badge: event.badge,
    toast: event.toast,
  }
}

function shortId(id: string | null): string {
  return id ? id.slice(0, 8) : ""
}

function fromEventLog(entry: EventLogEntry): FeedRowData {
  const object = [entry.object_type, shortId(entry.object_id)]
    .filter(Boolean)
    .join(" ")
  const outcome =
    typeof entry.payload.outcome === "string" ? entry.payload.outcome : null
  const text = [object, entry.project ? `· project ${entry.project}` : null, outcome]
    .filter(Boolean)
    .join(" ")
  return {
    id: String(entry.id),
    type: entry.event_type,
    category: categoryOfEventType(entry.event_type),
    text: text || entry.event_type,
    timeLabel: relativeTime(entry.created_at),
    badge: entry.event_type === "superseded" ? "superseded" : undefined,
  }
}

const FEED_LIMIT = 50
const FEED_POLL_MS = 5000

/**
 * `DEMO ? demo : real`, following `use-contribution-calendar.ts` — the real
 * branch reads `/events` (no aggregation) and polls, since there is no
 * `event.appended` WebSocket event to subscribe to yet (doc 13 §6.4 names
 * one, but it is not implemented — see report). Category filtering is a
 * client-side show/hide over the fetched page, exactly like the demo
 * `filterFeed` it replaces; it is not a count and does not stand in for a
 * server aggregate.
 */
export function useFeed(): {
  events: FeedRowData[]
  isLoading: boolean
  isError: boolean
} {
  const demoEvents = useDemoFeedEvents()
  const query = useEvents(
    { limit: FEED_LIMIT },
    { enabled: !DEMO, refetchInterval: FEED_POLL_MS },
  )

  if (DEMO) {
    return { events: demoEvents.map(fromDemo), isLoading: false, isError: false }
  }
  return {
    events: query.data ? query.data.items.map(fromEventLog) : [],
    isLoading: query.isLoading,
    isError: query.isError,
  }
}
