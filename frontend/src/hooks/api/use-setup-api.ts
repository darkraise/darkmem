import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { useAuthStore } from "@/features/auth"

export type ProbeModelsRequest = {
  api_kind: "openai" | "anthropic" | "ollama" | "google" | "deepseek" | "zai"
  base_url: string
  api_key?: string | null
}

export type ProbeModelsResponse = {
  models: string[]
  fetched_via: string
  error: string | null
}

export type FsRoot = { path: string; label: string }
export type FsRootsResponse = { roots: FsRoot[] }

export type FsListEntry = {
  name: string
  path: string
  is_dir: boolean
  is_git: boolean
  has_repos: boolean
  repo_count: number
}

export type FsListResponse = {
  path: string
  parent: string | null
  entries: FsListEntry[]
  is_git: boolean
  blocked_reason: string | null
}

export type SetupRepoSelection = { name: string; sub_path: string }

export type SetupProvider = {
  name: string
  api_kind: "openai" | "anthropic" | "ollama" | "google" | "deepseek" | "zai"
  base_url: string
  api_key?: string | null
}

export type SetupLLMPurpose = {
  provider_name: string
  model: string
  reasoning: boolean
  dimensions?: number | null
}

export type SetupLLM = {
  providers: SetupProvider[]
  purposes: Partial<
    Record<
      | "embedding"
      | "extraction"
      | "classification"
      | "reasoning"
      | "summarization"
      | "reranker",
      SetupLLMPurpose
    >
  >
}

export type SetupRequest = {
  password: string
  llm?: SetupLLM | null
  repos?: {
    base_path: string
    repos: SetupRepoSelection[]
  } | null
}

export type SetupSectionStatus = { ok: boolean; message: string | null }

export type SetupResponse = {
  password: SetupSectionStatus
  llm: SetupSectionStatus
  repos: SetupSectionStatus
  repos_added: string[]
  repos_failed: { name: string; error: string }[]
}

const API_BASE = "/api/v1"

// Single transparent retry on 502/503/504. The setup wizard sits idle on
// step 2 while the user types an API key, and the dev proxy can serve a
// stale keep-alive socket on the next click; that surfaces as 502 even
// though no real request reached the backend. A retry on a fresh socket
// always lands. The check is gated to the gateway-error range so genuine
// 4xx and 5xx-from-the-handler are not retried.
async function rawFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  }
  const doFetch = () =>
    fetch(`${API_BASE}${path}`, { ...init, headers, credentials: "include" })

  let response: Response
  try {
    response = await doFetch()
    if ([502, 503, 504].includes(response.status)) {
      response = await doFetch()
    }
  } catch {
    // The retry IS the handling: a transport-level failure on the first
    // attempt is retried once, exactly as a 502/503/504 is above.
    response = await doFetch()
  }

  if (!response.ok) {
    const errBody = await response
      .json()
      .catch(() => ({ detail: response.statusText }))
    throw new Error(
      (errBody as { detail?: string }).detail || `HTTP ${response.status}`,
    )
  }
  return response.json() as Promise<T>
}

// The wizard's model list for one provider's connection details, as a query
// keyed on them: every purpose row and the provider's own row read one probe
// and one answer, so a failure is reported once, on the provider, rather than
// once per purpose that picked it.
export function useSetupProviderModels(
  provider: ProbeModelsRequest | undefined,
) {
  return useQuery<ProbeModelsResponse>({
    queryKey: [
      "setupProbe",
      provider?.api_kind,
      provider?.base_url,
      provider?.api_key ?? null,
    ],
    queryFn: () =>
      rawFetch<ProbeModelsResponse>("/setup/probe-models", {
        method: "POST",
        body: JSON.stringify(provider),
      }),
    enabled: Boolean(provider?.base_url),
    retry: false,
    staleTime: 60_000,
  })
}

export function useFsRoots(apiBase: "/setup" | "/system") {
  return useQuery<FsRootsResponse>({
    queryKey: ["fs", apiBase, "roots"],
    queryFn: () =>
      apiBase === "/setup"
        ? rawFetch<FsRootsResponse>("/setup/fs/roots")
        : apiFetch<FsRootsResponse>("/system/fs/roots"),
  })
}

export async function fsList(
  apiBase: "/setup" | "/system",
  path: string,
  detectRepos = false,
): Promise<FsListResponse> {
  const qs = new URLSearchParams({ path, detect_repos: String(detectRepos) })
  if (apiBase === "/setup") {
    return rawFetch<FsListResponse>(`/setup/fs/list?${qs.toString()}`)
  }
  return apiFetch<FsListResponse>(`/system/fs/list?${qs.toString()}`)
}

export function useFinalizeSetup() {
  return useMutation<SetupResponse, Error, SetupRequest>({
    mutationFn: async (body) => {
      const result = await rawFetch<SetupResponse>("/setup", {
        method: "POST",
        body: JSON.stringify(body),
      })
      useAuthStore.getState().setAuthenticated(true)
      return result
    },
  })
}

export function useReposPath() {
  return useQuery<{ path: string | null }>({
    queryKey: ["reposPath"],
    queryFn: ({ signal }) => apiFetch<{ path: string | null }>("/config/repos-path", { signal }),
  })
}

export function useUpdateReposPath() {
  const qc = useQueryClient()
  return useMutation<{ path: string | null }, Error, { path: string }>({
    mutationFn: (body) =>
      apiFetch<{ path: string | null }>("/config/repos-path", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reposPath"] }),
  })
}
