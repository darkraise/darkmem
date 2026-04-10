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

export function useUpdateLlmConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      apiFetch("/config/llm", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["llmConfig"] }),
  });
}

export interface FeatureFlags {
  llm_enrichment_enabled: boolean;
  hybrid_search_enabled: boolean;
  reranker_enabled: boolean;
  pipeline_concurrency: number;
  classification_areas: string[];
  classification_mode: "simple" | "expanded";
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ["featureFlags"] }),
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
    onSuccess: () => qc.invalidateQueries({ queryKey: ["enrichmentConfig"] }),
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
