import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

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

export function useJobs(enabled: boolean = true) {
  return useQuery<JobsResponse>({
    queryKey: ["jobs"],
    queryFn: () => apiFetch<JobsResponse>("/jobs"),
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
    enabled,
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

export function useTriggerJob() {
  const qc = useQueryClient()
  return useMutation<JobTriggerResponse, Error, string>({
    mutationFn: (key) =>
      apiFetch<JobTriggerResponse>(`/jobs/${key}/trigger`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
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
