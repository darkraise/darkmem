import { CircleAlert, CircleCheck, CircleDashed, Clock } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import type { DemoJob } from "@/features/activity/types"
import { describeCron } from "../cron-describe"

/**
 * Schedule and last-run state, drawn rather than spelled out.
 *
 * The cron leads with its plain reading ("At 5:00 AM every day") and keeps
 * the expression in the tooltip, because the expression is what actually
 * governs the job and must stay reachable. When `describeCron` cannot read an
 * expression confidently it returns null and the expression itself is shown —
 * a wrong sentence beside a cron the reader can see is worse than no sentence.
 */
export function JobSchedule({ cron }: { cron: string }) {
  const plain = describeCron(cron)
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="text-muted-foreground inline-flex w-fit min-w-0 items-center gap-1.5 text-sm">
          <Clock aria-hidden className="size-[var(--icon-size-sm)] shrink-0" />
          <span className="truncate">{plain ?? cron}</span>
        </span>
      </TooltipTrigger>
      <TooltipContent>
        <span className="font-mono">{cron}</span>
      </TooltipContent>
    </Tooltip>
  )
}

/**
 * Last run as a status dot plus its time. `null` status is "never ran", which
 * must not borrow the healthy green — it gets its own neutral mark, because a
 * job that has never run and a job that ran fine are different facts.
 */
export function JobLastRun({ job }: { job: DemoJob }) {
  if (job.running) {
    return (
      <Badge className="w-fit gap-1.5">
        <CircleDashed aria-hidden className="size-[var(--icon-size-sm)] animate-spin" />
        running
      </Badge>
    )
  }

  const when = job.last_run_label
  if (!job.last_status) {
    return (
      <span className="text-muted-foreground inline-flex w-fit items-center gap-1.5 text-sm">
        <CircleDashed aria-hidden className="size-[var(--icon-size-sm)]" />
        never run
      </span>
    )
  }

  const ok = job.last_status === "ok"
  const Icon = ok ? CircleCheck : CircleAlert
  return (
    <span
      className={`inline-flex w-fit items-center gap-1.5 text-sm ${
        ok ? "text-success-text" : "text-destructive"
      }`}
    >
      <Icon aria-hidden className="size-[var(--icon-size-sm)] shrink-0" />
      {!ok && <span className="font-medium">failed</span>}
      <span className="text-muted-foreground truncate">{when ?? job.last_status}</span>
    </span>
  )
}
