import { ArrowRight, BatteryLow, RefreshCcw } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { cn } from "darkraise-ui/lib"
import { VerificationBadge, type VerificationStatus } from "@/components/darkmem"
import type { AppliesWhen } from "@/demo/types"

export function FactTriple({
  subject,
  rel,
  object,
  className,
}: {
  subject: string
  rel: string
  object: string
  className?: string
}) {
  return (
    <span
      className={cn("flex flex-wrap items-baseline gap-1.5 text-sm", className)}
    >
      <b className="font-semibold">{subject}</b>
      <ArrowRight aria-hidden className="text-muted-foreground h-3 w-3 self-center" />
      <Badge variant="outline" size="sm" className="rounded-sm font-mono">
        {rel}
      </Badge>
      <ArrowRight aria-hidden className="text-muted-foreground h-3 w-3 self-center" />
      <b className="font-semibold">{object}</b>
    </span>
  )
}

// One label per declared context key; an explicit "no context restriction"
// label when the fact carries none — the module is never silently omitted.
export function AppliesWhenChips({
  items,
  className,
}: {
  items: AppliesWhen[]
  className?: string
}) {
  if (items.length === 0) {
    return (
      <span className={cn("flex flex-wrap gap-1.5", className)}>
        <Badge
          variant="outline"
          size="sm"
          className="text-muted-foreground border-dashed italic"
        >
          no context restriction
        </Badge>
      </span>
    )
  }
  return (
    <span className={cn("flex flex-wrap gap-1.5", className)}>
      {items.map((item) => (
        <Badge
          key={item.key}
          variant="outline"
          size="sm"
          className="gap-1.5 border-dashed"
        >
          {item.key}={item.value}
          <span className="text-muted-foreground font-mono text-[10px]">
            {item.tag}
          </span>
        </Badge>
      ))}
    </span>
  )
}

// Stale overlay: appended after the rung badge, never replacing it.
export function StaleBadge({ className }: { className?: string }) {
  return (
    <Badge
      variant="outline"
      size="sm"
      className={cn("border-warning/50 bg-warning/10 text-warning gap-1", className)}
    >
      <RefreshCcw aria-hidden className="h-3 w-3" />
      stale
    </Badge>
  )
}

// Under-sourced overlay: appended after the rung badge during demotion
// hysteresis — the rung is unchanged, the label keeps retrieval honest.
export function UnderSourcedBadge({ className }: { className?: string }) {
  return (
    <Badge
      variant="outline"
      size="sm"
      className={cn("border-warning/50 bg-warning/10 text-warning gap-1", className)}
    >
      <BatteryLow aria-hidden className="h-3 w-3" />
      under-sourced
    </Badge>
  )
}

const LADDER: readonly string[] = [
  "candidate",
  "corroborated",
  "confirmed",
  "disputed",
  "superseded",
]

// A rung-pair side: a real badge when the value is a ladder rung, a plain
// label otherwise — never a fabricated pill.
export function RungLabel({ value }: { value: string | null }) {
  if (!value) {
    return (
      <span className="text-muted-foreground text-sm">— (no prior rung)</span>
    )
  }
  if (LADDER.includes(value)) {
    return <VerificationBadge status={value as VerificationStatus} />
  }
  return (
    <Badge
      variant="outline"
      size="sm"
      className="border-warning/50 bg-warning/10 text-warning"
    >
      {value}
    </Badge>
  )
}

export function RungTransition({
  from,
  to,
}: {
  from: string | null
  to: string
}) {
  return (
    <span className="flex items-center gap-2">
      <RungLabel value={from} />
      <ArrowRight aria-hidden className="text-muted-foreground h-3.5 w-3.5" />
      <RungLabel value={to} />
    </span>
  )
}
