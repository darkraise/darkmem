import { CircleDashed, Zap } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import { cn } from "darkraise-ui/lib"
import { armStatus } from "@/demo/settings"

// The badge is the whole explanation of an arm's state, so it carries its own.
// "inactive" is the word most likely to be misread here: it means the arm is
// built and wired and contributing a factor of exactly 1 — not that a feature
// is missing, and not that flipping it is unavailable.
const STATUS_HELP: Record<"active" | "inactive", string> = {
  active:
    "This arm is at a non-zero weight, so it is changing the order of results right now. Its factor multiplies each row's fused rrf_score.",
  inactive:
    "Built and wired, sitting at weight 0 — its factor is exactly 1, so it moves nothing. Invariant 23: an unspent arm is shown at zero rather than hidden, because omitting it would read as 'this does not exist'. Raising it above zero is a deliberate activation.",
}

// Invariant 23, per-row: an arm at 0 renders INACTIVE (built-but-unspent,
// dashed neutral) — never omitted, never implied "off entirely". A non-zero
// arm renders ACTIVE (a live, spent signal).
export function ArmPill({ value }: { value: number }) {
  const status = armStatus(value)
  const active = status === "active"
  const Icon = active ? Zap : CircleDashed
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger
          aria-label={`About the ${status} state`}
          className={cn(
            "inline-flex cursor-help items-center gap-1 rounded-full border px-2.5 py-0.5 font-mono text-[10px] tracking-wide uppercase whitespace-nowrap",
            active
              ? "border-primary/55 bg-primary/10 text-primary-text"
              : "border-border text-muted-foreground bg-muted/40 border-dashed",
          )}
        >
          <Icon aria-hidden className="h-3 w-3" />
          {status}
        </TooltipTrigger>
        <TooltipContent className="max-w-sm text-sm leading-relaxed font-normal normal-case">
          {STATUS_HELP[status]}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
