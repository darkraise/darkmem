import { FileText, FolderGit2, RefreshCw, X } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { EmptyState, listItemClass } from "@/components/darkmem"
import { cn } from "darkraise-ui/lib"
import { groupFailuresByStep, isPoison, POISON_ATTEMPTS } from "@/demo/activity"
import type { DemoPipelineFailure } from "@/features/activity/types"
import { usePipelineTriage } from "../use-pipeline-triage"
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
  const Icon = failure.target_kind === "memory" ? FileText : FolderGit2

  return (
    <div
      className={listItemClass({
        className: cn(
          "flex flex-col gap-2 p-3",
          poison && "border-warning/55 bg-warning/5",
        ),
      })}
    >
      <div className="flex flex-wrap items-center gap-2.5">
        <Icon aria-hidden className="text-muted-foreground h-4 w-4 shrink-0" />
        <span className="min-w-0 flex-1 text-sm font-semibold">
          {failure.target_label}
        </span>
        <span className="border-border bg-muted/40 text-muted-foreground rounded-sm border px-2 py-0.5 font-mono text-[10px]">
          {failure.pipeline}
        </span>
        {poison && (
          <span className="border-warning/65 bg-warning/10 text-warning inline-flex items-center gap-1 rounded-full border border-dashed px-2 py-0.5 font-mono text-[10px] uppercase">
            poison
          </span>
        )}
        <span className="text-muted-foreground font-mono text-sm whitespace-nowrap">
          {failure.attempts} attempt{failure.attempts === 1 ? "" : "s"}
        </span>
      </div>
      <div className="flex items-start gap-2 text-sm">
        <span className="text-muted-foreground w-20 shrink-0 pt-0.5 font-mono text-[10px] tracking-wide uppercase">
          failed step
        </span>
        <span className="font-mono font-semibold">{failure.failed_step}</span>
      </div>
      <div className="flex items-start gap-2 text-sm">
        <span className="text-muted-foreground w-20 shrink-0 pt-0.5 font-mono text-[10px] tracking-wide uppercase">
          reason
        </span>
        {/* The raw error_message, verbatim — never summarised to "failed". */}
        <span className="font-mono text-sm">{failure.reason}</span>
      </div>
      <div className="border-border text-muted-foreground flex flex-wrap gap-4 border-t border-dashed pt-2 font-mono text-[10px]">
        <span>first failed {failure.first_failed}</span>
        <span>last attempt {failure.last_attempt}</span>
      </div>
      {poison && (
        <p className="border-warning/50 bg-warning/5 rounded-md border border-dashed px-2.5 py-2 text-sm">
          Same failed step and error message across all {failure.attempts}{" "}
          attempts — surfaced instead of retried again automatically. Retrying
          will not resolve this without a fix upstream (e.g. the extraction LLM
          profile); retry stays available as a manual, deliberate action.
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant={poison ? "outline" : "default"}
          className={cn(poison && "border-warning/60 text-warning")}
          disabled={failure.retry_queued}
          onClick={() => retry(failure.id)}
        >
          <RefreshCw className="mr-1.5 size-3.5" />
          {failure.retry_queued
            ? "Retry queued"
            : poison
              ? "Retry anyway"
              : "Retry"}
        </Button>
        <Button variant="outline" onClick={() => forget(failure.id)}>
          <X className="mr-1.5 size-3.5" />
          Forget
        </Button>
      </div>
      {failure.retry_queued && (
        <p className="text-muted-foreground text-sm italic">
          retry queued — the pipeline will re-attempt this step; the row stays
          open until a clean run resolves it.
        </p>
      )}
    </div>
  )
}

export function TriageTab() {
  const { failures, isLoading, isError, retry, retryAll, forget } =
    usePipelineTriage()
  const groups = groupFailuresByStep(failures)
  const retryable = failures.filter((f) => !f.retry_queued).length

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-4xl text-sm">
        Unresolved pipeline_failures rows, each naming its failed step and its
        reason verbatim. A row still failing the same way after{" "}
        {POISON_ATTEMPTS}+ attempts is surfaced as poison rather than left to
        retry unnoticed — the threshold is a triage-surface heuristic, not a
        backend gate.
      </p>
      <ModuleSurface
        title="Failure triage"
        state={
          isLoading ? "empty" : failures.length > 0 ? "populated" : "empty"
        }
        meta={`pipeline_failures · ${failures.length} unresolved`}
        actions={
          failures.length > 0 ? (
            <Button
              variant="outline"
              disabled={retryable === 0}
              onClick={retryAll}
            >
              <RefreshCw className="mr-1.5 size-3.5" />
              Retry all
            </Button>
          ) : undefined
        }
      >
        {isError ? (
          <EmptyState
            kind="failed"
            title="Couldn't load pipeline failures"
            description="The /pipeline-failures request failed — this is an error state, not an empty triage queue."
          />
        ) : failures.length === 0 ? (
          // Healthy-empty: a queue at zero is a positive state, not an
          // absence to explain away.
          <EmptyState
            kind="resolved"
            title="No failures to triage"
            description="Every memory-ingest and code-index run in the last 100 attempts completed without an unresolved pipeline_failures row — nothing is stuck, nothing is waiting on a retry."
          />
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
    </div>
  )
}
