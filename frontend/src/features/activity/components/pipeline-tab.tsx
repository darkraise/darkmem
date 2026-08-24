import { Check, RefreshCw, TriangleAlert, type LucideIcon } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { EmptyState } from "@/components/darkmem"
import { cn } from "darkraise-ui/lib"
import { deriveRunFailedStep, failedStepSeverity } from "@/demo/activity"
import type {
  DemoPipelineRun,
  PipelineTerminal,
} from "@/features/activity/types"
import { useSubjectTotals, type SubjectTotalRow } from "@/hooks/api"
import { UsageChip } from "@/features/usage/components/usage-chip"
import { usePipelineRuns } from "../use-pipeline-runs"
import { ModuleSurface } from "./module-surface"
import { PipelineStepper } from "./pipeline-stepper"

const TERMINAL_STYLES: Record<
  PipelineTerminal,
  { icon: LucideIcon; className: string }
> = {
  running: {
    icon: RefreshCw,
    className: "border-info/50 bg-info/10 text-info",
  },
  completed: {
    icon: Check,
    className: "border-success/50 bg-success/10 text-success",
  },
  partial: {
    icon: TriangleAlert,
    className: "border-warning/50 bg-warning/10 text-warning",
  },
  failed: {
    icon: TriangleAlert,
    className: "border-destructive/50 bg-destructive/10 text-destructive",
  },
}

function TerminalChip({ terminal }: { terminal: PipelineTerminal }) {
  const { icon: Icon, className } = TERMINAL_STYLES[terminal]
  return (
    <Badge
      variant="outline"
      size="sm"
      className={cn("gap-1 font-mono", className)}
    >
      <Icon aria-hidden className="h-3 w-3" />
      {terminal}
    </Badge>
  )
}

function PipelineRow({
  run,
  totals,
  pending,
}: {
  run: DemoPipelineRun
  totals: Map<string, SubjectTotalRow> | undefined
  pending: boolean
}) {
  // Honesty rule: a partial/failed memory always NAMES its failed step —
  // never a collapsed batch pass/fail.
  const failedStep = deriveRunFailedStep(run)
  return (
    <div className="border-border flex flex-col gap-2.5 rounded-md border p-3">
      <div className="flex flex-wrap items-baseline gap-2.5">
        <span className="text-muted-foreground font-mono text-sm">
          {run.id}
        </span>
        <span className="min-w-0 flex-1 text-sm">{run.content}</span>
        <span className="text-muted-foreground ml-auto font-mono text-sm whitespace-nowrap">
          {run.time_label}
        </span>
      </div>
      <PipelineStepper run={run} />
      <div className="flex flex-wrap items-center gap-2.5">
        <TerminalChip terminal={run.terminal} />
        {failedStep && (
          <span className="inline-flex items-center gap-1.5 text-sm">
            failed step:
            <code
              className={cn(
                "rounded-sm border px-1.5 py-0.5 font-mono text-sm",
                failedStepSeverity(failedStep) === "warn"
                  ? "border-warning/60 bg-warning/10 text-warning"
                  : "border-destructive/60 bg-destructive/10 text-destructive",
              )}
            >
              {failedStep}
            </code>
          </span>
        )}
        {run.counts && (
          <span className="text-muted-foreground font-mono text-sm">
            entities: {run.counts.entities} · relations: {run.counts.relations}
          </span>
        )}
        {/* What this memory's own extraction/classification calls cost. The
            batch embeds are not included and are not divided into it: one
            embed call covers the whole batch and has no per-memory share. */}
        {run.memory_id ? (
          <UsageChip
            className="ml-auto"
            pending={pending}
            totals={totals?.get(run.memory_id)}
          />
        ) : null}
      </div>
      {run.note && <p className="text-muted-foreground text-sm">{run.note}</p>}
    </div>
  )
}

export function PipelineTab() {
  const { runs, isLoading, isError } = usePipelineRuns()
  // One request for the whole page rather than one per row.
  const usage = useSubjectTotals(
    "memory",
    runs.map((r) => r.memory_id).filter((id): id is string => Boolean(id)),
  )
  const inFlight = runs.filter((r) => r.terminal === "running")
  const recent = runs.filter((r) => r.terminal !== "running")
  const partial = recent.filter((r) => r.terminal === "partial").length
  const failed = recent.filter((r) => r.terminal === "failed").length

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-4xl text-sm">
        Each captured memory's progress through{" "}
        <code className="bg-muted rounded-sm px-1 font-mono text-sm">
          content embed → extract &amp; classify → entity embed → dedup → write
        </code>
        , ending in one honest terminal state — completed, partial, or failed. A
        partial memory always names exactly which step broke; there is no
        per-phase progress event, so a running row shows the decomposition the
        one eventual terminal broadcast resolves into.
      </p>
      <ModuleSurface
        title="Pipeline — in flight"
        state={inFlight.length > 0 ? "populated" : "empty"}
        meta={`${inFlight.length} memory processing`}
      >
        {inFlight.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            Nothing is being processed right now — new captures appear here the
            moment the pipeline claims them.
          </p>
        ) : (
          inFlight.map((run) => (
            <PipelineRow
              key={run.id}
              pending={usage.isLoading}
              run={run}
              totals={usage.data}
            />
          ))
        )}
      </ModuleSurface>
      <ModuleSurface
        title="Pipeline — recent"
        state={isLoading ? "empty" : recent.length > 0 ? "populated" : "empty"}
        meta={`${recent.length} memories · ${partial} partial · ${failed} failed`}
      >
        {isError ? (
          <EmptyState
            kind="failed"
            title="Couldn't load recent pipeline runs"
            description="The /analytics/pipeline-logs request failed — this is an error state, not an absence of activity."
          />
        ) : (
          recent.map((run) => (
            <PipelineRow
              key={run.id}
              pending={usage.isLoading}
              run={run}
              totals={usage.data}
            />
          ))
        )}
      </ModuleSurface>
    </div>
  )
}
