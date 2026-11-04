import { Check, RefreshCw, TriangleAlert, type LucideIcon } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { EmptyState, listItemClass } from "@/components/darkmem"
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
import { DEMO } from "@/lib/demo-flag"

const TERMINAL_STYLES: Record<
  PipelineTerminal,
  { icon: LucideIcon; className: string }
> = {
  running: {
    icon: RefreshCw,
    className: "border-info-edge/50 bg-info-solid/10 text-info-text",
  },
  completed: {
    icon: Check,
    className: "border-success-edge/50 bg-success-solid/10 text-success-text",
  },
  partial: {
    icon: TriangleAlert,
    className: "border-warning-edge/50 bg-warning-solid/10 text-warning-text",
  },
  failed: {
    icon: TriangleAlert,
    className: "border-destructive-edge/50 bg-destructive-solid/10 text-destructive-text",
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
    <div className={listItemClass({ className: "flex flex-col gap-2.5 p-3" })}>
      <div className="flex flex-col gap-1 md:flex-row md:flex-wrap md:items-baseline md:gap-2.5">
        <span className="text-muted-foreground font-mono text-sm">
          {run.id}
        </span>
        <span className="min-w-0 text-sm md:flex-1">{run.content}</span>
        <span className="text-muted-foreground font-mono text-sm whitespace-nowrap md:ml-auto">
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
                  ? "border-warning-edge/60 bg-warning-solid/10 text-warning-text"
                  : "border-destructive-edge/60 bg-destructive-solid/10 text-destructive-text",
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
      {/* Real mode has no per-phase progress signal (doc 05 §10): every run it
          reads is terminal, so this panel could only ever say "idle". Only
          the demo fixture has in-flight rows to show. */}
      {DEMO && (
        <ModuleSurface
          title="Pipeline — in flight"
          state="populated"
          meta={
            inFlight.length === 0
              ? "idle"
              : `${inFlight.length} ${inFlight.length === 1 ? "memory" : "memories"} processing`
          }
        >
          {inFlight.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              Nothing is being processed right now.
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
      )}
      <ModuleSurface
        title="Pipeline — recent"
        state="populated"
        meta={`${recent.length} ${recent.length === 1 ? "run" : "runs"} · ${partial} partial · ${failed} failed`}
      >
        {isError ? (
          <EmptyState
            kind="failed"
            title="Couldn't load recent pipeline runs"
          />
        ) : !isLoading && recent.length === 0 ? (
          <p className="text-muted-foreground text-sm">No recent runs.</p>
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
