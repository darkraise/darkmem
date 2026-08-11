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
