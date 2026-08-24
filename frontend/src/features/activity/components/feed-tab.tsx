import { useState } from "react"
import { ArrowRight, Bell, Activity } from "lucide-react"
import {
  EmptyState,
  LayerChip,
  listItemClass,
  VerificationBadge,
} from "@/components/darkmem"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import { cn } from "darkraise-ui/lib"
import { FEED_CATEGORIES } from "@/demo/activity"
import type { FeedCategory } from "@/features/activity/types"
import { DEMO } from "@/lib/demo-flag"
import { ModuleSurface } from "./module-surface"
import { useFeed, type FeedRowData } from "../use-feed"

function FeedRow({ event }: { event: FeedRowData }) {
  return (
    <div
      className={listItemClass({
        className: cn(
          "flex flex-wrap items-center gap-2.5 px-3 py-2",
          event.toast && "border-destructive/45 bg-destructive/5",
        ),
      })}
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
        {event.timeLabel}
      </span>
    </div>
  )
}

export function FeedTab() {
  const { events, isLoading, isError } = useFeed()
  const [category, setCategory] = useState<FeedCategory | "all">("all")
  const filtered =
    category === "all" ? events : events.filter((e) => e.category === category)

  return (
    <div className="space-y-4">
      <p className="text-muted-foreground max-w-4xl text-sm">
        The recent slice of the durable{" "}
        <code className="font-mono">events</code> substrate — captures, pipeline
        outcomes, verification changes, consolidation, and repo syncs. This list
        refreshes on a short poll; for the authoritative reconstruction of one
        object's history or a calendar day, use the timeline or the day
        drill-down, both reading the same substrate directly, never a
        client-side count of what this page happened to fetch.
      </p>
      <ModuleSurface
        title="Activity — live feed"
        state={
          isLoading ? "empty" : filtered.length > 0 ? "populated" : "empty"
        }
        meta="/activity"
        actions={
          <span className="text-success inline-flex items-center gap-1.5 font-mono text-sm">
            <span aria-hidden className="bg-success h-1.5 w-1.5 rounded-full" />
            {DEMO ? "connected" : "polling every 5s"}
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
        {isError ? (
          <EmptyState
            kind="failed"
            title="Couldn't load the feed"
            description="The /events request failed — this is an error state, not an empty feed. Retry by reopening Activity."
          />
        ) : filtered.length === 0 ? (
          <EmptyState
            kind="empty"
            icon={Activity}
            title={
              category === "all"
                ? "No recent events"
                : `No recent ${category} events`
            }
            description={`The feed shows the ${events.length} most recent events substrate rows. For history further back, use the day drill-down, which reads the durable events substrate directly rather than this bounded page.`}
          />
        ) : (
          filtered.map((event) => <FeedRow key={event.id} event={event} />)
        )}
      </ModuleSurface>
    </div>
  )
}
