import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

export interface LlmPurposeConfig {
  // No `provider`: it duplicated `api_kind` and nothing dispatched on it, so
  // T1.01 dropped the column and the wire key together (F-10). `api_kind` is
  // the sole vendor field.
  base_url: string
  model: string
  api_key: string | null
  dimensions: number | null
  reasoning: boolean
  api_kind: string
  params: Record<string, unknown>
  // Present only on the classification purpose; absent means the LLM-backed
  // classifier (T1.04). Not yet declared on the backend's
  // LLMPurposeConfigUpdate wire schema, so a write of this field is a no-op
  // until that schema catches up (owned outside this surface).
  classifier_kind?: "llm" | "local" | null
}

export interface LlmConfigResponse {
  embedding?: LlmPurposeConfig
  extraction?: LlmPurposeConfig
  classification?: LlmPurposeConfig
  reasoning?: LlmPurposeConfig
  summarization?: LlmPurposeConfig
  reranker?: LlmPurposeConfig
}

export function useLlmConfig(enabled: boolean = true) {
  return useQuery<LlmConfigResponse>({
    queryKey: ["llmConfig"],
    queryFn: () => apiFetch<LlmConfigResponse>("/config/llm"),
    enabled,
  })
}

export interface LlmConfigUpdateResponse extends LlmConfigResponse {
  obsolete_after_change: {
    memories: number
    code_chunks: number
    entities: number
  } | null
}

export function useUpdateLlmConfig() {
  const qc = useQueryClient()
  return useMutation<LlmConfigUpdateResponse, Error, Record<string, unknown>>({
    mutationFn: (data) =>
      apiFetch<LlmConfigUpdateResponse>("/config/llm", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llmConfig"] })
      qc.invalidateQueries({ queryKey: ["obsoleteCounts"] })
      qc.invalidateQueries({ queryKey: ["pipeline"] })
    },
  })
}

export interface FeatureFlags {
  hybrid_search_enabled: boolean
  reranker_enabled: boolean
  pipeline_concurrency: number
  // classification_areas / classification_mode are classification tuning
  // parameters, not behavioral on/off flags; they live in this row for
  // transport convenience but don't gate a pipeline phase the way the boolean
  // flags above do.
  classification_areas: string[]
  classification_mode: "simple" | "expanded"
  embedding_batch_size: number
  embedding_concurrency: number
  entity_cache_ttl_minutes: number
  relation_rescue: boolean
  confidence_rank_gamma: number
}

export function useFeatureFlags() {
  return useQuery<FeatureFlags>({
    queryKey: ["featureFlags"],
    queryFn: () => apiFetch<FeatureFlags>("/config/feature-flags"),
    staleTime: 30_000,
  })
}

export function useUpdateFeatureFlags() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<FeatureFlags>) =>
      apiFetch<FeatureFlags>("/config/feature-flags", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["featureFlags"] })
      qc.invalidateQueries({ queryKey: ["pipeline"] })
    },
  })
}

export interface ClassificationAreaInfo {
  key: string
  display_name: string
  types: string[]
  type_descriptions: Record<string, string>
}

export function useClassificationAreas() {
  return useQuery<ClassificationAreaInfo[]>({
    queryKey: ["classificationAreas"],
    queryFn: () =>
      apiFetch<ClassificationAreaInfo[]>("/config/classification-areas"),
    staleTime: 300_000,
  })
}

// -- System prompts (UI-editable overrides of the in-code defaults) ---------

export interface SystemPromptsResponse {
  defaults: Record<string, string>
  overrides: Record<string, string>
  effective: Record<string, string>
}

export function useSystemPrompts() {
  return useQuery<SystemPromptsResponse>({
    queryKey: ["systemPrompts"],
    queryFn: () => apiFetch<SystemPromptsResponse>("/config/system-prompts"),
  })
}

export function useUpdateSystemPrompts() {
  const qc = useQueryClient()
  return useMutation<
    SystemPromptsResponse,
    Error,
    { overrides: Record<string, string> }
  >({
    mutationFn: (body) =>
      apiFetch<SystemPromptsResponse>("/config/system-prompts", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["systemPrompts"] })
      qc.invalidateQueries({ queryKey: ["pipeline"] })
    },
  })
}
