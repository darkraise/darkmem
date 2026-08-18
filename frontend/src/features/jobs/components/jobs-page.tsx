import { useState } from "react"
import { LayoutGrid, List, Timer } from "lucide-react"
import { EmptyState } from "@/components/darkmem"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import { PageChrome } from "@/components/app-chrome"
import {
  HelpTip,
  IconSegmented,
  type IconSegmentedOption,
} from "@/components/darkmem"
import type { DemoJob } from "@/features/activity/types"
import { useJobsSettingsBinding } from "../use-jobs-binding"
import { JobsListLayout } from "./jobs-list-layout"
import { JobGridCard } from "./job-grid-card"
import { JobConfigDialog } from "./job-config-dialog"
import { JobHistoryDialog } from "./job-history-dialog"

type JobsLayout = "list" | "grid"

const LAYOUTS: ReadonlyArray<IconSegmentedOption<JobsLayout>> = [
  { value: "list", label: "List layout", icon: List },
  { value: "grid", label: "Grid layout", icon: LayoutGrid },
]

export function JobsPage() {
  const [layout, setLayout] = useState<JobsLayout>("list")
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

  // Same handling the list layout proves: a held lock resolves {ok:false,409}
  // rather than throwing, so it must not be reported as a request failure.
  const handleTrigger = (job: DemoJob) => {
    trigger(job.key)
      .then((result) => {
        if (result.ok) toast.success(`${job.key} — triggered`)
        else
          toast.warning(`${job.key} — busy`, {
            description:
              "A run already holds the lock; the trigger was discarded, not queued.",
          })
      })
      .catch((err: unknown) => {
        toast.error(`Trigger failed for ${job.key}`, {
          description: err instanceof Error ? err.message : undefined,
        })
      })
  }

  return (
    <div className="space-y-4">
      <PageChrome
        icon={Timer}
        title="Jobs"
        description="The registered JobRegistry jobs — schedule, config, and manual triggers."
        actions={
          <IconSegmented
            value={layout}
            options={LAYOUTS}
            onChange={setLayout}
            label="Jobs layout"
          />
        }
      />

      <div className="text-muted-foreground flex max-w-4xl items-center gap-1.5 text-sm">
        <span>
          Cron, the enabled switch, per-job config and a manual trigger.
        </span>
        <HelpTip label="About Jobs">
          A manual trigger acquires the same asyncio.Lock the scheduled loop
          uses, so a save can never race a running tick, and a trigger that
          lands while the lock is held returns busy (HTTP 409) immediately —
          discarded, never queued behind the in-flight run.
        </HelpTip>
      </div>

      {isError ? (
        <EmptyState
          kind="failed"
          title="Couldn't load the job board"
          description="The /jobs request failed — this is an error state, not an empty registry."
        />
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
          description="The registry returned no jobs. On a healthy install this list is never empty, so treat it as a boot problem rather than a quiet day."
        />
      ) : layout === "list" ? (
        <JobsListLayout />
      ) : (
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
          {jobs.map((job) => (
            <JobGridCard
              key={job.key}
              job={job}
              onTrigger={() => handleTrigger(job)}
              onConfigure={() => setConfiguring(job)}
              onHistory={() => setViewingHistory(job)}
              onToggleEnabled={(on) => setEnabled(job.key, on)}
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
