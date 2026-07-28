import { Check, CircleDashed, Minus, TriangleAlert, Waves } from "lucide-react"
import { cn } from "darkraise-ui/lib"
import type {
  DemoPipelineRun,
  PipelineStepState,
  PipelineWriteSubsteps,
} from "@/features/activity/types"

const PHASE_LABELS = [
  "Content embed",
  "Extract & classify",
  "Entity embed",
  "Dedup",
  "Write",
] as const

function StepIcon({ state }: { state: PipelineStepState }) {
  const cls = "h-3.5 w-3.5"
  switch (state) {
    case "ok":
      return <Check aria-hidden className={cls} strokeWidth={2.4} />
    case "error":
      return <TriangleAlert aria-hidden className={cls} />
    case "degraded":
      return <Waves aria-hidden className={cls} />
    case "skipped":
      return <Minus aria-hidden className={cls} />
    default:
      return <CircleDashed aria-hidden className={cls} />
  }
}

const DOT_STYLES: Record<PipelineStepState, string> = {
  ok: "border-success text-success",
  pending: "border-border text-muted-foreground/60",
  error: "border-destructive text-destructive bg-destructive/10",
  degraded: "border-warning border-dashed text-warning bg-warning/10",
  skipped: "border-border border-dashed text-muted-foreground/50 opacity-60",
}

const LABEL_STYLES: Record<PipelineStepState, string> = {
  ok: "text-foreground",
  pending: "text-muted-foreground",
  error: "text-destructive font-semibold",
  degraded: "text-warning font-semibold",
  skipped: "text-muted-foreground opacity-60",
}

// Connector colour follows the step it feeds: red for a hard error, amber
// for degraded-not-fatal (never reads as a hard failure), neutral otherwise.
function connectorClass(next: PipelineStepState): string {
  if (next === "error") return "bg-destructive/50"
  if (next === "degraded") return "bg-warning/50"
  if (next === "ok") return "bg-success"
  return "bg-border"
}

function SubstepPill({
  label,
  state,
}: {
  label: string
  state: "ok" | "error" | "skipped"
}) {
  return (
    <span
      className={cn(
        "rounded-full border px-1.5 font-mono text-[10px]",
        state === "ok" && "border-success/60 text-success",
        state === "error" && "border-destructive/60 text-destructive",
        state === "skipped" && "border-border text-muted-foreground",
      )}
    >
      {label}
    </span>
  )
}

function WriteDot({
  state,
  substeps,
}: {
  state: PipelineStepState
  substeps: PipelineWriteSubsteps | null
}) {
  // The write dot splits when the two Phase-5 savepoints disagree — the
  // two-savepoint architecture rendered directly, not collapsed to one colour.
  const split =
    substeps != null &&
    substeps.vector !== substeps.graph &&
    (substeps.vector === "error" || substeps.graph === "error")
  if (split) {
    return (
      <span
        aria-hidden
        className="border-border flex h-7 w-7 flex-none items-center justify-center rounded-full border-2"
        style={{
          background:
            "linear-gradient(90deg, hsl(var(--success) / 0.35) 50%, hsl(var(--destructive) / 0.45) 50%)",
        }}
      />
    )
  }
  return (
    <span
      className={cn(
        "bg-card flex h-7 w-7 flex-none items-center justify-center rounded-full border-2",
        DOT_STYLES[state],
      )}
    >
      <StepIcon state={state} />
    </span>
  )
}

export function PipelineStepper({ run }: { run: DemoPipelineRun }) {
  return (
    <div className="flex items-start overflow-x-auto pb-1">
      {run.steps.map((state, i) => (
        <div key={PHASE_LABELS[i]} className="flex flex-1 items-start">
          {i > 0 && (
            <span
              aria-hidden
              className={cn(
                "mt-3.5 h-0.5 min-w-3 flex-1",
                connectorClass(state),
              )}
            />
          )}
          <div className="flex w-24 flex-none flex-col items-center gap-1">
            {i === 4 ? (
              <WriteDot state={state} substeps={run.substeps} />
            ) : (
              <span
                className={cn(
                  "bg-card flex h-7 w-7 flex-none items-center justify-center rounded-full border-2",
                  DOT_STYLES[state],
                )}
              >
                <StepIcon state={state} />
              </span>
            )}
            <span className="text-muted-foreground font-mono text-[10px]">
              {i + 1}
            </span>
            <span
              className={cn(
                "text-center text-sm leading-tight",
                LABEL_STYLES[state],
              )}
            >
              {PHASE_LABELS[i]}
            </span>
            {i === 4 && run.substeps && (
              <span className="flex gap-1">
                <SubstepPill label="vector" state={run.substeps.vector} />
                <SubstepPill label="graph" state={run.substeps.graph} />
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
