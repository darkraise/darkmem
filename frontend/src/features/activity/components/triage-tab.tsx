import { useState } from "react"
import { FileText, FolderGit2, RefreshCw, X } from "lucide-react"
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
import { EmptyState, listItemClass } from "@/components/darkmem"
import { cn } from "darkraise-ui/lib"
import { groupFailuresByStep, isPoison } from "@/demo/activity"
import type { DemoPipelineFailure } from "@/features/activity/types"
import {
  useDiscardBufferItem,
  useMemoryBufferItems,
  useRequeueBufferItem,
} from "@/hooks/api/use-memory-buffer-api"
import { DEMO } from "@/lib/demo-flag"
import { usePipelineTriage } from "../use-pipeline-triage"
import { FailedCapturesSection } from "./failed-captures-section"
import { ModuleSurface } from "./module-surface"

function FailureRow({
  failure,
  retry,
  forget,
}: {
  failure: DemoPipelineFailure
  retry: (id: string) => void
  forget: (id: string) => void
}) {
  const poison = isPoison(failure)
  const [confirmForget, setConfirmForget] = useState(false)
  const Icon = failure.target_kind === "memory" ? FileText : FolderGit2

  return (
    <div
      className={listItemClass({
        className: cn(
          "flex flex-col gap-2 p-3",
          poison && "border-warning-edge/55 bg-warning-solid/5",
        ),
      })}
    >
      <div className="flex flex-wrap items-center gap-2.5">
        <Icon aria-hidden className="text-muted-foreground h-4 w-4 shrink-0" />
        {/* basis-full below sm: the chips and attempt count drop to their
            own line rather than squeezing the title to a word per line. */}
        <span className="min-w-0 basis-[calc(100%-1.625rem)] text-sm font-semibold sm:flex-1 sm:basis-auto">
          {failure.target_label}
        </span>
        <span className="border-border bg-muted/40 text-muted-foreground rounded-sm border px-2 py-0.5 font-mono text-xs">
          {failure.pipeline}
        </span>
        {poison && (
          <span className="border-warning-edge/65 bg-warning-solid/10 text-warning-text inline-flex items-center gap-1 rounded-full border border-dashed px-2 py-0.5 font-mono text-xs uppercase">
            poison
          </span>
        )}
        <span className="text-muted-foreground font-mono text-sm whitespace-nowrap">
          {failure.attempts} attempt{failure.attempts === 1 ? "" : "s"}
        </span>
      </div>
      <div className="flex items-start gap-2 text-sm">
        <span className="text-muted-foreground w-20 shrink-0 pt-0.5 font-mono text-xs tracking-wide uppercase">
          failed step
        </span>
        <span className="font-mono font-semibold">{failure.failed_step}</span>
      </div>
      <div className="flex items-start gap-2 text-sm">
        <span className="text-muted-foreground w-20 shrink-0 pt-0.5 font-mono text-xs tracking-wide uppercase">
          reason
        </span>
        {/* The raw error_message, verbatim — never summarised to "failed". */}
        <span className="font-mono text-sm">{failure.reason}</span>
      </div>
      <div className="border-border text-muted-foreground flex flex-wrap gap-4 border-t border-dashed pt-2 font-mono text-xs">
        <span>first failed {failure.first_failed}</span>
        <span>last attempt {failure.last_attempt}</span>
      </div>
      {poison && (
        <p className="border-warning-edge/50 bg-warning-solid/5 rounded-md border border-dashed px-2.5 py-2 text-sm">
          Failed the same way on all {failure.attempts} attempts; retrying
          won&apos;t help until the cause is fixed.
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant={poison ? "outline" : "default"}
          className={cn(poison && "border-warning-edge/60 text-warning-text")}
          disabled={failure.retry_queued}
          onClick={() => {
            retry(failure.id)
            toast.success("Retry queued", {
              description: failure.target_label,
            })
          }}
        >
          <RefreshCw className="mr-1.5 size-3.5" />
          {failure.retry_queued
            ? "Retry queued"
            : poison
              ? "Retry anyway"
              : "Retry"}
        </Button>
        <Button variant="outline" onClick={() => setConfirmForget(true)}>
          <X className="mr-1.5 size-3.5" />
          Forget
        </Button>
      </div>

      {/* Forget sits beside Retry and cannot be taken back, so it confirms. */}
      <AlertDialog open={confirmForget} onOpenChange={setConfirmForget}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Forget this failure?</AlertDialogTitle>
            <AlertDialogDescription>
              The failure record for {failure.target_label} is removed from
              triage and is not retried. This cannot be undone; it reappears
              only if the {failure.failed_step} step fails again.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                forget(failure.id)
                setConfirmForget(false)
                toast.success("Failure forgotten", {
                  description: failure.target_label,
                })
              }}
            >
              <X className="mr-1.5 size-3.5" />
              Forget
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function FailedCaptures() {
  const { items, total, isLoading, isError } = useMemoryBufferItems()
  const discard = useDiscardBufferItem()
  const requeue = useRequeueBufferItem()
  return (
    <FailedCapturesSection
      items={items}
      total={total}
      isLoading={isLoading}
      isError={isError}
      onRequeue={requeue.mutateAsync}
      onDiscard={discard.mutateAsync}
    />
  )
}

export function TriageTab() {
  const { failures, isLoading, isError, retry, retryAll, forget } =
    usePipelineTriage()
  const groups = groupFailuresByStep(failures)
  const queueable = failures.filter((f) => !f.retry_queued)
  // A poison row says retrying won't help and asks for an explicit "Retry
  // anyway", so the bulk action leaves those rows out rather than overriding
  // the per-row guidance. With no poison row it stays the one retry-all call.
  const poisonCount = queueable.filter(isPoison).length
  const bulkTargets = queueable.filter((f) => !isPoison(f))
  const retryBulk = () => {
    if (poisonCount === 0) retryAll()
    else for (const f of bulkTargets) retry(f.id)
    toast.success(
      `Retry queued for ${bulkTargets.length} failure${bulkTargets.length === 1 ? "" : "s"}`,
      poisonCount > 0
        ? {
            description: `${poisonCount} poison row${poisonCount === 1 ? "" : "s"} skipped; retry ${poisonCount === 1 ? "it" : "them"} individually.`,
          }
        : undefined,
    )
  }

  return (
    <div className="space-y-4">
      <ModuleSurface
        title="Failure triage"
        state="populated"
        meta={`${failures.length} unresolved`}
        actions={
          failures.length > 0 ? (
            <Button
              variant="outline"
              disabled={bulkTargets.length === 0}
              onClick={retryBulk}
            >
              <RefreshCw className="mr-1.5 size-3.5" />
              {poisonCount > 0 && bulkTargets.length > 0
                ? `Retry ${bulkTargets.length} non-poison`
                : "Retry all"}
            </Button>
          ) : undefined
        }
      >
        {isError ? (
          <EmptyState kind="failed" title="Couldn't load pipeline failures" />
        ) : failures.length === 0 && !isLoading ? (
          // Healthy-empty: a queue at zero is a positive state, not an
          // absence to explain away.
          <EmptyState kind="resolved" title="No failures to triage" />
        ) : (
          groups.map((group) => (
            <div key={group.step} className="space-y-2">
              <p className="text-muted-foreground font-mono text-sm">
                failed step: <b className="text-foreground">{group.step}</b> ·{" "}
                {group.failures.length} row
                {group.failures.length === 1 ? "" : "s"}
              </p>
              {group.failures.map((failure) => (
                <FailureRow
                  key={failure.id}
                  failure={failure}
                  retry={retry}
                  forget={forget}
                />
              ))}
            </div>
          ))
        )}
      </ModuleSurface>
      {/* The demo store holds no buffer rows to triage. */}
      {!DEMO && <FailedCaptures />}
    </div>
  )
}
