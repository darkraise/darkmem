import {
  CircleAlert,
  CircleCheck,
  CircleDashed,
  History,
  Waypoints,
  type LucideIcon,
} from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { cn } from "darkraise-ui/lib"

export type VerificationStatus =
  | "candidate"
  | "corroborated"
  | "confirmed"
  | "disputed"
  | "superseded"

const STYLES: Record<VerificationStatus, { icon: LucideIcon; className: string }> = {
  candidate: {
    icon: CircleDashed,
    className: "border-dashed border-border bg-muted/50 text-muted-foreground",
  },
  corroborated: {
    icon: Waypoints,
    className: "border-primary/50 bg-primary/10 text-primary-text",
  },
  confirmed: {
    icon: CircleCheck,
    className: "border-success-edge/50 bg-success-solid/10 text-success-text",
  },
  disputed: {
    icon: CircleAlert,
    className: "border-warning-edge/50 bg-warning-solid/10 text-warning-text",
  },
  superseded: {
    icon: History,
    className: "border-warning-edge/50 bg-warning-solid/10 text-warning-text",
  },
}

export interface VerificationBadgeProps {
  status: VerificationStatus
  /** The full honest claim, e.g. "asserted by 3 distinct origins…". */
  detail?: string
  /** Visible-text override — e.g. "human-ratified" for the confirmed rung,
   *  which is never labelled with the bare word "confirmed" in transitions. */
  label?: string
  className?: string
}

// Honesty label (invariant 14): callers must render this in every detail
// mode — the Simple/Advanced toggle may collapse scores, never this badge.
export function VerificationBadge({
  status,
  detail,
  label,
  className,
}: VerificationBadgeProps) {
  const { icon: Icon, className: statusClass } = STYLES[status]
  return (
    <Badge
      variant="outline"
      size="sm"
      title={detail}
      className={cn("gap-1", statusClass, className)}
    >
      <Icon aria-hidden className="h-3 w-3" />
      {label ?? status}
    </Badge>
  )
}
