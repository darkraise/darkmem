import { useState } from "react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "darkraise-ui/components/alert-dialog"
import { Button } from "darkraise-ui/components/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "darkraise-ui/components/sheet"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import { relativeTime } from "@/lib/format"
import { usePageRestore, usePageTrashEmpty, usePagesTrash } from "@/hooks/api"
import { PAGE_TITLE_FALLBACK } from "./lib/build-page-tree"

export function PageTrashSheet({
  project,
  open,
  onOpenChange,
  onRestored,
}: {
  project: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onRestored: () => void
}) {
  const trash = usePagesTrash(project, open)
  const restore = usePageRestore()
  const empty = usePageTrashEmpty()
  const [confirming, setConfirming] = useState(false)

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Trash</SheetTitle>
          <SheetDescription>
            The root of every trashed subtree. Restoring one brings its children
            back with it.
          </SheetDescription>
        </SheetHeader>

        {trash.isLoading ? <Skeleton className="h-24 w-full" /> : null}
        {trash.isError ? (
          <p className="text-destructive text-sm">
            The trash could not be read — a failed read, not an empty trash.
          </p>
        ) : null}
        {trash.isSuccess && trash.data.length === 0 ? (
          <p className="text-muted-foreground text-sm">Trash is empty.</p>
        ) : null}

        <ul className="space-y-1">
          {(trash.data ?? []).map((item) => {
            const label = item.title?.trim() ? item.title : PAGE_TITLE_FALLBACK
            return (
              <li
                key={item.id}
                className="flex items-center justify-between gap-3 rounded px-1 py-1.5"
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm">{label}</span>
                  <span className="text-muted-foreground text-xs">
                    {relativeTime(item.deleted_at)}
                  </span>
                </span>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  aria-label={`Restore ${label}`}
                  onClick={() =>
                    restore.mutate(item.id, {
                      onSuccess: () => onRestored(),
                      // The server's own message, because the only refusal
                      // here -- a still-trashed parent -- names the page the
                      // operator has to restore first.
                      onError: (error) => toast.error(String(error.message)),
                    })
                  }
                >
                  Restore
                </Button>
              </li>
            )
          })}
        </ul>

        <div className="pt-2">
          <Button
            type="button"
            variant="outline"
            disabled={(trash.data ?? []).length === 0}
            onClick={() => setConfirming(true)}
          >
            Empty trash
          </Button>
        </div>

        <AlertDialog open={confirming} onOpenChange={setConfirming}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Empty the trash?</AlertDialogTitle>
              <AlertDialogDescription>
                This deletes every trashed page and its blocks for good. It
                cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={() =>
                  empty.mutate(project, {
                    onError: (error) => toast.error(String(error.message)),
                  })
                }
              >
                Delete permanently
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </SheetContent>
    </Sheet>
  )
}
