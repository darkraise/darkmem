import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import type {
  ChatContextFact,
  ChatContextRow,
  ChatRetrievalEnvelope,
} from "@/features/chat/lib/retrieval"

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
    // The persisted snapshot carries the same rows the live `sources` event
    // did, trimmed, plus the envelope the turn answered under: a panel
    // rendering history must be able to say the same things about it as the
    // panel that watched it stream.
    memories?: ChatContextRow[]
    facts?: ChatContextFact[]
    envelope?: ChatRetrievalEnvelope | null
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
