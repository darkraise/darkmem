import { useState } from "react"
import { CalendarClock, CircleAlert, Lock, X, Zap } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { Input } from "darkraise-ui/components/input"
import { toast } from "darkraise-ui/components/sonner"
import { Switch } from "darkraise-ui/components/switch"
import { cn } from "darkraise-ui/lib"
import { HelpTip } from "@/components/darkmem"
import { ModuleSurface } from "@/features/activity/components/module-surface"
import { validateJobConfig } from "@/demo/activity"
import { cronInfo } from "@/demo/settings"
import type { DemoJob } from "@/features/activity/types"
import {
  useJobsSettingsBinding,
  type JobsSettingsBinding,
} from "../use-jobs-tab-binding"

function SectionHead({
  label,
  role,
  help,
}: {
  label: string
  role: string
  help?: string
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="font-mono text-[10px] font-semibold tracking-wide uppercase">
        {label}
      </span>
      <span className="text-muted-foreground font-mono text-[10px]">
        {role}
      </span>
      {help && <HelpTip label={`About ${label}`}>{help}</HelpTip>}
    </div>
  )
}

function ScheduleSection({
  job,
  saveCron,
}: {
  job: DemoJob
  saveCron: (key: string, cron: string) => void
}) {
  const [draft, setDraft] = useState(job.cron)
  const [saved, setSaved] = useState(false)
  const info = cronInfo(draft)

  return (
    <div className="border-border bg-muted/8 flex flex-col gap-2 rounded-md border border-dashed px-3 py-2.5">
      <SectionHead
        label="schedule"
        role={`editable · PUT /api/v1/jobs/${job.key}`}
      />
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex min-w-52 flex-col gap-1">
          <span className="font-mono text-sm font-semibold">cron</span>
          <Input
            value={draft}
            aria-label={`${job.key} cron`}
            onChange={(e) => {
              setDraft(e.target.value)
              setSaved(false)
            }}
            className={cn("w-60 font-mono", !info.ok && "border-destructive")}
          />
          {info.ok ? (
            <span className="text-muted-foreground text-sm">{info.hint}</span>
          ) : (
            <span className="text-destructive text-sm">{info.error}</span>
          )}
        </div>
        <Button
          size="sm"
          variant="outline"
          className="border-primary/60 text-primary"
          disabled={!info.ok || draft === job.cron}
          onClick={() => {
            saveCron(job.key, draft)
            setSaved(true)
          }}
        >
          Save schedule
        </Button>
        {saved && (
          <span className="text-success font-mono text-sm">
            saved — takes effect on the next scheduled tick
          </span>
        )}
      </div>
    </div>
  )
}

function ConstantsSection({ job }: { job: DemoJob }) {
  return (
    <div className="border-border flex flex-col gap-2 rounded-md border border-dashed px-3 py-2.5">
      <SectionHead
        label="registration constants"
        role="read-only"
        help="Fixed Job-dataclass attributes set once at registration in app/main.py — no write path for either. The loop never fires more often than the floor, no matter how aggressive the cron computes."
      />
      <div className="flex flex-wrap gap-6">
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground font-mono text-[10px]">
            min_interval_seconds (floor)
          </span>
          <span className="font-mono text-sm font-semibold">
            {job.min_interval_seconds}
          </span>
        </div>
        {/* JobItem carries no max_run_seconds over the wire (T1.45's
            precedent) — skipped entirely rather than printing a
            fabricated or explicitly-null value. */}
        {job.max_run_seconds !== null && (
          <div className="flex flex-col gap-0.5">
            <span className="text-muted-foreground font-mono text-[10px]">
              max_run_seconds (ceiling)
            </span>
            <span className="font-mono text-sm font-semibold">
              {job.max_run_seconds}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

function ConfigSchemaSection({
  job,
  saveConfig,
}: {
  job: DemoJob
  saveConfig: (key: string, config: Record<string, number>) => void
}) {
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(job.config_schema.map((f) => [f.key, String(f.value)])),
  )
  const [saved, setSaved] = useState(false)

  if (job.config_schema.length === 0) {
    return (
      <div className="border-border bg-muted/8 flex flex-col gap-1.5 rounded-md border border-dashed px-3 py-2.5">
        <SectionHead label="config_schema" role="no fields declared for this job" />
        <p className="text-muted-foreground text-sm italic">
          {job.key} declares no config_schema — nothing beyond schedule to
          configure.
        </p>
      </div>
    )
  }

  const validation = validateJobConfig(job.config_schema, values)
  return (
    <div className="border-border bg-muted/8 flex flex-col gap-2 rounded-md border border-dashed px-3 py-2.5">
      <SectionHead
        label="config_schema"
        role={`editable · PUT /api/v1/jobs/${job.key}/config`}
      />
      <div className="flex flex-wrap items-end gap-3">
        {job.config_schema.map((field) => {
          const error = validation.ok ? undefined : validation.errors[field.key]
          return (
            <div key={field.key} className="flex min-w-52 flex-col gap-1">
              <span className="flex items-center gap-1.5 font-mono text-sm font-semibold">
                {field.key}{" "}
                <span className="text-muted-foreground font-normal lowercase">
                  {field.type}
                </span>
                {field.help && (
                  <HelpTip label={`About ${field.key}`}>{field.help}</HelpTip>
                )}
              </span>
              <Input
                type="number"
                value={values[field.key] ?? ""}
                aria-label={`${job.key} ${field.key}`}
                onChange={(e) => {
                  setValues((v) => ({ ...v, [field.key]: e.target.value }))
                  setSaved(false)
                }}
                className={cn("w-28 font-mono", error && "border-destructive")}
              />
              {(field.min !== undefined || field.max !== undefined) && (
                <span className="text-muted-foreground font-mono text-[10px]">
                  {field.min !== undefined && `min ${field.min}`}
                  {field.min !== undefined && field.max !== undefined && " · "}
                  {field.max !== undefined && `max ${field.max}`}
                </span>
              )}
              {error && <span className="text-destructive text-sm">{error}</span>}
            </div>
          )
        })}
        <Button
          size="sm"
          variant="outline"
          className="border-primary/60 text-primary"
          disabled={!validation.ok}
          onClick={() => {
            if (validation.ok) {
              saveConfig(job.key, validation.config)
              setSaved(true)
            }
          }}
        >
          Save config
        </Button>
        {saved && (
          <span className="text-success font-mono text-sm">saved</span>
        )}
      </div>
    </div>
  )
}

interface BusyOutcome {
  key: string
  lock_held_since: string | null
}

function TriggerSection({
  job,
  busy,
  onTrigger,
  onDismissBusy,
}: {
  job: DemoJob
  busy: BusyOutcome | null
  onTrigger: (key: string) => void
  onDismissBusy: () => void
}) {
  return (
    <div className="border-border flex flex-col gap-2 rounded-md border border-dashed px-3 py-2.5">
      <SectionHead
        label="trigger"
        role={`POST /api/v1/jobs/${job.key}/trigger`}
        help="Acquires the same per-job lock the scheduled loop uses. A trigger that lands while the lock is held returns busy (HTTP 409) immediately — never queued behind the in-flight run."
      />
      <div className="flex flex-wrap items-center gap-2.5">
        <Button
          size="sm"
          variant="outline"
          disabled={job.running}
          onClick={() => onTrigger(job.key)}
        >
          <Zap className="mr-1.5 size-3.5" />
          {job.running ? "Running…" : "Trigger now"}
        </Button>
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
            size="sm"
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

function JobConfigCard({
  job,
  binding,
  busy,
  onTrigger,
  onDismissBusy,
}: {
  job: DemoJob
  binding: JobsSettingsBinding
  busy: BusyOutcome | null
  onTrigger: (key: string) => void
  onDismissBusy: () => void
}) {
  return (
    <div
      className={cn(
        "border-border bg-card flex flex-col gap-2.5 rounded-lg border p-3.5",
        !job.enabled && "opacity-80",
      )}
    >
      <div className="flex flex-wrap items-center gap-2.5">
        <CalendarClock
          aria-hidden
          className="text-muted-foreground h-4 w-4 shrink-0"
        />
        <div className="flex items-center gap-1.5">
          <div className="flex flex-col">
            <span className="font-mono text-sm font-semibold">{job.key}</span>
            <span className="text-muted-foreground text-sm">{job.name}</span>
          </div>
          <HelpTip label={`About ${job.key}`}>{job.description}</HelpTip>
        </div>
        <span className="text-muted-foreground ml-auto font-mono text-[10px]">
          config row: job:{job.key}
        </span>
        <div className="flex items-center gap-1.5">
          <Switch
            checked={job.enabled}
            onCheckedChange={(on) => binding.setEnabled(job.key, on)}
            aria-label={`${job.key} enabled`}
          />
          <span className="text-muted-foreground font-mono text-[10px] uppercase">
            {job.enabled ? "enabled" : "disabled"}
          </span>
        </div>
      </div>
      <ScheduleSection job={job} saveCron={binding.saveCron} />
      <ConstantsSection job={job} />
      <ConfigSchemaSection job={job} saveConfig={binding.saveConfig} />
      <TriggerSection
        job={job}
        busy={busy}
        onTrigger={onTrigger}
        onDismissBusy={onDismissBusy}
      />
    </div>
  )
}

export function JobsSettingsTab() {
  const binding = useJobsSettingsBinding()
  const { jobs, isLoading, isError, trigger } = binding
  const [busy, setBusy] = useState<BusyOutcome | null>(null)
  const disabled = jobs.filter((j) => !j.enabled).length

  const handleTrigger = (key: string) => {
    // ruling 1: a held lock must render as busy, never as queued — the
    // 409 branch of `trigger` (proven by useJobBoard, T1.45) resolves
    // {ok:false, status:409} instead of throwing, so this is never
    // mistaken for a request failure. Any other rejection is a genuine
    // failure and must not be swallowed as busy.
    trigger(key)
      .then((result) => {
        setBusy(result.ok ? null : { key, lock_held_since: result.lock_held_since })
      })
      .catch((err: unknown) => {
        toast.error(`Trigger failed for ${key}`, {
          description: err instanceof Error ? err.message : undefined,
        })
      })
  }

  return (
    <div className="space-y-4">
      <div className="text-muted-foreground flex max-w-4xl items-center gap-1.5 text-sm">
        <span>
          JobRegistry configuration for the registered jobs — cron, the
          enabled switch, per-job config, and a manual trigger, all in one
          place.
        </span>
        <HelpTip label="About the Jobs tab">
          Cron, the enabled switch, and config_schema fields save per job;
          the floor/ceiling stay read-only registration constants. A manual
          trigger acquires the same asyncio.Lock the scheduled loop uses, so
          a save can never race a running tick, and a trigger that lands
          while the lock is held returns busy (HTTP 409) immediately —
          discarded, never queued behind the in-flight run. The full run
          history lives on Activity → Jobs, which shares this same trigger
          mechanism.
        </HelpTip>
      </div>
      <ModuleSurface
        title="Jobs configuration"
        state={isLoading ? "empty" : jobs.length > 0 ? "populated" : "empty"}
        meta={`${jobs.length} registered · ${disabled} disabled`}
      >
        {isError ? (
          <EmptyState
            icon={<CircleAlert aria-hidden className="h-6 w-6" />}
            title="Couldn't load the job board"
            description="The /jobs request failed — this is an error state, not an empty registry."
          />
        ) : (
          jobs.map((job) => (
            <JobConfigCard
              key={job.key}
              job={job}
              binding={binding}
              busy={busy}
              onTrigger={handleTrigger}
              onDismissBusy={() => setBusy(null)}
            />
          ))
        )}
      </ModuleSurface>
    </div>
  )
}
