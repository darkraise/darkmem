import { useState } from "react"
import { ArrowRight, Bell, Inbox } from "lucide-react"
import { EmptyState } from "darkraise-ui/components/empty-state"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import { cn } from "darkraise-ui/lib"
import { LayerChip, VerificationBadge } from "@/components/darkmem"
import { FEED_CATEGORIES, filterFeed } from "@/demo/activity"
import { useDemoFeedEvents } from "@/demo/hooks"
import type { DemoFeedEvent, FeedCategory } from "@/demo/types"
import { ModuleSurface } from "./module-surface"

function FeedRow({ event }: { event: DemoFeedEvent }) {
  return (
    <div
      className={cn(
        "border-border flex flex-wrap items-center gap-2.5 rounded-md border px-3 py-2",
        event.toast && "border-destructive/45 bg-destructive/5",
      )}
    >
      <span className="border-border bg-muted text-muted-foreground rounded-sm border px-1.5 py-0.5 font-mono text-[10px] tracking-wide whitespace-nowrap">
        {event.type}
      </span>
      {event.layer !== undefined && <LayerChip layer={event.layer} />}
      {event.transition && (
        <span className="inline-flex items-center gap-1.5">
          <VerificationBadge status={event.transition.from} />
          <ArrowRight aria-hidden className="text-muted-foreground h-3 w-3" />
          <VerificationBadge status={event.transition.to} />
        </span>
      )}
      {event.badge && <VerificationBadge status={event.badge} />}
      <span className="min-w-0 flex-1 basis-64 text-sm">{event.text}</span>
      {event.toast && (
        <span className="border-destructive/55 bg-destructive/10 text-destructive inline-flex items-center gap-1 rounded-full border border-dashed px-2 py-0.5 font-mono text-[10px] whitespace-nowrap">
          <Bell aria-hidden className="h-3 w-3" />
          toast shown
        </span>
      )}
      <span className="text-muted-foreground font-mono text-sm whitespace-nowrap">
        {event.time_label}
      </span>
    </div>
  )
}

export function FeedTab() {
  const events = useDemoFeedEvents()
  const [category, setCategory] = useState<FeedCategory | "all">("all")
  const filtered = filterFeed(events, category)

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-4xl text-sm">
        The transient live stream while this view stays open — captures,
        pipeline outcomes, verification changes, consolidation, and repo syncs
        as they happen. This list is convenience only, not the record of truth:
        the per-object timeline and the calendar day drill-down reconstruct
        history from the durable events substrate, not from what this socket
        happened to deliver.
      </p>
      <ModuleSurface
        title="Activity — live feed"
        state={filtered.length > 0 ? "populated" : "empty"}
        meta="/activity"
        actions={
          <span className="text-success inline-flex items-center gap-1.5 font-mono text-sm">
            <span aria-hidden className="bg-success h-1.5 w-1.5 rounded-full" />
            connected
          </span>
        }
      >
        <ToggleGroup
          type="single"
          value={category}
          onValueChange={(value) => {
            // ToggleGroup emits "" when the active item is clicked again —
            // keep the current filter instead of losing the selection.
            if (value) setCategory(value as FeedCategory | "all")
          }}
          className="flex-wrap justify-start"
        >
          <ToggleGroupItem value="all" size="sm" className="font-mono text-sm">
            all
          </ToggleGroupItem>
          {FEED_CATEGORIES.map((c) => (
            <ToggleGroupItem
              key={c}
              value={c}
              size="sm"
              className="font-mono text-sm"
            >
              {c}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
        {filtered.length === 0 ? (
          <EmptyState
            icon={<Inbox aria-hidden className="h-6 w-6" />}
            title={`No ${category === "all" ? "" : `${category} `}events since this view opened`}
            description="The feed streams only while Activity stays open — matching events will appear here the moment they happen. For history before this view was opened, use the day drill-down, which reads the durable events substrate."
          />
        ) : (
          filtered.map((event) => <FeedRow key={event.id} event={event} />)
        )}
        <p className="text-muted-foreground text-sm">
          The row marked <span className="font-mono">toast shown</span> is the
          one event whose toast carries honesty content — a fact.verified
          dispute — and its toast body states the same two-sided claim the
          Review queue renders, so a fast-moving alert can never contradict the
          detail view.
        </p>
      </ModuleSurface>
    </div>
  )
}
