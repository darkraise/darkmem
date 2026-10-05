import { useState } from "react"
import { Link } from "@tanstack/react-router"
import { ArrowUpRight } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "@/components/darkmem"
import type { DemoJob } from "@/features/activity/types"
import { JobConfigDialog } from "@/features/jobs/components/job-config-dialog"
import { JobHistoryDialog } from "@/features/jobs/components/job-history-dialog"
import { JobListRow } from "@/features/jobs/components/job-list-row"
import {
  triggerWithToast,
  useJobsSettingsBinding,
} from "@/features/jobs/use-jobs-binding"
import { useUsageByJob } from "@/hooks/api"
import { UsageChip } from "@/features/usage/components/usage-chip"
import { ModuleSurface } from "./module-surface"

/**
 * Activity → Jobs is a second door onto the /jobs board, so it renders the
 * same row, the same configure and history dialogs and the same trigger
 * handling (a disabled trigger while a run holds the lock, a toast for the
 * outcome). What it adds is the 30-day usage chip per job; everything an
 * operator can do to a job behaves identically on both surfaces.
 */
export function JobsTab() {
  const {
    jobs,
    isLoading,
    isError,
    trigger,
    saveCron,
    saveConfig,
    setEnabled,
  } = useJobsSettingsBinding()
  const [configuring, setConfiguring] = useState<DemoJob | null>(null)
  const [viewingHistory, setViewingHistory] = useState<DemoJob | null>(null)
  const jobUsage = useUsageByJob("30d")
  const usageByJob = new Map(
    (jobUsage.data?.jobs ?? []).map((j) => [j.job_key, j]),
  )

  const running = jobs.filter((j) => j.running).length
  const failed = jobs.filter(
    (j) => !j.running && j.last_status === "error",
  ).length
  // The dialog reads the live row, so a save shows through while it is open.
  const configJob = configuring
    ? (jobs.find((j) => j.key === configuring.key) ?? configuring)
    : null

  return (
    <div className="space-y-4">
      <ModuleSurface
        title="Jobs"
        state="populated"
        meta={`${jobs.length} registered · ${running} running · ${failed} last-run failed`}
        actions={
          <Button variant="ghost" asChild>
            <Link to="/jobs">
              Open Jobs
              <ArrowUpRight className="ml-1 size-3.5" />
            </Link>
          </Button>
        }
      >
        {isError ? (
          <EmptyState kind="failed" title="Couldn't load the job board" />
        ) : !isLoading && jobs.length === 0 ? (
          <p className="text-muted-foreground text-sm">No jobs registered.</p>
        ) : (
          jobs.map((job) => (
            <JobListRow
              key={job.key}
              job={job}
              onTrigger={() => triggerWithToast(trigger, job)}
              onConfigure={() => setConfiguring(job)}
              onHistory={() => setViewingHistory(job)}
              onToggleEnabled={(on) => setEnabled(job.key, on)}
              // Every run this job has made in the window, not the last one:
              // a job's cost is a rate, and one run's number invites reading
              // a cheap tick as a cheap job. The tooltip carries the run count.
              aside={
                <UsageChip
                  pending={jobUsage.isLoading}
                  totals={usageByJob.get(job.key)}
                />
              }
            />
          ))
        )}
      </ModuleSurface>
      {configJob && (
        <JobConfigDialog
          job={configJob}
          open
          onOpenChange={(open) => !open && setConfiguring(null)}
          saveCron={saveCron}
          saveConfig={saveConfig}
        />
      )}
      {viewingHistory && (
        <JobHistoryDialog
          jobKey={viewingHistory.key}
          displayName={viewingHistory.name}
          open
          onOpenChange={(open) => !open && setViewingHistory(null)}
        />
      )}
    </div>
  )
}
