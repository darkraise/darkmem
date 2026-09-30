import { AlertTriangle, Info } from "lucide-react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "darkraise-ui/components/table"

import type {
  UsageBreakdownRow,
  UsageOverview as UsageOverviewData,
  UsageSeriesBucket,
} from "@/hooks/api"
import { costCell, formatTokens, formatUsd } from "../format"
import { CostByPurpose, ShareBar, SpendOverTime } from "./usage-charts"

/** A caveat the number cannot carry on its own.
 *
 *  Each of these exists because the figure beside it is honest but incomplete,
 *  and an operator acting on the figure alone would act wrongly. */
function Caveat({ children }: { children: React.ReactNode }) {
  return (
    <li className="text-muted-foreground flex items-start gap-1.5 text-xs">
      <Info aria-hidden className="mt-0.5 h-3 w-3 shrink-0" />
      <span>{children}</span>
    </li>
  )
}

/** Label above, value below, in the app's own text tokens. Deliberately not a
 *  one-bar chart: a handful of headline numbers is a KPI row. */
function Figure({
  label,
  value,
  hint,
  hero = false,
}: {
  label: string
  value: string
  hint?: string
  hero?: boolean
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-muted-foreground font-mono text-xs font-semibold tracking-[0.14em] uppercase">
        {label}
      </span>
      <span
        className={
          hero
            ? "text-4xl leading-none font-semibold tabular-nums"
            : "text-xl leading-none font-medium tabular-nums"
        }
      >
        {value}
      </span>
      {hint ? (
        <span className="text-muted-foreground text-xs">{hint}</span>
      ) : null}
    </div>
  )
}

/** A single ratio against its ceiling reads as a meter, not a pie of two
 *  slices. The track is the same hue one step back. */
function CacheMeter({ ratio }: { ratio: number | null }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-muted-foreground font-mono text-xs font-semibold tracking-[0.14em] uppercase">
        Cache hit
      </span>
      <span className="text-xl leading-none font-medium tabular-nums">
        {ratio === null ? "—" : `${(ratio * 100).toFixed(0)}%`}
      </span>
      <div className="bg-muted mt-1 h-1.5 w-full overflow-hidden rounded-full">
        <div
          className="h-full rounded-full"
          style={{
            width: `${Math.round((ratio ?? 0) * 100)}%`,
            background: "var(--chart-1)",
          }}
        />
      </div>
      <span className="text-muted-foreground text-xs">
        {ratio === null ? "no measured input tokens" : "of input tokens cached"}
      </span>
    </div>
  )
}

function BreakdownTable({
  title,
  rows,
  keyLabel,
}: {
  title: string
  rows: UsageBreakdownRow[]
  keyLabel: string
}) {
  const max = rows.reduce((m, r) => Math.max(m, r.cost_micros), 0)
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <p className="text-muted-foreground text-xs">
            No calls in this window.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{keyLabel}</TableHead>
                  <TableHead className="w-28">Share</TableHead>
                  <TableHead className="text-right">Cost</TableHead>
                  <TableHead className="text-right">Calls</TableHead>
                  <TableHead className="text-right">In</TableHead>
                  <TableHead className="text-right">Out</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row) => (
                  <TableRow key={row.key}>
                    <TableCell className="font-mono text-xs">
                      {row.key}
                      {/* An incomplete row says so where it is read, not only
                          in the page-level caveat list. */}
                      {row.unmeasured_calls > 0 || row.unpriced_calls > 0 ? (
                        <AlertTriangle
                          aria-label={`${row.key} has calls that are not fully costed`}
                          className="text-warning-text ml-1 inline h-3 w-3"
                        />
                      ) : null}
                    </TableCell>
                    <TableCell>
                      <ShareBar max={max} value={row.cost_micros} />
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">
                      {costCell(row)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">
                      {row.calls}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">
                      {formatTokens(row.prompt_tokens)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">
                      {formatTokens(row.completion_tokens)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function UsageOverview({
  data,
  series = [],
}: {
  data: UsageOverviewData
  series?: UsageSeriesBucket[]
}) {
  const caveats: React.ReactNode[] = []
  if (data.merged_classification_present) {
    caveats.push(
      <Caveat key="merged">
        Classification runs inside extraction calls, so its cost is counted
        under extraction.
      </Caveat>,
    )
  }
  if (data.unmeasured_calls > 0) {
    caveats.push(
      <Caveat key="unmeasured">
        {data.unmeasured_calls} calls reported no token counts, so spend is a
        lower bound.
      </Caveat>,
    )
  }
  if (data.unpriced_calls > 0) {
    caveats.push(
      <Caveat key="unpriced">
        {data.unpriced_calls} calls not priced
        {data.unpriced_models.length > 0
          ? ` (${data.unpriced_models.join(", ")})`
          : ""}{" "}
        — add a rate under Prices.
      </Caveat>,
    )
  }
  if (data.failed_calls > 0) {
    caveats.push(
      <Caveat key="failed">
        {data.failed_calls} calls failed, costing{" "}
        {formatUsd(data.failed_cost_micros)}.
      </Caveat>,
    )
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="grid gap-6 pt-5 md:grid-cols-[minmax(0,1.4fr)_repeat(3,minmax(0,1fr))]">
          <Figure
            hero
            hint={
              data.window_start
                ? `since ${new Date(data.window_start).toLocaleDateString()}`
                : "all recorded calls"
            }
            label="Spend"
            value={formatUsd(data.total_cost_micros)}
          />
          <Figure
            hint={
              data.failed_calls > 0 ? `${data.failed_calls} failed` : "all ok"
            }
            label="Calls"
            value={String(data.total_calls)}
          />
          <Figure
            hint={`${formatTokens(data.completion_tokens)} out`}
            label="Input tokens"
            value={formatTokens(data.prompt_tokens)}
          />
          <CacheMeter ratio={data.cache_hit_ratio} />
        </CardContent>
      </Card>

      {caveats.length > 0 ? (
        <Card border="accent">
          <CardContent className="pt-4">
            <ul className="space-y-1.5">{caveats}</ul>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Spend over time</CardTitle>
          </CardHeader>
          <CardContent>
            <SpendOverTime buckets={series} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Cost by purpose</CardTitle>
          </CardHeader>
          <CardContent>
            <CostByPurpose rows={data.by_purpose} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <BreakdownTable title="By model" keyLabel="Model" rows={data.by_model} />
        <BreakdownTable
          title="By subject"
          keyLabel="Subject"
          rows={data.by_subject_type}
        />
      </div>
    </div>
  )
}
