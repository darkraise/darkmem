import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import type { LlmPurposeConfig } from "./use-config-api"

export type Mode = "ml" | "llm" | "mixed"
export type StageMode = "ml" | "llm"
export type Device = "auto" | "cpu" | "cuda"
export type Persistence = "persistent" | "ttl"

export interface MLDeviceInfo {
  id: string
  label: string
  kind: "cpu" | "cuda"
  index: number | null
}

export interface PipelineState {
  mode: Mode
  stages: { extraction: StageMode; classification: StageMode; retrieval: StageMode }
  shadow_mode: boolean
  ml: {
    device: Device
    effective_device: string | null
    cuda_index: number
    persistence: Persistence
    idle_ttl_minutes: number
    eviction_check_interval_seconds: number
    cpu_fallback: boolean
    available_devices: MLDeviceInfo[]
  }
  llm: {
    embedding: LlmPurposeConfig
    extraction: LlmPurposeConfig
    classification: LlmPurposeConfig
    reasoning: LlmPurposeConfig
    summarization: LlmPurposeConfig
    reranker: LlmPurposeConfig
  }
  prompts: Record<string, { default: string; override: string; effective: string }>
}

export interface MetricsSnapshot {
  cpu_percent: number | null
  ram_used_mb: number | null
  ram_total_mb: number | null
  gpu_util_percent: number | null
  vram_used_mb: number | null
  vram_total_mb: number | null
  groups: Record<string, { loaded: boolean; idle_seconds: number | null }>
}

export function usePipeline() {
  return useQuery<PipelineState>({
    queryKey: ["pipeline"],
    queryFn: () => apiFetch<PipelineState>("/pipeline"),
    staleTime: 0,
    refetchOnWindowFocus: true,
  })
}

export function useSetPipelineMode() {
  const qc = useQueryClient()
  return useMutation<
    { mode: StageMode; stages: PipelineState["stages"] },
    Error,
    { mode: StageMode }
  >({
    mutationFn: (body) =>
      apiFetch("/pipeline/mode", { method: "POST", body: JSON.stringify(body) }),
    onMutate: async ({ mode }) => {
      await qc.cancelQueries({ queryKey: ["pipeline"] })
      const prev = qc.getQueryData<PipelineState>(["pipeline"])
      if (prev) {
        qc.setQueryData<PipelineState>(["pipeline"], {
          ...prev,
          mode,
          stages: { extraction: mode, classification: mode, retrieval: mode },
        })
      }
      return { prev }
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(["pipeline"], ctx.prev)
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ["pipeline"] }),
  })
}

export function useUnloadPipeline() {
  const qc = useQueryClient()
  return useMutation<
    { unloaded: string[]; groups: MetricsSnapshot["groups"] },
    Error,
    { group?: "extraction" | "classification" | "retriever" }
  >({
    mutationFn: ({ group }) => {
      const q = group ? `?group=${group}` : ""
      return apiFetch(`/pipeline/unload${q}`, { method: "POST" })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipeline"] })
      qc.invalidateQueries({ queryKey: ["mlMetrics"] })
    },
  })
}

export function useMLMetrics(enabled: boolean = true) {
  return useQuery<MetricsSnapshot>({
    queryKey: ["mlMetrics"],
    queryFn: () => apiFetch<MetricsSnapshot>("/pipeline/metrics"),
    refetchInterval: enabled ? 5_000 : false,
    enabled,
  })
}
