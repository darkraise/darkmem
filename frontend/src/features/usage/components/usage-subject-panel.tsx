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
import { formatTokens, formatUsd } from "../format"

export function UsageSubjectPanel({ data }: { data: UsageSubject }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">
          {data.subject_type}{" "}
          <span className="text-muted-foreground font-mono text-xs">
            {data.subject_id}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <span className="font-mono">{formatUsd(data.total_cost_micros)}</span>
          <span className="text-muted-foreground">
            {data.total_calls} calls
          </span>
          {data.batched_embedding ? (
            // Not "no embedding cost": the content and entity-name embeds for
            // this memory rode one call covering the whole batch, deduped and
            // cache-hit across it. There is no defined per-memory share to
            // show, and inventing one would read as a measurement.
            <Badge variant="outline">embedding batched</Badge>
          ) : null}
        </div>

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
                  <TableHead className="text-right">ms</TableHead>
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
                    <TableCell className="text-right font-mono text-xs">
                      {call.duration_ms}
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
