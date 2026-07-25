import type { ReactNode } from "react"
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
        <span
          className={cn(
            "font-mono text-sm",
            populated ? "text-success" : "text-muted-foreground",
          )}
        >
          {populated ? "populated" : "empty"}
        </span>
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
