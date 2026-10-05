import { useState } from "react"
import { ChevronLeft, ChevronRight, History } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { EmptyState } from "@/components/darkmem"
import { relativeTime } from "@/lib/format"
import { HISTORY_PAGE_SIZE, useJobHistory, type JobRun } from "../use-job-history"

/** Sub-second runs are the common case for a queue drainer, so ms below 1s. */
function formatDuration(seconds: number): string {
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`
  if (seconds < 60) return `${seconds.toFixed(2)}s`
  return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`
}

function RunRow({ run }: { run: JobRun }) {
  const ok = run.outcome === "ok"
  const detail = Object.entries(run.detail ?? {})
  return (
    <li className="border-border flex flex-col gap-1.5 rounded-md border px-2.5 py-2 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={ok ? "outline" : "destructive"} className="w-fit">
          {run.outcome}
        </Badge>
        <span className="text-muted-foreground">{relativeTime(run.started_at)}</span>
        <span className="text-muted-foreground font-mono text-xs">
          {formatDuration(run.duration_seconds)}
        </span>
        {/* A manual run and a scheduled tick are different facts when you are
            working out why something ran at all. */}
        {run.trigger === "manual" && (
          <Badge variant="outline" className="w-fit">
            manual
          </Badge>
        )}
        {/* Schedules read in UTC; a run time with no zone beside them read
            as the same clock. */}
        <span className="text-muted-foreground ml-auto font-mono text-xs">
          {new Date(run.started_at).toLocaleString(undefined, {
            timeZoneName: "short",
          })}
        </span>
      </div>

      {detail.length > 0 && (
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-xs">
          {detail.map(([k, v]) => (
            <span key={k} className="text-muted-foreground">
              {k}=<span className="text-foreground">{String(v)}</span>
            </span>
          ))}
        </div>
      )}

      {run.error && (
        <p className="text-destructive font-mono text-xs break-words">
          {run.error}
        </p>
      )}
    </li>
  )
}

export function JobHistoryDialog({
  jobKey,
  displayName,
  open,
  onOpenChange,
}: {
  jobKey: string
  displayName: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [page, setPage] = useState(0)
  const { runs, total, isLoading, isError } = useJobHistory(jobKey, {
    enabled: open,
    page,
  })
  const pages = Math.max(1, Math.ceil(total / HISTORY_PAGE_SIZE))
  const from = total === 0 ? 0 : page * HISTORY_PAGE_SIZE + 1
  const to = Math.min(total, (page + 1) * HISTORY_PAGE_SIZE)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[80vh] max-w-xl flex-col">
        <DialogHeader>
          <DialogTitle>{displayName} — run history</DialogTitle>
          <DialogDescription>
            Newest first. Runs that did no work are not recorded.
          </DialogDescription>
        </DialogHeader>

        {isError ? (
          <EmptyState
            kind="failed"
            title="Couldn’t load the history"
          />
        ) : isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-12 w-full rounded-md" />
            ))}
          </div>
        ) : runs.length === 0 ? (
          <EmptyState
            kind="empty"
            icon={History}
            title="No runs recorded yet"
          />
        ) : (
          <>
            <ul className="min-h-0 flex-1 space-y-1.5 overflow-y-auto">
              {runs.map((run) => (
                <RunRow key={run.id} run={run} />
              ))}
            </ul>
            <div className="flex items-center gap-2 pt-1">
              <span className="text-muted-foreground text-sm">
                {from}–{to} of {total}
              </span>
              <div className="ml-auto flex items-center gap-1.5">
                <Button
                  variant="outline"
                  size="icon"
                  aria-label="Previous page"
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >
                  <ChevronLeft aria-hidden className="size-[var(--icon-size)]" />
                </Button>
                <span className="text-muted-foreground text-sm tabular-nums">
                  {page + 1} / {pages}
                </span>
                <Button
                  variant="outline"
                  size="icon"
                  aria-label="Next page"
                  disabled={page + 1 >= pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  <ChevronRight aria-hidden className="size-[var(--icon-size)]" />
                </Button>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
