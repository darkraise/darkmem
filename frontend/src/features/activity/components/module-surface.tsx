import type { ReactNode } from "react"
import {
  CircleDashed,
  Clock,
  List,
  type LucideIcon,
} from "lucide-react"
import { cn } from "darkraise-ui/lib"

export type SurfaceState = "populated" | "empty" | "staged"

const STATE_STYLES: Record<
  SurfaceState,
  { icon: LucideIcon; className: string }
> = {
  populated: { icon: List, className: "text-success border-success/40" },
  empty: {
    icon: CircleDashed,
    className: "text-muted-foreground border-border border-dashed",
  },
  staged: {
    icon: Clock,
    className: "text-warning border-warning/50 border-dashed",
  },
}

export function SurfaceStateChip({
  state,
  label,
  className,
}: {
  state: SurfaceState
  label?: string
  className?: string
}) {
  const { icon: Icon, className: stateClass } = STATE_STYLES[state]
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide",
        stateClass,
        className,
      )}
    >
      <Icon aria-hidden className="h-3 w-3" />
      {label ?? state}
    </span>
  )
}

export function ModuleSurface({
  title,
  state,
  meta,
  actions,
  children,
  className,
}: {
  title: string
  state: SurfaceState
  meta?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
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
        {meta && (
          <span className="text-muted-foreground font-mono text-sm">{meta}</span>
        )}
        <div className="ml-auto flex items-center gap-2">
          {actions}
          <SurfaceStateChip state={state} />
        </div>
      </div>
      <div className="flex flex-col gap-2.5 p-4">{children}</div>
    </div>
  )
}
