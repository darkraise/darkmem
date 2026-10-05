import { useLayoutEffect, useRef, useState, type ReactNode } from "react"
import { ChevronDown } from "lucide-react"
import { Card, CardContent } from "darkraise-ui/components/card"
import { Switch } from "darkraise-ui/components/switch"
import { cn } from "darkraise-ui/lib"
import type { DemoJob } from "@/features/activity/types"
import { JobActions } from "./job-actions"
import { JobDisabledBadge, JobLastRun, JobSchedule } from "./job-schedule-state"

export function JobGridCard({
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
  /** A per-job figure beside the actions (the jobs page's usage chip). */
  aside?: ReactNode
}) {
  const [expanded, setExpanded] = useState(false)
  const [clamped, setClamped] = useState(false)
  const descRef = useRef<HTMLSpanElement>(null)

  // Only a description the clamp actually cuts gets the more/less control;
  // a short one is plain text, not a button that does nothing visible.
  useLayoutEffect(() => {
    const el = descRef.current
    if (!el || expanded) return
    setClamped(el.scrollHeight > el.clientHeight + 1)
  }, [job.description, expanded])

  return (
    <Card>
      <CardContent className="flex h-full flex-col gap-2.5 pt-4">
        <div className="flex items-start gap-2">
          {/* A disabled job will not run; dimming its identity and schedule
              lets a scan of the grid say which, not only the switch. */}
          <div className={cn("min-w-0 flex-1", !job.enabled && "opacity-60")}>
            <p className="truncate font-medium">{job.name}</p>
            <p className="text-muted-foreground truncate font-mono text-xs">
              {job.key}
            </p>
          </div>
          {!job.enabled && <JobDisabledBadge />}
          <Switch
            checked={job.enabled}
            onCheckedChange={onToggleEnabled}
            aria-label={`${job.key} enabled`}
          />
        </div>

        {clamped || expanded ? (
          <button
            type="button"
            aria-expanded={expanded}
            onClick={() => setExpanded((open) => !open)}
            className="group text-muted-foreground hover:text-foreground flex cursor-pointer flex-col items-start gap-0.5 text-left text-sm"
          >
            <span ref={descRef} className={cn(!expanded && "line-clamp-2")}>
              {job.description}
            </span>
            <span className="text-primary-text inline-flex items-center gap-0.5 text-xs font-medium">
              {expanded ? "less" : "more"}
              <ChevronDown
                aria-hidden
                className={cn(
                  "size-3 transition-transform",
                  expanded && "rotate-180",
                )}
              />
            </span>
          </button>
        ) : (
          <p className="text-muted-foreground text-sm">
            <span ref={descRef} className="line-clamp-2">
              {job.description}
            </span>
          </p>
        )}

        <div
          className={cn("flex flex-col gap-1", !job.enabled && "opacity-60")}
        >
          <JobSchedule cron={job.cron} />
          <JobLastRun job={job} />
        </div>

        <div className="mt-auto flex items-center justify-between gap-2 pt-1">
          <JobActions
            job={job}
            onTrigger={onTrigger}
            onConfigure={onConfigure}
            onHistory={onHistory}
          />
          {aside}
        </div>
      </CardContent>
    </Card>
  )
}
