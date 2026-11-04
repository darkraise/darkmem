import type { ReactNode } from "react"
import {
  CircleAlert,
  CircleDashed,
  Clock,
  List,
  type LucideIcon,
} from "lucide-react"
import { cn } from "darkraise-ui/lib"

export type SurfaceState = "populated" | "empty" | "staged" | "error"

const STATE_STYLES: Record<
  SurfaceState,
  { icon: LucideIcon; className: string }
> = {
  populated: { icon: List, className: "text-success-text border-success-edge/40" },
  empty: {
    icon: CircleDashed,
    className: "text-muted-foreground border-border border-dashed",
  },
  staged: {
    icon: Clock,
    className: "text-warning-text border-warning-edge/50 border-dashed",
  },
  // A failed read is not an empty one, and a surface that renders it as
  // `empty` asserts an absence it never observed (invariant 14).
  error: {
    icon: CircleAlert,
    className: "text-destructive-text border-destructive-edge/50",
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
  // A caller-supplied label ("connected", "claimed") carries meaning of its
  // own; only the bare data-state words are hidden.
  if (!label && (state === "populated" || state === "staged")) return null
  const { icon: Icon, className: stateClass } = STATE_STYLES[state]
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-xs tracking-wide uppercase",
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
          <span className="text-muted-foreground font-mono text-sm">
            {meta}
          </span>
        )}
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {actions}
          {state === "error" && <SurfaceStateChip state="error" />}
        </div>
      </div>
      <div className="flex flex-col gap-2.5 p-4">{children}</div>
    </div>
  )
}
