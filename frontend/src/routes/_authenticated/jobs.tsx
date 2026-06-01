import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { DataTable, DataTableSkeleton } from "darkraise-ui/data-table"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
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
import { toast } from "darkraise-ui/components/sonner"
import { Play, Save } from "lucide-react"
import { useJobs, useUpdateJob, useTriggerJob, type Job } from "@/hooks/api"
import { relativeTime as _relativeTime } from "@/lib/format"

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
  return _relativeTime(iso)
}

// Inline cron editor lives in the cell renderer to keep per-row draft state.
function CronCell({ job }: { job: Job }) {
  const updateJob = useUpdateJob()
  const [cron, setCron] = useState<string>(job.cron)
  const dirty = cron.trim() !== job.cron

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

  return (
    <div className="flex items-center gap-1">
      <Select value="" onValueChange={(v) => v && setCron(v)}>
        <SelectTrigger className="h-7 w-28 text-base">
          <SelectValue placeholder="Preset…" />
        </SelectTrigger>
        <SelectContent>
          {CRON_PRESETS.map((p) => (
            <SelectItem key={p.value} value={p.value} className="text-base">
              {p.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Input
        type="text"
        className="h-7 w-36 font-mono text-base"
        value={cron}
        onChange={(e) => setCron(e.target.value)}
        placeholder="*/5 * * * *"
        aria-label={`Cron expression for ${job.display_name}`}
      />
      <Button
        variant="ghost"
        size="sm"
        className="h-7 px-2 text-base"
        onClick={handleSave}
        disabled={!dirty || updateJob.isPending}
      >
        <Save className="h-3.5 w-3.5" />
      </Button>
    </div>
  )
}

function EnabledCell({ job }: { job: Job }) {
  const updateJob = useUpdateJob()

  const handleToggle = (enabled: boolean) => {
    updateJob.mutate(
      { key: job.key, data: { enabled } },
      {
        onSuccess: () =>
          toast.success(
            `${job.display_name} ${enabled ? "enabled" : "disabled"}`,
          ),
        onError: (err) => toast.error(`Failed: ${err.message}`),
      },
    )
  }

  return (
    <Switch
      checked={job.enabled}
      onCheckedChange={handleToggle}
      disabled={updateJob.isPending}
      aria-label={`Toggle ${job.display_name}`}
    />
  )
}

function TriggerCell({ job }: { job: Job }) {
  const triggerJob = useTriggerJob()

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
    <Button
      variant="outline"
      size="sm"
      className="h-7 px-2 text-base"
      onClick={handleTrigger}
      disabled={triggerJob.isPending}
    >
      <Play className="mr-1 h-3.5 w-3.5" />
      {triggerJob.isPending ? "Running..." : "Trigger"}
    </Button>
  )
}

const columns: ColumnDef<Job>[] = [
  {
    accessorKey: "display_name",
    header: "Job",
    size: 200,
    cell: ({ row }) => (
      <div>
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 shrink-0 rounded-full ${
              !row.original.enabled
                ? "bg-muted-foreground"
                : row.original.last_status === "error"
                  ? "bg-red-500"
                  : row.original.running
                    ? "bg-green-500"
                    : "bg-yellow-500"
            }`}
            title={
              !row.original.enabled
                ? "disabled"
                : row.original.last_status === "error"
                  ? `last error: ${row.original.last_error}`
                  : row.original.running
                    ? "loop running"
                    : "loop not running"
            }
          />
          <span className="text-base font-medium">
            {row.original.display_name}
          </span>
        </div>
        <div className="text-muted-foreground mt-0.5 text-base">
          {row.original.description}
        </div>
        {row.original.last_status === "error" && row.original.last_error && (
          <div className="text-destructive bg-destructive/10 mt-1 rounded px-2 py-1 font-mono text-base">
            {row.original.last_error}
          </div>
        )}
      </div>
    ),
  },
  {
    accessorKey: "key",
    header: "Key",
    size: 160,
    cell: ({ getValue }) => (
      <Badge variant="outline" className="px-1.5 py-0 font-mono text-sm">
        {String(getValue())}
      </Badge>
    ),
  },
  {
    id: "enabled",
    header: "Enabled",
    size: 80,
    cell: ({ row }) => <EnabledCell job={row.original} />,
  },
  {
    id: "cron",
    header: "Schedule",
    cell: ({ row }) => <CronCell job={row.original} />,
  },
  {
    accessorKey: "last_run_at",
    header: "Last run",
    size: 130,
    cell: ({ getValue }) => relativeTime(getValue() as string | null),
  },
  {
    accessorKey: "last_status",
    header: "Status",
    size: 90,
    cell: ({ getValue }) => {
      const v = getValue() as string | null
      if (!v) return <span className="text-muted-foreground text-base">—</span>
      return (
        <Badge
          variant={v === "error" ? "destructive" : "secondary"}
          className="px-1.5 py-0 text-sm"
        >
          {v}
        </Badge>
      )
    },
  },
  {
    accessorKey: "min_interval_seconds",
    header: "Min interval",
    size: 110,
    cell: ({ getValue }) => (
      <span className="text-muted-foreground text-base">
        {getValue() as number}s
      </span>
    ),
  },
  {
    id: "actions",
    header: "",
    size: 110,
    cell: ({ row }) => <TriggerCell job={row.original} />,
  },
]

function JobsPage() {
  const { data, isLoading, error } = useJobs()

  return (
    <div className="space-y-4 p-6">
      <PageHeader title="Jobs" />
      {error && (
        <p className="text-destructive">
          Failed to load jobs: {(error as Error).message}
        </p>
      )}
      {isLoading ? (
        <DataTableSkeleton columnCount={8} />
      ) : data && data.jobs.length === 0 ? (
        <p className="text-muted-foreground">No jobs registered.</p>
      ) : (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-muted-foreground text-base font-medium tracking-wider uppercase">
              Background Jobs
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <DataTable columns={columns} data={data?.jobs ?? []} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
