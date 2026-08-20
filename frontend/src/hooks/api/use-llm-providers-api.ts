import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import type { ApiKind } from "@/features/settings/types"

export interface LlmProvider {
  name: string
  api_kind: ApiKind
  base_url: string
  // "***" when a key is stored, null when none is (never the raw secret).
  api_key: string | null
  used_by: string[]
  serves_verification: boolean
}

export interface LlmProvidersResponse {
  providers: LlmProvider[]
}

// Adds the field the PUT response carries beyond a GET row: purposes that
// were using this provider for embeddings and lost that capability because
// the new api_kind has none.
export interface UpdateLlmProviderResponse extends LlmProvider {
  no_embedding_purposes: string[]
}

export interface ProbeModelsResult {
  models: string[]
  fetched_via: string
  error: string | null
}

export interface CreateLlmProviderInput {
  name: string
  api_kind: ApiKind
  base_url: string
  api_key?: string | null
}

// Field-level PUT patch. `api_key` carries all four wire cases: omitted
// keeps the stored key, "***" round-trips it (also a keep), explicit null
// clears it, any other string replaces it.
export interface UpdateLlmProviderInput {
  api_kind?: ApiKind
  base_url?: string
  api_key?: string | null
}

export interface ProbeDraftInput {
  api_kind: ApiKind
  base_url: string
  api_key?: string | null
}

export function useLlmProviders() {
  return useQuery<LlmProvidersResponse>({
    queryKey: ["llmProviders"],
    queryFn: () => apiFetch<LlmProvidersResponse>("/config/llm-providers"),
  })
}

export function useCreateLlmProvider() {
  const qc = useQueryClient()
  return useMutation<LlmProvider, Error, CreateLlmProviderInput>({
    mutationFn: (data) =>
      apiFetch<LlmProvider>("/config/llm-providers", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      // A provider edit changes what every purpose resolves to.
      qc.invalidateQueries({ queryKey: ["llmProviders"] })
      qc.invalidateQueries({ queryKey: ["llmConfig"] })
    },
  })
}

export function useUpdateLlmProvider() {
  const qc = useQueryClient()
  return useMutation<
    UpdateLlmProviderResponse,
    Error,
    { name: string; data: UpdateLlmProviderInput }
  >({
    mutationFn: ({ name, data }) =>
      apiFetch<UpdateLlmProviderResponse>(
        `/config/llm-providers/${encodeURIComponent(name)}`,
        { method: "PUT", body: JSON.stringify(data) },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llmProviders"] })
      qc.invalidateQueries({ queryKey: ["llmConfig"] })
    },
  })
}

export function useDeleteLlmProvider() {
  const qc = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (name) =>
      apiFetch<void>(`/config/llm-providers/${encodeURIComponent(name)}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llmProviders"] })
      qc.invalidateQueries({ queryKey: ["llmConfig"] })
    },
  })
}

// Probes either a saved provider by name, or an unsaved draft — both wire
// shapes return HTTP 200 even when the vendor fails; `error` is information
// about the vendor, never a thrown request error.
export function useProbeProviderModels() {
  return useMutation<
    ProbeModelsResult,
    Error,
    { name: string } | { draft: ProbeDraftInput }
  >({
    mutationFn: (input) =>
      "name" in input
        ? apiFetch<ProbeModelsResult>(
            `/config/llm-providers/${encodeURIComponent(input.name)}/probe-models`,
            { method: "POST" },
          )
        : apiFetch<ProbeModelsResult>("/config/llm-providers/probe-models", {
            method: "POST",
            body: JSON.stringify(input.draft),
          }),
  })
}
