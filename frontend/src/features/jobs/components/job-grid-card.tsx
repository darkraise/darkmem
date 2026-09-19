import { useState } from "react"
import { Card, CardContent } from "darkraise-ui/components/card"
import { Switch } from "darkraise-ui/components/switch"
import { cn } from "darkraise-ui/lib"
import type { DemoJob } from "@/features/activity/types"
import { JobActions } from "./job-actions"
import { JobLastRun, JobSchedule } from "./job-schedule-state"

export function JobGridCard({
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
  const [expanded, setExpanded] = useState(false)
  return (
    <Card>
      <CardContent className="flex h-full flex-col gap-2.5 pt-4">
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium">{job.name}</p>
            <p className="text-muted-foreground truncate font-mono text-xs">
              {job.key}
            </p>
          </div>
          <Switch
            checked={job.enabled}
            onCheckedChange={onToggleEnabled}
            aria-label={`${job.key} enabled`}
          />
        </div>

        <button
          type="button"
          aria-expanded={expanded}
          onClick={() => setExpanded((open) => !open)}
          className={cn(
            "text-muted-foreground text-left text-sm",
            !expanded && "line-clamp-2",
          )}
        >
          {job.description}
        </button>

        <div className="flex flex-col gap-1">
          <JobSchedule cron={job.cron} />
          <JobLastRun job={job} />
        </div>

        <div className="mt-auto pt-1">
          <JobActions
            job={job}
            onTrigger={onTrigger}
            onConfigure={onConfigure}
            onHistory={onHistory}
          />
        </div>
      </CardContent>
    </Card>
  )
}
