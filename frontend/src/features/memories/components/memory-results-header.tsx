import type { ReactNode } from "react"
import { cn } from "darkraise-ui/lib"

/** The results card's header, shared by the real Memories view and the demo
 *  page so the two cannot drift apart. With list controls it is a toolbar
 *  band (controls left, count right); without any it collapses to a slim
 *  caption rather than an empty band holding only the count. */
export function MemoryResultsHeader({
  shown,
  total,
  children,
}: {
  shown: number
  total: number
  /** List controls (filters) rendered at the start of the band. */
  children?: ReactNode
}) {
  return (
    <div
      data-testid="memory-results-header"
      className={cn(
        "flex flex-wrap items-center gap-2.5 px-4",
        children ? "border-border bg-muted/30 border-b py-2" : "pt-3 pb-0",
      )}
    >
      {children}
      <span className="text-muted-foreground ml-auto font-mono text-sm">
        {shown} of {total} shown
      </span>
    </div>
  )
}
