import { DEMO } from "@/lib/demo-flag"
import { useDemoBufferMonitor } from "@/demo/hooks"
import type { DemoBufferMonitor } from "@/demo/types"

export type BufferMonitorState =
  | { mode: "demo"; monitor: DemoBufferMonitor }
  /**
   * No REST route reads `memory_buffer` yet (see T1.61's report): the
   * table and the `buffer_flush` job are live, but nothing exposes rows or
   * counts over the API, and adding that route is outside this frontend
   * lane. Rendered as an honest gap, never as a silently empty panel
   * (invariant 23) — this branch is unreachable until `lib/demo-flag.ts`'s
   * default flips (T1.58), at which point it is the true state, not a bug.
   */
  | { mode: "unavailable" }

/**
 * `DEMO ? demo : real`, following `use-contribution-calendar.ts` — except
 * there is no real data source to bind to. The buffer table exists
 * (T1.10/T1.13), but no endpoint reads it, so the "real" branch reports
 * that gap honestly instead of fetching against a guessed contract.
 */
export function useBufferMonitor(): BufferMonitorState {
  const demo = useDemoBufferMonitor()
  if (DEMO) return { mode: "demo", monitor: demo }
  return { mode: "unavailable" }
}
