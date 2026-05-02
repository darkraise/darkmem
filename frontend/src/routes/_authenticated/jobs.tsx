import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import { Button } from "darkraise-ui/components/button"
import { Badge } from "darkraise-ui/components/badge"
import { Input } from "darkraise-ui/components/input"
import { Switch } from "darkraise-ui/components/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { PageHeader } from "darkraise-ui/layout"
import { toast } from "sonner"
import { Play, Save } from "lucide-react"
import { useJobs, useUpdateJob, useTriggerJob, type Job } from "@/hooks/api"

const CRON_PRESETS: { label: string; value: string }[] = [
  { label: "Every 10 seconds", value: "*/10 * * * * *" },
  { label: "Every 30 seconds", value: "*/30 * * * * *" },
  { label: "Every minute", value: "* * * * *" },
  { label: "Every 5 minutes", value: "*/5 * * * *" },
  { label: "Every 15 minutes", value: "*/15 * * * *" },
  { label: "Every 30 minutes", value: "*/30 * * * *" },
  { label: "Hourly", value: "0 * * * *" },
  { label: "Every 6 hours", value: "0 */6 * * *" },
  { label: "Daily at 03:00", value: "0 3 * * *" },
  { label: "Weekdays at 09:00", value: "0 9 * * 1-5" },
]

export const Route = createFileRoute("/_authenticated/jobs")({
  component: JobsPage,
})

function relativeTime(iso: string | null): string {
  if (!iso) return "never"
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function JobRow({ job }: { job: Job }) {
  const updateJob = useUpdateJob()
  const triggerJob = useTriggerJob()
  const [cron, setCron] = useState<string>(job.cron)
  const dirty = cron.trim() !== job.cron

  const handleToggle = (enabled: boolean) => {
    updateJob.mutate(
      { key: job.key, data: { enabled } },
      {
        onSuccess: () =>
          toast.success(`${job.display_name} ${enabled ? "enabled" : "disabled"}`),
        onError: (err) => toast.error(`Failed: ${err.message}`),
      },
    )
  }

  const handleSave = () => {
    if (!dirty) return
    updateJob.mutate(
      { key: job.key, data: { cron: cron.trim() } },
      {
        onSuccess: () => toast.success(`${job.display_name} schedule saved`),
        onError: (err) => toast.error(`Save failed: ${err.message}`),
      },
    )
  }

  const handleTrigger = () => {
    triggerJob.mutate(job.key, {
      onSuccess: (res) => {
        if (res.last_status === "error") {
          toast.error(`${job.display_name} failed: ${res.last_error}`)
        } else {
          toast.success(`${job.display_name} ran`)
        }
      },
      onError: (err) => toast.error(`Trigger failed: ${err.message}`),
    })
  }

  return (
    <div className="px-4 py-3 space-y-2">
      <div className="flex items-center gap-3">
        <span
          className={`w-2 h-2 rounded-full shrink-0 ${
            !job.enabled
              ? "bg-muted-foreground"
              : job.last_status === "error"
                ? "bg-red-500"
                : job.running
                  ? "bg-green-500"
                  : "bg-yellow-500"
          }`}
          title={
            !job.enabled
              ? "disabled"
              : job.last_status === "error"
                ? `last error: ${job.last_error}`
                : job.running
                  ? "loop running"
                  : "loop not running"
          }
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold">{job.display_name}</span>
            <Badge variant="outline" className="text-[10px] px-1.5 py-0 font-mono">
              {job.key}
            </Badge>
            {job.last_status === "error" && (
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0 text-destructive border-destructive"
                title={job.last_error ?? ""}
              >
                last run errored
              </Badge>
            )}
            {!job.enabled && (
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                disabled
              </Badge>
            )}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">{job.description}</div>
          <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
            <span>last run: {relativeTime(job.last_run_at)}</span>
            <span>·</span>
            <span>min interval: {job.min_interval_seconds}s</span>
            <span>·</span>
            <span className="font-mono">default: {job.default_cron}</span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Switch
            checked={job.enabled}
            onCheckedChange={handleToggle}
            disabled={updateJob.isPending}
            aria-label={`Toggle ${job.display_name}`}
          />
          <div className="flex items-center gap-1">
            <Select value="" onValueChange={(v) => v && setCron(v)}>
              <SelectTrigger className="h-8 w-32 text-xs">
                <SelectValue placeholder="Preset…" />
              </SelectTrigger>
              <SelectContent>
                {CRON_PRESETS.map((p) => (
                  <SelectItem key={p.value} value={p.value} className="text-xs">
                    {p.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Input
              type="text"
              className="h-8 w-44 text-xs font-mono"
              value={cron}
              onChange={(e) => setCron(e.target.value)}
              placeholder="*/5 * * * *"
              aria-label={`Cron expression for ${job.display_name}`}
            />
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={handleSave}
              disabled={!dirty || updateJob.isPending}
            >
              <Save className="w-3.5 h-3.5 mr-1" />
              Save
            </Button>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={handleTrigger}
            disabled={triggerJob.isPending}
          >
            <Play className="w-3.5 h-3.5 mr-1" />
            {triggerJob.isPending ? "Running..." : "Trigger"}
          </Button>
        </div>
      </div>
      {job.last_status === "error" && job.last_error && (
        <div className="ml-5 text-xs text-destructive bg-destructive/10 rounded px-2 py-1 font-mono">
          {job.last_error}
        </div>
      )}
    </div>
  )
}

function JobsPage() {
  const { data, isLoading, error } = useJobs()

  return (
    <div className="p-6 space-y-4">
      <PageHeader title="Jobs" />
      {isLoading && <p className="text-muted-foreground">Loading...</p>}
      {error && (
        <p className="text-destructive">Failed to load jobs: {(error as Error).message}</p>
      )}
      {data && data.jobs.length === 0 && (
        <p className="text-muted-foreground">No jobs registered.</p>
      )}
      {data && data.jobs.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
              Background Jobs
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {data.jobs.map((job) => (
                <JobRow key={job.key} job={job} />
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
