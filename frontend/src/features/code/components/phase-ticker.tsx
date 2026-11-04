import { Check, CircleDashed, LoaderCircle, SkipForward } from "lucide-react"
import { cn } from "darkraise-ui/lib"
import type { DemoIndexPhase } from "@/demo/types"

const STATE_ICON = {
  done: Check,
  current: LoaderCircle,
  pending: CircleDashed,
  skipped: SkipForward,
} as const

// The live phase list (S14) — a rewritten-per-tick label, never a bare
// spinner. Skipped opt-in phases render labelled, not silently missing.
// State is carried by the icon and the trailing state word, never by
// dimming the row: these rows are the only record of what the run will
// still do, so every one keeps full-contrast text.
export function PhaseTicker({ phases }: { phases: DemoIndexPhase[] }) {
  return (
    <div className="flex flex-col gap-1">
      {phases.map((phase) => {
        const Icon = STATE_ICON[phase.state]
        return (
          <div
            key={phase.n}
            className={cn(
              "text-muted-foreground flex items-center gap-2.5 rounded-sm px-2.5 py-1 text-sm",
              phase.state === "done" && "text-foreground",
              phase.state === "current" &&
                "border-info-edge/40 bg-info-solid/10 text-foreground border font-semibold",
              phase.state === "skipped" && "italic",
            )}
          >
            <span
              className={cn(
                "w-5 shrink-0 font-mono text-sm",
                phase.state === "done" && "text-primary-text",
                phase.state === "current" && "text-info-text",
              )}
            >
              {String(phase.n).padStart(2, "0")}
            </span>
            <Icon
              aria-hidden
              className={cn(
                "h-3.5 w-3.5 shrink-0",
                phase.state === "done" && "text-primary-text",
                phase.state === "current" &&
                  "text-info-text motion-safe:animate-spin",
              )}
            />
            <span className="min-w-0 flex-1">{phase.label}</span>
            <span className="text-muted-foreground ml-auto shrink-0 font-mono text-sm">
              {phase.state}
            </span>
          </div>
        )
      })}
    </div>
  )
}
