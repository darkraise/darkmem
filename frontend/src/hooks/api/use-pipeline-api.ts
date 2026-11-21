import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import { useProjectScopedKey } from "@/lib/query-keys"
import { useProjectStore } from "@/stores/project-store"

export interface Stats {
  memories: number
  tags: number
  entities: number | null
  relationships: number | null
  sources: string[]
}

export interface HealthStatus {
  status: string
  pipeline: boolean
  services: { pgvector: boolean; llm: boolean }
  /** A stored `classifier_kind=local` this install cannot load (no torch). */
  classifier_unavailable: boolean
}

export interface PipelineLog {
  id: number
  memory_id: string | null
  details: Record<string, unknown>
  timestamp: string
}

export interface PipelineFailure {
  id: string
  entity_type: string
  entity_id: string
  pipeline_name: string
  failed_step: string
  error_message: string | null
  attempts: number
  first_failed_at: string
  last_attempt_at: string
  resolved_at: string | null
  metadata: Record<string, unknown>
  entity_preview: string | null
}

export interface PipelineFailureListResponse {
  items: PipelineFailure[]
  total: number
}

export function useStats(options?: { enabled?: boolean }) {
  return useQuery<Stats>({
    queryKey: ["stats"],
    queryFn: ({ signal }) => apiFetch("/analytics/stats", { signal }),
    enabled: options?.enabled ?? true,
  })
}

export function useHealth() {
  return useQuery<HealthStatus>({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/health")
      if (!res.ok) throw new Error(`Health check failed: ${res.status}`)
      return res.json()
    },
    refetchInterval: 30000,
    enabled: !DEMO,
  })
}

export function usePipelineLogs(limit = 10, enabled: boolean = true) {
  const queryKey = useProjectScopedKey("pipelineLogs", limit)
  const project = useProjectStore((s) => s.activeProject)
  return useQuery<PipelineLog[]>({
    queryKey,
    queryFn: () => {
      const params = new URLSearchParams({ limit: String(limit) })
      if (project) params.set("project", project)
      return apiFetch(`/analytics/pipeline-logs?${params}`)
    },
    enabled,
  })
}

export function usePipelineFailures(
  filters?: { entity_type?: string; pipeline_name?: string },
  enabled: boolean = true,
) {
  const qs = new URLSearchParams()
  if (filters?.entity_type) qs.set("entity_type", filters.entity_type)
  if (filters?.pipeline_name) qs.set("pipeline_name", filters.pipeline_name)
  const url = `/pipeline-failures${qs.toString() ? `?${qs}` : ""}`
  return useQuery<PipelineFailureListResponse>({
    queryKey: ["pipelineFailures", filters ?? {}],
    queryFn: ({ signal }) => apiFetch<PipelineFailureListResponse>(url, { signal }),
    enabled,
  })
}

export function usePipelineFailureCounts() {
  return useQuery<Record<string, number>>({
    queryKey: ["pipelineFailureCounts"],
    queryFn: ({ signal }) =>
      apiFetch<Record<string, number>>("/pipeline-failures/counts", { signal }),
    enabled: !DEMO,
  })
}

export function useRetryFailure() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<{ accepted: boolean; failure_id: string }>(
        `/pipeline-failures/${id}/retry`,
        { method: "POST" },
      ),
    // Outcome normally arrives via the pipeline.failure.updated WS event. But an
    // accepted:false response never emits one, and a dropped WS has no replay —
    // so refresh on rejection and add a delayed safety refetch.
    onSuccess: (data) => {
      if (!data?.accepted) {
        qc.invalidateQueries({ queryKey: ["pipelineFailures"] })
        qc.invalidateQueries({ queryKey: ["pipelineFailureCounts"] })
      }
    },
    onSettled: () => {
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ["pipelineFailureCounts"] })
      }, 4000)
    },
  })
}

export function useForgetFailure() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/pipeline-failures/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipelineFailures"] })
      qc.invalidateQueries({ queryKey: ["pipelineFailureCounts"] })
    },
  })
}

export function useRetryAllFailures() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (filters?: {
      entity_type?: string
      pipeline_name?: string
    }) => {
      const qs = new URLSearchParams()
      if (filters?.entity_type) qs.set("entity_type", filters.entity_type)
      if (filters?.pipeline_name) qs.set("pipeline_name", filters.pipeline_name)
      const url = `/pipeline-failures/retry-all${qs.toString() ? `?${qs}` : ""}`
      return apiFetch<{ accepted: boolean; batch_id: string; total: number }>(
        url,
        {
          method: "POST",
        },
      )
    },
    // Outcomes/final refresh normally arrive via pipeline.retry_batch.progress
    // ("done"). Guard the no-WS-event cases: refresh on rejection / empty batch,
    // plus a delayed safety refetch against a dropped WS (no event replay).
    onSuccess: (data) => {
      if (!data?.accepted || data.total === 0) {
        qc.invalidateQueries({ queryKey: ["pipelineFailures"] })
        qc.invalidateQueries({ queryKey: ["pipelineFailureCounts"] })
      }
    },
    onSettled: () => {
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ["pipelineFailureCounts"] })
      }, 5000)
    },
  })
}

export interface ObsoleteCounts {
  memories: number
  code_chunks: number
  entities: number
  current_fingerprint: string
}

export function useObsoleteCounts() {
  return useQuery<ObsoleteCounts>({
    queryKey: ["obsoleteCounts"],
    queryFn: ({ signal }) => apiFetch<ObsoleteCounts>("/reembed/obsolete-counts", { signal }),
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
    enabled: !DEMO,
  })
}
