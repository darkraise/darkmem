import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface RepoStats {
  total_repos: number;
  total_files: number;
  total_symbols: number;
  enrichment_pending: number;
  enrichment_completed: number;
}

export interface Repo {
  id: string;
  name: string;
  url: string | null;
  local_path: string | null;
  provider: string;
  default_branch: string;
  last_indexed_commit: string | null;
  last_indexed_at: string | null;
  sync_interval_minutes: number;
  status: string;
  status_message: string | null;
  is_active: boolean;
  file_count: number;
  symbol_count: number;
  created_at: string;
  updated_at: string;
}

export interface RepoCreateParams {
  name: string;
  url?: string;
  local_path?: string;
  provider?: string;
  default_branch?: string;
  auth_token?: string;
  sync_interval_minutes?: number;
}

export interface CodeGraphNode {
  id: string;
  label: string;
  kind?: string;
  language?: string;
  file_path?: string;
  symbol_count?: number;
}

export interface CodeGraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface CodeGraphData {
  nodes: CodeGraphNode[];
  edges: CodeGraphEdge[];
}

export interface CodeSearchResult {
  chunk_content: string;
  file_path: string;
  repo_id: string;
  language: string | null;
  symbol_name: string | null;
  line_start: number;
  line_end: number;
  score: number;
}

export interface CodeSymbolDetail {
  id: string;
  name: string;
  kind: string;
  file_path: string | null;
  line_start: number;
  line_end: number;
  signature: string | null;
  docstring: string | null;
  visibility: string | null;
  source_code: string;
  summary: string | null;
  enrichment_status: string;
}

export interface BlastRadiusResult {
  source: { id: string; name: string; file_path: string | null };
  affected: Array<{ name: string; kind: string; file_path: string }>;
  total_affected: number;
}

export function useRepoStats() {
  return useQuery<RepoStats>({
    queryKey: ["repoStats"],
    queryFn: () => apiFetch("/repos/stats"),
  });
}

export function useRepos(refetchInterval?: number) {
  return useQuery<Repo[]>({
    queryKey: ["repos"],
    queryFn: () => apiFetch("/repos"),
    refetchInterval,
  });
}

export interface RepoTask {
  id: string;
  kind: string;
  status: string;
  message: string;
  created_at: string;
}

export function useRepoTasks(repoId: string | null) {
  return useQuery<RepoTask[]>({
    queryKey: ["repoTasks", repoId],
    queryFn: () => apiFetch(`/repos/${repoId}/tasks`),
    enabled: !!repoId,
    refetchInterval: 3000,
  });
}

export function useCancelTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ repoId, taskId }: { repoId: string; taskId: string }) =>
      apiFetch(`/repos/${repoId}/tasks/${taskId}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["repoTasks"] });
      qc.invalidateQueries({ queryKey: ["repos"] });
    },
  });
}

export function useCreateRepo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: RepoCreateParams) =>
      apiFetch<Repo>("/repos", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["repos"] });
      qc.invalidateQueries({ queryKey: ["repoStats"] });
    },
  });
}

export function useDeleteRepo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch(`/repos/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["repos"] });
      qc.invalidateQueries({ queryKey: ["repoStats"] });
    },
  });
}

export function useReindexRepo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch(`/repos/${id}/reindex`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["repos"] });
      qc.invalidateQueries({ queryKey: ["repoStats"] });
    },
  });
}

export function useCodeGraph(repoId: string | null, view: "files" | "symbols" = "symbols") {
  return useQuery<CodeGraphData>({
    queryKey: ["codeGraph", repoId, view],
    queryFn: () => apiFetch(`/code/graph/${repoId}?view=${view}`),
    enabled: !!repoId,
  });
}

export function useCodeSearch() {
  return useMutation({
    mutationFn: (params: { query: string; repo_id?: string; language?: string; limit?: number }) =>
      apiFetch<CodeSearchResult[]>("/code/search", { method: "POST", body: JSON.stringify(params) }),
  });
}

export function useCodeSymbolDetail(symbolId: string | null) {
  return useQuery<CodeSymbolDetail>({
    queryKey: ["codeSymbol", symbolId],
    queryFn: () => apiFetch(`/code/symbols/${symbolId}`),
    enabled: !!symbolId,
  });
}

export function useBlastRadius() {
  return useMutation({
    mutationFn: (params: { symbol_id: string; max_depth?: number }) =>
      apiFetch<BlastRadiusResult>("/code/blast-radius", { method: "POST", body: JSON.stringify(params) }),
  });
}
