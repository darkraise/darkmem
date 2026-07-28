import { useMemo, useState } from "react"
import { DEMO } from "@/lib/demo-flag"
import { useDemoContributions } from "@/demo/hooks"
import type { ContributionDay } from "@/features/dashboard/types"
import { useEventsCalendar } from "@/hooks/api"
import { calendarWindow, fillCalendarDays } from "./calendar"

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
  const query = useEventsCalendar(
    { since: window.since, until: window.until },
    { enabled: !DEMO },
  )

  if (DEMO) {
    return { days: demoDays, isLoading: false, isError: false }
  }

  return {
    days: query.data ? fillCalendarDays(query.data.buckets, now) : [],
    isLoading: query.isLoading,
    isError: query.isError,
  }
}
