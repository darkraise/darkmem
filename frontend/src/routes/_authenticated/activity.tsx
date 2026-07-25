import { createFileRoute } from "@tanstack/react-router"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "darkraise-ui/components/tabs"
import { PageHeader } from "darkraise-ui/layout"
import { DAY_DRILL_DEFAULT } from "@/demo/data/activity-curated"
import { isValidDay } from "@/demo/activity"
import { PipelineTab } from "@/features/activity/components/pipeline-tab"
import { FeedTab } from "@/features/activity/components/feed-tab"
import { TriageTab } from "@/features/activity/components/triage-tab"
import { JobsTab } from "@/features/activity/components/jobs-tab"
import { MonitorsTab } from "@/features/activity/components/monitors-tab"
import { DreamTab } from "@/features/activity/components/dream-tab"
import { DayTab } from "@/features/activity/components/day-tab"
import { CheckpointsTab } from "@/features/activity/components/checkpoints-tab"

const TAB_VALUES = [
  "pipeline",
  "feed",
  "triage",
  "jobs",
  "monitors",
  "dream",
  "day",
  "checkpoints",
] as const
export type ActivityTab = (typeof TAB_VALUES)[number]

export const Route = createFileRoute("/_authenticated/activity")({
  validateSearch: (search: Record<string, unknown>) => ({
    tab: TAB_VALUES.includes(search.tab as ActivityTab)
      ? (search.tab as ActivityTab)
      : undefined,
    day: isValidDay(search.day) ? search.day : undefined,
  }),
  component: ActivityPage,
})

function ActivityPage() {
  const { tab, day } = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <div className="space-y-4 p-6">
      <PageHeader
        title="Activity"
        description="What the system is doing: pipeline runs, jobs, monitors, and digests."
      />
      <Tabs
        value={tab ?? "pipeline"}
        onValueChange={(value) => {
          if (TAB_VALUES.includes(value as ActivityTab)) {
            void navigate({
              search: (prev) => ({ ...prev, tab: value as ActivityTab }),
            })
          }
        }}
      >
        <div className="overflow-x-auto">
          <TabsList>
            <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
            <TabsTrigger value="feed">Feed</TabsTrigger>
            <TabsTrigger value="triage">Triage</TabsTrigger>
            <TabsTrigger value="jobs">Jobs</TabsTrigger>
            <TabsTrigger value="monitors">Monitors</TabsTrigger>
            <TabsTrigger value="dream">Dream digest</TabsTrigger>
            <TabsTrigger value="day">Day drill</TabsTrigger>
            <TabsTrigger value="checkpoints">Session checkpoints</TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="pipeline" className="pt-4">
          <PipelineTab />
        </TabsContent>
        <TabsContent value="feed" className="pt-4">
          <FeedTab />
        </TabsContent>
        <TabsContent value="triage" className="pt-4">
          <TriageTab />
        </TabsContent>
        <TabsContent value="jobs" className="pt-4">
          <JobsTab />
        </TabsContent>
        <TabsContent value="monitors" className="pt-4">
          <MonitorsTab
            onOpenDigest={() =>
              void navigate({ search: (prev) => ({ ...prev, tab: "dream" }) })
            }
          />
        </TabsContent>
        <TabsContent value="dream" className="pt-4">
          <DreamTab />
        </TabsContent>
        <TabsContent value="day" className="pt-4">
          <DayTab
            day={day ?? DAY_DRILL_DEFAULT}
            onDayChange={(next) =>
              void navigate({ search: (prev) => ({ ...prev, day: next }) })
            }
          />
        </TabsContent>
        <TabsContent value="checkpoints" className="pt-4">
          <CheckpointsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
