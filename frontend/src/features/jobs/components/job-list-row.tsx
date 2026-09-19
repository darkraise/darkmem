import { Switch } from "darkraise-ui/components/switch"
import type { DemoJob } from "@/features/activity/types"
import { JobActions } from "./job-actions"
import { JobLastRun, JobSchedule } from "./job-schedule-state"
import { listItemClass } from "@/components/darkmem"

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
    <div
      className={listItemClass({
        className:
          "bg-card flex flex-wrap items-center gap-x-4 gap-y-2 px-3 py-2.5",
      })}
    >
      <Switch
        checked={job.enabled}
        onCheckedChange={onToggleEnabled}
        aria-label={`${job.key} enabled`}
      />

      <div className="min-w-0 flex-1 basis-56">
        <p className="truncate font-medium">{job.name}</p>
        <p className="text-muted-foreground truncate font-mono text-xs">
          {job.key}
        </p>
      </div>

      <div className="min-w-0 basis-56">
        <JobSchedule cron={job.cron} />
      </div>

      <div className="min-w-0 basis-40">
        <JobLastRun job={job} />
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
