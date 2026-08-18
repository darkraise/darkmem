import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import type { DemoJob } from "@/features/activity/types"
import { ConfigSchemaSection, ScheduleSection } from "./jobs-list-layout"

/**
 * The grid layout's configure CTA. Deliberately renders the *same* schedule
 * and config_schema sections the list layout does rather than a second set
 * of fields, so the two layouts cannot drift into disagreeing about what a
 * job is configurable by.
 */
export function JobConfigDialog({
  job,
  open,
  onOpenChange,
  saveCron,
  saveConfig,
}: {
  job: DemoJob
  open: boolean
  onOpenChange: (open: boolean) => void
  saveCron: (key: string, cron: string) => void
  saveConfig: (key: string, config: Record<string, number>) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[80vh] max-w-2xl flex-col gap-3">
        <DialogHeader>
          <DialogTitle>{job.name} — configuration</DialogTitle>
          <DialogDescription>
            Schedule and config_schema. The floor and ceiling stay read-only
            registration constants.
          </DialogDescription>
        </DialogHeader>
        <div className="flex min-h-0 flex-1 flex-col gap-2.5 overflow-y-auto">
          <ScheduleSection job={job} saveCron={saveCron} />
          <ConfigSchemaSection job={job} saveConfig={saveConfig} />
        </div>
      </DialogContent>
    </Dialog>
  )
}
