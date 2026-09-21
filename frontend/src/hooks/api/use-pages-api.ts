import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query"

import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
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
 *  here rather than at the view so callers need no page-specific row type,
 *  and so a re-read after a write and the pane read the one cache entry. */
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

export function invalidatePageLists(qc: QueryClient) {
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
