import { useMemo, useState } from "react"
import { DEMO } from "@/lib/demo-flag"
import { useDemoContributions } from "@/demo/hooks"
import type { ContributionDay } from "@/features/dashboard/types"
import { useEventsCalendar } from "@/hooks/api"
import { useProjectStore } from "@/stores/project-store"
import { calendarWindow, fillCalendarDays } from "./calendar"

const INJECT_EVENT_TYPE = "inject"
const CAPTURE_EVENT_TYPE = "created"
const CAPTURE_OBJECT_TYPE = "memory"

export interface ContributionCalendarState {
  days: ContributionDay[]
  isLoading: boolean
  isError: boolean
}

/**
 * Binds the dashboard calendar to `/events/calendar` outside demo mode; in
 * demo mode it keeps the standalone fixture so the showcase still needs no
 * backend. Both hooks run unconditionally (rules of hooks) — only the
 * network request is skipped via `enabled`.
 */
export function useContributionCalendar(
  fixedNow?: number,
): ContributionCalendarState {
  const demoDays = useDemoContributions()
  // Date.now() is impure, so it's read once via useState's lazy initializer
  // (the sanctioned escape hatch) rather than as a render-time default param
  // — the window is frozen for the component's lifetime, not re-read on
  // every re-render.
  const [now] = useState(() => fixedNow ?? Date.now())
  const window = useMemo(() => calendarWindow(now), [now])
  // Memory captures only: every cell is labelled "N captures", and
  // the unscoped journal also counts logins, setup, maintenance runs and
  // indexing — which is how a fresh install showed a day of captures beside
  // an empty Memories page.
  const project = useProjectStore((s) => s.activeProject) ?? undefined
  const query = useEventsCalendar(
    {
      since: window.since,
      until: window.until,
      project,
      event_type: CAPTURE_EVENT_TYPE,
      object_type: CAPTURE_OBJECT_TYPE,
    },
    { enabled: !DEMO },
  )
  // A second aggregate rather than a client-side split of the first: the
  // endpoint returns counts, not rows, so there is nothing here to slice
  // (T3.20). Its failure is deliberately not folded into `isError` — a
  // calendar that refused to draw because the inject overlay was unavailable
  // would hide the activity it does know about.
  const injectQuery = useEventsCalendar(
    {
      since: window.since,
      until: window.until,
      project,
      event_type: INJECT_EVENT_TYPE,
    },
    { enabled: !DEMO },
  )

  if (DEMO) {
    return { days: demoDays, isLoading: false, isError: false }
  }

  return {
    days: query.data
      ? fillCalendarDays(query.data.buckets, now, injectQuery.data?.buckets ?? [])
      : [],
    isLoading: query.isLoading,
    isError: query.isError,
  }
}
