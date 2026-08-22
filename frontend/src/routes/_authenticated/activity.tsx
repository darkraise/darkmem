import { createFileRoute } from "@tanstack/react-router"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "darkraise-ui/components/tabs"
import {
  Activity,
  Bookmark,
  Bug,
  CalendarDays,
  Gauge,
  Moon,
  Radio,
  Rss,
  Timer,
} from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { DAY_DRILL_DEFAULT } from "@/demo/data-exports"
import { isValidDay } from "@/demo/activity"
import { DEMO } from "@/lib/demo-flag"
import { utcDayKey } from "@/features/dashboard/calendar"
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

// The demo fixture pins a fixed date so its curated day-bucket resolves;
// real mode has no such fixture, so it defaults to "today" in UTC — the
// same day-bucket unit the day view itself never re-derives client-side.
const dayDrillDefault = () => (DEMO ? DAY_DRILL_DEFAULT : utcDayKey(new Date()))

function ActivityPage() {
  const { tab, day } = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <div className="space-y-4">
      <PageChrome
        icon={Activity}
        title="Activity"
        description="What the system is doing: pipeline runs, jobs, monitors, and digests."
      />
      <Tabs
        border="accent"
        value={tab ?? "pipeline"}
        onValueChange={(value) => {
          if (TAB_VALUES.includes(value as ActivityTab)) {
            void navigate({
              search: (prev) => ({ ...prev, tab: value as ActivityTab }),
            })
          }
        }}
      >
        {/* The same sticky strip Settings uses, and for the same reasons:
            `sticky` on this wrapper with `overflow-x-auto` on the one inside,
            because a scroll container clips its own overflow and a sticky
            element inside one pins to that container rather than to the page.
            The `before` band paints the shell's top padding, which sticky
            leaves as a gap that scrolling rows would otherwise show through. */}
        <div className="bg-background before:bg-background sticky top-0 z-20 pb-2 before:absolute before:inset-x-0 before:bottom-full before:h-8 before:content-['']">
          <div className="overflow-x-auto">
            <TabsList className="w-full">
              <TabsTrigger className="flex-1 gap-2" value="pipeline">
                <Gauge aria-hidden className="size-[var(--icon-size)]" />
                Pipeline
              </TabsTrigger>
              <TabsTrigger className="flex-1 gap-2" value="feed">
                <Rss aria-hidden className="size-[var(--icon-size)]" />
                Feed
              </TabsTrigger>
              <TabsTrigger className="flex-1 gap-2" value="triage">
                <Bug aria-hidden className="size-[var(--icon-size)]" />
                Triage
              </TabsTrigger>
              <TabsTrigger className="flex-1 gap-2" value="jobs">
                <Timer aria-hidden className="size-[var(--icon-size)]" />
                Jobs
              </TabsTrigger>
              <TabsTrigger className="flex-1 gap-2" value="monitors">
                <Radio aria-hidden className="size-[var(--icon-size)]" />
                Monitors
              </TabsTrigger>
              <TabsTrigger className="flex-1 gap-2" value="dream">
                <Moon aria-hidden className="size-[var(--icon-size)]" />
                Dream digest
              </TabsTrigger>
              <TabsTrigger className="flex-1 gap-2" value="day">
                <CalendarDays aria-hidden className="size-[var(--icon-size)]" />
                Day drill
              </TabsTrigger>
              <TabsTrigger className="flex-1 gap-2" value="checkpoints">
                <Bookmark aria-hidden className="size-[var(--icon-size)]" />
                Checkpoints
              </TabsTrigger>
            </TabsList>
          </div>
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
            day={day ?? dayDrillDefault()}
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
