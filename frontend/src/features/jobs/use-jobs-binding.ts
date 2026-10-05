import { toast } from "darkraise-ui/components/sonner"
import { DEMO } from "@/lib/demo-flag"
import { useDemoStore } from "@/demo/store"
import type { DemoJob } from "@/features/activity/types"
import {
  useJobBoard,
  type JobBoardState,
} from "@/features/activity/use-job-board"
import { useUpdateJob } from "@/hooks/api"

export interface JobsSettingsBinding extends JobBoardState {
  saveCron: (key: string, cron: string) => void
  setEnabled: (key: string, enabled: boolean) => void
}

/**
 * Reuses `useJobBoard` (T1.45, Activity → Jobs) for the job list, `trigger`,
 * and `saveConfig` — the busy-409-never-queued handling it already proves
 * (ruling 1) is not reimplemented here. This binding adds only the two
 * writes Activity's board doesn't need: cron and the enabled switch, via the
 * same `PUT /jobs/{key}` the demo store's `saveJobCron`/`setJobEnabled`
 * simulate.
 */
export function useJobsSettingsBinding(): JobsSettingsBinding {
  const board = useJobBoard()
  const saveDemoCron = useDemoStore((s) => s.saveJobCron)
  const setDemoEnabled = useDemoStore((s) => s.setJobEnabled)
  const updateJob = useUpdateJob()

  if (DEMO) {
    return { ...board, saveCron: saveDemoCron, setEnabled: setDemoEnabled }
  }

  return {
    ...board,
    saveCron: (key, cron) => updateJob.mutate({ key, data: { cron } }),
    setEnabled: (key, enabled) => updateJob.mutate({ key, data: { enabled } }),
  }
}

/**
 * Trigger a job and report the outcome as a toast. Shared by /jobs and
 * Activity → Jobs so both doors answer a trigger the same way. A held lock
 * resolves `{ok:false, 409}` rather than throwing, so it is reported as busy,
 * never as a request failure.
 */
export function triggerWithToast(
  trigger: JobBoardState["trigger"],
  job: Pick<DemoJob, "key" | "name">,
): void {
  trigger(job.key)
    .then((result) => {
      if (result.ok) toast.success(`${job.name} — triggered`)
      else
        toast.warning(`${job.name} — busy`, {
          description: "Already running; try again when it finishes.",
        })
    })
    .catch((err: unknown) => {
      toast.error(`Trigger failed for ${job.name}`, {
        description: err instanceof Error ? err.message : undefined,
      })
    })
}
