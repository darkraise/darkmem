import { BadgeCheck, MapPin, Sparkles, TrendingUp, Users, Waypoints, X } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { useDemoStore } from "@/demo/store"
import {
  useDemoCommunities,
  useDemoLastDetectionRun,
  useDemoPinSuggestions,
} from "@/demo/hooks"
import type { DemoCommunity, DemoPinSuggestion } from "@/demo/types"
import { PRIOR_DISMISSED_NOTE } from "@/demo/data-exports"
import { ListSurface } from "./list-surface"

// This tab renders NO verification badge and NO layer chip: a community
// and a pin suggestion are organizational views of what memory contains,
// never a verified claim — those belong to Facts/Articles.
function CommunityCard({ community }: { community: DemoCommunity }) {
  return (
    <div className="border-border space-y-2 rounded-md border p-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <Waypoints aria-hidden className="text-muted-foreground h-4 w-4 shrink-0" />
        <span className="text-sm font-semibold">{community.label}</span>
        <span className="text-muted-foreground ml-auto flex gap-3 font-mono text-sm whitespace-nowrap">
          <span>{community.member_count} members</span>
          <span>impact: {community.impact}</span>
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {community.dominant_entities.map((entity) => (
          <Badge key={entity} variant="secondary" size="sm" className="font-mono">
            {entity}
          </Badge>
        ))}
      </div>
      <div className="border-border border-l-2 border-dashed pl-2.5">
        <p className="text-muted-foreground text-sm">
          <span className="mr-1.5 font-mono text-[10px] tracking-wide uppercase not-italic">
            report
          </span>
          {community.report ? (
            <span className="italic">{community.report}</span>
          ) : (
            community.report_pending
          )}
        </p>
      </div>
      {community.note && (
        <p className="text-muted-foreground text-sm">{community.note}</p>
      )}
    </div>
  )
}

function PinSuggestionCard({
  suggestion,
  onDecide,
}: {
  suggestion: DemoPinSuggestion
  onDecide: (id: string, decision: "accepted" | "dismissed") => void
}) {
  if (suggestion.decision) {
    const accepted = suggestion.decision === "accepted"
    const Icon = accepted ? BadgeCheck : X
    return (
      <div className="bg-muted/30 text-muted-foreground flex items-center gap-2 rounded-md px-2.5 py-2 text-sm">
        <Icon aria-hidden className="h-4 w-4 shrink-0" />
        <span>
          <b className="text-foreground font-semibold">{suggestion.subject}</b>{" "}
          {accepted
            ? "pinned — eligible for synthesis on the next salience pass; the article itself still has to be grounded from verified facts."
            : "dismissed — recorded against the subject so later detection diffs suppress the suggestion, not merely hidden client-side."}
        </span>
      </div>
    )
  }
  return (
    <div className="border-border bg-muted/10 space-y-2 rounded-md border border-dashed p-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <MapPin aria-hidden className="text-muted-foreground h-4 w-4 shrink-0" />
        <span className="font-mono text-sm font-semibold">
          {suggestion.subject}
        </span>
        <Badge
          variant="outline"
          size="sm"
          className="ml-auto gap-1 border-dashed font-mono uppercase"
        >
          {suggestion.reason_kind === "new" ? (
            <Sparkles aria-hidden className="h-3 w-3" />
          ) : (
            <TrendingUp aria-hidden className="h-3 w-3" />
          )}
          {suggestion.reason}
        </Badge>
      </div>
      <p className="text-muted-foreground text-sm">
        supporting community:{" "}
        <b className="text-foreground font-semibold">
          {suggestion.supporting_community}
        </b>
      </p>
      <div className="flex flex-wrap gap-4 text-sm">
        <span className="flex items-center gap-1.5">
          <Users aria-hidden className="text-muted-foreground h-3.5 w-3.5" />
          {suggestion.member_count} members
        </span>
        <span className="flex items-center gap-1.5">
          <BadgeCheck aria-hidden className="text-muted-foreground h-3.5 w-3.5" />
          anchors {suggestion.anchored_fact_count} verified facts
        </span>
      </div>
      <div className="border-border flex flex-wrap gap-2 border-t border-dashed pt-2">
        {/* Accept pins a subject; it never auto-creates an article. */}
        <Button size="sm" onClick={() => onDecide(suggestion.id, "accepted")}>
          <MapPin className="mr-1.5 size-3.5" />
          Accept — pin subject
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={() => onDecide(suggestion.id, "dismissed")}
        >
          <X className="mr-1.5 size-3.5" />
          Dismiss
        </Button>
      </div>
    </div>
  )
}

export function TopicsTab() {
  const communities = useDemoCommunities()
  const suggestions = useDemoPinSuggestions()
  const lastRun = useDemoLastDetectionRun()
  const decide = useDemoStore((s) => s.decidePinSuggestion)

  const open = suggestions.filter((s) => s.decision == null)

  return (
    <div className="space-y-4">
      <div className="border-border flex flex-wrap items-center gap-2.5 border-b border-dashed pb-3">
        <span className="text-sm font-semibold">Leiden communities</span>
        <span className="text-muted-foreground ml-auto font-mono text-sm">
          last detection run: {lastRun}
        </span>
      </div>

      <ListSurface
        title="Topics — project: darkmem"
        populated={communities.length > 0}
        meta={`${communities.length} communities`}
      >
        {communities.length > 0 ? (
          communities.map((community) => (
            <CommunityCard key={community.id} community={community} />
          ))
        ) : (
          <EmptyState
            icon={<Waypoints aria-hidden className="h-6 w-6" />}
            title="No topics detected yet"
            description="Community detection clusters memories once enough of them share entities — this project has not accumulated enough yet, or the detection job has not completed its first run. Nothing here means not yet, not broken."
          />
        )}
      </ListSurface>

      <ListSurface
        title="Pin suggestions"
        populated={open.length > 0}
        meta={`${open.length} open`}
      >
        {/* Community ids churn per detection run — every suggestion keys
            on the stable dominant-entity label, never the row's id. */}
        {suggestions.map((suggestion) => (
          <PinSuggestionCard
            key={suggestion.id}
            suggestion={suggestion}
            onDecide={decide}
          />
        ))}
        <div className="bg-muted/30 text-muted-foreground flex items-center gap-2 rounded-md px-2.5 py-2 text-sm">
          <X aria-hidden className="h-4 w-4 shrink-0" />
          {PRIOR_DISMISSED_NOTE}
        </div>
      </ListSurface>
    </div>
  )
}
