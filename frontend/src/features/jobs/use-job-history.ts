import { DEMO } from "@/lib/demo-flag"
import { useEvents } from "@/hooks/api"

export interface JobRun {
  id: string
  at: string
  outcome: string
  detail: Record<string, unknown>
}

export interface JobHistoryState {
  runs: JobRun[]
  isLoading: boolean
  isError: boolean
}

const HISTORY_LIMIT = 100

/**
 * Run history for one job, read from the `job_run` stream that `_run_once`
 * writes for every registered job.
 *
 * It used to read `maintenance_run`, which only the three cleanup runners
 * emit — so eighteen jobs ran, finished, and showed an empty history that
 * looked like "never ran" rather than "never recorded".
 *
 * `/events` filters by `event_type` but not by payload, so the job match
 * happens here. The limit bounds the page, so a busy stream can push a quiet
 * job's runs out of the window — a property of reading history off a shared
 * journal rather than a per-job endpoint.
 */
export function useJobHistory(
  jobKey: string,
  options?: { enabled?: boolean },
): JobHistoryState {
  const query = useEvents(
    { event_type: "job_run", limit: HISTORY_LIMIT },
    { enabled: !DEMO && (options?.enabled ?? true) },
  )

  const runs = (query.data?.items ?? [])
    .filter((row) => row.payload?.job === jobKey)
    .map((row) => ({
      id: String(row.id),
      at: row.created_at,
      outcome: String(row.payload?.outcome ?? "unknown"),
      detail: (row.payload?.detail as Record<string, unknown>) ?? {},
    }))

  return { runs, isLoading: query.isLoading, isError: query.isError }
}
