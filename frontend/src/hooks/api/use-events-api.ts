import { useQuery } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"

export interface CalendarBucket {
  /** UTC calendar day, YYYY-MM-DD — see ix_events_day's immutable UTC cast. */
  day: string
  count: number
}

export interface EventCalendarResponse {
  buckets: CalendarBucket[]
}

export function useEventsCalendar(
  params: { since?: string; until?: string; project?: string } = {},
  options?: { enabled?: boolean },
) {
  const qs = new URLSearchParams()
  if (params.since) qs.set("since", params.since)
  if (params.until) qs.set("until", params.until)
  if (params.project) qs.set("project", params.project)
  const query = qs.toString()
  return useQuery<EventCalendarResponse>({
    queryKey: ["eventsCalendar", params.since ?? null, params.until ?? null, params.project ?? null],
    queryFn: () => apiFetch(`/events/calendar${query ? `?${query}` : ""}`),
    enabled: options?.enabled ?? true,
  })
}
