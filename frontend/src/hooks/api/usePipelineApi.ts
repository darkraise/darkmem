import { useState, useCallback, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch, getAuthToken } from "@/lib/api";

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

export interface ReprocessProgress {
  current: number;
  total: number;
  processed: number;
  errors: number;
  memoryId?: string;
  status?: string;
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

export function useReprocessStream(endpoint: "/analytics/reprocess/stream" | "/analytics/reprocess-failed/stream") {
  const qc = useQueryClient();
  const [isPending, setIsPending] = useState(false);
  const [progress, setProgress] = useState<ReprocessProgress | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const mutate = useCallback(async () => {
    if (isPending) return;
    setIsPending(true);
    setProgress(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const token = getAuthToken();
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`/api/v1${endpoint}`, {
        method: "POST",
        headers,
        signal: controller.signal,
      });

      if (!res.ok) throw new Error(`Reprocess failed: ${res.status}`);
      if (!res.body) throw new Error("No response body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data: ")) continue;
          const event = JSON.parse(trimmed.slice(6));

          if (event.type === "start") {
            setProgress({ current: 0, total: event.total, processed: 0, errors: 0 });
          } else if (event.type === "progress") {
            setProgress({
              current: event.current,
              total: event.total,
              processed: event.processed,
              errors: event.errors,
              memoryId: event.memory_id,
              status: event.status,
            });
          } else if (event.type === "done") {
            setProgress({
              current: event.total,
              total: event.total,
              processed: event.processed,
              errors: event.errors,
            });
          }
        }
      }

      qc.invalidateQueries({ queryKey: ["pipelineLogs"] });
      qc.invalidateQueries({ queryKey: ["stats"] });
    } finally {
      setIsPending(false);
      abortRef.current = null;
    }
  }, [endpoint, isPending, qc]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { mutate, isPending, progress, cancel };
}

export interface OverviewData {
  counts: {
    memories: number;
    tags: number;
    entities: number | null;
    relationships: number | null;
  };
  activity: Array<{ date: string; count: number }>;
  sources: Array<{ name: string; count: number }>;
  top_tags: Array<{ name: string; count: number }>;
  recent_memories: Array<{
    id: string;
    content: string;
    source: string;
    memory_type: string | null;
    tags: string[];
    created_at: string;
  }>;
  recent_errors: number;
}

export function useOverview(days: number = 7) {
  return useQuery<OverviewData>({
    queryKey: ["overview", days],
    queryFn: () => apiFetch(`/analytics/overview?days=${days}`),
  });
}
