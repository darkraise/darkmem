import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import type { MemoryStatus } from "./use-memory-api"

export interface ChatConversation {
  id: string
  title: string | null
  created_at: string
  updated_at: string
  is_archived: boolean
  message_count?: number
}

export interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  context: {
    memories?: {
      id: string
      score: number
      content?: string
      source?: string
      tags?: string[]
      created_at?: string
      // scope_labels already puts both on the persisted wire (T1.60 §5) —
      // a type-completeness fix, not a wire change.
      project?: string
      status?: MemoryStatus
    }[]
    entities?: { id: string; name: string; entity_type?: string }[]
  } | null
  created_at: string
}

export interface ChatConversationDetail {
  id: string
  title: string | null
  created_at: string
  updated_at: string
  messages: ChatMessage[]
}

export function useConversations(archived = false) {
  return useQuery<{ conversations: ChatConversation[] }>({
    queryKey: ["conversations", archived],
    queryFn: () => apiFetch(`/chat/conversations?archived=${archived}`),
  })
}

export function useConversation(id: string | null) {
  return useQuery<ChatConversationDetail>({
    queryKey: ["conversation", id],
    queryFn: () => apiFetch(`/chat/conversations/${id}`),
    enabled: !!id,
  })
}

export function useCreateConversation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { title?: string }) =>
      apiFetch<ChatConversation>("/chat/conversations", {
        method: "POST",
        body: JSON.stringify(data),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
  })
}

export function useUpdateConversation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      ...data
    }: {
      id: string
      title?: string
      is_archived?: boolean
    }) =>
      apiFetch<ChatConversation>(`/chat/conversations/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["conversations"] })
      // The open detail pane is keyed ['conversation', id]; without this a
      // rename/archive leaves the open view stale.
      qc.invalidateQueries({ queryKey: ["conversation", variables.id] })
    },
  })
}

export function useDeleteConversation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/chat/conversations/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
  })
}
