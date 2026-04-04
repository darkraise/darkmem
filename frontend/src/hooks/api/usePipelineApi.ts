import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface Stats {
  memories: number;
  tags: number;
  entities: number | null;
  relationships: number | null;
  sources: string[];
}

export interface HealthStatus {
  status: string;
  pipeline: boolean;
  services: { qdrant: boolean; neo4j: boolean; llm: boolean };
}

export interface PipelineLog {
  id: number;
  memory_id: string | null;
  details: Record<string, unknown>;
  timestamp: string;
}

export function useStats() {
  return useQuery<Stats>({ queryKey: ["stats"], queryFn: () => apiFetch("/analytics/stats") });
}

export function useHealth() {
  return useQuery<HealthStatus>({
    queryKey: ["health"],
    queryFn: async () => {
      const res = await fetch("/health");
      return res.json();
    },
    refetchInterval: 30000,
  });
}

export function usePipelineLogs(limit = 10) {
  return useQuery<PipelineLog[]>({
    queryKey: ["pipelineLogs", limit],
    queryFn: () => apiFetch(`/analytics/pipeline-logs?limit=${limit}`),
  });
}

export function useReprocessAll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<{ processed: number; errors: number; total: number }>("/analytics/reprocess", { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipelineLogs"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });
}

export function useReprocessFailed() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiFetch<{ processed: number; errors: number; total: number }>("/analytics/reprocess-failed", { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pipelineLogs"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    },
  });
}
