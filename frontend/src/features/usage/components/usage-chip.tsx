import { Coins } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { cn } from "darkraise-ui/lib"

import type { JobUsageRow, SubjectTotalRow } from "@/hooks/api"
import { formatTokens, formatUsd } from "../format"

type Totals = SubjectTotalRow | JobUsageRow

/**
 * What one item's LLM calls cost, in the space a table row has.
 *
 * `totals` is deliberately allowed to be `undefined` and rendered differently
 * from a zero. An item with no recorded calls has not been measured at zero --
 * the recorder may never have run for it, it may predate metering, or the row
 * may have been pruned by the retention sweep. "no spend recorded" says that;
 * "$0.00" would assert a measurement nothing took.
 */
export function UsageChip({
  totals,
  className,
  pending = false,
}: {
  totals: Totals | undefined
  className?: string
  pending?: boolean
}) {
  if (pending) {
    return (
      <span className={cn("text-muted-foreground font-mono text-xs", className)}>
        …
      </span>
    )
  }
  if (!totals) {
    return (
      <span
        className={cn("text-muted-foreground font-mono text-xs", className)}
        title="No LLM calls were recorded for this item."
      >
        no spend recorded
      </span>
    )
  }

  const tokens = totals.prompt_tokens + totals.completion_tokens
  // Three states the cost cannot collapse: fully costed, a floor (some call
  // was unmeasured or unpriced), and nothing priced at all.
  const incomplete =
    totals.unmeasured_calls > 0 || totals.unpriced_calls > 0
  const allUnpriced =
    totals.calls > 0 &&
    (totals.unpriced_calls === totals.calls ||
      totals.unmeasured_calls === totals.calls)

  return (
    <Badge
      variant="outline"
      size="sm"
      className={cn("gap-1.5 font-mono", className)}
      title={
        `${totals.calls} call${totals.calls === 1 ? "" : "s"} · ` +
        `${formatTokens(totals.prompt_tokens)} in · ` +
        `${formatTokens(totals.completion_tokens)} out` +
        (totals.cached_tokens
          ? ` · ${formatTokens(totals.cached_tokens)} cached`
          : "") +
        (totals.unmeasured_calls
          ? ` · ${totals.unmeasured_calls} unmeasured`
          : "") +
        (totals.unpriced_calls ? ` · ${totals.unpriced_calls} unpriced` : "")
      }
    >
      <Coins aria-hidden className="h-3 w-3" />
      {formatTokens(tokens)} tok
      <span className="text-muted-foreground">
        {allUnpriced
          ? "not priced"
          : `${incomplete ? "≥" : ""}${formatUsd(totals.cost_micros)}`}
      </span>
    </Badge>
  )
}
