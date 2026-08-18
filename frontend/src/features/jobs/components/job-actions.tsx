import { History, Play, Settings2, type LucideIcon } from "lucide-react"
import { Button, type ButtonVariant } from "darkraise-ui/components/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import type { DemoJob } from "@/features/activity/types"

/**
 * The per-job actions, shared by both layouts so a card and a row can never
 * offer different verbs for the same job.
 *
 * Variant grades weight rather than decorating:
 *
 * - `default` (filled) for **Trigger now** — the only one that acts on the
 *   system the moment it is pressed, and the reason most people open this
 *   page. It is disabled while a run holds the lock.
 * - `outline` for **Configure** — changes what the job will do, but through a
 *   dialog with its own save, so pressing it commits nothing.
 * - `ghost` for **Run history** — read-only. Nothing it opens can change a
 *   thing, so it should not compete with the two that can.
 *
 * Icon-only throughout, which is why every one carries the tooltip label as
 * its accessible name: an icon button has no text of its own to be named by.
 */
function Action({
  label,
  icon: Icon,
  variant,
  onClick,
  disabled,
}: {
  label: string
  icon: LucideIcon
  variant: ButtonVariant
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex">
          <Button
            variant={variant}
            size="icon"
            aria-label={label}
            onClick={onClick}
            disabled={disabled}
          >
            <Icon aria-hidden className="size-[var(--icon-size)]" />
          </Button>
        </span>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  )
}

export function JobActions({
  job,
  onTrigger,
  onConfigure,
  onHistory,
}: {
  job: DemoJob
  onTrigger: () => void
  onConfigure: () => void
  onHistory: () => void
}) {
  return (
    <div className="flex items-center gap-1.5">
      <Action
        label={job.running ? "Running — trigger unavailable" : "Trigger now"}
        icon={Play}
        variant="default"
        onClick={onTrigger}
        // A trigger landing on a held lock returns busy and is discarded, not
        // queued; disabling says so before the click rather than after.
        disabled={job.running}
      />
      <Action
        label="Configure"
        icon={Settings2}
        variant="outline"
        onClick={onConfigure}
      />
      <Action
        label="Run history"
        icon={History}
        variant="ghost"
        onClick={onHistory}
      />
    </div>
  )
}
