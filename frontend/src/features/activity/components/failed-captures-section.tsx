import { useEffect, useRef, useState } from "react"
import { RefreshCw, Trash2 } from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "darkraise-ui/components/alert-dialog"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import { EmptyState, listItemClass } from "@/components/darkmem"
import type { BufferRow } from "@/hooks/api/use-memory-buffer-api"
import { shortId } from "@/lib/short-id"
import { ModuleSurface } from "./module-surface"

export interface FailedCapturesSectionProps {
  items: BufferRow[]
  total: number
  isLoading: boolean
  isError: boolean
  onRequeue: (id: string) => Promise<unknown>
  onDiscard: (id: string) => Promise<unknown>
}

function errorText(error: unknown): string | undefined {
  return error instanceof Error ? error.message : undefined
}

function FailedCaptureRow({
  item,
  onRequeue,
  onDiscard,
}: {
  item: BufferRow
  onRequeue: (id: string) => Promise<unknown>
  onDiscard: (id: string) => Promise<unknown>
}) {
  const memory = item.memory_exists && item.memory_id ? item.memory_id : null
  const [busy, setBusy] = useState(false)
  // Each action disables its own button while it runs, which drops focus
  // (and the confirmed dialog closes while the Discard trigger is disabled),
  // so the button takes focus back once the action settles.
  const requeueTrigger = useRef<HTMLButtonElement>(null)
  const discardTrigger = useRef<HTMLButtonElement>(null)
  const refocus = useRef<HTMLButtonElement | null>(null)
  useEffect(() => {
    if (busy || !refocus.current) return
    const target = refocus.current
    refocus.current = null
    target.focus()
  }, [busy])

  const requeue = () => {
    if (busy) return
    refocus.current = requeueTrigger.current
    setBusy(true)
    onRequeue(item.id)
      .then(
        () => toast.success("Capture requeued"),
        (error) =>
          toast.error("Couldn't requeue the capture", {
            description: errorText(error),
          }),
      )
      .finally(() => setBusy(false))
  }
  const discard = () => {
    if (busy) return
    refocus.current = discardTrigger.current
    setBusy(true)
    onDiscard(item.id).then(
      () =>
        toast.success(
          memory ? "Capture and memory discarded" : "Capture discarded",
        ),
      (error) =>
        toast.error("Couldn't discard the capture", {
          description: errorText(error),
        }),
    ).finally(() => setBusy(false))
  }

  return (
    <div
      data-buffer-row
      className={listItemClass({ className: "flex flex-col gap-2 p-3" })}
    >
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="min-w-0 basis-full text-sm font-semibold break-words sm:flex-1 sm:basis-auto">
          {item.content_preview}
        </span>
        <span className="border-border bg-muted/40 text-muted-foreground rounded-sm border px-2 py-0.5 font-mono text-xs">
          {item.project}
        </span>
        <span className="text-muted-foreground font-mono text-sm whitespace-nowrap">
          {item.attempts} of {item.max_attempts} attempts
        </span>
      </div>
      {item.last_error && (
        <div className="flex items-start gap-2 text-sm">
          <span className="text-muted-foreground w-20 shrink-0 pt-0.5 font-mono text-xs tracking-wide uppercase">
            reason
          </span>
          <span className="min-w-0 font-mono text-sm break-all">
            {item.last_error}
          </span>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          ref={requeueTrigger}
          variant="outline"
          disabled={busy}
          onClick={requeue}
        >
          <RefreshCw className="mr-1.5 size-3.5" />
          Requeue
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button ref={discardTrigger} variant="outline" disabled={busy}>
              <Trash2 className="mr-1.5 size-3.5" />
              Discard
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Discard this capture?</AlertDialogTitle>
              <AlertDialogDescription>
                {memory
                  ? `Memory ${shortId(memory)} was created from this capture before it failed. The capture is removed from the queue. This also deletes the memory.`
                  : "The capture is removed from the queue."}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction data-variant="destructive" onClick={discard}>
                Discard
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  )
}

export function FailedCapturesSection({
  items,
  total,
  isLoading,
  isError,
  onRequeue,
  onDiscard,
}: FailedCapturesSectionProps) {
  const state = isError ? "error" : items.length > 0 ? "populated" : "empty"
  return (
    <ModuleSurface
      title="Failed captures"
      state={state}
      meta={isError || isLoading ? undefined : `${total} in error`}
    >
      {isError ? (
        <EmptyState kind="failed" title="Couldn't load failed captures" />
      ) : isLoading ? (
        <div className="space-y-2" aria-busy>
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : items.length === 0 ? (
        <EmptyState kind="resolved" title="No failed captures" />
      ) : (
        <>
          {total > items.length && (
            <p className="text-muted-foreground font-mono text-sm">
              Showing the newest {items.length} of {total}
            </p>
          )}
          {items.map((item) => (
            <FailedCaptureRow
              key={item.id}
              item={item}
              onRequeue={onRequeue}
              onDiscard={onDiscard}
            />
          ))}
        </>
      )}
    </ModuleSurface>
  )
}
