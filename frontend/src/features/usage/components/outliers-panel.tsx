import { AlertTriangle, Coins, Phone, Timer } from "lucide-react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Badge } from "darkraise-ui/components/badge"
import {
  SegmentGroup,
  SegmentGroupIndicator,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { cn } from "darkraise-ui/lib"

import { EmptyState } from "@/components/darkmem"
import type { UsageTopRow } from "@/hooks/api"
import { formatDuration, formatTokens, formatUsd } from "../format"
import { subjectLabel, subjectTypeTitle } from "../subject-label"

export type OutlierAxis = "cost" | "calls" | "duration"

export const AXES: ReadonlyArray<{
  value: OutlierAxis
  label: string
  icon: typeof Coins
}> = [
  { value: "cost", label: "Cost", icon: Coins },
  { value: "calls", label: "Calls", icon: Phone },
  { value: "duration", label: "Time", icon: Timer },
]

/** The value the active ranking is actually sorted by, rendered in its own
 *  units. Ranking by one axis and showing another is how a list stops making
 *  sense halfway down. */
function axisValue(row: UsageTopRow, axis: OutlierAxis): number {
  if (axis === "calls") return row.calls
  if (axis === "duration") return row.duration_ms
  return row.cost_micros
}

function axisText(row: UsageTopRow, axis: OutlierAxis): string {
  if (axis === "calls") return String(row.calls)
  if (axis === "duration") return formatDuration(row.duration_ms)
  return formatUsd(row.cost_micros)
}

function OutlierRow({
  row,
  rank,
  axis,
  max,
  windowTotal,
  selected,
  onSelect,
}: {
  row: UsageTopRow
  rank: number
  axis: OutlierAxis
  max: number
  windowTotal: number
  selected: boolean
  onSelect: () => void
}) {
  const label = subjectLabel(row.subject_type, row.subject_id)
  const value = axisValue(row, axis)
  const pct = max > 0 ? Math.max(1.5, (value / max) * 100) : 0
  // Share is only meaningful against a total in the same units, and the window
  // total this page has is money. Ranking by calls or time shows no share
  // rather than a percentage of the wrong denominator.
  const share =
    axis === "cost" && windowTotal > 0
      ? (row.cost_micros / windowTotal) * 100
      : null
  const perCall = row.calls > 0 ? row.cost_micros / row.calls : 0

  const openable = row.subject_id !== null

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      disabled={!openable}
      title={openable ? label.raw ?? undefined : "No subject id to open"}
      className={cn(
        "border-border focus-visible:ring-ring w-full rounded-md border p-3 text-left transition-colors focus-visible:ring-2 focus-visible:outline-none",
        openable ? "hover:bg-muted/40" : "cursor-default",
        selected && "border-primary/50 bg-primary/5",
      )}
    >
      <div className="flex items-start gap-3">
        <span className="text-muted-foreground w-6 shrink-0 pt-0.5 text-right font-mono text-xs tabular-nums">
          {rank}
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-2">
            <span className="truncate font-mono text-sm font-medium">
              {label.title}
            </span>
            {/* Only where it adds something: for a job run or a maintenance
                pass the title is the key, not the kind. */}
            {label.title !== subjectTypeTitle(row.subject_type) ? (
              <Badge variant="outline" size="sm" className="font-mono">
                {subjectTypeTitle(row.subject_type)}
              </Badge>
            ) : null}
            {label.detail ? (
              <span className="text-muted-foreground truncate font-mono text-xs">
                {label.detail}
              </span>
            ) : null}
            {row.project ? (
              <span className="text-muted-foreground truncate text-xs">
                · {row.project}
              </span>
            ) : null}
            {row.unmeasured_calls > 0 ? (
              <span
                className="text-warning-text inline-flex items-center gap-1 text-xs"
                title={`${row.unmeasured_calls} of ${row.calls} calls reported no token counts, so this is a lower bound`}
              >
                <AlertTriangle aria-hidden className="h-3 w-3" />
                {row.unmeasured_calls} unmeasured
              </span>
            ) : null}
          </div>

          <div className="mt-2 flex items-center gap-3">
            <div className="bg-muted h-1.5 min-w-0 flex-1 overflow-hidden rounded-full">
              <div
                className="h-full rounded-full"
                style={{ width: `${pct}%`, background: "var(--chart-1)" }}
              />
            </div>
            <span className="text-muted-foreground shrink-0 font-mono text-xs tabular-nums">
              {share !== null ? `${share.toFixed(1)}% of window` : ""}
            </span>
          </div>

          <div className="text-muted-foreground mt-1.5 flex flex-wrap gap-x-3 font-mono text-xs tabular-nums">
            <span>{row.calls} calls</span>
            <span>{formatDuration(row.duration_ms)}</span>
            {axis !== "cost" ? <span>{formatUsd(row.cost_micros)}</span> : null}
            {row.calls > 0 ? <span>{formatUsd(perCall)}/call</span> : null}
          </div>
        </div>

        <span className="shrink-0 pt-0.5 text-right font-mono text-base font-medium tabular-nums">
          {axisText(row, axis)}
        </span>
      </div>
    </button>
  )
}

export function OutliersPanel({
  rows,
  axis,
  onAxisChange,
  windowTotal,
  windowCalls,
  selectedKey,
  onSelect,
  isLoading,
  isError,
  typeFilter,
  onTypeFilterChange,
  availableTypes,
}: {
  rows: UsageTopRow[]
  axis: OutlierAxis
  onAxisChange: (axis: OutlierAxis) => void
  windowTotal: number
  windowCalls: number
  /** `${subject_type}:${subject_id}` of the open row, or null. Keyed on both
   *  because a null subject_id is shared by every unattributed row -- comparing
   *  ids alone marked them all as open. */
  selectedKey: string | null
  onSelect: (subjectType: string, subjectId: string) => void
  isLoading: boolean
  isError: boolean
  typeFilter: string | null
  onTypeFilterChange: (type: string | null) => void
  availableTypes: string[]
}) {
  const max = rows.reduce((m, r) => Math.max(m, axisValue(r, axis)), 0)
  const listedCost = rows.reduce((sum, r) => sum + r.cost_micros, 0)
  const listedCalls = rows.reduce((sum, r) => sum + r.calls, 0)
  const concentration =
    windowTotal > 0 ? (listedCost / windowTotal) * 100 : null

  return (
    <Card>
      <CardHeader className="gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <CardTitle className="text-sm">Outliers</CardTitle>
          <div className="ml-auto">
            <SegmentGroup
              aria-label="Rank by"
              color="accent"
              value={axis}
              onValueChange={(v) => {
                if (v) onAxisChange(v as OutlierAxis)
              }}
            >
              <SegmentGroupIndicator />
              {AXES.map((a) => (
                <SegmentGroupItem key={a.value} value={a.value}>
                  {a.label}
                </SegmentGroupItem>
              ))}
            </SegmentGroup>
          </div>
        </div>

        {/* The number that turns a ranked list into a finding: whether the
            spend is concentrated in these rows or spread across the corpus. */}
        {!isLoading && !isError && rows.length > 0 ? (
          <p className="text-muted-foreground text-xs">
            These {rows.length} subjects account for{" "}
            <strong className="text-foreground">
              {concentration !== null
                ? `${concentration.toFixed(0)}% of ${formatUsd(windowTotal)}`
                : formatUsd(listedCost)}
            </strong>{" "}
            and {listedCalls} of {windowCalls} calls in this window.
            {typeFilter ? ` Filtered to ${subjectTypeTitle(typeFilter)}.` : ""}
          </p>
        ) : null}

        {availableTypes.length > 1 ? (
          <div className="flex flex-wrap gap-1.5">
            <button
              type="button"
              onClick={() => onTypeFilterChange(null)}
              className={cn(
                "border-border rounded-full border px-2 py-0.5 font-mono text-xs transition-colors",
                typeFilter === null
                  ? "border-primary/50 bg-primary/10 text-foreground"
                  : "text-muted-foreground hover:bg-muted/50",
              )}
            >
              all
            </button>
            {availableTypes.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => onTypeFilterChange(t)}
                className={cn(
                  "border-border rounded-full border px-2 py-0.5 font-mono text-xs transition-colors",
                  typeFilter === t
                    ? "border-primary/50 bg-primary/10 text-foreground"
                    : "text-muted-foreground hover:bg-muted/50",
                )}
              >
                {t}
              </button>
            ))}
          </div>
        ) : null}
      </CardHeader>

      <CardContent className="space-y-2">
        {isLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : isError ? (
          <EmptyState
            kind="failed"
            title="Could not read the outlier list"
          />
        ) : rows.length === 0 ? (
          <EmptyState
            kind="empty"
            title={
              typeFilter
                ? `No ${subjectTypeTitle(typeFilter)} calls in this window`
                : "No recorded calls in this window"
            }
          />
        ) : (
          rows.map((row, i) => (
            <OutlierRow
              key={`${row.subject_type}:${row.subject_id}`}
              axis={axis}
              max={max}
              onSelect={() =>
                row.subject_id && onSelect(row.subject_type, row.subject_id)
              }
              rank={i + 1}
              row={row}
              selected={
                row.subject_id !== null &&
                selectedKey === `${row.subject_type}:${row.subject_id}`
              }
              windowTotal={windowTotal}
            />
          ))
        )}
      </CardContent>
    </Card>
  )
}

export { formatTokens }
