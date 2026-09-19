import { cn } from "darkraise-ui/lib"
import { useDetailLevel } from "@/components/darkmem"

/** The results card's header, shared by the real Memories view and the demo
 *  page so the two cannot drift apart. "populated" is Advanced-only; "empty"
 *  is shown in both modes. */
export function MemoryResultsHeader({
  scopeLabel,
  shown,
  total,
}: {
  scopeLabel: string
  shown: number
  total: number
}) {
  const advanced = useDetailLevel((s) => s.level) === "advanced"
  return (
    <div
      data-testid="memory-results-header"
      className="border-border bg-muted/30 flex flex-wrap items-center gap-2.5 border-b px-4 py-2.5"
    >
      <span className="text-sm font-semibold">Results — project: {scopeLabel}</span>
      {(shown === 0 || advanced) && (
        <span
          className={cn(
            "font-mono text-sm",
            shown > 0 ? "text-success-text" : "text-muted-foreground",
          )}
        >
          {shown > 0 ? "populated" : "empty"}
        </span>
      )}
      <span className="text-muted-foreground ml-auto font-mono text-sm">
        {shown} of {total} shown
      </span>
    </div>
  )
}
