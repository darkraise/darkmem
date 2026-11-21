import { useState, useCallback, useRef } from "react"
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

export interface ReprocessProgress {
  current: number
  total: number
  processed: number
  errors: number
  memoryId?: string
  status?: string
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

export function useReprocessStream(endpoint: "/analytics/reprocess/stream") {
  const qc = useQueryClient()
  const [isPending, setIsPending] = useState(false)
  const [progress, setProgress] = useState<ReprocessProgress | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const mutate = useCallback(async () => {
    if (isPending) return
    setIsPending(true)
    setProgress(null)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const res = await fetch(`/api/v1${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        signal: controller.signal,
      })

      if (!res.ok) throw new Error(`Reprocess failed: ${res.status}`)
      if (!res.body) throw new Error("No response body")

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split("\n\n")
        buffer = events.pop() ?? ""

        for (const block of events) {
          const dataLine = block
            .split("\n")
            .find((l) => l.trim().startsWith("data: "))
          if (!dataLine) continue
          const event = JSON.parse(dataLine.trim().slice(6))

          if (event.type === "start") {
            setProgress({
              current: 0,
              total: event.total,
              processed: 0,
              errors: 0,
            })
          } else if (event.type === "progress") {
            setProgress({
              current: event.current,
              total: event.total,
              processed: event.processed,
              errors: event.errors,
              memoryId: event.memory_id,
              status: event.status,
            })
          } else if (event.type === "done") {
            setProgress({
              current: event.total,
              total: event.total,
              processed: event.processed,
              errors: event.errors,
            })
          }
        }
      }

      // Reprocess re-runs extraction/classification across the set (changing
      // technologies, llm_* fields, entity/relation counts and possibly status),
      // and is its own SSE stream — not the per-memory pipeline.* WS path — so
      // refresh the grid/tag views here too.
      qc.invalidateQueries({ queryKey: ["pipelineLogs"] })
      qc.invalidateQueries({ queryKey: ["stats"] })
      qc.invalidateQueries({ queryKey: ["overview"] })
      qc.invalidateQueries({ queryKey: ["memories"] })
      qc.invalidateQueries({ queryKey: ["memoriesPaginated"] })
      qc.invalidateQueries({ queryKey: ["tags"] })
    } finally {
      setIsPending(false)
      abortRef.current = null
    }
  }, [endpoint, isPending, qc])

  const cancel = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  return { mutate, isPending, progress, cancel }
}

export interface OverviewData {
  counts: {
    memories: number
    tags: number
    entities: number | null
    relationships: number | null
  }
  activity: Array<{ date: string; count: number }>
  sources: Array<{ name: string; count: number }>
  top_tags: Array<{ name: string; count: number }>
  recent_memories: Array<{
    id: string
    content: string
    source: string
    memory_type: string | null
    tags: string[]
    created_at: string
  }>
  recent_errors: number
}

export function useOverview(days: number = 7) {
  return useQuery<OverviewData>({
    queryKey: ["overview", days],
    queryFn: ({ signal }) => apiFetch(`/analytics/overview?days=${days}`, { signal }),
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

export function useRetryBatchProgress(batchId: string | null) {
  return useQuery<
    import("@/lib/websocket-events").PipelineRetryBatchProgress | undefined
  >({
    queryKey: ["retryBatchProgress", batchId],
    queryFn: () => undefined,
    enabled: false,
    staleTime: Infinity,
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

export function useReembedMemories() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ accepted: boolean; batch_id: string; total: number }>(
        "/reembed/memories",
        { method: "POST" },
      ),
  })
}

export function useReembedCodeChunks() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ accepted: boolean; batch_id: string; total: number }>(
        "/reembed/code-chunks",
        { method: "POST" },
      ),
  })
}

export function useReembedEntities() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ accepted: boolean; batch_id: string; total: number }>(
        "/reembed/entities",
        { method: "POST" },
      ),
  })
}

export function useReembedAll() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{
        accepted: boolean
        batch_id: string
        totals: { memories: number; entities: number; code_chunks: number }
      }>("/reembed/all", { method: "POST" }),
  })
}

export function usePruneObsoleteCache() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<{ deleted: number }>("/reembed/prune-cache", { method: "POST" }),
    // Synchronous result (not a batch-progress WS event), so refresh the counts here.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["obsoleteCounts"] })
    },
  })
}

export function useReembedBatchProgress(
  batchId: string | null,
  category: "memories" | "code_chunks" | "entities",
) {
  return useQuery<
    import("@/lib/websocket-events").PipelineReembedBatchProgress | undefined
  >({
    queryKey: ["reembedBatchProgress", batchId, category],
    queryFn: () => undefined,
    enabled: false,
    staleTime: Infinity,
  })
}
