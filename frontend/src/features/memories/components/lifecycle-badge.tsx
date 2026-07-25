import { History } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { cn } from "darkraise-ui/lib"
import type { MemoryStatus } from "@/hooks/api"

// Lifecycle caution marker (superseded/deprecated) — distinct from the
// verification ladder; honesty invariant 14 says it renders in every mode.
export function LifecycleBadge({
  status,
  className,
}: {
  status?: MemoryStatus
  className?: string
}) {
  if (!status || status === "active") return null
  return (
    <Badge
      variant="outline"
      size="sm"
      className={cn(
        "border-warning/50 bg-warning/10 text-warning gap-1",
        className,
      )}
    >
      <History aria-hidden className="h-3 w-3" />
      {status}
    </Badge>
  )
}
