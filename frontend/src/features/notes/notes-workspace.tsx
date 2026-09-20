import { useCallback, useEffect, useMemo, useState } from "react"
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
import { EmptyState } from "@/components/darkmem"
import {
  invalidatePageLists,
  usePage,
  usePageCreate,
  usePageDelete,
  usePageMove,
  usePageRename,
  usePageRestore,
  usePages,
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

  const roots = useMemo(() => buildPageTree(list.data ?? []), [list.data])
  const index = useMemo(() => pageNodeIndex(roots), [roots])

  const [trashOpen, setTrashOpen] = useState(false)
  const [focusTitle, setFocusTitle] = useState(false)
  const [renameTarget, setRenameTarget] = useState<PageNode | null>(null)
  const [renameValue, setRenameValue] = useState("")
  const [importing, setImporting] = useState(false)

  // A 404 says the selection no longer exists -- trashed or purged elsewhere,
  // which the server does not distinguish. Every other failure is a fault and
  // renders as one.
  const vanished =
    page.isError && page.error instanceof ApiError && page.error.status === NOT_FOUND
  useEffect(() => {
    if (vanished) onSelect(null)
  }, [onSelect, vanished])

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
      orientation="horizontal"
      className="min-h-[60vh] lg:min-h-0 lg:flex-1"
    >
      <ResizablePanel defaultSize={26} minSize={15} maxSize={45} id="page-tree">
        <div className="flex h-full min-h-0 flex-col">
          <div className="mb-1.5 flex items-center justify-end gap-1">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => createPage(null)}
            >
              <Plus className="mr-1 size-3.5" />
              New page
            </Button>
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
                The page tree could not be loaded — a failed read, not an empty
                space.
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
          <div className="pt-2">
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={() => setTrashOpen(true)}
            >
              <Trash2 className="mr-1 size-3.5" />
              Trash
            </Button>
          </div>
        </div>
      </ResizablePanel>

      <ResizableHandle withHandle />

      <ResizablePanel defaultSize={74} id="page-pane">
        <div className="h-full min-h-0 pl-3">
          {selectedId === null || vanished ? (
            <EmptyState
              kind="empty"
              icon={Plus}
              title="Nothing selected"
              description="Pick a page from the tree, or start a new one."
            />
          ) : page.isError ? (
            <p className="text-destructive text-sm">
              This page could not be loaded — a failed read, not an empty page.
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
        onRestored={() => setTrashOpen(false)}
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
