import type { ReactNode } from "react"
import { Switch } from "darkraise-ui/components/switch"
import { cn } from "darkraise-ui/lib"
import type { DemoJob } from "@/features/activity/types"
import { JobActions } from "./job-actions"
import { JobDisabledBadge, JobLastRun, JobSchedule } from "./job-schedule-state"
import { listItemClass } from "@/components/darkmem"

/**
 * One job as a row. Same data and same verbs as the card, laid out for
 * scanning a long registry rather than reading one job: identity and schedule
 * on the left, state in the middle, actions pinned right so they form a
 * column the eye can run down.
 *
 * `aside` is a slot before the actions for a per-job figure (the jobs page
 * puts its 30-day usage chip there).
 */
export function JobListRow({
  job,
  onTrigger,
  onConfigure,
  onHistory,
  onToggleEnabled,
  aside,
}: {
  job: DemoJob
  onTrigger: () => void
  onConfigure: () => void
  onHistory: () => void
  onToggleEnabled: (enabled: boolean) => void
  aside?: ReactNode
}) {
  // A disabled job will not run: its identity and schedule dim, and it says
  // so in words, so a scan of the list does not depend on every switch.
  const dim = !job.enabled && "opacity-60"
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

      <div className={cn("min-w-0 flex-1 basis-56", dim)}>
        <p className="truncate font-medium">{job.name}</p>
        <p className="text-muted-foreground truncate font-mono text-xs">
          {job.key}
        </p>
      </div>

      <div className={cn("flex min-w-0 basis-56 items-center gap-2", dim)}>
        <JobSchedule cron={job.cron} />
        {!job.enabled && <JobDisabledBadge />}
      </div>

      <div className="min-w-0 basis-40">
        <JobLastRun job={job} />
      </div>

      {aside}

      <JobActions
        job={job}
        onTrigger={onTrigger}
        onConfigure={onConfigure}
        onHistory={onHistory}
      />
    </div>
  )
}
