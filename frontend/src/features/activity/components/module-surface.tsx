import type { ReactNode } from "react"
import {
  CircleAlert,
  CircleDashed,
  Clock,
  List,
  type LucideIcon,
} from "lucide-react"
import { cn } from "darkraise-ui/lib"
import { useDetailLevel } from "@/components/darkmem"

export type SurfaceState = "populated" | "empty" | "staged" | "error"

const STATE_STYLES: Record<
  SurfaceState,
  { icon: LucideIcon; className: string }
> = {
  populated: { icon: List, className: "text-success-text border-success/40" },
  empty: {
    icon: CircleDashed,
    className: "text-muted-foreground border-border border-dashed",
  },
  staged: {
    icon: Clock,
    className: "text-warning-text border-warning/50 border-dashed",
  },
  // A failed read is not an empty one, and a surface that renders it as
  // `empty` asserts an absence it never observed (invariant 14).
  error: {
    icon: CircleAlert,
    className: "text-destructive border-destructive/50",
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
  const advanced = useDetailLevel((s) => s.level) === "advanced"
  if (state === "populated" && !advanced) return null
  const { icon: Icon, className: stateClass } = STATE_STYLES[state]
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-xs uppercase tracking-wide",
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
