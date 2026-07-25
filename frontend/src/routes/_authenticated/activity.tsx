import { createFileRoute } from "@tanstack/react-router"
import { PageHeader } from "darkraise-ui/layout"
import {
  CalendarDays,
  Flag,
  Moon,
  Radar,
  Rss,
  Timer,
  TriangleAlert,
  Workflow,
} from "lucide-react"
import {
  PlaceholderTabs,
  type PlaceholderTab,
} from "@/components/placeholder-tabs"

export const Route = createFileRoute("/_authenticated/activity")({
  component: ActivityPage,
})

const TABS: PlaceholderTab[] = [
  {
    value: "pipeline",
    label: "Pipeline",
    icon: <Workflow />,
    title: "The pipeline stepper lands here",
    description:
      "Per-memory phase progress (embed, extract, dedup, write) with per-step failure states. Built in Wave 4.",
  },
  {
    value: "feed",
    label: "Feed",
    icon: <Rss />,
    title: "The live event feed lands here",
    description:
      "Everything the system did, as it happens — ingests, supersessions, job runs. Built in Wave 4.",
  },
  {
    value: "triage",
    label: "Triage",
    icon: <TriangleAlert />,
    title: "Failure triage lands here",
    description:
      "Pipeline failures grouped by step with retry controls. Built in Wave 4.",
  },
  {
    value: "jobs",
    label: "Jobs",
    icon: <Timer />,
    title: "The job registry lands here",
    description:
      "Cron-scheduled jobs with last-run status, manual triggers, and per-job config. Built in Wave 4.",
  },
  {
    value: "monitors",
    label: "Monitors",
    icon: <Radar />,
    title: "Staged monitors land here",
    description:
      "Watchpoints that promote observations into candidate facts. Built in Wave 4.",
  },
  {
    value: "dream",
    label: "Dream digest",
    icon: <Moon />,
    title: "The dream digest lands here",
    description:
      "What the overnight consolidation cycle merged, promoted, and archived. Built in Wave 4.",
  },
  {
    value: "day",
    label: "Day drill",
    icon: <CalendarDays />,
    title: "The day drill-down lands here",
    description:
      "Pick a day on the contribution calendar and replay what happened. Built in Wave 4.",
  },
  {
    value: "checkpoints",
    label: "Session checkpoints",
    icon: <Flag />,
    title: "Session checkpoints land here",
    description:
      "Agent session snapshots you can diff and restore context from. Built in Wave 4.",
  },
]

function ActivityPage() {
  return (
    <div className="space-y-4 p-6">
      <PageHeader
        title="Activity"
        description="What the system is doing: pipeline runs, jobs, monitors, and digests."
      />
      <PlaceholderTabs tabs={TABS} />
    </div>
  )
}
