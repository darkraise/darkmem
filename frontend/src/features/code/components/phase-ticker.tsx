import { cn } from "darkraise-ui/lib"
import type { DemoIndexPhase } from "@/demo/types"

// The live phase list (S14) — a rewritten-per-tick label, never a bare
// spinner. Skipped opt-in phases render labelled, not silently missing.
export function PhaseTicker({ phases }: { phases: DemoIndexPhase[] }) {
  return (
    <div className="flex flex-col gap-1">
      {phases.map((phase) => (
        <div
          key={phase.n}
          className={cn(
            "text-muted-foreground flex items-center gap-2.5 rounded-sm px-2.5 py-1 text-sm",
            phase.state === "done" && "text-foreground",
            phase.state === "current" &&
              "border-info/40 bg-info/10 text-foreground border font-semibold",
            phase.state === "pending" && "opacity-55",
            phase.state === "skipped" && "italic opacity-45",
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
          <span className="min-w-0 flex-1">{phase.label}</span>
          <span className="text-muted-foreground ml-auto shrink-0 font-mono text-sm">
            {phase.state === "skipped" ? "skipped — opt-in" : phase.state}
          </span>
        </div>
      ))}
    </div>
  )
}
