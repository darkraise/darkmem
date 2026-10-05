import { useState } from "react"
import { toast } from "darkraise-ui/components/sonner"
import { LayoutGrid, List, Timer } from "lucide-react"
import { EmptyState } from "@/components/darkmem"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import { IconSegmented, type IconSegmentedOption } from "@/components/darkmem"
import type { DemoJob } from "@/features/activity/types"
import { triggerWithToast, useJobsSettingsBinding } from "../use-jobs-binding"
import { JobGridCard } from "./job-grid-card"
import { JobListRow } from "./job-list-row"
import { JobConfigDialog } from "./job-config-dialog"
import { JobHistoryDialog } from "./job-history-dialog"
import { useUsageByJob } from "@/hooks/api"
import { UsageChip } from "@/features/usage/components/usage-chip"

type JobsLayout = "list" | "grid"

const LAYOUTS: ReadonlyArray<IconSegmentedOption<JobsLayout>> = [
  { value: "list", label: "List layout", icon: List },
  { value: "grid", label: "Grid layout", icon: LayoutGrid },
]

export function JobsPage() {
  const [layout, setLayout] = useState<JobsLayout>("grid")
  const [configuring, setConfiguring] = useState<DemoJob | null>(null)
  const [viewingHistory, setViewingHistory] = useState<DemoJob | null>(null)
  const binding = useJobsSettingsBinding()
  const {
    jobs,
    isLoading,
    isError,
    trigger,
    saveCron,
    saveConfig,
    setEnabled,
  } = binding

  // Every run a job made in the window, not the last one: a job's cost is a
  // rate, and one run's number invites reading a cheap tick as a cheap job.
  const jobUsage = useUsageByJob("30d")
  const usageByJob = new Map(
    (jobUsage.data?.jobs ?? []).map((j) => [j.job_key, j]),
  )
  const usageChip = (job: DemoJob) => (
    <UsageChip pending={jobUsage.isLoading} totals={usageByJob.get(job.key)} />
  )

  const handleTrigger = (job: DemoJob) => triggerWithToast(trigger, job)
  // The switch follows the server's state, so a refused toggle snaps back on
  // its own; the toast says why it did.
  const toggle = (job: DemoJob, on: boolean) =>
    setEnabled(job.key, on).catch((error: unknown) =>
      toast.error(
        `${job.name}: ${error instanceof Error ? error.message : String(error)}`,
      ),
    )
  const running = jobs.filter((j) => j.running).length
  const disabled = jobs.filter((j) => !j.enabled).length

  return (
    <div className="space-y-4">
      <PageChrome icon={Timer} title="Jobs" />

      {/* The layout toggle shares its row with the board's summary rather
          than holding a toolbar band on its own. */}
      <div className="flex flex-wrap items-center gap-3">
        {!isLoading && !isError && jobs.length > 0 && (
          <p className="text-muted-foreground font-mono text-sm">
            {jobs.length} registered · {running} running
            {disabled > 0 && ` · ${disabled} disabled`}
          </p>
        )}
        <IconSegmented
          value={layout}
          options={LAYOUTS}
          onChange={setLayout}
          label="Jobs layout"
          className="ml-auto"
        />
      </div>

      {isError ? (
        <EmptyState kind="failed" title="Couldn't load the job board" />
      ) : isLoading ? (
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-44 w-full rounded-md" />
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <EmptyState
          kind="empty"
          icon={Timer}
          scope="page"
          title="No registered jobs"
          description="This usually means the server did not start cleanly."
        />
      ) : layout === "list" ? (
        <div className="flex flex-col gap-2">
          {jobs.map((job) => (
            <JobListRow
              key={job.key}
              job={job}
              onTrigger={() => handleTrigger(job)}
              onConfigure={() => setConfiguring(job)}
              onHistory={() => setViewingHistory(job)}
              onToggleEnabled={(on) => void toggle(job, on)}
              aside={usageChip(job)}
            />
          ))}
        </div>
      ) : (
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {jobs.map((job) => (
            <JobGridCard
              key={job.key}
              job={job}
              onTrigger={() => handleTrigger(job)}
              onConfigure={() => setConfiguring(job)}
              onHistory={() => setViewingHistory(job)}
              onToggleEnabled={(on) => void toggle(job, on)}
              aside={usageChip(job)}
            />
          ))}
        </div>
      )}

      {configuring && (
        <JobConfigDialog
          job={configuring}
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
