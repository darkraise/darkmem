import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface LlmPurposeConfig {
  provider: string;
  base_url: string;
  model: string;
  api_key: string | null;
  dimensions: number | null;
  reasoning: boolean;
  tool_call_mode: string;
  params: Record<string, unknown>;
}

export interface LlmConfigResponse {
  embedding?: LlmPurposeConfig;
  extraction?: LlmPurposeConfig;
  classification?: LlmPurposeConfig;
  reasoning?: LlmPurposeConfig;
  summarization?: LlmPurposeConfig;
  reranker?: LlmPurposeConfig;
}

export function useLlmConfig() {
  return useQuery<LlmConfigResponse>({
    queryKey: ["llmConfig"],
    queryFn: () => apiFetch<LlmConfigResponse>("/config/llm"),
  });
}

export interface LlmConfigUpdateResponse extends LlmConfigResponse {
  obsolete_after_change: { memories: number; code_chunks: number; entities: number } | null
}

export function useUpdateLlmConfig() {
  const qc = useQueryClient();
  return useMutation<LlmConfigUpdateResponse, Error, Record<string, unknown>>({
    mutationFn: (data) =>
      apiFetch<LlmConfigUpdateResponse>("/config/llm", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llmConfig"] });
      qc.invalidateQueries({ queryKey: ["obsoleteCounts"] });
      qc.invalidateQueries({ queryKey: ["pipeline"] });
    },
  });
}

export type MLDeviceFamily = "auto" | "cpu" | "cuda";

export interface FeatureFlags {
  llm_enrichment_enabled: boolean;
  hybrid_search_enabled: boolean;
  reranker_enabled: boolean;
  pipeline_concurrency: number;
  classification_areas: string[];
  classification_mode: "simple" | "expanded";
  embedding_batch_size: number;
  embedding_concurrency: number;
  entity_cache_ttl_minutes: number;
  // Per-stage pipeline path: true -> ML head, false -> LLM fallback.
  ml_extraction: boolean;
  ml_classification: boolean;
  ml_retrieval: boolean;
  ml_shadow_mode: boolean;
  confidence_rank_gamma: number;
  // Device selection + lazy-load TTL controls.
  ml_device: MLDeviceFamily;
  ml_cuda_index: number;
  ml_idle_ttl_minutes: number;
  ml_eviction_check_interval_seconds: number;
}

export function useFeatureFlags() {
  return useQuery<FeatureFlags>({
    queryKey: ["featureFlags"],
    queryFn: () => apiFetch<FeatureFlags>("/config/feature-flags"),
    staleTime: 30_000,
  });
}

export function useUpdateFeatureFlags() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<FeatureFlags>) =>
      apiFetch<FeatureFlags>("/config/feature-flags", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["featureFlags"] });
      qc.invalidateQueries({ queryKey: ["pipeline"] });
    },
  });
}

export interface ClassificationAreaInfo {
  key: string;
  display_name: string;
  types: string[];
  type_descriptions: Record<string, string>;
}

export function useClassificationAreas() {
  return useQuery<ClassificationAreaInfo[]>({
    queryKey: ["classificationAreas"],
    queryFn: () => apiFetch<ClassificationAreaInfo[]>("/config/classification-areas"),
    staleTime: 300_000,
  });
}

export interface EnrichmentConfig {
  enabled: boolean;
  batch_size: number;
  interval_seconds: number;
}

export function useEnrichmentConfig() {
  return useQuery<EnrichmentConfig>({
    queryKey: ["enrichmentConfig"],
    queryFn: () => apiFetch("/config/enrichment"),
  });
}

export function useUpdateEnrichmentConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: EnrichmentConfig) =>
      apiFetch("/config/enrichment", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["enrichmentConfig"] });
      qc.invalidateQueries({ queryKey: ["pipeline"] });
    },
  });
}

export function useTriggerEnrichment() {
  return useMutation({
    mutationFn: () =>
      apiFetch<{ processed: number }>("/config/enrichment/trigger", {
        method: "POST",
      }),
  });
}

// -- System prompts (UI-editable overrides of the in-code defaults) ---------

export interface SystemPromptsResponse {
  defaults: Record<string, string>;
  overrides: Record<string, string>;
  effective: Record<string, string>;
}

export function useSystemPrompts() {
  return useQuery<SystemPromptsResponse>({
    queryKey: ["systemPrompts"],
    queryFn: () => apiFetch<SystemPromptsResponse>("/config/system-prompts"),
  });
}

export function useUpdateSystemPrompts() {
  const qc = useQueryClient();
  return useMutation<SystemPromptsResponse, Error, { overrides: Record<string, string> }>({
    mutationFn: (body) =>
      apiFetch<SystemPromptsResponse>("/config/system-prompts", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["systemPrompts"] });
      qc.invalidateQueries({ queryKey: ["pipeline"] });
    },
  });
}

// -- ML device picker -------------------------------------------------------

export interface MLDeviceInfo {
  id: string;
  label: string;
  kind: "cpu" | "cuda";
  index: number | null;
}

export interface MLDeviceCurrent {
  ml_device: MLDeviceFamily;
  ml_cuda_index: number;
  loaded: boolean;
  effective_device: string | null;
  cpu_fallback: boolean;
}

export interface MLDevicesResponse {
  available: MLDeviceInfo[];
  current: MLDeviceCurrent;
}

export function useMLDevices() {
  return useQuery<MLDevicesResponse>({
    queryKey: ["mlDevices"],
    queryFn: () => apiFetch<MLDevicesResponse>("/config/ml-devices"),
    staleTime: 30_000,
  });
}

export interface MLDeviceApplyResponse {
  ml_device: MLDeviceFamily;
  ml_cuda_index: number;
  effective_device: string;
  loaded: boolean;
  reloaded: boolean;
}

export function useApplyMLDevice() {
  const qc = useQueryClient();
  return useMutation<
    MLDeviceApplyResponse,
    Error,
    { ml_device?: MLDeviceFamily; ml_cuda_index?: number }
  >({
    mutationFn: (body) =>
      apiFetch<MLDeviceApplyResponse>("/config/ml-device/apply", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mlDevices"] });
      qc.invalidateQueries({ queryKey: ["featureFlags"] });
      qc.invalidateQueries({ queryKey: ["mlModelsHealth"] });
      qc.invalidateQueries({ queryKey: ["pipeline"] });
      qc.invalidateQueries({ queryKey: ["mlMetrics"] });
    },
  });
}

// -- ML models health (per-group load + idle state) -------------------------

export interface MLModelsHealthResponse {
  enabled: boolean;
  device: string;
  models_dir: string;
  loaded: boolean;
  any_loaded?: boolean;
  heads: Record<string, boolean>;
  groups?: Record<string, { loaded: boolean; idle_seconds: number | null }>;
  embedding_dims: number | null;
  fingerprint: string | null;
  vram_allocated_mb: number | null;
  note?: string;
}

export function useMLModelsHealth() {
  return useQuery<MLModelsHealthResponse>({
    queryKey: ["mlModelsHealth"],
    queryFn: async () => {
      // Health endpoint lives at /api/health, not /api/v1, so bypass apiFetch.
      const resp = await fetch("/api/health/ml_models", { credentials: "include" });
      if (!resp.ok) throw new Error(`ml_models health failed: ${resp.status}`);
      return (await resp.json()) as MLModelsHealthResponse;
    },
    refetchInterval: 10_000,
  });
}
