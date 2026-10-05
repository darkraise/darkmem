import { createFileRoute, redirect } from "@tanstack/react-router"
import { Tabs, TabsContent, TabsTrigger } from "darkraise-ui/components/tabs"
import {
  Activity,
  ScrollText,
  Bug,
  CalendarDays,
  Gauge,
  Moon,
  Plug,
  Rss,
} from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { ScrollTabsList } from "@/components/darkmem"
import { DAY_DRILL_DEFAULT } from "@/demo/data-exports"
import { isValidDay } from "@/demo/activity"
import { DEMO } from "@/lib/demo-flag"
import { utcDayKey } from "@/features/dashboard/calendar"
import { PipelineTab } from "@/features/activity/components/pipeline-tab"
import { FeedTab } from "@/features/activity/components/feed-tab"
import { TriageTab } from "@/features/activity/components/triage-tab"
import { DreamTab } from "@/features/activity/components/dream-tab"
import { DayTab } from "@/features/activity/components/day-tab"
import { McpTab } from "@/features/activity/components/mcp-tab"
import { OpenWorkstreams } from "@/features/worklog/components/open-workstreams"

const TAB_VALUES = [
  "pipeline",
  "feed",
  "triage",
  "dream",
  "day",
  "worklog",
  "mcp",
] as const
export type ActivityTab = (typeof TAB_VALUES)[number]

export const Route = createFileRoute("/_authenticated/activity")({
  validateSearch: (search: Record<string, unknown>) => ({
    tab: TAB_VALUES.includes(search.tab as ActivityTab)
      ? (search.tab as ActivityTab)
      : undefined,
    day: isValidDay(search.day) ? search.day : undefined,
  }),
  // Activity used to carry a second copy of the job board; its links now go
  // to the one board.
  beforeLoad: ({ location }) => {
    if ((location.search as { tab?: unknown }).tab === "jobs") {
      throw redirect({ to: "/jobs" })
    }
  },
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
      <PageChrome icon={Activity} title="Activity" />
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
            `sticky` on this wrapper with the scroller (`ScrollTabsList`) inside it,
            because a scroll container clips its own overflow and a sticky
            element inside one pins to that container rather than to the page.
            The `before` band paints the shell's top padding, which sticky
            leaves as a gap that scrolling rows would otherwise show through. */}
        <div className="bg-background before:bg-background sticky top-0 z-20 pb-2 before:absolute before:inset-x-0 before:bottom-full before:h-8 before:content-['']">
          <ScrollTabsList activeValue={tab ?? "pipeline"}>
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
            <TabsTrigger className="flex-1 gap-2" value="dream">
              <Moon aria-hidden className="size-[var(--icon-size)]" />
              Dream digest
            </TabsTrigger>
            <TabsTrigger className="flex-1 gap-2" value="day">
              <CalendarDays aria-hidden className="size-[var(--icon-size)]" />
              Day drill
            </TabsTrigger>
            <TabsTrigger className="flex-1 gap-2" value="worklog">
              <ScrollText aria-hidden className="size-[var(--icon-size)]" />
              Work log
            </TabsTrigger>
            <TabsTrigger className="flex-1 gap-2" value="mcp">
              <Plug aria-hidden className="size-[var(--icon-size)]" />
              MCP calls
            </TabsTrigger>
          </ScrollTabsList>
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
        <TabsContent value="worklog" className="pt-4">
          <OpenWorkstreams />
        </TabsContent>
        <TabsContent value="mcp" className="pt-4">
          <McpTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
