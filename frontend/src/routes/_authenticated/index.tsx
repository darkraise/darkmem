import { createFileRoute } from "@tanstack/react-router"
import {
  Brain,
  ClipboardCheck,
  FileText,
  LayoutDashboard,
  ListChecks,
  Timer,
  Workflow,
  type LucideIcon,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import {
  Stat,
  StatChange,
  StatLabel,
  StatValue,
} from "darkraise-ui/components/stat"
import { PageChrome } from "@/components/app-chrome"
import { relativeTime } from "@/lib/format"
import { useDemoEvents, useDemoStats } from "@/demo/hooks"
import type { ActivityEvent } from "@/demo/types"
import { LayerChip, VerificationBadge } from "@/components/darkmem"
import { CalendarCard } from "@/features/dashboard/calendar-card"
import { useContributionCalendar } from "@/features/dashboard/use-contribution-calendar"

export const Route = createFileRoute("/_authenticated/")({
  component: DashboardPage,
})

function StatTile({
  label,
  value,
  change,
  caption,
}: {
  label: string
  value: string
  change?: { direction: "up" | "down" | "flat"; text: string }
  caption?: string
}) {
  return (
    <Card>
      <CardContent className="pt-5">
        <Stat>
          <StatLabel>{label}</StatLabel>
          <StatValue>{value}</StatValue>
          {change && (
            <StatChange direction={change.direction}>{change.text}</StatChange>
          )}
          {caption && <p className="text-warning text-sm">{caption}</p>}
        </Stat>
      </CardContent>
    </Card>
  )
}

const KIND_ICONS: Record<ActivityEvent["kind"], LucideIcon> = {
  memory: Brain,
  fact: ListChecks,
  article: FileText,
  pipeline: Workflow,
  job: Timer,
  review: ClipboardCheck,
}

function ActivityFeedItem({ event }: { event: ActivityEvent }) {
  const Icon = KIND_ICONS[event.kind]
  return (
    <div className="border-border flex items-start gap-3 rounded-md border p-2.5">
      <span className="bg-muted text-muted-foreground mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full">
        <Icon aria-hidden className="h-4 w-4" />
      </span>
      <div className="min-w-0 flex-1 space-y-1">
        <p className="text-sm">{event.title}</p>
        {event.detail && (
          <p className="text-muted-foreground text-sm">{event.detail}</p>
        )}
        {(event.verification || event.layer != null) && (
          <div className="flex flex-wrap items-center gap-1.5">
            {event.layer != null && <LayerChip layer={event.layer} />}
            {event.verification && (
              <VerificationBadge status={event.verification} />
            )}
          </div>
        )}
      </div>
      <span className="text-muted-foreground shrink-0 text-sm">
        {relativeTime(event.at)}
      </span>
    </div>
  )
}

function DashboardPage() {
  const stats = useDemoStats()
  const events = useDemoEvents()
  const { days, isLoading, isError } = useContributionCalendar()
  const todayCount = days[days.length - 1]?.count ?? 0

  return (
    <div className="space-y-4">
      <PageChrome
        icon={LayoutDashboard}
        title="Dashboard"
        description="What the vault knows and what changed recently."
      />

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatTile
          label="Total memories"
          value={stats.totalMemories.toLocaleString()}
          change={
            isLoading
              ? undefined
              : todayCount > 0
                ? { direction: "up", text: `+${todayCount} today` }
                : { direction: "flat", text: "quiet today" }
          }
        />
        <StatTile
          label="Verified facts"
          value={stats.verifiedFacts.toLocaleString()}
          change={{ direction: "up", text: "+6 this week" }}
        />
        <StatTile
          label="Live articles"
          value={stats.liveArticles.toLocaleString()}
          change={{ direction: "flat", text: "no change" }}
        />
        <StatTile
          label="Pending review"
          value={stats.pendingReview.toLocaleString()}
          caption={
            stats.disputedFacts > 0
              ? `includes ${stats.disputedFacts} disputed`
              : undefined
          }
        />
      </div>

      <CalendarCard days={days} isLoading={isLoading} isError={isError} />

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-muted-foreground text-sm font-medium tracking-wider uppercase">
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          {events.length > 0 ? (
            <div className="space-y-2">
              {events.map((event) => (
                <ActivityFeedItem key={event.id} event={event} />
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-sm">No activity yet.</p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
