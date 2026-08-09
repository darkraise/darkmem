import { ArrowRight, BatteryLow, CalendarOff, EyeOff, History, RefreshCcw } from "lucide-react"
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

// T2.95's suppression marker, rendered beside the rung it replaced. The
// backend withholds a promoted status when its evidence record is absent and
// serves `candidate` instead — honest about the rung, silent about the reason.
// Without this the suppressed row and a genuinely-candidate row are identical
// on screen, so a reader cannot tell "not yet corroborated" from "corroborated,
// but we have not earned the right to say so". The reason arrives as a full
// sentence from `claim_gates`, not a slug, so it is shown rather than re-worded:
// this surface has one job, which is not to paraphrase the gate.
export function SuppressedBadge({
  reason,
  className,
}: {
  reason: string
  className?: string
}) {
  return (
    <Badge
      variant="outline"
      size="sm"
      title={reason}
      className={cn("border-muted-foreground/50 text-muted-foreground gap-1", className)}
    >
      <EyeOff aria-hidden className="h-3 w-3" />
      label withheld
    </Badge>
  )
}

// The belief axis, rendered beside the rung and never folded into it: the
// two are independent (doc 08 §3), so a closed window is retained history
// and not a weaker verification state. Absent both markers the row says
// nothing about belief, which is what a current fact means.
export function BeliefStateBadge({
  windowClosed,
  expired,
  invalidAt,
  className,
}: {
  windowClosed: boolean
  expired: boolean
  /** Shown only where the surface asks for the technical detail. */
  invalidAt?: string | null
  className?: string
}) {
  if (!windowClosed && !expired) return null
  const Icon = expired ? CalendarOff : History
  return (
    <Badge
      variant="outline"
      size="sm"
      className={cn("border-dashed gap-1", className)}
    >
      <Icon aria-hidden className="h-3 w-3" />
      {expired ? "belief withdrawn" : "window closed"}
      {invalidAt && (
        <span className="text-muted-foreground font-mono text-[10px]">
          {invalidAt}
        </span>
      )}
    </Badge>
  )
}

// review_state='open' means a human verdict is queued. The fact is listed
// either way — the queue is never a gate on a read (doc 08 §6) — so the
// label discloses the queue rather than withholding the row.
export function InReviewBadge({ className }: { className?: string }) {
  return (
    <Badge
      variant="outline"
      size="sm"
      className={cn("text-muted-foreground border-dashed", className)}
    >
      in review
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
