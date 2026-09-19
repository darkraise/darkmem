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
        "border-warning/50 bg-warning/10 text-warning-text gap-1",
        className,
      )}
    >
      <History aria-hidden className="h-3 w-3" />
      {status}
    </Badge>
  )
}

/**
 * The compact counterpart for a prose-embedded citation chip (chat's inline
 * MemoryBadge, T1.60): where LifecycleBadge renders nothing on `active` (a
 * caller with room for the full badge already shows a stated absence
 * elsewhere), a chip with no room for that has no way to distinguish "known
 * active" from "no lifecycle signal at all" if this also rendered nothing.
 * So this dot is always present — muted for active/unset, the same warning
 * color LifecycleBadge uses otherwise — reusing its status→visual mapping
 * rather than a second, chat-local color scheme.
 */
export function LifecycleDot({
  status,
  className,
}: {
  status?: MemoryStatus
  className?: string
}) {
  const isCaution = !!status && status !== "active"
  return (
    <span
      aria-hidden
      className={cn(
        "inline-block h-1.5 w-1.5 shrink-0 rounded-full",
        isCaution ? "bg-warning" : "bg-muted-foreground/40",
        className,
      )}
    />
  )
}
