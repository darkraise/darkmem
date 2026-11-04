import { useState } from "react"
import { Link } from "@tanstack/react-router"
import { X } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "darkraise-ui/components/table"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import { cn } from "darkraise-ui/lib"
import { EmptyState, listItemClass, Timestamp } from "@/components/darkmem"
import {
  useMcpCalls,
  useMcpCallSummary,
  type McpCallRow,
  type McpCallStatus,
  type McpCallSummary,
  type McpCallWindow,
} from "@/hooks/api"
import { DEMO } from "@/lib/demo-flag"
import { ShareBar } from "@/features/usage/components/usage-charts"
import { formatArguments } from "../mcp-format"
import { ModuleSurface } from "./module-surface"
import { shortId } from "@/lib/short-id"

const WINDOWS: McpCallWindow[] = ["24h", "7d", "30d"]
const STATUSES: (McpCallStatus | "all")[] = ["all", "ok", "error", "denied"]
const PAGE = 50
const MAX_PAGE = 200

const STATUS_TONE: Record<McpCallStatus, string> = {
  ok: "text-success-text border-success-edge/40",
  error: "text-destructive-text border-destructive-edge/50",
  denied: "text-warning-text border-warning-edge/50",
}

function StatusChip({ status }: { status: McpCallStatus }) {
  return (
    <span
      className={cn(
        "rounded-full border px-2 py-0.5 font-mono text-xs uppercase",
        STATUS_TONE[status],
      )}
    >
      {status}
    </span>
  )
}

function callerLabel(row: { key_name: string | null; client: string | null }) {
  return [row.key_name, row.client].filter(Boolean).join(" · ") || "unknown"
}

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-muted-foreground font-mono text-xs font-semibold tracking-[0.14em] uppercase">
        {label}
      </span>
      <span className="text-xl leading-none font-medium tabular-nums">
        {value}
      </span>
    </div>
  )
}

/** An object id links to its memory only when every tool that returned it is
 *  a memory tool; a document, fact or symbol id has no single detail route. */
function ObjectId({ id, tools }: { id: string; tools: string[] }) {
  if (tools.length > 0 && tools.every((t) => t.startsWith("memory_"))) {
    return (
      <Link
        to="/memories/$memoryId"
        params={{ memoryId: id }}
        className="text-primary-text font-mono text-xs underline-offset-2 hover:underline"
      >
        {shortId(id)}
      </Link>
    )
  }
  return (
    <span className="font-mono text-xs" title={id}>
      {shortId(id)}
    </span>
  )
}

function SummaryPanel({
  summary,
  onPickTool,
  onPickObject,
}: {
  summary: McpCallSummary
  onPickTool: (tool: string) => void
  onPickObject: (id: string) => void
}) {
  const maxCalls = summary.tools.reduce((m, t) => Math.max(m, t.calls), 0)
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
        <Figure label="Calls" value={summary.total.toLocaleString()} />
        <Figure label="Errors" value={summary.errors.toLocaleString()} />
        <Figure label="Denied" value={summary.denied.toLocaleString()} />
        <Figure label="Avg" value={`${summary.avg_duration_ms} ms`} />
        <Figure label="p95" value={`${summary.p95_duration_ms} ms`} />
      </div>
      {!summary.query_text_logged && (
        <p className="text-muted-foreground text-xs">
          Search queries are stored as their length only. Set{" "}
          <span className="font-mono">log_query_text</span> to 1 on the MCP Call
          Log Retention job to record them.
        </p>
      )}
      <div className="grid gap-4 2xl:grid-cols-2">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tool</TableHead>
                <TableHead className="w-24">Share</TableHead>
                <TableHead className="text-right">Calls</TableHead>
                <TableHead className="text-right">Err</TableHead>
                <TableHead className="text-right">Denied</TableHead>
                <TableHead className="text-right">p95</TableHead>
                <TableHead className="text-right">Last</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {summary.tools.map((t) => (
                <TableRow key={t.tool}>
                  <TableCell>
                    <button
                      type="button"
                      className="font-mono text-xs underline-offset-2 hover:underline"
                      onClick={() => onPickTool(t.tool)}
                    >
                      {t.tool}
                    </button>
                  </TableCell>
                  <TableCell>
                    <ShareBar max={maxCalls} value={t.calls} />
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs tabular-nums">
                    {t.calls}
                  </TableCell>
                  {/* Two columns, as the totals above count them: one "Err"
                      summing both disagreed with ERRORS / DENIED. */}
                  <TableCell className="text-right font-mono text-xs tabular-nums">
                    {t.errors}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs tabular-nums">
                    {t.denied}
                  </TableCell>
                  <TableCell className="text-right font-mono text-xs whitespace-nowrap tabular-nums">
                    {t.p95_duration_ms} ms
                  </TableCell>
                  <TableCell className="text-muted-foreground text-right text-xs whitespace-nowrap">
                    <Timestamp iso={t.last_at} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        <div className="space-y-4">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Caller</TableHead>
                  <TableHead>Mostly</TableHead>
                  <TableHead className="text-right">Calls</TableHead>
                  <TableHead className="text-right">Last</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {summary.callers.map((c) => (
                  <TableRow key={`${c.api_key_id}-${c.client}`}>
                    <TableCell className="text-xs">{callerLabel(c)}</TableCell>
                    <TableCell className="font-mono text-xs">
                      {c.top_tool}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs tabular-nums">
                      {c.calls}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-right text-xs whitespace-nowrap">
                      <Timestamp iso={c.last_at} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {summary.top_objects.length > 0 && (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Most-returned item</TableHead>
                    <TableHead>Via</TableHead>
                    <TableHead className="text-right">Times</TableHead>
                    <TableHead className="text-right">Calls</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {summary.top_objects.map((o) => (
                    <TableRow key={o.id}>
                      <TableCell>
                        <ObjectId id={o.id} tools={o.tools} />
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {o.tools.join(", ")}
                      </TableCell>
                      <TableCell className="text-right font-mono text-xs tabular-nums">
                        {o.hits}
                      </TableCell>
                      <TableCell className="text-right">
                        <button
                          type="button"
                          className="text-primary-text text-xs underline-offset-2 hover:underline"
                          onClick={() => onPickObject(o.id)}
                        >
                          show
                        </button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function CallRow({ call }: { call: McpCallRow }) {
  const args = formatArguments(call.arguments)
  return (
    <div
      className={listItemClass({
        className: "flex flex-col gap-1 px-3 py-2",
      })}
    >
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="border-border bg-muted rounded-sm border px-1.5 py-0.5 font-mono text-xs whitespace-nowrap">
          {call.tool}
        </span>
        <StatusChip status={call.status} />
        <span className="text-sm">{callerLabel(call)}</span>
        {call.project && (
          <span className="text-muted-foreground font-mono text-xs">
            project {call.project}
          </span>
        )}
        <span className="text-muted-foreground ml-auto font-mono text-xs whitespace-nowrap">
          {call.result_count !== null && `${call.result_count} results · `}
          {call.duration_ms} ms · <Timestamp iso={call.occurred_at} />
        </span>
      </div>
      {args && (
        <span className="text-muted-foreground font-mono text-xs break-all">
          {args}
        </span>
      )}
      {call.error && (
        <span className="text-destructive-text text-xs break-words">
          {call.error}
        </span>
      )}
    </div>
  )
}

export function McpTab() {
  const [range, setRange] = useState<McpCallWindow>("7d")
  const [tool, setTool] = useState<string | undefined>()
  const [status, setStatus] = useState<McpCallStatus | "all">("all")
  const [objectId, setObjectId] = useState<string | undefined>()
  const [limit, setLimit] = useState(PAGE)

  const summary = useMcpCallSummary(range)
  const calls = useMcpCalls({
    tool,
    status: status === "all" ? undefined : status,
    object_id: objectId,
    limit,
  })

  const tools = summary.data?.tools.map((t) => t.tool) ?? []
  const filtered = Boolean(tool || objectId || status !== "all")
  const items = calls.data?.items ?? []
  const total = calls.data?.total ?? 0
  const nothingYet =
    !filtered &&
    calls.isSuccess &&
    items.length === 0 &&
    summary.data?.total === 0

  return (
    <div className="space-y-4">
      <ModuleSurface
        title="MCP calls — insights"
        state={summary.isError ? "error" : "populated"}
        meta={summary.data ? `last ${range}` : undefined}
        actions={
          <ToggleGroup
            type="single"
            value={range}
            onValueChange={(v) => {
              if (v) setRange(v as McpCallWindow)
            }}
          >
            {WINDOWS.map((w) => (
              <ToggleGroupItem
                key={w}
                value={w}
                size="sm"
                className="font-mono text-sm"
              >
                {w}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        }
      >
        {summary.isError ? (
          <EmptyState
            kind="failed"
            title="Couldn't load the MCP call summary"
            description="Reopen the tab to retry."
          />
        ) : !summary.data ? null : summary.data.total === 0 ? (
          <EmptyState
            kind="empty"
            title="No MCP calls in this window"
            description="Calls appear here as soon as a client uses an API key on /mcp."
          />
        ) : (
          <SummaryPanel
            summary={summary.data}
            onPickTool={(t) => {
              setTool(t)
              setLimit(PAGE)
            }}
            onPickObject={(id) => {
              setObjectId(id)
              setLimit(PAGE)
            }}
          />
        )}
      </ModuleSurface>

      {/* With no call in the window and none ever listed, the insights card
          already says so; a second empty card under it said it again. */}
      {nothingYet ? null : (
        <ModuleSurface
          title="Recent MCP calls"
          state={calls.isError ? "error" : "populated"}
          meta={calls.data ? `${total.toLocaleString()} matching` : undefined}
          actions={
            <span className="text-muted-foreground font-mono text-sm">
              {DEMO ? "demo data" : "polling every 10s"}
            </span>
          }
        >
          <div className="flex flex-wrap items-center gap-2.5">
            <Select
              value={tool ?? "__all"}
              onValueChange={(v) => {
                setTool(v === "__all" ? undefined : v)
                setLimit(PAGE)
              }}
            >
              <SelectTrigger
                className="w-auto min-w-44 rounded-full"
                aria-label="Tool"
              >
                <SelectValue>{tool ?? "all tools"}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all">all tools</SelectItem>
                {(tool && !tools.includes(tool) ? [tool, ...tools] : tools).map(
                  (t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ),
                )}
              </SelectContent>
            </Select>
            <ToggleGroup
              type="single"
              value={status}
              onValueChange={(v) => {
                if (v) {
                  setStatus(v as McpCallStatus | "all")
                  setLimit(PAGE)
                }
              }}
              className="flex-wrap justify-start"
            >
              {STATUSES.map((s) => (
                <ToggleGroupItem
                  key={s}
                  value={s}
                  size="sm"
                  className="font-mono text-sm"
                >
                  {s}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
            {objectId && (
              <Button
                size="sm"
                variant="outline"
                className="gap-1 rounded-full font-mono"
                onClick={() => setObjectId(undefined)}
              >
                returned {shortId(objectId)}
                <X aria-label="Clear item filter" className="h-3 w-3" />
              </Button>
            )}
          </div>
          {calls.isError ? (
            <EmptyState
              kind="failed"
              title="Couldn't load MCP calls"
              description="Reopen the tab to retry."
            />
          ) : items.length === 0 && !calls.isLoading ? (
            <EmptyState
              kind={filtered ? "filtered" : "empty"}
              title={
                filtered ? "No calls match these filters" : "No MCP calls yet"
              }
              description={
                filtered
                  ? "Clear a filter to see more."
                  : "Calls appear here as soon as a client uses an API key on /mcp."
              }
            />
          ) : (
            <>
              {items.map((call) => (
                <CallRow key={call.id} call={call} />
              ))}
              {items.length < total && limit < MAX_PAGE && (
                <Button
                  variant="outline"
                  size="sm"
                  className="self-start"
                  onClick={() => setLimit((l) => Math.min(MAX_PAGE, l + PAGE))}
                >
                  Show more
                </Button>
              )}
            </>
          )}
        </ModuleSurface>
      )}
    </div>
  )
}
