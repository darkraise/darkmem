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
          event.toast && "border-destructive-edge/45 bg-destructive-solid/5",
        ),
      })}
    >
      <span className="border-border bg-muted text-muted-foreground rounded-sm border px-1.5 py-0.5 font-mono text-xs tracking-wide whitespace-nowrap">
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
        <span className="border-destructive-edge/55 bg-destructive-solid/10 text-destructive-text inline-flex items-center gap-1 rounded-full border border-dashed px-2 py-0.5 font-mono text-xs whitespace-nowrap">
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
      <ModuleSurface
        title="Activity — live feed"
        state="populated"
        actions={
          <span className="text-success-text inline-flex items-center gap-1.5 font-mono text-sm">
            <span aria-hidden className="bg-success-solid h-1.5 w-1.5 rounded-full" />
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
            description="Reopen Activity to retry."
          />
        ) : filtered.length === 0 && !isLoading ? (
          <EmptyState
            kind="empty"
            icon={Activity}
            title={
              category === "all"
                ? "No recent events"
                : `No recent ${category} events`
            }
            description="Older events are in the Day drill."
          />
        ) : (
          filtered.map((event) => <FeedRow key={event.id} event={event} />)
        )}
      </ModuleSurface>
    </div>
  )
}
