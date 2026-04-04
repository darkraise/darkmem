import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface Memory {
  id: string;
  content: string;
  source: string;
  source_agent: string | null;
  memory_type: string | null;
  importance: number;
  metadata: Record<string, unknown>;
  tags: string[];
  created_at: string;
  updated_at: string;
  expires_at: string | null;
  is_archived: boolean;
}

export interface Tag {
  id: number;
  name: string;
  category: string | null;
  memory_count: number;
}

export function useMemories() {
  return useQuery<Memory[]>({
    queryKey: ["memories"],
    queryFn: () => apiFetch("/memories/search", { method: "POST", body: JSON.stringify({ limit: 50 }) }),
  });
}

export function useMemory(id: string) {
  return useQuery<Memory>({
    queryKey: ["memory", id],
    queryFn: () => apiFetch(`/memories/${id}`),
    enabled: !!id,
  });
}

export function useCreateMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { content: string; tags?: string[]; source?: string }) =>
      apiFetch<Memory>("/memories", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["memories"] }),
  });
}

export function useDeleteMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch(`/memories/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["memories"] }),
  });
}

export function useSearchMemories() {
  return useMutation({
    mutationFn: (params: { query?: string; tags_any?: string[]; limit?: number }) =>
      apiFetch<Memory[]>("/memories/search", { method: "POST", body: JSON.stringify(params) }),
  });
}

export function useTags() {
  return useQuery<Tag[]>({ queryKey: ["tags"], queryFn: () => apiFetch("/tags") });
}
