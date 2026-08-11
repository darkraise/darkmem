import { useQuery } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"

export interface EventLogEntry {
  id: number
  created_at: string
  event_type: string
  object_type: string
  object_id: string | null
  project: string | null
  actor: string | null
  api_key_id: string | null
  source: string | null
  payload: Record<string, unknown>
}

export interface EventListResponse {
  items: EventLogEntry[]
  total: number
}

export interface EventListParams {
  object_type?: string
  object_id?: string
  project?: string
  event_type?: string
  since?: string
  until?: string
  limit?: number
  offset?: number
}

function eventsQueryString(params: EventListParams): string {
  const qs = new URLSearchParams()
  if (params.object_type) qs.set("object_type", params.object_type)
  if (params.object_id) qs.set("object_id", params.object_id)
  if (params.project) qs.set("project", params.project)
  if (params.event_type) qs.set("event_type", params.event_type)
  if (params.since) qs.set("since", params.since)
  if (params.until) qs.set("until", params.until)
  if (params.limit !== undefined) qs.set("limit", String(params.limit))
  if (params.offset !== undefined) qs.set("offset", String(params.offset))
  return qs.toString()
}

/** `GET /events` — the feed and day-drill substrate. Server-paginated and
 *  server-filtered; callers must not derive counts from `items` alone and
 *  should read `total` instead once a filter can truncate the page. */
export function useEvents(
  params: EventListParams = {},
  options?: { enabled?: boolean; refetchInterval?: number },
) {
  const query = eventsQueryString(params)
  return useQuery<EventListResponse>({
    queryKey: ["events", params],
    queryFn: () => apiFetch(`/events${query ? `?${query}` : ""}`),
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval,
  })
}

export interface CalendarBucket {
  /** UTC calendar day, YYYY-MM-DD — see ix_events_day's immutable UTC cast. */
  day: string
  count: number
}

export interface EventCalendarResponse {
  buckets: CalendarBucket[]
}

export function useEventsCalendar(
  params: {
    since?: string
    until?: string
    project?: string
    /** Narrows the same buckets to one kind — how a caller asks which days
     *  hold an inject without fetching those days' rows and counting them. */
    event_type?: string
  } = {},
  options?: { enabled?: boolean },
) {
  const qs = new URLSearchParams()
  if (params.since) qs.set("since", params.since)
  if (params.until) qs.set("until", params.until)
  if (params.project) qs.set("project", params.project)
  if (params.event_type) qs.set("event_type", params.event_type)
  const query = qs.toString()
  return useQuery<EventCalendarResponse>({
    // The event type belongs in the key: without it the filtered and
    // unfiltered series share one cache entry, and whichever resolved first
    // would answer for both.
    queryKey: [
      "eventsCalendar",
      params.since ?? null,
      params.until ?? null,
      params.project ?? null,
      params.event_type ?? null,
    ],
    queryFn: () => apiFetch(`/events/calendar${query ? `?${query}` : ""}`),
    enabled: options?.enabled ?? true,
  })
}
