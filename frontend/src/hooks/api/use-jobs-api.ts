import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"

export interface FieldDescriptor {
  key: string
  type: "int"
  label: string
  default: number
  min?: number
  max?: number
  step?: number
  help?: string
}

export interface Job {
  key: string
  display_name: string
  description: string
  enabled: boolean
  cron: string
  min_interval_seconds: number
  default_cron: string
  last_run_at: string | null
  last_status: "ok" | "error" | null
  last_error: string | null
  running: boolean
  config?: Record<string, number>
  config_schema?: FieldDescriptor[]
}

export interface JobsResponse {
  jobs: Job[]
}

export interface JobUpdateParams {
  enabled?: boolean
  cron?: string
}

export interface JobTriggerResponse {
  key: string
  last_status: "ok" | "error" | null
  last_error: string | null
  last_run_at: string | null
}

/** `poll: false` reads the shared list without keeping it live: a surface
 *  showing one job's settings has nothing to watch every five seconds. */
export function useJobs(enabled: boolean = true, { poll = true }: { poll?: boolean } = {}) {
  return useQuery<JobsResponse>({
    queryKey: ["jobs"],
    queryFn: ({ signal }) => apiFetch<JobsResponse>("/jobs", { signal }),
    refetchInterval: poll ? 5000 : false,
    refetchIntervalInBackground: false,
    enabled: !DEMO && enabled,
  })
}

export function useUpdateJob() {
  const qc = useQueryClient()
  return useMutation<Job, Error, { key: string; data: JobUpdateParams }>({
    mutationFn: ({ key, data }) =>
      apiFetch<Job>(`/jobs/${key}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  })
}

/**
 * `POST /jobs/{key}/trigger` **awaits the run** — the route calls
 * `registry.trigger`, which awaits `_run_once` — so the job is genuinely
 * running for exactly as long as this request is in flight.
 *
 * That is why the running state is marked optimistically rather than waited
 * for. Invalidating only `onSuccess` refetched *after* the run had finished,
 * and the list's own 5s poll almost never lands inside a run that takes
 * ~0.1s, so a job went from idle to done with nothing in between. This is not
 * a guess about state: the request being open *is* the run being open.
 * `onSettled` puts the server's own answer back.
 */
export function useTriggerJob() {
  const qc = useQueryClient()
  return useMutation<JobTriggerResponse, Error, string>({
    mutationFn: (key) =>
      apiFetch<JobTriggerResponse>(`/jobs/${key}/trigger`, { method: "POST" }),
    onMutate: async (key) => {
      await qc.cancelQueries({ queryKey: ["jobs"] })
      const previous = qc.getQueryData<JobsResponse>(["jobs"])
      qc.setQueryData<JobsResponse>(["jobs"], (current) =>
        current
          ? {
              ...current,
              jobs: current.jobs.map((job) =>
                job.key === key ? { ...job, running: true } : job,
              ),
            }
          : current,
      )
      return { previous }
    },
    onError: (_err, _key, context) => {
      const previous = (context as { previous?: JobsResponse } | undefined)?.previous
      if (previous) qc.setQueryData(["jobs"], previous)
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  })
}

export function useUpdateJobConfig() {
  const qc = useQueryClient()
  return useMutation<Job, Error, { key: string; config: Record<string, number> }>({
    mutationFn: ({ key, config }) =>
      apiFetch<Job>(`/jobs/${key}/config`, {
        method: "PUT",
        body: JSON.stringify({ config }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  })
}
