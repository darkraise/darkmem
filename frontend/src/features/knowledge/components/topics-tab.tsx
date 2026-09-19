import {
  BadgeCheck,
  MapPin,
  Sparkles,
  Tags,
  TrendingUp,
  Users,
  Waypoints,
  X,
} from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { ProjectChooser } from "@/components/app-chrome"
import { EmptyState, listItemClass, useDetailLevel } from "@/components/darkmem"
import { PRIOR_DISMISSED_NOTE } from "@/demo/data-exports"
import { useProjects } from "@/hooks/api"
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"
import {
  useTopics,
  type PinSuggestionRowData,
  type TopicDiffRowData,
  type TopicRowData,
} from "../use-topics"
import { ListSurface } from "./list-surface"

// This tab renders NO verification badge and NO layer chip: a community
// and a pin suggestion are organizational views of what memory contains,
// never a verified claim — those belong to Facts/Articles.

/** The four report states, said plainly. `pending` and `skipped` are not the
 *  same sentence: one resolves later, the other never will, and collapsing
 *  them is how a topic shows a permanent spinner. */
const REPORT_NOTE: Record<string, string> = {
  pending: "not generated yet",
  skipped: "too small for a report — this one will not get one",
  failed: "generation failed; it will be retried",
}

function reportNote(status: string): string {
  return REPORT_NOTE[status] ?? "no report"
}

function CommunityCard({
  topic,
  diff,
}: {
  topic: TopicRowData
  diff: TopicDiffRowData | undefined
}) {
  const level = useDetailLevel((s) => s.level)
  return (
    <div className={listItemClass({ className: "space-y-2 p-2.5" })}>
      <div className="flex flex-wrap items-center gap-2">
        <Waypoints
          aria-hidden
          className="text-muted-foreground h-4 w-4 shrink-0"
        />
        <span className="text-sm font-semibold">{topic.label}</span>
        {diff && (
          <Badge variant="outline" size="sm" className="font-mono uppercase">
            {diff.status}
          </Badge>
        )}
        <span className="text-muted-foreground ml-auto flex gap-3 font-mono text-sm whitespace-nowrap">
          <span>{topic.memberCount} members</span>
          {topic.impact && <span>impact: {topic.impact}</span>}
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {topic.dominantEntities.map((entity) => (
          <Badge
            key={entity}
            variant="secondary"
            size="sm"
            className="font-mono"
          >
            {entity}
          </Badge>
        ))}
      </div>
      <div className="border-border border-l-2 border-dashed pl-2.5">
        <p className="text-muted-foreground text-sm">
          <span className="mr-1.5 font-mono text-xs tracking-wide uppercase not-italic">
            report
          </span>
          {topic.reportStatus === "ready" && topic.report ? (
            <span className="italic">{topic.report}</span>
          ) : (
            reportNote(topic.reportStatus)
          )}
        </p>
      </div>
      {/* The cross-run arithmetic is detail, not honesty: the status badge
          above already says what changed, and this only shows the counts it
          was derived from. */}
      {level === "advanced" && diff && diff.priorMemberCount != null && (
        <p className="text-muted-foreground font-mono text-sm">
          previous run: {diff.priorMemberCount} members
        </p>
      )}
    </div>
  )
}

function PinSuggestionCard({
  suggestion,
  onDecide,
}: {
  suggestion: PinSuggestionRowData
  onDecide: (subjectKey: string, decision: "accepted" | "dismissed") => void
}) {
  const level = useDetailLevel((s) => s.level)
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
        <MapPin
          aria-hidden
          className="text-muted-foreground h-4 w-4 shrink-0"
        />
        <span className="font-mono text-sm font-semibold">
          {suggestion.subject}
        </span>
        <Badge
          variant="outline"
          size="sm"
          className="ml-auto gap-1 border-dashed font-mono uppercase"
        >
          {suggestion.why === "new" ? (
            <Sparkles aria-hidden className="h-3 w-3" />
          ) : (
            <TrendingUp aria-hidden className="h-3 w-3" />
          )}
          {suggestion.why}
        </Badge>
      </div>
      <p className="text-muted-foreground text-sm">
        supporting community:{" "}
        <b className="text-foreground font-semibold">
          {suggestion.supportingCommunity}
        </b>
      </p>
      <div className="flex flex-wrap gap-4 text-sm">
        <span className="flex items-center gap-1.5">
          <Users aria-hidden className="text-muted-foreground h-3.5 w-3.5" />
          {suggestion.memberCount} members
        </span>
        <span className="flex items-center gap-1.5">
          <BadgeCheck
            aria-hidden
            className="text-muted-foreground h-3.5 w-3.5"
          />
          anchors {suggestion.anchoredFactCount} verified facts
        </span>
      </div>
      {level === "advanced" && (
        <p className="text-muted-foreground font-mono text-sm">
          subject key: {suggestion.subjectKey}
        </p>
      )}
      <div className="border-border flex flex-wrap gap-2 border-t border-dashed pt-2">
        {/* Accept pins a subject; it never auto-creates an article. Both
            verbs key on the subject key, never on a community id. */}
        <Button onClick={() => onDecide(suggestion.subjectKey, "accepted")}>
          <MapPin className="mr-1.5 size-3.5" />
          Accept — pin subject
        </Button>
        <Button
          variant="outline"
          onClick={() => onDecide(suggestion.subjectKey, "dismissed")}
        >
          <X className="mr-1.5 size-3.5" />
          Dismiss
        </Button>
      </div>
    </div>
  )
}

/** Topic detection runs per project, so the all-projects scope has no topic
 *  set to show; it offers the projects instead. */
export function TopicsTab() {
  const project = useProjectStore((s) => s.activeProject)
  return project === ALL_PROJECTS ? (
    <TopicsProjectChooser />
  ) : (
    <TopicsForProject key={project} project={project} />
  )
}

function TopicsProjectChooser() {
  const setProject = useProjectStore((s) => s.setProject)
  const { data, isLoading, isError } = useProjects()
  if (isError) {
    return (
      <p className="text-destructive text-sm">
        Projects could not be loaded — a failed read, not an empty corpus.
      </p>
    )
  }
  if (isLoading) return null
  return (
    <ProjectChooser
      icon={Tags}
      heading="Topics open one project at a time"
      description="Topics are detected per project. Pick one to see its communities; the project switcher in the header changes it later."
      projects={(data ?? [])
        .filter((p) => p.kind !== "personal" && p.memory_count > 0)
        .map((p) => ({ name: p.name, count: p.memory_count }))}
      noun={{ one: "memory", many: "memories" }}
      emptyTitle="No project holds memories yet"
      emptyDescription="Topics are detected from memories; capture some and a project appears here."
      onChoose={setProject}
    />
  )
}

export function TopicsForProject({ project }: { project: string }) {
  const { topics, suggestions, diff, lastRun, loading, error, decide } =
    useTopics(project)

  const diffByLabel = new Map(diff.map((entry) => [entry.label, entry]))
  const open = suggestions.filter((s) => s.decision == null)

  return (
    <div className="space-y-4">
      <div className="border-border flex flex-wrap items-center gap-2.5 border-b border-dashed pb-3">
        <span className="text-sm font-semibold">Leiden communities</span>
        <span className="text-muted-foreground ml-auto font-mono text-sm">
          last detection run: {lastRun ?? "not reported"}
        </span>
      </div>

      {error && (
        <div className="border-border text-muted-foreground rounded-md border border-dashed p-2.5 text-sm">
          Topics could not be loaded: {error.message}
        </div>
      )}

      <ListSurface
        title={`Topics — project: ${project}`}
        populated={topics.length > 0}
        meta={loading ? "loading" : `${topics.length} communities`}
      >
        {topics.length > 0 ? (
          topics.map((topic) => (
            <CommunityCard
              key={topic.label}
              topic={topic}
              diff={diffByLabel.get(topic.label)}
            />
          ))
        ) : (
          <EmptyState
            kind="empty"
            icon={Waypoints}
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
            on the stable dominant-entity subject key, never the row's id. */}
        {suggestions.map((suggestion) => (
          <PinSuggestionCard
            key={suggestion.subjectKey}
            suggestion={suggestion}
            onDecide={decide}
          />
        ))}
        {suggestions.length === 0 && (
          <EmptyState
            kind="empty"
            icon={MapPin}
            title="Nothing to pin yet"
            description="A subject is suggested once its community is new or growing and it already anchors verified facts. None qualify in this project right now."
          />
        )}
        <div className="bg-muted/30 text-muted-foreground flex items-center gap-2 rounded-md px-2.5 py-2 text-sm">
          <X aria-hidden className="h-4 w-4 shrink-0" />
          {PRIOR_DISMISSED_NOTE}
        </div>
      </ListSurface>
    </div>
  )
}
