import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface LlmPurposeConfig {
  provider: string;
  base_url: string;
  model: string;
  api_key: string | null;
  dimensions: number | null;
  reasoning: boolean;
  api_kind: string;
  params: Record<string, unknown>;
  // Optional reference to a stored LLM provider profile. When set, the
  // purpose inherits provider/base_url/api_key/api_kind from that profile.
  provider_ref?: string | null;
  // Optional reference to a stored LLM profile (preset). When set, the
  // dropdown shows this profile as the active selection.
  profile_ref?: string | null;
}

export interface LlmProviderProfile {
  provider: string;
  base_url: string;
  api_key: string | null;
  api_kind: string;
  supports_embedding: boolean;
}

export interface LlmProvidersResponse {
  profiles: Record<string, LlmProviderProfile>;
}

export interface LlmProviderTestRequest {
  mode?: "chat" | "embedding";
  model?: string;
}

export interface LlmProviderTestResponse {
  ok: boolean;
  status_code: number | null;
  latency_ms: number;
  url: string;
  message: string;
}

export function useLlmProviders() {
  return useQuery<LlmProvidersResponse>({
    queryKey: ["llmProviders"],
    queryFn: () => apiFetch<LlmProvidersResponse>("/config/llm-providers"),
  });
}

export function useUpdateLlmProviders() {
  const qc = useQueryClient();
  return useMutation<LlmProvidersResponse, Error, LlmProvidersResponse>({
    mutationFn: (body) =>
      apiFetch<LlmProvidersResponse>("/config/llm-providers", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llmProviders"] });
      qc.invalidateQueries({ queryKey: ["llmConfig"] });
      qc.invalidateQueries({ queryKey: ["pipeline"] });
    },
  });
}

export function useDeleteLlmProvider() {
  const qc = useQueryClient();
  return useMutation<LlmProvidersResponse, Error, { name: string }>({
    mutationFn: ({ name }) =>
      apiFetch<LlmProvidersResponse>(`/config/llm-providers/${encodeURIComponent(name)}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llmProviders"] });
      qc.invalidateQueries({ queryKey: ["llmConfig"] });
      qc.invalidateQueries({ queryKey: ["pipeline"] });
    },
  });
}

export function useTestLlmProvider() {
  return useMutation<
    LlmProviderTestResponse,
    Error,
    { name: string; body?: LlmProviderTestRequest }
  >({
    mutationFn: ({ name, body }) =>
      apiFetch<LlmProviderTestResponse>(
        `/config/llm-providers/${encodeURIComponent(name)}/test`,
        { method: "POST", body: JSON.stringify(body ?? { mode: "chat" }) },
      ),
  });
}

// -- LLM Provider models-fetch ---------------------------------------------

export interface LlmProviderModelsResponse {
  models: string[];
  fetched_via: string;
  error: string | null;
}

export function useProviderModels(providerName: string | null, enabled: boolean = true) {
  return useQuery<LlmProviderModelsResponse>({
    queryKey: ["llmProviderModels", providerName],
    queryFn: () =>
      apiFetch<LlmProviderModelsResponse>(
        `/config/llm-providers/${encodeURIComponent(providerName!)}/models`,
      ),
    enabled: enabled && !!providerName,
    staleTime: 60_000,
  });
}

// -- LLM Profiles ----------------------------------------------------------

export interface LlmProfile {
  provider_ref: string;
  model: string;
  params: Record<string, unknown>;
  is_embedding: boolean;
  reasoning: boolean;
}

export interface LlmProfilesResponse {
  profiles: Record<string, LlmProfile>;
}

export function useLlmProfiles() {
  return useQuery<LlmProfilesResponse>({
    queryKey: ["llmProfiles"],
    queryFn: () => apiFetch<LlmProfilesResponse>("/config/llm-profiles"),
  });
}

export function useUpdateLlmProfiles() {
  const qc = useQueryClient();
  return useMutation<LlmProfilesResponse, Error, LlmProfilesResponse>({
    mutationFn: (body) =>
      apiFetch<LlmProfilesResponse>("/config/llm-profiles", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llmProfiles"] });
    },
  });
}

export function useDeleteLlmProfile() {
  const qc = useQueryClient();
  return useMutation<LlmProfilesResponse, Error, { name: string }>({
    mutationFn: ({ name }) =>
      apiFetch<LlmProfilesResponse>(`/config/llm-profiles/${encodeURIComponent(name)}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llmProfiles"] });
    },
  });
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
  relation_rescue: boolean;
  confidence_rank_gamma: number;
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

