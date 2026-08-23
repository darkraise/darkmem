import { useState } from "react"
import {
  Lock,
  RefreshCw,
  Settings2,
  TriangleAlert,
  X,
  Zap,
  type LucideIcon,
} from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { EmptyState } from "@/components/darkmem"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { toast } from "darkraise-ui/components/sonner"
import { cn } from "darkraise-ui/lib"
import { NumberField } from "@/components/darkmem"
import { validateJobConfig } from "@/demo/activity"
import type { DemoJob } from "@/features/activity/types"
import { useUsageByJob, type JobUsageRow } from "@/hooks/api"
import { UsageChip } from "@/features/usage/components/usage-chip"
import { useJobBoard } from "../use-job-board"
import { ModuleSurface } from "./module-surface"

type JobRowStatus = "idle" | "running" | "last-run-failed"

function jobStatus(job: DemoJob): JobRowStatus {
  if (job.running) return "running"
  if (job.last_status === "error") return "last-run-failed"
  return "idle"
}

const STATUS_STYLES: Record<
  JobRowStatus,
  { icon: LucideIcon | null; label: string; className: string }
> = {
  idle: {
    icon: null,
    label: "idle",
    className: "border-success/40 bg-success/10 text-success",
  },
  running: {
    icon: RefreshCw,
    label: "running",
    className: "border-info/50 bg-info/10 text-info",
  },
  "last-run-failed": {
    icon: TriangleAlert,
    label: "last run failed",
    className: "border-destructive/50 bg-destructive/10 text-destructive",
  },
}

interface BusyOutcome {
  key: string
  lock_held_since: string | null
}

function ReadOnlyField({
  label,
  role,
  value,
  desc,
}: {
  label: string
  role: string
  value: string
  desc: string
}) {
  return (
    <div className="border-border flex flex-col gap-1.5 border-b border-dashed px-1 py-2.5 last:border-b-0">
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-sm font-semibold">{label}</span>
        <span className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
          {role}
        </span>
      </div>
      <Input value={value} readOnly className="w-fit min-w-40 font-mono" />
      <p className="text-muted-foreground max-w-prose text-sm">{desc}</p>
    </div>
  )
}

function JobConfigDialog({
  job,
  onClose,
  saveConfig,
}: {
  job: DemoJob
  onClose: () => void
  saveConfig: (key: string, config: Record<string, number>) => void
}) {
  const [values, setValues] = useState<Record<string, number>>(() =>
    Object.fromEntries(job.config_schema.map((f) => [f.key, f.value])),
  )
  const validation = validateJobConfig(job.config_schema, values)

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings2 aria-hidden className="text-muted-foreground h-4 w-4" />
            Configure — {job.key}
          </DialogTitle>
          <DialogDescription className="font-mono text-sm">
            config row: job:{job.key}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col">
          <ReadOnlyField
            label="cron"
            role="schedule · read-only here"
            value={job.cron}
            desc={`${job.cron_label}. Five-field expressions are minute-precision; six-field put the seconds field first, Quartz-style. Edited via PUT /api/v1/jobs/{key}, not this dialog's Save.`}
          />
          <ReadOnlyField
            label="min_interval_seconds"
            role="floor · read-only"
            value={String(job.min_interval_seconds)}
            desc="The loop will not fire more often than this floor, no matter how aggressive the cron computes. A registration-time constant — not editable via config."
          />
          {job.max_run_seconds !== null && (
            <ReadOnlyField
              label="max_run_seconds"
              role="ceiling · read-only"
              value={String(job.max_run_seconds)}
              desc="A run still executing past this ceiling is treated as overrun. Also a registration-time constant, not editable via config."
            />
          )}
          <p className="text-muted-foreground pt-2 font-mono text-[10px] tracking-wide uppercase">
            config_schema — job-specific, editable fields
          </p>
          {job.config_schema.length === 0 ? (
            <p className="text-muted-foreground py-2 text-sm italic">
              This job declares no config_schema — there is nothing this dialog
              can save.
            </p>
          ) : (
            job.config_schema.map((field) => {
              const error = validation.ok
                ? undefined
                : validation.errors[field.key]
              return (
                <div
                  key={field.key}
                  className="flex flex-col gap-1.5 px-1 py-2.5"
                >
                  <div className="flex items-baseline gap-2">
                    <Label
                      htmlFor={`job-config-${field.key}`}
                      className="font-mono text-sm font-semibold"
                    >
                      {field.label}
                    </Label>
                    <span className="text-muted-foreground font-mono text-[10px] uppercase">
                      {field.type}
                    </span>
                  </div>
                  <NumberField
                    value={values[field.key] ?? field.value}
                    min={field.min}
                    max={field.max}
                    aria-label={field.label}
                    onValueChange={(next) =>
                      setValues((v) => ({ ...v, [field.key]: next }))
                    }
                    className={cn(
                      "w-fit min-w-40",
                      error && "border-destructive",
                    )}
                  />
                  {field.help && (
                    <p className="text-muted-foreground text-sm">
                      {field.help}
                    </p>
                  )}
                  <p className="text-muted-foreground font-mono text-sm">
                    {field.min !== undefined && `min ${field.min}`}
                    {field.min !== undefined &&
                      field.max !== undefined &&
                      " · "}
                    {field.max !== undefined && `max ${field.max}`}
                  </p>
                  {error && <p className="text-destructive text-sm">{error}</p>}
                </div>
              )
            })
          )}
        </div>
        <DialogFooter className="items-center gap-2 sm:justify-between">
          <span className="text-muted-foreground text-sm">
            config_schema writes acquire the same lock the scheduled tick uses.
          </span>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button
              disabled={!validation.ok || job.config_schema.length === 0}
              onClick={() => {
                if (validation.ok) {
                  saveConfig(job.key, validation.config)
                  onClose()
                }
              }}
            >
              Save
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function JobRow({
  job,
  busy,
  onTrigger,
  onConfigure,
  onDismissBusy,
  usage,
  usagePending,
}: {
  job: DemoJob
  busy: BusyOutcome | null
  onTrigger: (key: string) => Promise<boolean>
  onConfigure: (key: string) => void
  onDismissBusy: () => void
  usage: JobUsageRow | undefined
  usagePending: boolean
}) {
  const status = jobStatus(job)
  const { icon: Icon, label, className } = STATUS_STYLES[status]
  const [triggered, setTriggered] = useState(false)

  return (
    <div
      className={cn(
        "border-border flex flex-col gap-2 rounded-md border p-3",
        job.running && "border-primary/45 bg-primary/3",
      )}
    >
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="font-mono text-sm font-semibold">{job.key}</span>
        <Badge
          variant="outline"
          size="sm"
          className={cn("gap-1 font-mono", className)}
        >
          {Icon && <Icon aria-hidden className="h-3 w-3" />}
          {label}
        </Badge>
        {/* Every run this job has made in the window, not the last one: a
            job's cost is a rate, and one run's number invites reading a cheap
            tick as a cheap job. The tooltip carries the run count. */}
        <UsageChip
          className="ml-auto"
          pending={usagePending}
          totals={usage}
        />
        <span className="text-muted-foreground font-mono text-sm whitespace-nowrap">
          {job.next_run_label}
        </span>
      </div>
      <p className="text-muted-foreground text-sm">
        cron <code className="text-foreground font-mono">{job.cron}</code> ·{" "}
        {job.cron_label}
      </p>
      {job.last_run_label === null ? (
        <p className="text-muted-foreground text-sm italic">
          last run: never — waiting on its first scheduled tick.
        </p>
      ) : (
        <p
          className={cn(
            "text-sm",
            job.last_status === "error"
              ? "text-destructive"
              : "text-muted-foreground",
          )}
        >
          last run <b className="font-semibold">{job.last_run_label}</b> —{" "}
          {job.last_summary}
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          aria-label={`Configure ${job.key}`}
          onClick={() => onConfigure(job.key)}
        >
          <Settings2 className="size-3.5" />
        </Button>
        <Button
          variant="outline"
          className={cn(
            job.last_status === "error" && "border-warning/60 text-warning",
          )}
          onClick={() => {
            // The success message only fires once the request actually
            // resolves as not-busy (ruling 4) — never optimistically, since
            // a real trigger is async and could come back 409.
            void onTrigger(job.key).then((ok) => {
              if (ok) {
                setTriggered(true)
                window.setTimeout(() => setTriggered(false), 2500)
              }
            })
          }}
        >
          <Zap className="mr-1.5 size-3.5" />
          {job.last_status === "error" && !job.running
            ? "Trigger now (retry)"
            : "Trigger now"}
        </Button>
        {triggered && (
          <span className="text-success font-mono text-sm">
            triggered — ran to completion
          </span>
        )}
      </div>
      {busy?.key === job.key && (
        <div className="border-warning/55 bg-warning/10 flex gap-2.5 rounded-md border p-3">
          <Lock aria-hidden className="text-warning h-4 w-4 shrink-0" />
          <div className="flex min-w-0 flex-1 flex-col gap-1">
            <span className="text-sm font-semibold">
              busy — {job.key} is already running
            </span>
            <span className="text-muted-foreground text-sm">
              {busy.lock_held_since
                ? `The lock acquired at ${busy.lock_held_since} is still held. `
                : "The job's lock is still held by an earlier run. "}
              This trigger request was not queued; try again once the current
              run finishes.
            </span>
            <span className="text-warning font-mono text-sm">
              HTTP 409 · POST /api/v1/jobs/{job.key}/trigger
            </span>
          </div>
          <Button
            variant="ghost"
            aria-label="Dismiss busy notice"
            onClick={onDismissBusy}
          >
            <X className="size-3.5" />
          </Button>
        </div>
      )}
    </div>
  )
}

export function JobsTab() {
  const { jobs, isLoading, isError, trigger, saveConfig } = useJobBoard()
  const [busy, setBusy] = useState<BusyOutcome | null>(null)
  const [configKey, setConfigKey] = useState<string | null>(null)
  const configJob = jobs.find((j) => j.key === configKey)
  const jobUsage = useUsageByJob("30d")
  const usageByJob = new Map(
    (jobUsage.data?.jobs ?? []).map((j) => [j.job_key, j]),
  )

  const running = jobs.filter((j) => j.running).length
  const failed = jobs.filter(
    (j) => !j.running && j.last_status === "error",
  ).length

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-4xl text-sm">
        The registered JobRegistry jobs with their cron schedule, last run, and
        the per-job floor/ceiling. A manual trigger acquires the same per-job
        lock the scheduled loop uses — a trigger that lands while the lock is
        held returns busy (HTTP 409) immediately, discarded and never queued
        behind the in-flight run.
      </p>
      <ModuleSurface
        title="Jobs"
        state={isLoading ? "empty" : jobs.length > 0 ? "populated" : "empty"}
        meta={`${jobs.length} registered · ${running} running · ${failed} last-run failed`}
      >
        {isError ? (
          <EmptyState
            kind="failed"
            title="Couldn't load the job board"
            description="The /jobs request failed — this is an error state, not an empty registry."
          />
        ) : (
          jobs.map((job) => (
            <JobRow
              key={job.key}
              job={job}
              busy={busy}
              usage={usageByJob.get(job.key)}
              usagePending={jobUsage.isLoading}
              onTrigger={async (key) => {
                let result: Awaited<ReturnType<typeof trigger>>
                try {
                  result = await trigger(key)
                } catch (err) {
                  toast.error(`Trigger failed for ${key}`, {
                    description: err instanceof Error ? err.message : undefined,
                  })
                  return false
                }
                if (result.ok) {
                  setBusy(null)
                  return true
                }
                setBusy({ key, lock_held_since: result.lock_held_since })
                return false
              }}
              onConfigure={setConfigKey}
              onDismissBusy={() => setBusy(null)}
            />
          ))
        )}
      </ModuleSurface>
      {configJob && (
        <JobConfigDialog
          job={configJob}
          onClose={() => setConfigKey(null)}
          saveConfig={saveConfig}
        />
      )}
    </div>
  )
}
