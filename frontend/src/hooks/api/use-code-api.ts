import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

export interface RepoStats {
  total_repos: number
  total_files: number
  total_symbols: number
  enrichment_pending: number
  enrichment_completed: number
}

export interface Repo {
  id: string
  name: string
  url: string | null
  local_path: string | null
  provider: string
  default_branch: string
  last_indexed_commit: string | null
  last_indexed_at: string | null
  status: string
  status_message: string | null
  auto_sync: boolean
  file_count: number
  symbol_count: number
  created_at: string
  updated_at: string
}

export interface RepoCreateParams {
  name: string
  url?: string
  local_path?: string
  provider?: string
  default_branch?: string
  auth_token?: string
  auto_sync?: boolean
}

export interface RepoUpdateParams {
  name?: string
  default_branch?: string
  auth_token?: string
  auto_sync?: boolean
  enrich_symbols?: boolean
  generate_wiki?: boolean
}

export interface CodeGraphNode {
  id: string
  label: string
  kind?: string
  language?: string
  file_path?: string
  symbol_count?: number
  properties?: Record<string, unknown> | null
}

export interface CodeGraphEdge {
  source: string
  target: string
  type: string
  properties?: Record<string, unknown> | null
}

export interface CodeGraphData {
  nodes: CodeGraphNode[]
  edges: CodeGraphEdge[]
}

export interface CodeSearchResult {
  chunk_content: string
  file_path: string
  repo_id: string
  language: string | null
  symbol_name: string | null
  line_start: number
  line_end: number
  score: number
}

export interface CodeSymbolResponse {
  id: string
  name: string
  kind: string
  file_path: string
  line_start: number
  line_end: number
  signature: string | null
  docstring: string | null
  visibility: string | null
  source_code: string
  summary: string | null
  enrichment_status: string
}

export interface CodeSymbolDetail {
  id: string
  name: string
  kind: string
  file_path: string | null
  line_start: number
  line_end: number
  signature: string | null
  docstring: string | null
  visibility: string | null
  source_code: string
  summary: string | null
  enrichment_status: string
}

export interface CodeSymbolListResult {
  items: CodeSymbolResponse[]
  total: number
}

export interface CodeSymbolsParams {
  repoId: string | null
  q?: string
  kind?: string
  filePath?: string
  offset?: number
  limit?: number
}

export interface BlastRadiusResult {
  symbol: { id: string; name: string; file_path: string | null }
  affected: Array<{
    key?: string
    name: string
    kind: string
    file_path: string
    distance: number
  }>
  by_depth: { "1": Array<unknown>; "2": Array<unknown>; "3+": Array<unknown> }
  risk: string
  total: number
}

export function useRepoStats() {
  return useQuery<RepoStats>({
    queryKey: ["repoStats"],
    queryFn: () => apiFetch("/repos/stats"),
  })
}

export function useRepos() {
  return useQuery<Repo[]>({
    queryKey: ["repos"],
    queryFn: () => apiFetch("/repos"),
  })
}

export interface RepoTask {
  id: string
  kind: string
  status: string
  message: string
  created_at: string
}

export function useRepoTasks(repoId: string | null) {
  return useQuery<RepoTask[]>({
    queryKey: ["repoTasks", repoId],
    queryFn: () => apiFetch(`/repos/${repoId}/tasks`),
    enabled: !!repoId,
  })
}

export function useCancelTask() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ repoId, taskId }: { repoId: string; taskId: string }) =>
      apiFetch(`/repos/${repoId}/tasks/${taskId}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["repoTasks"] })
      qc.invalidateQueries({ queryKey: ["repos"] })
    },
  })
}

export function useCreateRepo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: RepoCreateParams) =>
      apiFetch<Repo>("/repos", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["repos"] })
      qc.invalidateQueries({ queryKey: ["repoStats"] })
    },
  })
}

export function useUpdateRepo() {
  const qc = useQueryClient()
  return useMutation<Repo, Error, { id: string; data: RepoUpdateParams }>({
    mutationFn: ({ id, data }) =>
      apiFetch<Repo>(`/repos/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["repos"] })
      qc.invalidateQueries({ queryKey: ["repoStats"] })
    },
  })
}

export function useDeleteRepo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => apiFetch(`/repos/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["repos"] })
      qc.invalidateQueries({ queryKey: ["repoStats"] })
    },
  })
}

export function useReindexRepo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      options,
    }: {
      id: string
      options: { full?: boolean; enrich_symbols?: boolean; generate_wiki?: boolean }
    }) =>
      apiFetch(`/repos/${id}/reindex`, {
        method: "POST",
        body: JSON.stringify(options),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["repos"] })
      qc.invalidateQueries({ queryKey: ["repoStats"] })
    },
  })
}

export function useCodeGraph(repoId: string | null) {
  return useQuery<CodeGraphData>({
    queryKey: ["codeGraph", repoId],
    queryFn: () => apiFetch(`/code/graph/${repoId}`),
    enabled: !!repoId,
  })
}

export function useCodeSymbols({
  repoId,
  q,
  kind,
  filePath,
  offset = 0,
  limit = 50,
}: CodeSymbolsParams) {
  return useQuery<CodeSymbolListResult>({
    queryKey: ["codeSymbols", repoId, q, kind, filePath, offset, limit],
    queryFn: () => {
      const params = new URLSearchParams()
      if (repoId) params.set("repo_id", repoId)
      if (q) params.set("q", q)
      if (kind) params.set("kind", kind)
      if (filePath) params.set("file_path", filePath)
      params.set("offset", String(offset))
      params.set("limit", String(limit))
      return apiFetch(`/code/symbols?${params.toString()}`)
    },
    enabled: !!repoId,
  })
}

export function useCodeSearch() {
  return useMutation({
    mutationFn: (params: {
      query: string
      repo_id?: string
      language?: string
      limit?: number
    }) =>
      apiFetch<CodeSearchResult[]>("/code/search", {
        method: "POST",
        body: JSON.stringify(params),
      }),
  })
}

export function useCodeSymbolDetail(symbolId: string | null) {
  return useQuery<CodeSymbolDetail>({
    queryKey: ["codeSymbol", symbolId],
    queryFn: () => {
      if (!symbolId) throw new Error("No symbol ID")
      if (symbolId.includes("::")) {
        const [name = "", ...rest] = symbolId.split("::")
        const filePath = rest.join("::")
        return apiFetch(
          `/code/symbols/lookup?name=${encodeURIComponent(name)}&file_path=${encodeURIComponent(filePath)}`,
        )
      }
      return apiFetch(`/code/symbols/${symbolId}`)
    },
    enabled: !!symbolId,
  })
}

export function useBlastRadius() {
  return useMutation({
    mutationFn: (params: { symbol_id: string; max_depth?: number }) =>
      apiFetch<BlastRadiusResult>("/code/blast-radius", {
        method: "POST",
        body: JSON.stringify(params),
      }),
  })
}
