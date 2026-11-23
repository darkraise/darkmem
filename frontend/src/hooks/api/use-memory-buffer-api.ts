import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"

/** One buffered capture as `GET /api/v1/memory-buffer` serves it.
 *  `memory_id` is the pre-minted id the capture's ack carried; `memory_exists`
 *  says whether the replay wrote that memory row before it failed, which a
 *  discard then deletes too. */
export interface BufferRow {
  id: string
  memory_id: string | null
  memory_exists: boolean
  project: string
  source: string | null
  status: string
  is_stale: boolean
  attempts: number
  max_attempts: number
  last_error: string | null
  created_at: string
  claimed_at: string | null
  claimed_by: string | null
  token_size: number | null
  content_preview: string
  content_length: number
}

export interface BufferList {
  items: BufferRow[]
  total: number
  limit: number
  offset: number
}

/** The route's page ceiling: the section lists the newest page and says how
 *  many more exist rather than paging a triage queue. */
export const FAILED_CAPTURES_LIMIT = 200

const EMPTY: BufferList = {
  items: [],
  total: 0,
  limit: FAILED_CAPTURES_LIMIT,
  offset: 0,
}

export function useMemoryBufferItems() {
  const query = useQuery<BufferList>({
    queryKey: ["memoryBuffer", "poison"],
    queryFn: ({ signal }) =>
      apiFetch<BufferList>(
        `/memory-buffer?state=poison&limit=${FAILED_CAPTURES_LIMIT}`, { signal }),
    enabled: !DEMO,
  })
  const data = query.data ?? EMPTY
  return {
    items: data.items,
    total: data.total,
    isLoading: !DEMO && query.isLoading,
    isError: !DEMO && query.isError,
  }
}

export function useDiscardBufferItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<void>(`/memory-buffer/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memoryBuffer"] })
    },
  })
}

export function useRequeueBufferItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch<BufferRow>(`/memory-buffer/${id}/requeue`, { method: "POST" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memoryBuffer"] })
    },
  })
}
