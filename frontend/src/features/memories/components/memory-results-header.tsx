/** The results card's header, shared by the real Memories view and the demo
 *  page so the two cannot drift apart. */
export function MemoryResultsHeader({
  shown,
  total,
}: {
  shown: number
  total: number
}) {
  return (
    <div
      data-testid="memory-results-header"
      className="border-border bg-muted/30 flex flex-wrap items-center gap-2.5 border-b px-4 py-2.5"
    >
      <span className="text-muted-foreground ml-auto font-mono text-sm">
        {shown} of {total} shown
      </span>
    </div>
  )
}
