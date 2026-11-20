import type { ReactNode } from "react"
import { TriangleAlert } from "lucide-react"
import { cn } from "darkraise-ui/lib"

export interface ExclusionItem {
  count: number
  /** What was excluded, e.g. "facts" — defaults to row/rows. */
  unit?: string
  /** Human explanation, e.g. "your context env=prod conflicts with a dev-only row". */
  reason: ReactNode
  /** Machine reason tag, e.g. "by_result_limit". Not rendered. */
  tag?: string
}

export interface ExclusionStripProps {
  items: ExclusionItem[]
  className?: string
}

// Honest-exclusion surface: silent drops are the failure the design fears
// most, so exclusion counts render as plain copy in every detail mode.
export function ExclusionStrip({ items, className }: ExclusionStripProps) {
  if (items.length === 0) return null
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {items.map((item, i) => (
        <div
          key={i}
          className="border-warning-edge/55 bg-warning-solid/8 flex items-center gap-2 rounded-sm border border-dashed px-2.5 py-1.5 text-sm"
        >
          <TriangleAlert aria-hidden className="text-warning-text h-4 w-4 shrink-0" />
          <span>
            <b className="font-semibold">
              {item.count} {item.unit ?? (item.count === 1 ? "row" : "rows")}{" "}
              excluded
            </b>
            <span className="text-muted-foreground"> — {item.reason}</span>
          </span>
        </div>
      ))}
    </div>
  )
}
