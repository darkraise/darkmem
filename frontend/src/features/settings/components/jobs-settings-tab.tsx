import { useState } from "react"
import { CalendarClock } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Switch } from "darkraise-ui/components/switch"
import { cn } from "darkraise-ui/lib"
import { ModuleSurface } from "@/features/activity/components/module-surface"
import { validateJobConfig } from "@/demo/activity"
import { cronInfo } from "@/demo/settings"
import { useDemoJobs } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type { DemoJob } from "@/demo/types"

function SectionHead({ label, role }: { label: string; role: string }) {
  return (
    <div className="flex flex-wrap items-baseline gap-2">
      <span className="font-mono text-[10px] font-semibold tracking-wide uppercase">
        {label}
      </span>
      <span className="text-muted-foreground font-mono text-[10px]">
        {role}
      </span>
    </div>
  )
}

function ScheduleSection({ job }: { job: DemoJob }) {
  const saveJobCron = useDemoStore((s) => s.saveJobCron)
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
            saveJobCron(job.key, draft)
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
      <SectionHead label="registration constants" role="read-only" />
      <div className="flex flex-wrap gap-6">
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground font-mono text-[10px]">
            min_interval_seconds (floor)
          </span>
          <span className="font-mono text-sm font-semibold">
            {job.min_interval_seconds}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground font-mono text-[10px]">
            max_run_seconds (ceiling)
          </span>
          <span className="font-mono text-sm font-semibold">
            {job.max_run_seconds}
          </span>
        </div>
      </div>
      <span className="text-muted-foreground text-sm">
        Fixed Job-dataclass attributes set once at registration in app/main.py —
        no write path for either. The loop never fires more often than the
        floor, no matter how aggressive the cron computes.
      </span>
    </div>
  )
}

function ConfigSchemaSection({ job }: { job: DemoJob }) {
  const saveConfig = useDemoStore((s) => s.saveJobConfig)
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
              <span className="font-mono text-sm font-semibold">
                {field.key}{" "}
                <span className="text-muted-foreground font-normal lowercase">
                  {field.type}
                </span>
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
              <span className="text-muted-foreground text-sm">
                {field.help ? `${field.help} ` : ""}
                {field.min !== undefined && `min ${field.min}`}
                {field.min !== undefined && field.max !== undefined && " · "}
                {field.max !== undefined && `max ${field.max}`}
              </span>
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

function JobConfigCard({ job }: { job: DemoJob }) {
  const setJobEnabled = useDemoStore((s) => s.setJobEnabled)
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
        <div className="flex flex-col">
          <span className="font-mono text-sm font-semibold">{job.key}</span>
          <span className="text-muted-foreground text-sm">{job.name}</span>
        </div>
        <span className="text-muted-foreground ml-auto font-mono text-[10px]">
          config row: job:{job.key}
        </span>
        <div className="flex items-center gap-1.5">
          <Switch
            checked={job.enabled}
            onCheckedChange={(on) => setJobEnabled(job.key, on)}
            aria-label={`${job.key} enabled`}
          />
          <span className="text-muted-foreground font-mono text-[10px] uppercase">
            {job.enabled ? "enabled" : "disabled"}
          </span>
        </div>
      </div>
      <p className="text-muted-foreground max-w-prose text-sm">
        {job.description}
      </p>
      <ScheduleSection job={job} />
      <ConstantsSection job={job} />
      <ConfigSchemaSection job={job} />
    </div>
  )
}

export function JobsSettingsTab() {
  const jobs = useDemoJobs()
  const disabled = jobs.filter((j) => !j.enabled).length
  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-4xl text-sm">
        The JobRegistry configuration surface for the same seven registered jobs
        the Activity job board monitors — read here for editing rather than
        operating. Cron and the enabled switch save per job; the floor/ceiling
        stay read-only registration constants. Both writes share the job&apos;s
        asyncio.Lock with the scheduled loop, so a save can never race a
        running tick. Run history, Trigger now, and the busy (409) outcome live
        on Activity → Jobs, not here.
      </p>
      <ModuleSurface
        title="Jobs configuration"
        state="populated"
        meta={`${jobs.length} registered · ${disabled} disabled`}
      >
        {jobs.map((job) => (
          <JobConfigCard key={job.key} job={job} />
        ))}
      </ModuleSurface>
    </div>
  )
}
