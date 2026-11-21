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
import { subscribeUploads, uploadsInFlight } from "./lib/attachments"
import { PageSync, type PageTransport, type SyncStatus } from "./lib/page-sync"
import { createPageTransport } from "./lib/page-transport"

/** How long typing may pause before the text it produced is saved. */
export const TEXT_IDLE_MS = 800

interface Entry {
  sync: PageSync
  rowIds: TableRowIds
  /** The editor's newest document, not yet converted to a tree: conversion
   *  waits for the save, so typing costs one conversion per idle pause. */
  latest: EditorBlockLike[] | null
  /** `editorShape` of the newest document the editor reported. */
  shape: string
  title: string
  mounted: number
  timer: ReturnType<typeof setTimeout> | null
  queryClient: QueryClient
}

/** One engine per page, outside React, so a page's unsaved work keeps
 *  draining after its pane unmounts and a page that is reopened mid-drain
 *  shows the work rather than the older server copy. */
const engines = new Map<string, Entry>()
let lifecycleInstalled = false

function onHidden() {
  if (document.visibilityState === "hidden") flushAll()
}

function onLeave(event: BeforeUnloadEvent) {
  if (!anyPending()) return
  event.preventDefault()
  event.returnValue = ""
}

function installLifecycle() {
  if (lifecycleInstalled) return
  document.addEventListener("visibilitychange", onHidden)
  window.addEventListener("beforeunload", onLeave)
  lifecycleInstalled = true
}

function anyPending(): boolean {
  // A block whose upload has not resolved carries no url, so it is absent
  // from every sync tree: the engines alone cannot see that work.
  if (uploadsInFlight() > 0) return true
  for (const entry of engines.values()) {
    convertLatest(entry)
    if (entry.sync.pending) return true
  }
  return false
}

function convertLatest(entry: Entry) {
  if (entry.latest === null) return
  const { tree, rowIds } = toSyncTree(entry.latest, entry.sync.snapshot, entry.rowIds, () => crypto.randomUUID())
  entry.latest = null
  entry.rowIds = rowIds
  entry.sync.setDesired(tree)
}

function flushEntry(entry: Entry) {
  if (entry.timer !== null) clearTimeout(entry.timer)
  entry.timer = null
  convertLatest(entry)
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
  if (entry.mounted !== 0 || entry.latest !== null || entry.sync.pending || engines.get(pageId) !== entry) return
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
    latest: null,
    shape: "",
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
  installLifecycle()
  entry.mounted++
}

function unmount(pageId: string, entry: Entry) {
  entry.mounted--
  if (engines.get(pageId) !== entry) return
  flushEntry(entry)
  release(pageId, entry)
}

/** The editor blocks to mount, from the engine's desired tree: the server's
 *  copy for a fresh engine, the unsent work for one still draining. */
function mountBlocks(entry: Entry): EditorBlockLike[] {
  convertLatest(entry)
  const { blocks, rowIds } = toEditorBlocks(entry.sync.desired)
  entry.rowIds = rowIds
  entry.shape = editorShape(blocks)
  return blocks
}

function acceptDocument(entry: Entry, blocks: EditorBlockLike[]) {
  entry.latest = blocks
  const shape = editorShape(blocks)
  const structural = shape !== entry.shape
  entry.shape = shape
  if (structural) {
    flushEntry(entry)
    return
  }
  if (entry.timer !== null) clearTimeout(entry.timer)
  entry.timer = setTimeout(() => flushEntry(entry), TEXT_IDLE_MS)
}

function discard(pageId: string, entry: Entry) {
  if (entry.timer !== null) clearTimeout(entry.timer)
  entry.latest = null
  if (engines.get(pageId) === entry) engines.delete(pageId)
}

/** The blocks' ids, parents, order and types, with what decides how many
 *  tree blocks each becomes (a table's rows, whether a file block has its
 *  url yet). Two documents with one shape convert to trees of one shape, so
 *  a change that keeps it is typing and anything else is structure. */
function editorShape(blocks: EditorBlockLike[]): string {
  const parts: string[] = []
  const walk = (block: EditorBlockLike, parentId: string) => {
    let extra = ""
    if (block.type === "table") {
      extra = String((block.content as { rows?: unknown[] } | undefined)?.rows?.length ?? 0)
    } else if (block.type === "image" || block.type === "file") {
      extra = block.props.url ? "url" : ""
    }
    parts.push(`${block.id}/${parentId}/${block.type}/${extra}`)
    for (const child of block.children) walk(child, block.id)
  }
  for (const block of blocks) walk(block, "")
  return parts.join("\n")
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

  const uploading = useSyncExternalStore(subscribeUploads, uploadsInFlight)

  useEffect(() => {
    mount(entry)
    return () => unmount(page.id, entry)
  }, [entry, page.id])

  return useMemo(
    () => ({
      initialBlocks,
      status:
        uploading > 0 && (status.kind === "idle" || status.kind === "saved")
          ? ({ kind: "saving" } as SyncStatus)
          : status,
      onDocumentChange: (blocks: EditorBlockLike[]) => acceptDocument(entry, blocks),
      flushNow: () => flushEntry(entry),
      discard: () => discard(page.id, entry),
    }),
    [entry, initialBlocks, page.id, status, uploading],
  )
}

/** Test hook: forget every engine between tests. */
export function resetPageSyncEngines() {
  for (const entry of engines.values()) if (entry.timer !== null) clearTimeout(entry.timer)
  engines.clear()
  document.removeEventListener("visibilitychange", onHidden)
  window.removeEventListener("beforeunload", onLeave)
  lifecycleInstalled = false
}
