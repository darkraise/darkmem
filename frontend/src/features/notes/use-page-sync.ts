import { useEffect, useMemo, useSyncExternalStore } from "react"
import { useQueryClient, type QueryClient } from "@tanstack/react-query"
import { toast } from "darkraise-ui/components/sonner"
import { pageQuery, type PageView } from "@/hooks/api"
import {
  canonicalTree,
  fromPageBlocks,
  toEditorBlocks,
  toSyncTree,
  type EditorBlockLike,
  type TableRowIds,
} from "./lib/block-mapping"
import { PageSync, type PageTransport, type SyncStatus } from "./lib/page-sync"
import { createPageTransport } from "./lib/page-transport"
import type { SyncTree } from "./lib/sync-tree"

/** How long typing may pause before the text it produced is saved. */
export const TEXT_IDLE_MS = 800

interface Entry {
  sync: PageSync
  rowIds: TableRowIds
  title: string
  mounted: number
  timer: ReturnType<typeof setTimeout> | null
  queryClient: QueryClient
}

/** One engine per page, outside React, so a page's unsaved work keeps
 *  draining after its pane unmounts and a page that is reopened mid-drain
 *  shows the work rather than the older server copy. */
const engines = new Map<string, Entry>()

function anyPending(): boolean {
  for (const entry of engines.values()) if (entry.sync.pending) return true
  return false
}

function flushEntry(entry: Entry) {
  if (entry.timer !== null) clearTimeout(entry.timer)
  entry.timer = null
  void entry.sync.flush()
}

function flushAll() {
  for (const entry of engines.values()) flushEntry(entry)
}

/** Discards a finished engine whose page nothing shows, together with the
 *  page's cached read: that read predates every edit the engine sent, and a
 *  page reopened from it would show old content and meet its own writes as a
 *  change made elsewhere. */
function release(pageId: string, entry: Entry) {
  if (entry.mounted !== 0 || entry.sync.pending || engines.get(pageId) !== entry) return
  engines.delete(pageId)
  entry.queryClient.removeQueries({ queryKey: pageQuery(pageId).queryKey, exact: true })
}

function acquire(
  page: PageView,
  createTransport: (pageId: string) => PageTransport,
  queryClient: QueryClient,
): Entry {
  const existing = engines.get(page.id)
  if (existing) return existing
  const { tree, rowIds } = canonicalTree(fromPageBlocks(page.blocks))
  const entry: Entry = {
    sync: new PageSync(tree, page.content_hash ?? "", createTransport(page.id)),
    rowIds,
    title: page.title?.trim() || "Untitled",
    mounted: 0,
    timer: null,
    queryClient,
  }
  entry.sync.subscribe((status) => {
    if (status.kind === "stopped" && entry.mounted === 0) {
      toast.error(`“${entry.title}” was not saved — ${status.message}`)
    }
  })
  entry.sync.onSettled(() => release(page.id, entry))
  engines.set(page.id, entry)
  return entry
}

function mount(entry: Entry) {
  entry.mounted++
}

function unmount(pageId: string, entry: Entry) {
  entry.mounted--
  flushEntry(entry)
  release(pageId, entry)
}

/** The editor blocks to mount, from the engine's desired tree: the server's
 *  copy for a fresh engine, the unsent work for one still draining. */
function mountBlocks(entry: Entry): EditorBlockLike[] {
  const { blocks, rowIds } = toEditorBlocks(entry.sync.desired)
  entry.rowIds = rowIds
  return blocks
}

function acceptDocument(entry: Entry, blocks: EditorBlockLike[]) {
  const before = entry.sync.desired
  const { tree, rowIds } = toSyncTree(blocks, entry.sync.snapshot, entry.rowIds, () => crypto.randomUUID())
  entry.rowIds = rowIds
  entry.sync.setDesired(tree)
  if (!sameShape(before, tree)) {
    flushEntry(entry)
    return
  }
  if (entry.timer !== null) clearTimeout(entry.timer)
  entry.timer = setTimeout(() => flushEntry(entry), TEXT_IDLE_MS)
}

function discard(pageId: string, entry: Entry) {
  if (entry.timer !== null) clearTimeout(entry.timer)
  if (engines.get(pageId) === entry) engines.delete(pageId)
}

/** Same blocks under the same parents in the same order with the same
 *  types: a change that keeps this is typing, anything else is structure. */
function sameShape(a: SyncTree, b: SyncTree): boolean {
  return a.length === b.length && a.every((x, i) => {
    const y = b[i]!
    return x.id === y.id && x.parentId === y.parentId && x.type === y.type
  })
}

export interface PageSyncBinding {
  initialBlocks: EditorBlockLike[]
  status: SyncStatus
  onDocumentChange: (blocks: EditorBlockLike[]) => void
  flushNow: () => void
  /** Drops the engine and any work it had not sent. */
  discard: () => void
}

/** Binds one mounted editor to its page's save engine. `generation` moves
 *  on a reload so a fresh engine is built from the fresh read. */
export function usePageSync(
  page: PageView,
  generation: number,
  createTransport: (pageId: string) => PageTransport = createPageTransport,
): PageSyncBinding {
  const queryClient = useQueryClient()
  const entry = useMemo(
    () => acquire(page, createTransport, queryClient),
    // The page's later reads must not rebuild the engine: the editor owns
    // the content once mounted, and only a reload replaces it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [page.id, generation],
  )

  const initialBlocks = useMemo(() => mountBlocks(entry), [entry])

  const status = useSyncExternalStore(
    (onChange) => entry.sync.subscribe(onChange),
    () => entry.sync.status,
  )

  useEffect(() => {
    mount(entry)
    return () => unmount(page.id, entry)
  }, [entry, page.id])

  useEffect(() => {
    const onHidden = () => {
      if (document.visibilityState === "hidden") flushAll()
    }
    const onLeave = (event: BeforeUnloadEvent) => {
      if (!anyPending()) return
      event.preventDefault()
      event.returnValue = ""
    }
    document.addEventListener("visibilitychange", onHidden)
    window.addEventListener("beforeunload", onLeave)
    return () => {
      document.removeEventListener("visibilitychange", onHidden)
      window.removeEventListener("beforeunload", onLeave)
    }
  }, [])

  return useMemo(
    () => ({
      initialBlocks,
      status,
      onDocumentChange: (blocks: EditorBlockLike[]) => acceptDocument(entry, blocks),
      flushNow: () => flushEntry(entry),
      discard: () => discard(page.id, entry),
    }),
    [entry, initialBlocks, page.id, status],
  )
}

/** Test hook: forget every engine between tests. */
export function resetPageSyncEngines() {
  for (const entry of engines.values()) if (entry.timer !== null) clearTimeout(entry.timer)
  engines.clear()
}
