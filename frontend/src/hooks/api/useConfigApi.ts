import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface LlmPurposeConfig {
  provider: string;
  base_url: string;
  model: string;
  api_key: string | null;
  dimensions: number | null;
  params: Record<string, unknown>;
}

export interface LlmConfigResponse {
  embedding?: LlmPurposeConfig;
  extraction?: LlmPurposeConfig;
  reasoning?: LlmPurposeConfig;
  summarization?: LlmPurposeConfig;
}

export interface SystemPromptProfile {
  purpose: string;
  display_name: string;
  content: string;
  is_editable: boolean;
  updated_at: string;
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

export function useSystemPrompts() {
  return useQuery<SystemPromptProfile[]>({
    queryKey: ["systemPrompts"],
    queryFn: () => apiFetch<SystemPromptProfile[]>("/config/system-prompt/list"),
  });
}

export function useUpdateSystemPrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ purpose, content }: { purpose: string; content: string }) =>
      apiFetch(`/config/system-prompt/${purpose}`, {
        method: "PUT",
        body: JSON.stringify({ content }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["systemPrompts"] }),
  });
}

export function useResetSystemPrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (purpose: string) =>
      apiFetch(`/config/system-prompt/${purpose}/reset`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["systemPrompts"] }),
  });
}
