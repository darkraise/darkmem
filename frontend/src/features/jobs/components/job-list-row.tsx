import { Badge } from "darkraise-ui/components/badge"
import { Switch } from "darkraise-ui/components/switch"
import type { DemoJob } from "@/features/activity/types"
import { JobActions } from "./job-actions"

/**
 * One job as a row. Same data and same verbs as the card, laid out for
 * scanning a long registry rather than reading one job: identity and schedule
 * on the left, state in the middle, actions pinned right so they form a
 * column the eye can run down.
 */
export function JobListRow({
  job,
  onTrigger,
  onConfigure,
  onHistory,
  onToggleEnabled,
}: {
  job: DemoJob
  onTrigger: () => void
  onConfigure: () => void
  onHistory: () => void
  onToggleEnabled: (enabled: boolean) => void
}) {
  return (
    <div className="border-border bg-card flex flex-wrap items-center gap-x-4 gap-y-2 rounded-md border px-3 py-2.5">
      <Switch
        checked={job.enabled}
        onCheckedChange={onToggleEnabled}
        aria-label={`${job.key} enabled`}
      />

      <div className="min-w-0 flex-1 basis-56">
        <p className="truncate font-medium">{job.name}</p>
        <p className="text-muted-foreground truncate font-mono text-[11px]">
          {job.key}
        </p>
      </div>

      <Badge variant="outline" className="font-mono">
        {job.cron}
      </Badge>

      <div className="flex min-w-0 basis-44 items-center gap-1.5">
        {job.running && <Badge>running</Badge>}
        {job.last_status && (
          <Badge variant={job.last_status === "ok" ? "outline" : "destructive"}>
            {job.last_status}
          </Badge>
        )}
        {/* null is "never ran", which must not read as a healthy last run. */}
        <span className="text-muted-foreground truncate text-sm">
          {job.last_run_label ?? "never run"}
        </span>
      </div>

      <JobActions
        job={job}
        onTrigger={onTrigger}
        onConfigure={onConfigure}
        onHistory={onHistory}
      />
    </div>
  )
}
