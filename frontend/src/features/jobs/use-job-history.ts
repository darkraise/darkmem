import { DEMO } from "@/lib/demo-flag"
import { useEvents } from "@/hooks/api"

/** Only these journal a run today. `record_maintenance_run` is written by
 *  `job_runners.py`'s cleanup runners and `reembed.py`, so the other
 *  registered jobs produce no `maintenance_run` row at all — their history is
 *  absent, not empty, and the dialog says which of the two it is rather than
 *  showing one blank list for both. */
export const JOURNALLING_JOBS = new Set([
  "expired_memory_cleanup",
  "tag_orphan_cleanup",
  "graph_orphan_cleanup",
])

export interface JobRun {
  id: string
  at: string
  outcome: string
  detail: Record<string, unknown>
}

export interface JobHistoryState {
  runs: JobRun[]
  /** False when this job never journals, which is not the same as a job that
   *  journals and has not run yet. */
  journals: boolean
  isLoading: boolean
  isError: boolean
}

const HISTORY_LIMIT = 100

/**
 * Run history for one job, read from the `maintenance_run` stream.
 *
 * `/events` filters by `event_type` but not by payload, so the operation
 * match happens here. The limit bounds the page, so a busy stream can push a
 * quiet job's runs out of the window — which is a property of reading history
 * off a shared journal rather than a per-job endpoint.
 */
export function useJobHistory(
  jobKey: string,
  options?: { enabled?: boolean },
): JobHistoryState {
  const journals = JOURNALLING_JOBS.has(jobKey)
  const query = useEvents(
    { event_type: "maintenance_run", limit: HISTORY_LIMIT },
    { enabled: !DEMO && journals && (options?.enabled ?? true) },
  )

  if (!journals) {
    return { runs: [], journals: false, isLoading: false, isError: false }
  }

  const runs = (query.data?.items ?? [])
    .filter((row) => row.payload?.operation === jobKey)
    .map((row) => ({
      id: String(row.id),
      at: row.created_at,
      outcome: String(row.payload?.outcome ?? "unknown"),
      detail: (row.payload?.detail as Record<string, unknown>) ?? {},
    }))

  return {
    runs,
    journals: true,
    isLoading: query.isLoading,
    isError: query.isError,
  }
}
