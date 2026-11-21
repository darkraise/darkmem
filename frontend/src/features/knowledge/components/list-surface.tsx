import type { MouseEvent, ReactNode } from "react"
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "darkraise-ui/components/pagination"
import { cn } from "darkraise-ui/lib"

export function ListSurface({
  title,
  populated,
  meta,
  children,
  className,
  bodyClassName,
}: {
  title: string
  populated: boolean
  meta?: string
  children: ReactNode
  className?: string
  /** Overrides the stacked-rows body — virtualized lists position their
   *  own rows and cannot sit in a flex column with a gap. */
  bodyClassName?: string
}) {
  return (
    <div
      className={cn(
        "border-border bg-card overflow-hidden rounded-lg border",
        className,
      )}
    >
      <div className="border-border bg-muted/30 flex flex-wrap items-center gap-2.5 border-b px-4 py-2.5">
        <span className="text-sm font-semibold">{title}</span>
        {/* A meta count ("0 open") already says it; "empty" beside it is
            noise. */}
        {!populated && !meta && (
          <span className="text-muted-foreground font-mono text-sm">empty</span>
        )}
        {meta && (
          <span className="text-muted-foreground ml-auto font-mono text-sm">
            {meta}
          </span>
        )}
      </div>
      <div className={cn("flex flex-col gap-2.5 p-4", bodyClassName)}>
        {children}
      </div>
    </div>
  )
}

/** The knowledge queues' pager: the library pagination with a previous and a
 *  next step and the range it shows. Hidden while one page holds everything. */
export function QueuePager({
  offset,
  limit,
  total,
  onPrev,
  onNext,
}: {
  offset: number
  limit: number
  total: number
  onPrev: () => void
  onNext: () => void
}) {
  if (total <= limit) return null
  const step = (enabled: boolean, go: () => void) => ({
    href: "#",
    "aria-disabled": enabled ? undefined : true,
    tabIndex: enabled ? undefined : -1,
    className: enabled ? undefined : "pointer-events-none opacity-50",
    onClick: (event: MouseEvent<HTMLAnchorElement>) => {
      event.preventDefault()
      if (enabled) go()
    },
  })
  return (
    <div className="flex items-center justify-end gap-2 pt-1">
      <span className="text-muted-foreground font-mono text-sm">
        {Math.min(offset + 1, total)}–{Math.min(offset + limit, total)} of{" "}
        {total}
      </span>
      <Pagination className="mx-0 w-auto">
        <PaginationContent>
          <PaginationItem>
            <PaginationPrevious {...step(offset > 0, onPrev)} />
          </PaginationItem>
          <PaginationItem>
            <PaginationNext {...step(offset + limit < total, onNext)} />
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </div>
  )
}
