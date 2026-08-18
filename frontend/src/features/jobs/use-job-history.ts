import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"

export interface JobRun {
  id: string
  outcome: string
  started_at: string
  duration_seconds: number
  trigger: string
  error: string | null
  detail: Record<string, unknown>
}

interface JobRunsResponse {
  items: JobRun[]
  total: number
  limit: number
  offset: number
}

export interface JobHistoryState {
  runs: JobRun[]
  /** Unpaginated count, so a reader can tell "page 1 of many" from "that is
   *  everything" — which the old client-side filter over a shared journal
   *  could not answer at all. */
  total: number
  isLoading: boolean
  isError: boolean
}

export const HISTORY_PAGE_SIZE = 10

/**
 * One page of one job's run history, newest first.
 *
 * Reads `GET /jobs/{key}/runs`, backed by the `job_runs` table. It used to
 * read the `events` journal, which meant two problems at once: only three of
 * the twenty-one jobs wrote there, and the page had to be filtered client
 * side out of a stream shared with every other event, so a busy stream could
 * push a quiet job's runs out of the window entirely.
 */
export function useJobHistory(
  jobKey: string,
  options?: { enabled?: boolean; page?: number },
): JobHistoryState {
  const page = options?.page ?? 0
  const query = useQuery<JobRunsResponse>({
    queryKey: ["jobRuns", jobKey, page],
    queryFn: () =>
      apiFetch<JobRunsResponse>(
        `/jobs/${jobKey}/runs?limit=${HISTORY_PAGE_SIZE}&offset=${page * HISTORY_PAGE_SIZE}`,
      ),
    enabled: !DEMO && (options?.enabled ?? true),
  })

  return {
    runs: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    isLoading: query.isLoading,
    isError: query.isError,
  }
}
