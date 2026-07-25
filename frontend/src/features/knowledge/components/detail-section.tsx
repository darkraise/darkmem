import type { ReactNode } from "react"
import {
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "darkraise-ui/components/accordion"

// Progressive disclosure for the knowledge detail pages: the hero stays a
// calm, readable claim; every supporting module (sources, ladder, windows,
// provenance, citations, coverage) lives in one of these sections —
// available on demand, never competing with the main content. The honesty
// statuses themselves (verification badge, disputed, stale) never move in
// here; only their supporting detail does.
export function DetailSection({
  value,
  title,
  meta,
  hint,
  children,
}: {
  value: string
  title: string
  /** Compact always-visible summary on the collapsed row, e.g. counts. */
  meta?: ReactNode
  /** Long explanation, shown muted at the top of the disclosed content. */
  hint?: ReactNode
  children: ReactNode
}) {
  return (
    <AccordionItem value={value} className="border-border">
      <AccordionTrigger className="gap-3 py-3 text-sm font-semibold hover:no-underline">
        <span className="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-2.5 gap-y-0.5 text-left">
          <span>{title}</span>
          {meta && (
            <span className="text-muted-foreground font-mono text-[10px] font-normal tracking-wide">
              {meta}
            </span>
          )}
        </span>
      </AccordionTrigger>
      <AccordionContent className="pb-4">
        <div className="space-y-2.5">
          {hint && (
            <p className="text-muted-foreground max-w-prose text-sm">{hint}</p>
          )}
          {children}
        </div>
      </AccordionContent>
    </AccordionItem>
  )
}
