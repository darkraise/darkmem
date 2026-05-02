import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import type { LlmPurposeConfig } from "./use-config-api"

export interface PipelineState {
  relation_rescue: boolean
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

export function usePipeline() {
  return useQuery<PipelineState>({
    queryKey: ["pipeline"],
    queryFn: () => apiFetch<PipelineState>("/pipeline"),
    staleTime: 0,
    refetchOnWindowFocus: true,
  })
}
