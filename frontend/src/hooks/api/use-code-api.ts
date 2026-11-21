import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

export interface RepoStats {
  total_repos: number
  total_files: number
  total_symbols: number
  enrichment_pending: number
  enrichment_completed: number
}

export interface IndexDebtRecord {
  at: string
  count: number
  commit: string
  vanished: number
}

// T1.39's debt contract: a bare `queued` count cannot distinguish a
// draining queue from a stuck one — same integer at a single instant.
// `last_drain`/`last_defer` carry the timestamp that makes the difference
// readable across a refetch.
export interface IndexDebtStatus {
  queued: number
  deferred_total: number
  drained_total: number
  last_defer: IndexDebtRecord | null
  last_drain: IndexDebtRecord | null
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
  fetch_enabled: boolean
  fetch_interval_seconds: number
  index_on_commit_enabled: boolean
  commit_poll_seconds: number
  index_uncommitted: boolean
  git_account_id: string | null
  // Denormalised by the server so a row renders its account without a
  // second lookup per repo.
  git_account_label: string | null
  // True when this repo carries its own token instead of using an account.
  has_custom_token: boolean
  file_count: number
  symbol_count: number
  index_debt: IndexDebtStatus
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
  // Omitted, the server stamps the provider's default account. Sent
  // explicitly — null included — the caller's choice wins.
  git_account_id?: string | null
  fetch_enabled?: boolean
  fetch_interval_seconds?: number
  index_on_commit_enabled?: boolean
  commit_poll_seconds?: number
  index_uncommitted?: boolean
}

export interface RepoUpdateParams {
  name?: string
  default_branch?: string
  auth_token?: string
  git_account_id?: string | null
  fetch_enabled?: boolean
  fetch_interval_seconds?: number
  index_on_commit_enabled?: boolean
  commit_poll_seconds?: number
  index_uncommitted?: boolean
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

/** What GET /code/graph/{repo_id} folded, answered only when the caller
 *  asked for a level or a scope. `file_edges` and the counts after it are
 *  present only at the file level. */
export interface CodeGraphStats {
  files: number
  symbols: number
  files_drawn?: number
  files_without_symbols?: number
  symbol_edges?: number
  file_edges?: number
  boundary_edges?: number
}

export type CodeGraphLevel = "symbol" | "file"

export interface CodeGraphData {
  nodes: CodeGraphNode[]
  edges: CodeGraphEdge[]
  level?: CodeGraphLevel
  requested_level?: CodeGraphLevel | "auto"
  scope?: string | null
  auto_limit?: number
  stats?: CodeGraphStats
}

export interface CodeGraphOptions {
  level?: CodeGraphLevel | "auto"
  /** A file or folder path; null draws the whole repository. */
  scope?: string | null
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
    queryFn: ({ signal }) => apiFetch("/repos/stats", { signal }),
  })
}

export function useRepos() {
  return useQuery<Repo[]>({
    queryKey: ["repos"],
    queryFn: ({ signal }) => apiFetch("/repos", { signal }),
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
    queryFn: ({ signal }) => apiFetch(`/repos/${repoId}/tasks`, { signal }),
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
      // Reindexing rewrites the code graph; without these the cached graph
      // serves stale data indefinitely (no window-focus refetch either).
      qc.invalidateQueries({ queryKey: ["codeGraph"] })
      qc.invalidateQueries({ queryKey: ["codeSymbols"] })
      qc.invalidateQueries({ queryKey: ["codeSymbol"] })
    },
  })
}

export function useCodeGraph(
  repoId: string | null,
  { level, scope }: CodeGraphOptions = {},
) {
  return useQuery<CodeGraphData>({
    // The repo id stays second so the indexing events' ["codeGraph"]
    // invalidation still reaches every level and scope.
    queryKey: ["codeGraph", repoId, level ?? null, scope ?? null],
    // Drilling into a folder asks for a new cache entry; holding the graph
    // already on screen keeps the page up until the narrower one lands. A
    // different repository never inherits another's graph.
    placeholderData: (previous, previousQuery) =>
      previousQuery?.queryKey[1] === repoId ? previous : undefined,
    queryFn: () => {
      const params = new URLSearchParams()
      if (level) params.set("level", level)
      if (scope) params.set("scope", scope)
      const query = params.toString()
      return apiFetch(`/code/graph/${repoId}${query ? `?${query}` : ""}`)
    },
    enabled: !!repoId,
  })
}

export interface CodeFile {
  id: string
  file_path: string
  language: string | null
  indexed_at: string
}

export function useCodeFiles(repoId: string | null) {
  return useQuery<CodeFile[]>({
    queryKey: ["codeFiles", repoId],
    queryFn: ({ signal }) => apiFetch(`/code/files/${repoId}`, { signal }),
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
        // Graph node ids are name::file_path[::owner] (graph_keys.compose_key);
        // file paths never contain "::", so segment [1] is always the path.
        // Joining the tail would smuggle the owner into file_path and 404
        // every method lookup. The owner disambiguates same-named methods
        // under different classes in one file.
        const [name = "", filePath = "", owner = ""] = symbolId.split("::")
        const params = new URLSearchParams({ name, file_path: filePath })
        if (owner) params.set("owner", owner)
        return apiFetch(`/code/symbols/lookup?${params.toString()}`)
      }
      return apiFetch(`/code/symbols/${symbolId}`)
    },
    enabled: !!symbolId,
  })
}

export interface SymbolCandidate {
  id: string
  key: string
  name: string
  kind: string
  file_path: string
  repo_id: string
}

/** The symbols a 409 `symbol_ambiguous` names, or null for any other error. */
export function symbolCandidates(err: unknown): SymbolCandidate[] | null {
  const e = err as { code?: unknown; candidates?: unknown } | null
  if (e?.code !== "symbol_ambiguous" || !Array.isArray(e.candidates)) return null
  return e.candidates as SymbolCandidate[]
}

export function useBlastRadius() {
  return useMutation({
    mutationFn: (params: {
      symbol_id: string
      repo_id: string
      max_depth?: number
    }) =>
      apiFetch<BlastRadiusResult>("/code/blast-radius", {
        method: "POST",
        body: JSON.stringify(params),
      }),
  })
}
