import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

export interface Job {
  key: string
  display_name: string
  description: string
  enabled: boolean
  interval_seconds: number
  min_interval_seconds: number
  default_interval_seconds: number
  last_run_at: string | null
  last_status: "ok" | "error" | null
  last_error: string | null
  running: boolean
}

export interface JobsResponse {
  jobs: Job[]
}

export interface JobUpdateParams {
  enabled?: boolean
  interval_seconds?: number
}

export interface JobTriggerResponse {
  key: string
  last_status: "ok" | "error" | null
  last_error: string | null
  last_run_at: string | null
}

export function useJobs() {
  return useQuery<JobsResponse>({
    queryKey: ["jobs"],
    queryFn: () => apiFetch<JobsResponse>("/jobs"),
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  })
}

export function useUpdateJob() {
  const qc = useQueryClient()
  return useMutation<Job, Error, { key: string; data: JobUpdateParams }>({
    mutationFn: ({ key, data }) =>
      apiFetch<Job>(`/jobs/${key}`, { method: "PUT", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  })
}

export function useTriggerJob() {
  const qc = useQueryClient()
  return useMutation<JobTriggerResponse, Error, string>({
    mutationFn: (key) =>
      apiFetch<JobTriggerResponse>(`/jobs/${key}/trigger`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  })
}
