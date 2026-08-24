import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Badge } from "darkraise-ui/components/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "darkraise-ui/components/table"

import type { UsageSubject } from "@/hooks/api"
import { formatDuration, formatTokens, formatUsd } from "../format"
import { subjectLabel, subjectTypeTitle } from "../subject-label"

export function UsageSubjectPanel({ data }: { data: UsageSubject }) {
  const label = subjectLabel(data.subject_type, data.subject_id)
  // What the calls were for, so a reader who asks "why is this one expensive"
  // gets an answer from the panel rather than by reading down the table.
  const byPurpose = new Map<string, { calls: number; cost: number }>()
  for (const call of data.calls) {
    const at = byPurpose.get(call.purpose) ?? { calls: 0, cost: 0 }
    at.calls += 1
    at.cost += call.cost_micros ?? 0
    byPurpose.set(call.purpose, at)
  }
  const purposes = [...byPurpose.entries()].sort((a, b) => b[1].cost - a[1].cost)
  const slowest = data.calls.reduce(
    (m, c) => Math.max(m, c.duration_ms),
    0,
  )

  return (
    <Card>
      <CardHeader className="gap-1">
        <CardTitle className="flex flex-wrap items-baseline gap-2 text-sm">
          <span className="font-mono">{label.title}</span>
          <Badge variant="outline" size="sm" className="font-mono">
            {subjectTypeTitle(data.subject_type)}
          </Badge>
          {label.detail ? (
            <span className="text-muted-foreground font-mono text-xs">
              {label.detail}
            </span>
          ) : null}
        </CardTitle>
        {label.raw ? (
          <p className="text-muted-foreground truncate font-mono text-[11px]">
            {label.raw}
          </p>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span className="font-mono">{formatUsd(data.total_cost_micros)}</span>
          <span className="text-muted-foreground">
            {data.total_calls} calls
          </span>
          {slowest > 0 ? (
            <span className="text-muted-foreground font-mono text-xs">
              slowest {formatDuration(slowest)}
            </span>
          ) : null}
          {data.batched_embedding ? (
            // Not "no embedding cost": the content and entity-name embeds for
            // this memory rode one call covering the whole batch, deduped and
            // cache-hit across it. There is no defined per-memory share to
            // show, and inventing one would read as a measurement.
            <Badge variant="outline">embedding batched</Badge>
          ) : null}
        </div>

        {purposes.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {purposes.map(([purpose, at]) => (
              <span
                key={purpose}
                className="border-border text-muted-foreground rounded-full border px-2 py-0.5 font-mono text-[11px]"
              >
                {purpose} · {at.calls} · {formatUsd(at.cost)}
              </span>
            ))}
          </div>
        ) : null}

        {data.calls.length === 0 ? (
          <p className="text-muted-foreground text-xs">
            No recorded calls for this subject.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Purpose</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead className="text-right">In</TableHead>
                  <TableHead className="text-right">Out</TableHead>
                  <TableHead className="text-right">Cost</TableHead>
                  <TableHead className="text-right">Took</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.calls.map((call) => (
                  <TableRow key={call.id}>
                    <TableCell className="font-mono text-xs">
                      {new Date(call.occurred_at).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-xs">
                      {call.purpose}
                      {call.merged_classification ? (
                        <Badge className="ml-1" variant="secondary">
                          +classification
                        </Badge>
                      ) : null}
                      {!call.ok ? (
                        <Badge className="ml-1" variant="destructive">
                          {call.error_kind ?? "failed"}
                        </Badge>
                      ) : null}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {call.model}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {call.prompt_tokens === null
                        ? "—"
                        : formatTokens(call.prompt_tokens)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {call.completion_tokens === null
                        ? "—"
                        : formatTokens(call.completion_tokens)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {/* Three different reasons for "no number", kept apart:
                          unmeasured, unpriced, and a genuine zero. */}
                      {!call.tokens_measured
                        ? "not measured"
                        : call.cost_micros === null
                          ? "not priced"
                          : formatUsd(call.cost_micros)}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">
                      {formatDuration(call.duration_ms)}
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
