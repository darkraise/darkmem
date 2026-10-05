import { createFileRoute, Link } from "@tanstack/react-router"
import {
  Brain,
  ClipboardCheck,
  FileText,
  LayoutDashboard,
  ListChecks,
  Timer,
  Workflow,
  type LucideIcon,
  Activity,
} from "lucide-react"
import type { ReactNode } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import {
  Stat,
  StatChange,
  StatLabel,
  StatValue,
} from "darkraise-ui/components/stat"
import {
  EmptyState,
  LayerChip,
  listItemClass,
  VerificationBadge,
} from "@/components/darkmem"
import { PageChrome } from "@/components/app-chrome"
import { relativeTime } from "@/lib/format"
import type { ActivityEvent } from "@/features/dashboard/types"
import { CalendarCard } from "@/features/dashboard/calendar-card"
import { useContributionCalendar } from "@/features/dashboard/use-contribution-calendar"
import { useDashboardStats } from "@/features/dashboard/use-dashboard-stats"
import { useDashboardActivity } from "@/features/dashboard/use-dashboard-activity"

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
      <CardContent className="px-4 py-3">
        <Stat>
          <StatLabel>{label}</StatLabel>
          <StatValue>{value}</StatValue>
          {change && (
            <StatChange direction={change.direction}>{change.text}</StatChange>
          )}
          {caption && <p className="text-warning-text text-sm">{caption}</p>}
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

/** Where a feed item opens: the journalled object itself when the event
 *  names one the app has a page for, otherwise the surface that lists that
 *  kind of event, so every item is a way in rather than a dead line. */
function FeedItemLink({
  event,
  className,
  children,
}: {
  event: ActivityEvent
  className: string
  children: ReactNode
}) {
  const id = event.object?.id
  switch (event.object?.type) {
    case "memory":
      if (id)
        return (
          <Link
            to="/memories/$memoryId"
            params={{ memoryId: id }}
            className={className}
          >
            {children}
          </Link>
        )
      break
    case "fact":
      if (id)
        return (
          <Link
            to="/knowledge/facts/$factId"
            params={{ factId: id }}
            className={className}
          >
            {children}
          </Link>
        )
      break
    case "article":
      if (id)
        return (
          <Link
            to="/knowledge/articles/$articleId"
            params={{ articleId: id }}
            className={className}
          >
            {children}
          </Link>
        )
      break
  }
  switch (event.kind) {
    case "memory":
      return (
        <Link to="/memories" className={className}>
          {children}
        </Link>
      )
    case "fact":
      return (
        <Link to="/knowledge/facts" className={className}>
          {children}
        </Link>
      )
    case "article":
      return (
        <Link to="/knowledge/articles" className={className}>
          {children}
        </Link>
      )
    case "review":
      return (
        <Link to="/knowledge/review" className={className}>
          {children}
        </Link>
      )
    case "job":
      return (
        <Link to="/jobs" className={className}>
          {children}
        </Link>
      )
    case "pipeline":
      return (
        <Link
          to="/activity"
          search={{ tab: "pipeline", day: undefined }}
          className={className}
        >
          {children}
        </Link>
      )
  }
}

function ActivityFeedItem({ event }: { event: ActivityEvent }) {
  const Icon = KIND_ICONS[event.kind]
  return (
    <FeedItemLink
      event={event}
      className={listItemClass({
        interactive: true,
        className:
          "focus-visible:ring-ring flex items-start gap-3 p-2.5 outline-none focus-visible:ring-1",
      })}
    >
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
    </FeedItemLink>
  )
}

function DashboardPage() {
  const { stats, isLoading: statsLoading } = useDashboardStats()
  const { events, isError: activityError } = useDashboardActivity()
  const { days, isLoading, isError } = useContributionCalendar()
  // A tile mid-load shows a dash rather than 0: a real zero and "not known
  // yet" are different claims, and the bug this page just came off was a
  // number that looked authoritative and was not.
  const tile = (n: number) => (statsLoading ? "—" : n.toLocaleString())

  return (
    <div className="space-y-4">
      <PageChrome
        icon={LayoutDashboard}
        title="Dashboard"
        description="What the vault knows and what changed recently."
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {/* No "+N today" delta: the only per-day series available is
            /events/calendar, which counts every event type — cron ticks and
            logins included — so on this vault it read "+20 today" beside a
            true total of 0. A delta that measures a different quantity than
            the tile it sits on is the same defect this page just came off. */}
        <StatTile label="Total memories" value={tile(stats.totalMemories)} />
        <StatTile label="Verified facts" value={tile(stats.verifiedFacts)} />
        <StatTile label="Live articles" value={tile(stats.liveArticles)} />
        <StatTile
          label="Pending review"
          value={tile(stats.pendingReview)}
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
          {activityError ? (
            <p className="text-muted-foreground text-sm">
              Could not load recent activity.
            </p>
          ) : events.length > 0 ? (
            <div className="space-y-2">
              {events.map((event) => (
                <ActivityFeedItem key={event.id} event={event} />
              ))}
            </div>
          ) : (
            <EmptyState
              kind="empty"
              icon={Activity}
              title="No activity yet"
              description="Capture a memory or wait for a scheduled job, and it appears here."
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
