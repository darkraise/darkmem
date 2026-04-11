import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface ChatConversation {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  is_archived: boolean;
  message_count?: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  context: {
    memories?: { id: string; score: number; content?: string; source?: string; tags?: string[]; created_at?: string }[];
    entities?: { id: string; name: string; entity_type?: string }[];
  } | null;
  created_at: string;
}

export interface ChatConversationDetail {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export function useConversations(archived = false) {
  return useQuery<{ conversations: ChatConversation[] }>({
    queryKey: ["conversations", archived],
    queryFn: () => apiFetch(`/chat/conversations?archived=${archived}`),
  });
}

export function useConversation(id: string | null) {
  return useQuery<ChatConversationDetail>({
    queryKey: ["conversation", id],
    queryFn: () => apiFetch(`/chat/conversations/${id}`),
    enabled: !!id,
  });
}

export function useCreateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { title?: string }) =>
      apiFetch<ChatConversation>("/chat/conversations", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
  });
}

export function useUpdateConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string; title?: string; is_archived?: boolean }) =>
      apiFetch<ChatConversation>(`/chat/conversations/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
    },
  });
}

export function useDeleteConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/chat/conversations/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
  });
}
