import { History, Play, Settings2 } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Card, CardContent } from "darkraise-ui/components/card"
import { Switch } from "darkraise-ui/components/switch"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import type { DemoJob } from "@/features/activity/types"

/** One outlined, icon-only action. The tooltip label is also the accessible
 *  name — an icon button has no text of its own to carry one. */
function CardAction({
  label,
  icon: Icon,
  onClick,
  disabled,
}: {
  label: string
  icon: typeof Play
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          aria-label={label}
          onClick={onClick}
          disabled={disabled}
        >
          <Icon aria-hidden className="size-[var(--icon-size)]" />
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  )
}

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
  return (
    <Card>
      <CardContent className="flex h-full flex-col gap-2.5 pt-4">
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            <p className="truncate font-medium">{job.name}</p>
            <p className="text-muted-foreground truncate font-mono text-[11px]">
              {job.key}
            </p>
          </div>
          <Switch
            checked={job.enabled}
            onCheckedChange={onToggleEnabled}
            aria-label={`${job.key} enabled`}
          />
        </div>

        <p className="text-muted-foreground line-clamp-2 text-sm">
          {job.description}
        </p>

        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant="outline" className="font-mono">
            {job.cron}
          </Badge>
          {job.running && <Badge>running</Badge>}
          {job.last_status && (
            <Badge
              variant={job.last_status === "ok" ? "outline" : "destructive"}
            >
              {job.last_status}
            </Badge>
          )}
          {/* null means never ran, which the list must not render as "ok". */}
          <span className="text-muted-foreground text-sm">
            {job.last_run_label ?? "never run"}
          </span>
        </div>

        <div className="mt-auto flex items-center gap-1.5 pt-1">
          <CardAction label="Trigger now" icon={Play} onClick={onTrigger} />
          <CardAction label="Configure" icon={Settings2} onClick={onConfigure} />
          <CardAction label="Run history" icon={History} onClick={onHistory} />
        </div>
      </CardContent>
    </Card>
  )
}
