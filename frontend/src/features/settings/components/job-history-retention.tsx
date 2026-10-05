import { useState } from "react"
import { History } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { SettingsCard } from "./settings-card"
import { toast } from "darkraise-ui/components/sonner"
import { NumberField } from "@/components/darkmem"
import { useJobs, useTriggerJob, useUpdateJobConfig } from "@/hooks/api"

const JOB_KEY = "job_run_cleanup"
const DEFAULT_MAX_ROWS = 5000

/**
 * The job-history ceiling, surfaced where an operator looks for disk-shaped
 * problems rather than only on the Jobs page.
 *
 * Why this exists at all: run telemetry used to land in `events`, which is
 * append-only by trigger and permanent by ruling, so nothing could remove it
 * — a five-second job wrote ~17k rows a day into a table with no delete path.
 * `job_runs` is an ordinary table, and this is the sweep that bounds it.
 */
export function JobHistoryRetention() {
  const jobs = useJobs()
  const trigger = useTriggerJob()
  const updateConfig = useUpdateJobConfig()

  const job = jobs.data?.jobs.find((j) => j.key === JOB_KEY)
  const committed = Number(job?.config?.max_rows ?? DEFAULT_MAX_ROWS)
  const [draft, setDraft] = useState(committed)
  const [seed, setSeed] = useState(committed)
  if (seed !== committed) {
    setSeed(committed)
    setDraft(committed)
  }

  const dirty = Number.isFinite(draft) && draft !== committed

  return (
    // The same card shell the rest of the Maintenance tab uses. This one sits
    // in that stack, so a second treatment for it read as a different kind of
    // thing when it is one more operation.
    <SettingsCard
      icon={History}
      title="Job history retention"
      actions={
        job && (
          <span className="text-muted-foreground font-mono text-xs whitespace-nowrap">
            keeps newest {committed}
          </span>
        )
      }
    >
      <p className="text-muted-foreground text-sm">
        Keeps the newest job runs and deletes older ones. Runs weekly.
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <span className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
          max rows
        </span>
        <NumberField
          value={draft}
          min={100}
          max={1000000}
          aria-label="Max job history rows retained"
          onValueChange={setDraft}
          className="w-32"
        />
        <Button
          variant="outline"
          disabled={!dirty || updateConfig.isPending}
          onClick={() => {
            updateConfig
              .mutateAsync({ key: JOB_KEY, config: { max_rows: draft } })
              .then(() => toast.success(`Job history ceiling set to ${draft}`))
              .catch((err: unknown) =>
                toast.error("Couldn’t save the ceiling", {
                  description: err instanceof Error ? err.message : undefined,
                }),
              )
          }}
        >
          Save ceiling
        </Button>
        <Button
          variant="outline"
          className="ml-auto"
          disabled={trigger.isPending}
          onClick={() => {
            trigger
              .mutateAsync(JOB_KEY)
              .then(() => toast.success("Job history swept"))
              .catch((err: unknown) =>
                toast.error("Sweep failed", {
                  description: err instanceof Error ? err.message : undefined,
                }),
              )
          }}
        >
          Sweep now
        </Button>
      </div>
    </SettingsCard>
  )
}
