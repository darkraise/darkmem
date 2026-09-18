import { useEffect } from "react"
import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query"

import { apiFetch, apiFetchWithHeaders } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import { createMutationQueue } from "@/features/documents/lib/mutation-queue"
import type { BlockRow } from "./use-documents-api"

export interface PageListItem {
  id: string
  project: string
  parent_id: string | null
  order_index: number
  title: string | null
  content_hash: string
  properties: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface PageTrashItem {
  id: string
  title: string | null
  parent_id: string | null
  deleted_at: string
}

/** The wire row. `PageBlock` names its id `id` and its span as two columns,
 *  where the editor and `BlockView` both read `block_id` and `char_span`. */
interface PageBlockWire {
  id: string
  parent_id: string | null
  order_index: number | null
  type: string | null
  text: string | null
  properties: Record<string, unknown> | null
  char_start: number | null
  char_end: number | null
  source: string | null
}

interface PageWire {
  id: string
  project: string
  parent_id: string | null
  order_index: number
  title: string | null
  content_hash: string
  properties: Record<string, unknown> | null
  content: string | null
  blocks: PageBlockWire[]
}

/** A page and its blocks in the shape the editor already renders. Normalised
 *  here rather than at the view so the block editor and `BlockView` need no
 *  page-specific row type, and so the mutation queue's hash re-read and the
 *  pane read the one cache entry. */
export interface PageView {
  id: string
  project: string
  parent_id: string | null
  order_index: number
  title: string | null
  content_hash: string | null
  blocks: BlockRow[]
}

function toBlockRow(block: PageBlockWire): BlockRow {
  return {
    block_id: block.id,
    type: block.type,
    text: block.text ?? "",
    order_index: block.order_index,
    char_span:
      block.char_start === null || block.char_end === null
        ? null
        : [block.char_start, block.char_end],
    parent_id: block.parent_id,
    properties: block.properties,
    source: block.source,
  }
}

function toPageView(wire: PageWire): PageView {
  return {
    id: wire.id,
    project: wire.project,
    parent_id: wire.parent_id,
    order_index: wire.order_index,
    title: wire.title,
    content_hash: wire.content_hash,
    blocks: wire.blocks.map(toBlockRow),
  }
}

/** Shared so the queue's hash re-read resolves the same cache entry the pane
 *  renders from, rather than a second one under a duplicated key. */
export function pageQuery(pageId: string) {
  return {
    queryKey: ["page", pageId] as const,
    queryFn: async (): Promise<PageView> =>
      toPageView(await apiFetch<PageWire>(`/pages/${pageId}`)),
  }
}

/** Demo mode carries no page fixtures and no backend, so this read 401s there
 *  — and `handleUnauthorized` answers a 401 with a hard navigation to /login,
 *  which takes the page down rather than leaving the tree empty. */
export function usePages(project: string) {
  return useQuery<PageListItem[]>({
    queryKey: ["pages", project],
    queryFn: () =>
      apiFetch<PageListItem[]>(`/pages?project=${encodeURIComponent(project)}`),
    enabled: !DEMO,
  })
}

export function usePage(pageId: string | null) {
  return useQuery<PageView>({
    ...pageQuery(pageId ?? ""),
    enabled: !DEMO && Boolean(pageId),
  })
}

/** `open` gates the read: the trash is a sheet, and a closed sheet has no
 *  reason to hold a list the operator cannot see. */
export function usePagesTrash(project: string, open: boolean) {
  return useQuery<PageTrashItem[]>({
    queryKey: ["pagesTrash", project],
    queryFn: () =>
      apiFetch<PageTrashItem[]>(`/pages/trash?project=${encodeURIComponent(project)}`),
    enabled: !DEMO && open,
  })
}

export interface PageBlockWriteResponse {
  page_id: string
  block_id: string | null
  outcome: string
  content_hash: string
  blocks_total: number
  blocks_embedded: number
}

/** The batch route answers its own model: `block_ids`, and no `block_id`. */
export interface PageBlockBatchWriteResponse {
  page_id: string
  block_ids: string[]
  outcome: string
  content_hash: string
  blocks_total: number
  blocks_embedded: number
}

export interface NewPageBlock {
  block_id: string
  type: string
  text: string
  properties?: Record<string, unknown> | null
  parent_id?: string | null
  after_block_id?: string | null
}

function invalidatePageLists(qc: QueryClient) {
  void qc.invalidateQueries({ queryKey: ["pages"] })
  void qc.invalidateQueries({ queryKey: ["pagesTrash"] })
}

export function usePageCreate() {
  const qc = useQueryClient()
  return useMutation<
    { id: string },
    Error,
    {
      project: string
      title?: string | null
      parentId?: string | null
      afterId?: string | null
      content?: string | null
    }
  >({
    mutationFn: ({ project, title, parentId, afterId, content }) =>
      apiFetch<{ id: string }>("/pages", {
        method: "POST",
        body: JSON.stringify({
          project,
          title: title ?? null,
          parent_id: parentId ?? null,
          after_id: afterId ?? null,
          content: content ?? null,
        }),
      }),
    onSuccess: () => invalidatePageLists(qc),
  })
}

/** Rename and move are two hooks over one route because PATCH dispatches on
 *  field PRESENCE: a rename that also named `parent_id` would move the page to
 *  the root, and a move that also named `title` would rename it. */
export function usePageRename() {
  const qc = useQueryClient()
  return useMutation<{ id: string }, Error, { pageId: string; title: string | null }>({
    mutationFn: ({ pageId, title }) =>
      apiFetch<{ id: string }>(`/pages/${pageId}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
      }),
    onSuccess: (_data, { pageId }) => {
      invalidatePageLists(qc)
      void qc.invalidateQueries({ queryKey: ["page", pageId] })
    },
  })
}

export function usePageMove() {
  const qc = useQueryClient()
  return useMutation<
    { id: string },
    Error,
    { pageId: string; parentId: string | null; afterId: string | null }
  >({
    mutationFn: ({ pageId, parentId, afterId }) =>
      apiFetch<{ id: string }>(`/pages/${pageId}`, {
        method: "PATCH",
        body: JSON.stringify({ parent_id: parentId, after_id: afterId }),
      }),
    // Settled rather than succeeded: a refused move is exactly when the
    // optimistically reordered tree is known to be wrong.
    onSettled: () => invalidatePageLists(qc),
  })
}

export function usePageDelete() {
  const qc = useQueryClient()
  return useMutation<void, Error, string>({
    mutationFn: (pageId) => apiFetch<void>(`/pages/${pageId}`, { method: "DELETE" }),
    onSuccess: () => invalidatePageLists(qc),
  })
}

export function usePageRestore() {
  const qc = useQueryClient()
  return useMutation<{ restored: number }, Error, string>({
    mutationFn: (pageId) =>
      apiFetch<{ restored: number }>(`/pages/${pageId}/restore`, { method: "POST" }),
    onSuccess: () => invalidatePageLists(qc),
  })
}

export function usePageTrashEmpty() {
  const qc = useQueryClient()
  return useMutation<{ purged: number }, Error, string>({
    mutationFn: (project) =>
      apiFetch<{ purged: number }>(
        `/pages/trash/empty?project=${encodeURIComponent(project)}`,
        { method: "POST" },
      ),
    onSuccess: () => invalidatePageLists(qc),
  })
}

/** One queue per page, held outside React and created at its first write, so
 *  the update and the insert that follow one keystroke chain rather than both
 *  carrying the hash read before either started. */
const queues = new Map<string, ReturnType<typeof createMutationQueue>>()
const holders = new Map<string, number>()

function queueFor(pageId: string, qc: QueryClient) {
  const existing = queues.get(pageId)
  if (existing) return existing
  const seed = qc.getQueryData<PageView>(pageQuery(pageId).queryKey)?.content_hash ?? null
  const queue = createMutationQueue(seed, async () => {
    if (DEMO) return ""
    const data = await pageQuery(pageId).queryFn()
    return data.content_hash ?? ""
  })
  queues.set(pageId, queue)
  return queue
}

function useQueueLifetime(pageId: string) {
  useEffect(() => {
    holders.set(pageId, (holders.get(pageId) ?? 0) + 1)
    return () => {
      const left = (holders.get(pageId) ?? 1) - 1
      if (left > 0) {
        holders.set(pageId, left)
      } else {
        holders.delete(pageId)
        queues.delete(pageId)
      }
    }
  }, [pageId])
}

function usePageBlockMutation<V>(
  fn: (
    value: V,
    expectedHash: string,
  ) => Promise<{ content_hash: string | null } | void>,
  pageId: string,
) {
  const qc = useQueryClient()
  useQueueLifetime(pageId)
  return useMutation({
    mutationFn: (value: V) =>
      queueFor(pageId, qc).enqueue(async (hash) => {
        const result = await fn(value, hash)
        return { result, content_hash: result?.content_hash ?? null }
      }),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: ["page", pageId] })
      void qc.invalidateQueries({ queryKey: ["pages"] })
    },
  })
}

function precondition(hash: string) {
  return hash === "" ? undefined : hash
}

export function usePageBlockUpdate(pageId: string) {
  return usePageBlockMutation<{
    blockId: string
    text: string
    type?: string
    properties?: Record<string, unknown> | null
  }>(
    ({ blockId, text, type, properties }, expectedHash) =>
      apiFetch<PageBlockWriteResponse>(`/pages/${pageId}/blocks/${blockId}`, {
        method: "PATCH",
        body: JSON.stringify({
          text,
          type,
          properties,
          expected_hash: precondition(expectedHash),
        }),
      }),
    pageId,
  )
}

export function usePageBlockInsert(pageId: string) {
  return usePageBlockMutation<{
    type: string
    text: string
    parentId?: string | null
    afterBlockId?: string | null
    properties?: Record<string, unknown> | null
    blockId?: string
  }>(
    ({ type, text, parentId, afterBlockId, properties, blockId }, expectedHash) =>
      apiFetch<PageBlockWriteResponse>(`/pages/${pageId}/blocks`, {
        method: "POST",
        body: JSON.stringify({
          type,
          text,
          parent_id: parentId ?? null,
          after_block_id: afterBlockId ?? null,
          properties: properties ?? null,
          block_id: blockId,
          expected_hash: precondition(expectedHash),
        }),
      }),
    pageId,
  )
}

export function usePageBlockMove(pageId: string) {
  return usePageBlockMutation<{
    blockId: string
    newParentId?: string | null
    afterBlockId?: string | null
  }>(
    ({ blockId, newParentId, afterBlockId }, expectedHash) =>
      apiFetch<PageBlockWriteResponse>(`/pages/${pageId}/blocks/${blockId}/move`, {
        method: "POST",
        body: JSON.stringify({
          new_parent_id: newParentId ?? null,
          after_block_id: afterBlockId ?? null,
          expected_hash: precondition(expectedHash),
        }),
      }),
    pageId,
  )
}

export function usePageBlockDelete(pageId: string) {
  return usePageBlockMutation<{ blockId: string }>(
    async ({ blockId }, expectedHash) => {
      // The hash rides the query string because DELETE carries no body, and
      // comes back in a header because a 204 carries none either -- which is
      // what spares the next write a re-read.
      const query = precondition(expectedHash)
        ? `?expected_hash=${encodeURIComponent(expectedHash)}`
        : ""
      const { headers } = await apiFetchWithHeaders<void>(
        `/pages/${pageId}/blocks/${blockId}${query}`,
        { method: "DELETE" },
      )
      return { content_hash: headers.get("X-Content-Hash") }
    },
    pageId,
  )
}

export function usePageBlocksInsertBatch(pageId: string) {
  return usePageBlockMutation<{ blocks: NewPageBlock[] }>(
    ({ blocks }, expectedHash) =>
      apiFetch<PageBlockBatchWriteResponse>(`/pages/${pageId}/blocks/batch`, {
        method: "POST",
        body: JSON.stringify({
          blocks,
          expected_hash: precondition(expectedHash),
        }),
      }),
    pageId,
  )
}
