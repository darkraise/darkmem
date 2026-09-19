/**
 * The two schedule/config sections the job config dialog renders.
 *
 * Extracted when Jobs moved to card and row layouts: both call the *same*
 * sections through the dialog rather than each growing its own fields, so
 * the two layouts cannot come to disagree about what a job is configurable
 * by. The floor and ceiling stay read-only registration constants.
 */
import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { cn } from "darkraise-ui/lib"
import { HelpTip, NumberField } from "@/components/darkmem"
import { validateJobConfig } from "@/demo/activity"
import { cronInfo } from "@/demo/settings"
import type { DemoJob } from "@/features/activity/types"

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
      <span className="font-mono text-xs font-semibold tracking-wide uppercase">
        {label}
      </span>
      <span className="text-muted-foreground font-mono text-xs">
        {role}
      </span>
      {help && <HelpTip label={`About ${label}`}>{help}</HelpTip>}
    </div>
  )
}

export function ScheduleSection({
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
          variant="outline"
          className="border-primary/60 text-primary-text"
          disabled={!info.ok || draft === job.cron}
          onClick={() => {
            saveCron(job.key, draft)
            setSaved(true)
          }}
        >
          Save schedule
        </Button>
        {saved && (
          <span className="text-success-text font-mono text-sm">
            saved — takes effect on the next scheduled tick
          </span>
        )}
      </div>
    </div>
  )
}

export function ConfigSchemaSection({
  job,
  saveConfig,
}: {
  job: DemoJob
  saveConfig: (key: string, config: Record<string, number>) => void
}) {
  const [values, setValues] = useState<Record<string, number>>(() =>
    Object.fromEntries(job.config_schema.map((f) => [f.key, f.value])),
  )
  const [saved, setSaved] = useState(false)

  if (job.config_schema.length === 0) {
    return (
      <div className="border-border bg-muted/8 flex flex-col gap-1.5 rounded-md border border-dashed px-3 py-2.5">
        <SectionHead
          label="config_schema"
          role="no fields declared for this job"
        />
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
              <NumberField
                value={values[field.key] ?? field.value}
                min={field.min}
                max={field.max}
                aria-label={`${job.key} ${field.key}`}
                onValueChange={(next) => {
                  setValues((v) => ({ ...v, [field.key]: next }))
                  setSaved(false)
                }}
                className={cn("w-28", error && "border-destructive")}
              />
              {(field.min !== undefined || field.max !== undefined) && (
                <span className="text-muted-foreground font-mono text-xs">
                  {field.min !== undefined && `min ${field.min}`}
                  {field.min !== undefined && field.max !== undefined && " · "}
                  {field.max !== undefined && `max ${field.max}`}
                </span>
              )}
              {error && (
                <span className="text-destructive text-sm">{error}</span>
              )}
            </div>
          )
        })}
        <Button
          variant="outline"
          className="border-primary/60 text-primary-text"
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
        {saved && <span className="text-success-text font-mono text-sm">saved</span>}
      </div>
    </div>
  )
}

