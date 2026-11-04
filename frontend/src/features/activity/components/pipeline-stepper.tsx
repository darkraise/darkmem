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
  ok: "border-success-edge text-success-text",
  pending: "border-border text-muted-foreground/60",
  error: "border-destructive-edge text-destructive-text bg-destructive-solid/10",
  degraded: "border-warning-edge border-dashed text-warning-text bg-warning-solid/10",
  skipped: "border-border border-dashed text-muted-foreground/50 opacity-60",
}

const LABEL_STYLES: Record<PipelineStepState, string> = {
  ok: "text-foreground",
  pending: "text-muted-foreground",
  error: "text-destructive-text font-semibold",
  degraded: "text-warning-text font-semibold",
  skipped: "text-muted-foreground opacity-60",
}

// Connector colour follows the step it feeds: red for a hard error, amber
// for degraded-not-fatal (never reads as a hard failure), neutral otherwise.
function connectorClass(next: PipelineStepState): string {
  if (next === "error") return "bg-destructive-solid/50"
  if (next === "degraded") return "bg-warning-solid/50"
  if (next === "ok") return "bg-success-solid"
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
        "rounded-full border px-1.5 font-mono text-xs",
        state === "ok" && "border-success-edge/60 text-success-text",
        state === "error" && "border-destructive-edge/60 text-destructive-text",
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
            "linear-gradient(90deg, hsl(var(--success-solid) / 0.35) 50%, hsl(var(--destructive-solid) / 0.45) 50%)",
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
    <ol
      aria-label="Pipeline steps"
      className="flex flex-col md:flex-row md:items-start md:overflow-x-auto md:pb-1"
    >
      {run.steps.map((state, i) => (
        <li
          key={PHASE_LABELS[i]}
          className="flex flex-col md:flex-1 md:flex-row md:items-start"
        >
          {i > 0 && (
            <>
              <span
                aria-hidden
                className={cn(
                  "ml-[13px] h-3 w-0.5 md:hidden",
                  connectorClass(state),
                )}
              />
              <span
                aria-hidden
                className={cn(
                  "mt-3.5 hidden h-0.5 min-w-3 flex-1 md:block",
                  connectorClass(state),
                )}
              />
            </>
          )}
          {/* The Write column carries two substep pills, wider than the
              fixed 6rem the other phases use, so it sizes to its content
              instead of clipping the "graph" pill. */}
          <div
            className={cn(
              "flex items-center gap-2 md:flex-none md:flex-col md:gap-1",
              i === 4 ? "md:w-auto md:min-w-24" : "md:w-24",
            )}
          >
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
            <span className="text-muted-foreground font-mono text-xs">
              {i + 1}
            </span>
            <span
              className={cn(
                "text-sm leading-tight md:text-center",
                LABEL_STYLES[state],
              )}
            >
              {PHASE_LABELS[i]}
            </span>
            {i === 4 && run.substeps && (
              <span className="flex flex-wrap justify-center gap-1">
                <SubstepPill label="vector" state={run.substeps.vector} />
                <SubstepPill label="graph" state={run.substeps.graph} />
              </span>
            )}
          </div>
        </li>
      ))}
    </ol>
  )
}
