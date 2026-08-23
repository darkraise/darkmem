import { AlertTriangle, Info } from "lucide-react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Stat, StatLabel, StatValue } from "darkraise-ui/components/stat"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "darkraise-ui/components/table"

import type { UsageBreakdownRow, UsageOverview as UsageOverviewData } from "@/hooks/api"
import { formatTokens, formatUsd } from "../format"

/** A caveat the number cannot carry on its own.
 *
 *  Each of these exists because the plain figure beside it is honest but
 *  incomplete, and an operator acting on the figure alone would act wrongly. */
function Caveat({ children }: { children: React.ReactNode }) {
  return (
    <li className="text-muted-foreground flex items-start gap-1.5 text-xs">
      <Info aria-hidden className="mt-0.5 h-3 w-3 shrink-0" />
      <span>{children}</span>
    </li>
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
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {rows.length === 0 ? (
          <p className="text-muted-foreground text-xs">No calls in this window.</p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{keyLabel}</TableHead>
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
                          className="text-warning ml-1 inline h-3 w-3"
                        />
                      ) : null}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {formatUsd(row.cost_micros)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {row.calls}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {formatTokens(row.prompt_tokens)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
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

export function UsageOverview({ data }: { data: UsageOverviewData }) {
  const caveats: React.ReactNode[] = []
  if (data.merged_classification_present) {
    caveats.push(
      <Caveat key="merged">
        Extraction <strong>includes folded classification</strong> — under the
        default config both run in one call, so classification&apos;s own total
        reads near zero rather than being cheap.
      </Caveat>,
    )
  }
  if (data.unmeasured_calls > 0) {
    caveats.push(
      <Caveat key="unmeasured">
        {data.unmeasured_calls} calls not measured — the vendor sent no token
        envelope, so this total is a floor, not the whole spend.
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
        — measured, but no rate is set for the model. Add one under Prices.
      </Caveat>,
    )
  }
  if (data.failed_calls > 0) {
    caveats.push(
      <Caveat key="failed">
        {data.failed_calls} calls failed, costing {formatUsd(data.failed_cost_micros)}.
        A vendor bills for work that errored after it started.
      </Caveat>,
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat>
          <StatLabel>Spend</StatLabel>
          <StatValue>{formatUsd(data.total_cost_micros)}</StatValue>
        </Stat>
        <Stat>
          <StatLabel>Calls</StatLabel>
          <StatValue>{data.total_calls}</StatValue>
        </Stat>
        <Stat>
          <StatLabel>Input tokens</StatLabel>
          <StatValue>{formatTokens(data.prompt_tokens)}</StatValue>
        </Stat>
        <Stat>
          <StatLabel>Cache hit</StatLabel>
          <StatValue>
            {data.cache_hit_ratio === null
              ? "—"
              : `${(data.cache_hit_ratio * 100).toFixed(0)}%`}
          </StatValue>
        </Stat>
      </div>

      {caveats.length > 0 ? (
        <Card border="accent">
          <CardContent className="pt-4">
            <ul className="space-y-1.5">{caveats}</ul>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <BreakdownTable
          title="By purpose"
          keyLabel="Purpose"
          rows={data.by_purpose}
        />
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
