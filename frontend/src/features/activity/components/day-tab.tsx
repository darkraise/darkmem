import { Link } from "@tanstack/react-router"
import {
  ArrowRight,
  CalendarX,
  ChevronLeft,
  ChevronRight,
  Circle,
  Clock,
  Link2,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "@/components/darkmem"
import { useState } from "react"
import { useDetailLevel, VerificationBadge } from "@/components/darkmem"
import { shiftDay } from "@/demo/activity"
import { ModuleSurface } from "./module-surface"
import {
  useDayEvents,
  type DayRowData,
  type InjectRecordData,
} from "../use-day-events"
import { DEMO } from "@/lib/demo-flag"
import { utcDayKey } from "@/features/dashboard/calendar"

/** One inject record's summary line and its expandable detail.
 *
 * The summary always carries the item count and the budget: a push that spent
 * 40 of 4000 tokens and one that hit its ceiling are indistinguishable from
 * the id list alone, and they mean different things about what the agent was
 * *not* told.
 *
 * Simple/Advanced (invariant 14): `simple` collapses the raw ids and the
 * per-layer breakdown, and keeps the count, the budget line and the target —
 * "what was I told, and how much of it" is the honesty signal here, not a
 * technical detail.
 */
function InjectDetail({ inject }: { inject: InjectRecordData }) {
  const advanced = useDetailLevel((s) => s.level) === "advanced"
  const [open, setOpen] = useState(false)

  if (inject.curbed) {
    return (
      <div className="space-y-1">
        <p className="text-sm">
          Push curbed for <b className="font-semibold">{inject.tool}</b>
          {inject.contextFile ? ` — ${inject.contextFile}` : ""}. Nothing was
          pushed.
        </p>
        {inject.reason && (
          <p className="text-muted-foreground text-sm">
            reason: {inject.reason}
          </p>
        )}
      </div>
    )
  }

  const budgetLine =
    inject.tokensUsed !== null && inject.budgetTokens !== null
      ? `${inject.tokensUsed.toLocaleString()} / ${inject.budgetTokens.toLocaleString()} token budget`
      : "token budget not recorded"

  return (
    <div className="space-y-1.5">
      <p className="text-sm">
        {inject.itemCount} item{inject.itemCount === 1 ? "" : "s"} pushed ·{" "}
        {budgetLine}
      </p>
      {inject.trigger && (
        // A watch refresh (T4.06). Without the cause, a re-inject is
        // indistinguishable from a session start and "the human can see the
        // swap" reduces to seeing that something was pushed twice.
        <p className="text-sm">
          re-injected because the{" "}
          <b className="font-semibold">
            {TRIGGER_LABELS[inject.trigger] ?? inject.trigger}
          </b>{" "}
          changed
        </p>
      )}
      <Button
        variant="ghost"
        className="h-auto px-0 text-sm"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? "hide what was pushed" : "show exactly what was pushed"}
      </Button>
      {open && (
        <div className="border-border space-y-1.5 rounded-md border border-dashed p-2.5">
          <p className="text-muted-foreground text-sm">
            {inject.factIds.length} fact
            {inject.factIds.length === 1 ? "" : "s"} ·{" "}
            {inject.articleIds.length} article
            {inject.articleIds.length === 1 ? "" : "s"} ·{" "}
            {inject.memoryIds.length} memor
            {inject.memoryIds.length === 1 ? "y" : "ies"}
          </p>
          {advanced &&
            (
              [
                ["facts", inject.factIds],
                ["articles", inject.articleIds],
                ["memories", inject.memoryIds],
              ] as const
            ).map(([label, ids]) =>
              ids.length === 0 ? null : (
                <div key={label} className="space-y-0.5">
                  <p className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
                    {label}
                  </p>
                  <ul className="space-y-0.5">
                    {ids.map((id) => (
                      <li
                        key={id}
                        className="text-muted-foreground font-mono text-sm break-all"
                      >
                        {id}
                      </li>
                    ))}
                  </ul>
                </div>
              ),
            )}
        </div>
      )}
    </div>
  )
}

// Watch's closed trigger vocabulary (`inject_watch.WATCH_TRIGGERS`), read out
// in words. An unknown value renders verbatim rather than being dropped: the
// swap happened, and hiding its cause because this map is stale is worse than
// showing a raw token.
const TRIGGER_LABELS: Record<string, string> = {
  project_changed: "project",
  file_opened: "open file",
  context_changed: "declared context",
}

function DayEventRow({ event }: { event: DayRowData }) {
  return (
    <div className="border-border flex flex-wrap items-start gap-2.5 border-t border-dashed py-2.5 first:border-t-0 first:pt-0">
      <span className="text-muted-foreground w-20 shrink-0 pt-0.5 font-mono text-sm whitespace-nowrap">
        {event.timeLabel}
      </span>
      <span className="border-border bg-muted text-muted-foreground inline-flex shrink-0 items-center gap-1 rounded-sm border px-2 py-0.5 font-mono text-sm whitespace-nowrap">
        <Circle aria-hidden className="h-2 w-2" />
        {event.type}
      </span>
      <div className="flex min-w-0 flex-1 basis-72 flex-col gap-1.5">
        <span className="flex items-start gap-1.5 text-sm">
          <Link2
            aria-hidden
            className="text-muted-foreground mt-0.5 h-3.5 w-3.5 shrink-0"
          />
          {event.linkLabel}
        </span>
        {event.transition && (
          <span className="inline-flex flex-wrap items-center gap-2">
            <VerificationBadge status={event.transition.from} />
            <ArrowRight
              aria-hidden
              className="text-muted-foreground h-3.5 w-3.5"
            />
            <VerificationBadge
              status={event.transition.to}
              label={event.transition.toLabel}
            />
          </span>
        )}
        {event.badge && <VerificationBadge status={event.badge} />}
        {event.note && (
          <span className="text-muted-foreground text-sm">{event.note}</span>
        )}
        {event.inject && <InjectDetail inject={event.inject} />}
      </div>
    </div>
  )
}

export function DayTab({
  day,
  onDayChange,
}: {
  day: string
  onDayChange: (day: string) => void
}) {
  const { events, total, isLoading, isError, truncated } = useDayEvents(day)
  // Days are UTC keys, so they compare as strings. Nothing has happened past
  // today; the stepper used to walk into empty future days.
  const atToday = !DEMO && day >= utcDayKey(new Date())

  return (
    <div className="space-y-4">
      <ModuleSurface
        title="Day drill"
        state="populated"
        meta={`day ${day}`}
        actions={
          <>
            <Button variant="ghost" asChild>
              {/* Goes to the dashboard, whose calendar links back here per day. */}
              <Link to="/">
                <ChevronLeft className="mr-1 size-3.5" />
                Dashboard
              </Link>
            </Button>
            {/* Icon-only below sm so the stepper fits a phone header; the
                date stays in the accessible name at every width. */}
            <Button
              variant="outline"
              aria-label={`Previous day, ${shiftDay(day, -1)}`}
              onClick={() => onDayChange(shiftDay(day, -1))}
            >
              <ChevronLeft className="size-3.5 sm:mr-1" />
              <span className="hidden sm:inline">{shiftDay(day, -1)}</span>
            </Button>
            <Button
              variant="outline"
              aria-label={`Next day, ${shiftDay(day, 1)}`}
              disabled={atToday}
              onClick={() => onDayChange(shiftDay(day, 1))}
            >
              <span className="hidden sm:inline">{shiftDay(day, 1)}</span>
              <ChevronRight className="size-3.5 sm:ml-1" />
            </Button>
          </>
        }
      >
        <span className="text-muted-foreground flex items-center gap-1.5 text-sm">
          <Clock aria-hidden className="h-3.5 w-3.5 shrink-0" />
          <span>Days are UTC.</span>
        </span>
        {isError ? (
          <EmptyState kind="failed" title="Couldn't load this day" />
        ) : events && events.length > 0 ? (
          <div className="flex flex-col">
            {events.map((event) => (
              <DayEventRow key={event.id} event={event} />
            ))}
            {truncated && (
              <p className="text-muted-foreground pt-2.5 text-sm">
                Showing {events.length} of {total} events for this day — narrow
                by project to see the rest.
              </p>
            )}
          </div>
        ) : isLoading ? null : (
          <EmptyState
            kind="empty"
            icon={CalendarX}
            title="No activity on this day"
          />
        )}
      </ModuleSurface>
    </div>
  )
}
