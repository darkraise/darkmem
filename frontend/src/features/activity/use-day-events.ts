import type { VerificationStatus } from "@/components/darkmem"
import { dayBucket } from "@/demo/activity"
import { DEMO } from "@/lib/demo-flag"
import { useDemoDayBuckets } from "@/demo/hooks"
import type { DemoDayEvent } from "@/demo/types"
import { useEvents, type EventLogEntry } from "@/hooks/api"
import { shortId } from "@/lib/short-id"

/** The one row shape DayTab renders, whichever source fed it. `transition`
 *  stays optional — only the demo fixture models a from→to rung pair
 *  today; the real payload does not carry one for every event_type. */
export interface DayRowData {
  id: string
  timeLabel: string
  type: string
  linkLabel: string
  note?: string
  badge?: VerificationStatus
  transition?: { from: VerificationStatus; to: VerificationStatus; toLabel?: string }
  /** Set on `inject` / `inject_curbed` rows only (T3.20, doc 13 §6.5). */
  inject?: InjectRecordData
}

/** One inject record, normalised from the journal payload.
 *
 * The three id lists stay separate exactly as older builds journalled them:
 * a reader asking whether a *fact* was pushed cannot recover the layer from a
 * merged list without querying every table for every id.
 *
 * Ids and counts, never the injected text — the journal records no content by
 * design (write-time minimization), so "exactly what was pushed" is answerable
 * as identity, and honest about rows that have since been deleted.
 */
export interface InjectRecordData {
  curbed: boolean
  tool: string
  contextFile: string | null
  factIds: string[]
  articleIds: string[]
  memoryIds: string[]
  itemCount: number
  budgetTokens: number | null
  tokensUsed: number | null
  /** The human's stated reason on a curb; null on a push. */
  reason: string | null
  /** `session_start` or `watch` (T4.06). */
  cadence: string | null
  /** What shifted, on a watch refresh; null on a session-start push, which
   *  had no cause beyond the session beginning. */
  trigger: string | null
}

function fromDemo(event: DemoDayEvent, index: number): DayRowData {
  return {
    id: `${event.time_label}-${index}`,
    timeLabel: event.time_label,
    type: event.type,
    linkLabel: event.link_label,
    note: event.note,
    inject: event.inject
      ? {
          curbed: event.type === "inject_curbed",
          tool: event.inject.tool,
          contextFile: event.inject.context_file,
          factIds: event.inject.fact_ids,
          articleIds: event.inject.article_ids,
          memoryIds: event.inject.memory_ids,
          itemCount:
            event.inject.fact_ids.length +
            event.inject.article_ids.length +
            event.inject.memory_ids.length,
          budgetTokens: event.inject.budget_tokens,
          tokensUsed: event.inject.tokens_used,
          reason: null,
          cadence: event.inject.cadence ?? null,
          trigger: event.inject.trigger ?? null,
        }
      : undefined,
    badge: event.badge,
    transition: event.transition
      ? {
          from: event.transition.from,
          to: event.transition.to,
          toLabel: event.transition.to_label,
        }
      : undefined,
  }
}


function utcTimeLabel(iso: string): string {
  return `${iso.slice(11, 16)} UTC`
}

function idList(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String) : []
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" ? value : null
}

function stringOrNull(value: unknown): string | null {
  return typeof value === "string" && value ? value : null
}

const INJECT_TYPES = new Set(["inject", "inject_curbed"])

/** An inject record's payload, or `undefined` for every other event type.
 *
 * `tool` falls back to a plain "unknown target" rather than being dropped:
 * the row exists because a push or a curb happened, and hiding it because one
 * payload field is missing would remove the record doc 13 §6.5 exists to
 * guarantee — the human seeing what the agent was told.
 */
function injectOf(entry: EventLogEntry): InjectRecordData | undefined {
  if (!INJECT_TYPES.has(entry.event_type)) return undefined
  const payload = entry.payload
  const factIds = idList(payload.fact_ids)
  const articleIds = idList(payload.article_ids)
  const memoryIds = idList(payload.memory_ids)
  return {
    curbed: entry.event_type === "inject_curbed",
    tool: stringOrNull(payload.tool) ?? "unknown target",
    contextFile: stringOrNull(payload.context_file),
    factIds,
    articleIds,
    memoryIds,
    itemCount: factIds.length + articleIds.length + memoryIds.length,
    budgetTokens: numberOrNull(payload.budget_tokens),
    tokensUsed: numberOrNull(payload.tokens_used),
    reason: stringOrNull(payload.reason),
    cadence: stringOrNull(payload.cadence),
    trigger: stringOrNull(payload.trigger),
  }
}

function fromEventLog(entry: EventLogEntry): DayRowData {
  const inject = injectOf(entry)
  // An inject targets a tool's context file, so `object_type` is `system` and
  // `object_id` is null — the generic label would read "system" and name
  // nothing. The target is the honest link label here.
  const linkLabel = inject
    ? [
        `distribution target: ${inject.tool}`,
        inject.contextFile ? `(${inject.contextFile})` : null,
        entry.project ? `· project ${entry.project}` : null,
      ]
        .filter(Boolean)
        .join(" ")
    : [
        entry.object_type,
        shortId(entry.object_id),
        entry.project ? `· project ${entry.project}` : null,
      ]
        .filter(Boolean)
        .join(" ")
  return {
    id: String(entry.id),
    timeLabel: utcTimeLabel(entry.created_at),
    type: entry.event_type,
    linkLabel: linkLabel || entry.event_type,
    badge: entry.event_type === "superseded" ? "superseded" : undefined,
    inject,
  }
}

/** UTC day-bucket boundaries for `since`/`until`, matching `ix_events_day`'s
 *  immutable `(created_at AT TIME ZONE 'UTC')::date` cast — never re-bucket
 *  to local time client-side (doc 04 §8.1, T1.08's fix). */
function utcDayWindow(day: string): { since: string; until: string } {
  const start = new Date(`${day}T00:00:00.000Z`)
  const end = new Date(start.getTime() + 86_400_000)
  return { since: start.toISOString(), until: end.toISOString() }
}

const DAY_EVENT_LIMIT = 200

/**
 * `DEMO ? demo : real` for one UTC day-bucket, following
 * `use-contribution-calendar.ts`. The real branch reads `/events` windowed
 * to that UTC day (`since`/`until`) — the endpoint has no per-day route, so
 * this is the list endpoint with a day-sized window, still zero
 * client-side aggregation: `total` comes from the server, never a count of
 * `items.length` after a truncated page.
 */
export function useDayEvents(day: string): {
  /** null = no bucket for this day (demo) or nothing fetched yet (real, not loading/error) */
  events: DayRowData[] | null
  total: number
  isLoading: boolean
  isError: boolean
  truncated: boolean
} {
  const demoBuckets = useDemoDayBuckets()
  const demoBucket = dayBucket(demoBuckets, day)
  const window = utcDayWindow(day)
  const query = useEvents(
    { since: window.since, until: window.until, limit: DAY_EVENT_LIMIT },
    { enabled: !DEMO },
  )

  if (DEMO) {
    return {
      events: demoBucket ? demoBucket.events.map(fromDemo) : null,
      total: demoBucket?.events.length ?? 0,
      isLoading: false,
      isError: false,
      truncated: false,
    }
  }

  if (!query.data) {
    return {
      events: null,
      total: 0,
      isLoading: query.isLoading,
      isError: query.isError,
      truncated: false,
    }
  }
  return {
    events: query.data.items.map(fromEventLog),
    total: query.data.total,
    isLoading: false,
    isError: false,
    truncated: query.data.total > query.data.items.length,
  }
}
