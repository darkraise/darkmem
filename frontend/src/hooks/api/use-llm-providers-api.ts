import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import { useDemoStore } from "@/demo/store"
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

// What the server sends in place of a stored key, and what a caller sends
// back to say "leave the key alone".
export const MASKED_PROVIDER_KEY = "***"

// Full-replace PUT body, not a patch: `api_kind` and `base_url` are required
// on the wire, and omitting either is a 422 rather than a partial update.
// `api_key` is the one exception — the server never returns the real secret,
// so it carries three cases: MASKED_PROVIDER_KEY keeps the stored key,
// explicit null clears it, any other string replaces it.
export interface UpdateLlmProviderInput {
  api_kind: ApiKind
  base_url: string
  api_key?: string | null
}

export interface ProbeDraftInput {
  api_kind: ApiKind
  base_url: string
  api_key?: string | null
}

/** The demo's provider rows, read off the purposes that name them. */
function demoProviders(): LlmProvidersResponse {
  const rows = new Map<string, LlmProvider>()
  for (const purpose of useDemoStore.getState().llm.purposes) {
    const row = rows.get(purpose.provider_name) ?? {
      name: purpose.provider_name,
      api_kind: purpose.api_kind,
      base_url: purpose.base_url,
      api_key: purpose.api_key ? MASKED_PROVIDER_KEY : null,
      used_by: [],
      serves_verification: false,
    }
    row.used_by.push(purpose.purpose)
    rows.set(purpose.provider_name, row)
  }
  return { providers: [...rows.values()] }
}

const demoRefusal = () =>
  Promise.reject(new Error("Provider connections are read-only in the demo"))

function demoProbe(name: string | null): ProbeModelsResult {
  const models = useDemoStore
    .getState()
    .llm.purposes.filter((p) => name === null || p.provider_name === name)
    .map((p) => p.model)
  return { models: [...new Set(models)], fetched_via: "demo", error: null }
}

export function useLlmProviders() {
  return useQuery<LlmProvidersResponse>({
    queryKey: ["llmProviders"],
    queryFn: ({ signal }) =>
      DEMO
        ? Promise.resolve(demoProviders())
        : apiFetch<LlmProvidersResponse>("/config/llm-providers", { signal }),
  })
}

export function useCreateLlmProvider() {
  const qc = useQueryClient()
  return useMutation<LlmProvider, Error, CreateLlmProviderInput>({
    mutationFn: (data) =>
      DEMO
        ? demoRefusal()
        : apiFetch<LlmProvider>("/config/llm-providers", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      // A provider edit changes what every purpose resolves to.
      qc.invalidateQueries({ queryKey: ["llmProviders"] })
      qc.invalidateQueries({ queryKey: ["llmConfig"] })
      qc.invalidateQueries({ queryKey: ["health"] })
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
      DEMO
        ? demoRefusal()
        : apiFetch<UpdateLlmProviderResponse>(
        `/config/llm-providers/${encodeURIComponent(name)}`,
        { method: "PUT", body: JSON.stringify(data) },
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llmProviders"] })
      qc.invalidateQueries({ queryKey: ["llmConfig"] })
      qc.invalidateQueries({ queryKey: ["health"] })
    },
  })
}

export function useDeleteLlmProvider() {
  const qc = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (name) =>
      DEMO
        ? demoRefusal()
        : apiFetch<void>(`/config/llm-providers/${encodeURIComponent(name)}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llmProviders"] })
      qc.invalidateQueries({ queryKey: ["llmConfig"] })
      qc.invalidateQueries({ queryKey: ["health"] })
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
      DEMO
        ? Promise.resolve(demoProbe("name" in input ? input.name : null))
        : "name" in input
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
