import { useCallback, useMemo, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { MoreHorizontal, Plus, Trash2 } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "darkraise-ui/components/dropdown-menu"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "darkraise-ui/components/resizable"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import { ApiError } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import { relativeTime } from "@/lib/format"
import { EmptyState, IconButton } from "@/components/darkmem"
import { useMediaQuery } from "@/hooks/use-media-query"
import {
  invalidatePageLists,
  usePage,
  usePageCreate,
  usePageDelete,
  usePageMove,
  usePageRename,
  usePageRestore,
  usePages,
  usePagesTrash,
  type PageListItem,
} from "@/hooks/api"
import {
  buildPageTree,
  pageNodeIndex,
  PAGE_TITLE_FALLBACK,
  type PageNode,
} from "./lib/build-page-tree"
import { applyPlacement, type DropPlacement } from "./lib/drop-target"
import { PagePane } from "./page-pane"
import { PageTree } from "./page-tree"
import { NotionImportDialog } from "./notion-import-dialog"
import { PageTrashSheet } from "./page-trash-sheet"

const NOT_FOUND = 404

function labelOf(node: PageNode): string {
  return node.title?.trim() ? node.title : PAGE_TITLE_FALLBACK
}

export function NotesWorkspace({
  project,
  selectedId,
  onSelect,
}: {
  project: string
  selectedId: string | null
  onSelect: (pageId: string | null) => void
}) {
  const list = usePages(project)
  const page = usePage(selectedId)
  const qc = useQueryClient()
  const create = usePageCreate()
  const rename = usePageRename()
  const remove = usePageDelete()
  const restore = usePageRestore()
  const move = usePageMove()

  const wide = useMediaQuery("(min-width: 1024px)")
  const roots = useMemo(() => buildPageTree(list.data ?? []), [list.data])
  const index = useMemo(() => pageNodeIndex(roots), [roots])

  const [trashOpen, setTrashOpen] = useState(false)
  const [focusTitle, setFocusTitle] = useState(false)
  const [renameTarget, setRenameTarget] = useState<PageNode | null>(null)
  const [renameValue, setRenameValue] = useState("")
  const [importing, setImporting] = useState(false)

  // A 404 says the selection no longer exists -- trashed or purged elsewhere,
  // which the page read does not distinguish. Every other failure is a fault
  // and renders as one. The selection is KEPT: clearing it showed "Nothing
  // selected", so a link to a purged page (the dashboard's rows) looked like
  // it went nowhere rather than saying the page is gone.
  const vanished =
    page.isError &&
    page.error instanceof ApiError &&
    page.error.status === NOT_FOUND
  // The trash roots tell trashed from purged. Read only once a selection has
  // vanished; it shares the trash sheet's cache entry.
  const trash = usePagesTrash(project, vanished)
  const trashed = vanished
    ? trash.data?.find((item) => item.id === selectedId)
    : undefined

  const refuse = useCallback(
    (error: unknown) =>
      toast.error(error instanceof Error ? error.message : String(error)),
    [],
  )

  const createPage = useCallback(
    (parentId: string | null) => {
      create.mutate(
        { project, parentId },
        {
          onSuccess: ({ id }) => {
            onSelect(id)
            setFocusTitle(true)
          },
          onError: refuse,
        },
      )
    },
    [create, onSelect, project, refuse],
  )

  const deletePage = useCallback(
    (node: PageNode) => {
      const label = labelOf(node)
      remove.mutate(node.id, {
        onSuccess: () => {
          if (selectedId === node.id) onSelect(null)
          toast.success(`${label} moved to trash`, {
            action: {
              label: "Undo",
              onClick: () => restore.mutate(node.id, { onError: refuse }),
            },
          })
        },
        onError: refuse,
      })
    },
    [onSelect, refuse, remove, restore, selectedId],
  )

  // Optimistic, with the snapshot rolled back on refusal: a drag that waited
  // for the round trip would snap the row back under the pointer. The hook's
  // own `onSettled` invalidation is what reconciles either outcome.
  const movePage = useCallback(
    (pageId: string, placement: DropPlacement) => {
      const key = ["pages", project]
      const snapshot = qc.getQueryData<PageListItem[]>(key)
      if (snapshot) {
        qc.setQueryData(key, applyPlacement(snapshot, pageId, placement))
      }
      move.mutate(
        { pageId, parentId: placement.parentId, afterId: placement.afterId },
        {
          onError: (error) => {
            if (snapshot) qc.setQueryData(key, snapshot)
            refuse(error)
          },
        },
      )
    },
    [move, project, qc, refuse],
  )

  const commitRename = useCallback(() => {
    if (!renameTarget) return
    const next = renameValue.trim()
    rename.mutate(
      { pageId: renameTarget.id, title: next === "" ? null : next },
      { onError: refuse },
    )
    setRenameTarget(null)
  }, [refuse, rename, renameTarget, renameValue])

  return (
    <ResizablePanelGroup
      // Stacked below `lg`, as the document workspace is: side by side on a
      // phone the tree was ~90px and showed no page name at all. Remounted on
      // a crossing because the panel sizes are seeded once.
      key={wide ? "split" : "stack"}
      orientation={wide ? "horizontal" : "vertical"}
      className="min-h-[60vh] max-lg:h-[85svh]! lg:min-h-0 lg:flex-1"
    >
      <ResizablePanel
        defaultSize={wide ? 26 : 35}
        minSize={15}
        maxSize={wide ? 45 : 70}
        id="page-tree"
      >
        <div className="flex h-full min-h-0 flex-col max-lg:pb-2">
          {/* The same head the document tree has: a mono region label with
              the pane's actions grouped beside it, not scattered top and
              bottom. */}
          <div className="mb-1.5 flex items-center gap-1 pr-3">
            <p className="text-muted-foreground flex-1 font-mono text-xs tracking-wide uppercase">
              pages
            </p>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => createPage(null)}
            >
              <Plus className="mr-1 size-3.5" />
              New page
            </Button>
            <IconButton
              icon={Trash2}
              label="Trash"
              variant="ghost"
              type="button"
              onClick={() => setTrashOpen(true)}
            />
            {DEMO ? null : (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    aria-label="Page tree actions"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <MoreHorizontal aria-hidden className="size-3.5" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  align="end"
                  onClick={(event) => event.stopPropagation()}
                >
                  <DropdownMenuItem onSelect={() => setImporting(true)}>
                    Import from Notion
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
          <ScrollArea className="min-h-0 flex-1 pr-3">
            {list.isLoading ? <Skeleton className="h-64 w-full" /> : null}
            {list.isError ? (
              <p className="text-destructive text-sm">
                The page tree could not be loaded.
              </p>
            ) : null}
            {list.data ? (
              <PageTree
                roots={roots}
                index={index}
                project={project}
                selectedId={selectedId}
                onSelect={(id) => {
                  setFocusTitle(false)
                  onSelect(id)
                }}
                onNewChild={createPage}
                onRename={(node) => {
                  setRenameTarget(node)
                  setRenameValue(node.title ?? "")
                }}
                onDelete={deletePage}
                onMove={movePage}
              />
            ) : null}
          </ScrollArea>
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      <ResizablePanel defaultSize={wide ? 74 : 65} id="page-pane">
        <div className="h-full min-h-0 max-lg:pt-2 lg:pl-3">
          {selectedId === null ? (
            <EmptyState
              kind="empty"
              icon={Plus}
              title="Nothing selected"
              description="Pick a page from the tree, or start a new one."
            />
          ) : vanished && trash.isLoading ? (
            <Skeleton className="h-64 w-full" />
          ) : vanished && trashed ? (
            <EmptyState
              kind="missing"
              title="This page is in the trash"
              description={`${trashed.title?.trim() ? trashed.title : PAGE_TITLE_FALLBACK} was moved to the trash ${relativeTime(trashed.deleted_at)}. Restore it to read and edit it again.`}
              action={
                <Button
                  type="button"
                  variant="outline"
                  disabled={restore.isPending}
                  onClick={() =>
                    restore.mutate(trashed.id, {
                      onSuccess: () => {
                        // The pane's own read 404'd; `invalidatePageLists`
                        // covers the tree and the trash, not this entry.
                        void qc.invalidateQueries({
                          queryKey: ["page", trashed.id],
                        })
                      },
                      onError: refuse,
                    })
                  }
                >
                  Restore
                </Button>
              }
            />
          ) : vanished ? (
            // Not in the trash roots: purged, never existed, or trashed along
            // with a page above it (the trash lists only subtree roots, and
            // restoring that root brings this one back).
            <EmptyState
              kind="missing"
              title="This page no longer exists"
              description="It was deleted for good, or moved to the trash along with a page above it. The trash lists what can still be restored."
              action={
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setTrashOpen(true)}
                >
                  Open trash
                </Button>
              }
            />
          ) : page.isError ? (
            <p className="text-destructive text-sm">
              This page could not be loaded.
            </p>
          ) : page.isLoading || !page.data ? (
            <Skeleton className="h-64 w-full" />
          ) : (
            <PagePane page={page.data} autoFocusTitle={focusTitle} />
          )}
        </div>
      </ResizablePanel>

      <PageTrashSheet
        project={project}
        open={trashOpen}
        onOpenChange={setTrashOpen}
      />

      <NotionImportDialog
        project={project}
        open={importing}
        onOpenChange={(next) => {
          setImporting(next)
          if (!next) invalidatePageLists(qc)
        }}
        onImported={(rootPageId) => {
          setImporting(false)
          invalidatePageLists(qc)
          onSelect(rootPageId)
        }}
      />

      <Dialog
        open={renameTarget !== null}
        onOpenChange={(open) => {
          if (!open) setRenameTarget(null)
        }}
      >
        <DialogContent>
          <form
            className="space-y-4"
            onSubmit={(e) => {
              e.preventDefault()
              commitRename()
            }}
          >
            <DialogHeader>
              <DialogTitle>
                Rename {renameTarget ? labelOf(renameTarget) : ""}
              </DialogTitle>
            </DialogHeader>
            <Label htmlFor="page-rename" className="sr-only">
              New title
            </Label>
            <Input
              id="page-rename"
              autoFocus
              // Selected on open, so a rename can be typed straight over.
              onFocus={(e) => e.currentTarget.select()}
              aria-label="New title"
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
            />
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setRenameTarget(null)}
              >
                Cancel
              </Button>
              <Button type="submit">Rename</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </ResizablePanelGroup>
  )
}
