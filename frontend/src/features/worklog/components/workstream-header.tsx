import { useState } from "react"
import { Trash2 } from "lucide-react"
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
import { toast } from "darkraise-ui/components/sonner"
import { IconButton } from "@/components/darkmem"
import {
  useWorkstreamPurge,
  useWorkstreamUpdate,
  type Workstream,
} from "@/hooks/api"

/** The workstream properties a client may point at a filed document with. */
const LINKS = [
  ["plan_uri", "Plan"],
  ["spec_uri", "Spec"],
  ["handoff_uri", "Handoff"],
] as const

export function WorkstreamHeader({
  workstream,
  onOpenDocument,
  onPurged,
}: {
  workstream: Workstream
  onOpenDocument?: (uri: string) => void
  /** The workstream no longer exists; the caller lets go of it. */
  onPurged?: () => void
}) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const update = useWorkstreamUpdate()
  const purge = useWorkstreamPurge()
  const closing = workstream.state === "open"
  const links = LINKS.flatMap(([property, label]) => {
    const uri = workstream.properties[property]
    return typeof uri === "string" && uri ? [{ uri, label }] : []
  })

  return (
    <div className="flex flex-wrap items-start gap-3">
      <div className="min-w-0 flex-1 space-y-0.5">
        <h3 className="text-lg font-semibold break-words">
          {workstream.title ?? workstream.key}
        </h3>
        <p className="text-muted-foreground font-mono text-xs break-words">
          {workstream.key} · {workstream.state}
          {workstream.client ? ` · ${workstream.client}` : ""}
          {workstream.retain ? " · retained" : ""}
        </p>
        {links.length > 0 ? (
          <div className="flex flex-wrap items-center gap-1">
            {links.map(({ uri, label }) =>
              onOpenDocument ? (
                <Button
                  key={label}
                  variant="link"
                  size="sm"
                  title={uri}
                  onClick={() => onOpenDocument(uri)}
                >
                  {label}
                </Button>
              ) : (
                <span
                  key={label}
                  className="text-muted-foreground font-mono text-xs"
                >
                  {label}: {uri}
                </span>
              ),
            )}
          </div>
        ) : null}
      </div>
      <div className="flex shrink-0 items-center gap-1">
        <Button
          variant="outline"
          size="sm"
          disabled={update.isPending}
          onClick={() =>
            update.mutate(
              { id: workstream.id, state: closing ? "closed" : "open" },
              { onError: (error) => toast.error(error.message) },
            )
          }
        >
          {closing ? "Close" : "Reopen"}
        </Button>
        <IconButton
          icon={Trash2}
          label="Purge workstream"
          variant="ghost"
          className="text-destructive-text hover:text-destructive-text"
          onClick={() => setConfirmOpen(true)}
        />
      </div>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Purge {workstream.title ?? workstream.key}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This erases the workstream and every entry in it. This cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              // The library hard-codes `data-variant="default"` (the primary
              // green) and spreads props after it; an erase is destructive.
              data-variant="destructive"
              onClick={() =>
                purge.mutate(workstream.id, {
                  onSuccess: () => {
                    toast.success("Workstream purged")
                    setConfirmOpen(false)
                    onPurged?.()
                  },
                  onError: (error) => toast.error(error.message),
                })
              }
            >
              Purge
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
