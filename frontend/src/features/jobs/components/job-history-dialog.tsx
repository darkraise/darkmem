import { History } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { EmptyState } from "@/components/darkmem"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { Badge } from "darkraise-ui/components/badge"
import { relativeTime } from "@/lib/format"
import { useJobHistory } from "../use-job-history"

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
  const { runs, journals, isLoading, isError } = useJobHistory(jobKey, {
    enabled: open,
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[80vh] max-w-lg flex-col">
        <DialogHeader>
          <DialogTitle>{displayName} — run history</DialogTitle>
          <DialogDescription>
            Read from the `maintenance_run` journal, newest first.
          </DialogDescription>
        </DialogHeader>

        {!journals ? (
          <EmptyState
            kind="empty"
          icon={History}
            title="This job does not journal its runs"
            description="Only the three cleanup runners write a maintenance_run row. This is an absent history, not an empty one — the job may well have run many times."
          />
        ) : isError ? (
          <EmptyState
            kind="failed"
            title="Couldn't load the history"
            description="The /events request failed. This is an error, not an empty history."
          />
        ) : isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-10 w-full rounded-md" />
            ))}
          </div>
        ) : runs.length === 0 ? (
          <EmptyState
            kind="empty"
          icon={History}
            title="No runs in the journal window"
            description="This job journals its runs, but none appear in the most recent maintenance_run page — it may not have run yet, or busier jobs may have pushed it out of the window."
          />
        ) : (
          <div className="min-h-0 flex-1 overflow-y-auto">
            <ul className="space-y-1.5">
              {runs.map((run) => (
                <li
                  key={run.id}
                  className="border-border flex items-center gap-2.5 rounded-md border px-2.5 py-2 text-sm"
                >
                  <Badge
                    variant={run.outcome === "ok" ? "outline" : "destructive"}
                  >
                    {run.outcome}
                  </Badge>
                  <span className="text-muted-foreground">
                    {relativeTime(run.at)}
                  </span>
                  {Object.keys(run.detail).length > 0 && (
                    <span className="text-muted-foreground ml-auto truncate font-mono text-[11px]">
                      {JSON.stringify(run.detail)}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
