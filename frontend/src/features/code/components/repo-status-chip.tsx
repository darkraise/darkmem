import {
  CircleCheck,
  CircleDashed,
  Clock,
  RefreshCw,
  TriangleAlert,
  type LucideIcon,
} from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { cn } from "darkraise-ui/lib"
import type { DemoRepoStatus } from "@/demo/types"

const STYLES: Record<
  DemoRepoStatus,
  { icon: LucideIcon; label: string; className: string }
> = {
  ready: {
    icon: CircleCheck,
    label: "ready",
    className: "border-success-edge/50 bg-success-solid/10 text-success-text",
  },
  indexing: {
    icon: RefreshCw,
    label: "indexing",
    className: "border-info-edge/50 bg-info-solid/10 text-info-text",
  },
  // stale is a per-repo status (T1), not a whole-screen render state: the
  // last-good graph is still served, only labelled.
  stale: {
    icon: Clock,
    label: "stale",
    className: "border-warning-edge/60 border-dashed bg-warning-solid/10 text-warning-text",
  },
  error: {
    icon: TriangleAlert,
    label: "error",
    className: "border-destructive-edge/50 bg-destructive-solid/10 text-destructive-text",
  },
  registered: {
    icon: CircleDashed,
    label: "registered",
    className: "border-border border-dashed bg-muted/50 text-muted-foreground",
  },
}

export function RepoStatusChip({
  status,
  className,
}: {
  status: DemoRepoStatus
  className?: string
}) {
  const { icon: Icon, label, className: statusClass } = STYLES[status]
  return (
    <Badge
      variant="outline"
      size="sm"
      className={cn("gap-1 font-mono uppercase", statusClass, className)}
    >
      <Icon aria-hidden className="h-3 w-3" />
      {label}
    </Badge>
  )
}
