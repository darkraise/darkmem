import { cronInfo } from "@/demo/settings"
import { DEMO } from "@/lib/demo-flag"
import { useDemoJobs } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type { DemoJob, DemoJobField, JobTriggerResult } from "@/features/activity/types"
import { relativeTime } from "@/lib/format"
import { ApiError } from "@/lib/api"
import { useJobs, useTriggerJob, useUpdateJobConfig, type Job } from "@/hooks/api"

function cronLabel(cron: string): string {
  const info = cronInfo(cron)
  return info.ok ? info.hint : info.error
}

function fromJob(job: Job): DemoJob {
  return {
    key: job.key,
    name: job.display_name,
    description: job.description,
    enabled: job.enabled,
    cron: job.cron,
    cron_label: cronLabel(job.cron),
    min_interval_seconds: job.min_interval_seconds,
    // JobItem does not carry the registry's max_run_seconds over the wire —
    // never fabricated to fill the read-only field the demo shows.
    max_run_seconds: null,
    running: job.running,
    lock_held_since: null,
    // No cron-next calculator exists client-side and the API returns none —
    // never fabricated.
    next_run_label: null,
    last_run_label: job.last_run_at ? relativeTime(job.last_run_at) : null,
    last_status: job.last_status,
    last_summary:
      job.last_status === "error" ? job.last_error : job.last_status === "ok" ? "completed" : null,
    config_schema: (job.config_schema ?? []).map(
      (fd): DemoJobField => ({
        key: fd.key,
        type: "int",
        label: fd.label,
        value: job.config?.[fd.key] ?? fd.default,
        min: fd.min,
        max: fd.max,
        help: fd.help,
      }),
    ),
  }
}

export interface JobBoardState {
  jobs: DemoJob[]
  isLoading: boolean
  isError: boolean
  trigger: (key: string) => Promise<JobTriggerResult>
  /** Rejects with the server's reason when the write is refused. */
  saveConfig: (key: string, config: Record<string, number>) => Promise<void>
}

/**
 * `DEMO ? demo : real`, following `use-contribution-calendar.ts`. `trigger`
 * is a `Promise` on both branches — real mode's `POST .../trigger` genuinely
 * is one, and the demo store's synchronous result is wrapped so the board
 * never special-cases which mode it's in (ruling 4: a 409 must render as
 * busy on either branch, not as a failure).
 */
export function useJobBoard(): JobBoardState {
  const demoJobs = useDemoJobs()
  const triggerDemo = useDemoStore((s) => s.triggerJob)
  const saveDemoConfig = useDemoStore((s) => s.saveJobConfig)

  const query = useJobs(!DEMO)
  const triggerMutation = useTriggerJob()
  const configMutation = useUpdateJobConfig()

  if (DEMO) {
    return {
      jobs: demoJobs,
      isLoading: false,
      isError: false,
      trigger: (key) => Promise.resolve(triggerDemo(key)),
      saveConfig: async (key, config) => saveDemoConfig(key, config),
    }
  }

  return {
    jobs: (query.data?.jobs ?? []).map(fromJob),
    isLoading: query.isLoading,
    isError: query.isError,
    trigger: async (key) => {
      try {
        await triggerMutation.mutateAsync(key)
        return { ok: true }
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          return { ok: false, status: 409, lock_held_since: null }
        }
        throw err
      }
    },
    saveConfig: async (key, config) => {
      await configMutation.mutateAsync({ key, config })
    },
  }
}
