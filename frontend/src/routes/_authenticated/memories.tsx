import { useEffect, useMemo, useRef, useState } from "react"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  Brain,
  ChevronDown,
  History,
  Inbox,
  Loader2,
  Plus,
  Search,
  SearchX,
  X,
} from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { Input } from "darkraise-ui/components/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { PageChrome } from "@/components/app-chrome"
import { cn } from "darkraise-ui/lib"
import { relativeTime } from "@/lib/format"
import { useDemoMemories } from "@/demo/hooks"
import { distinctProjects, searchDemoMemories } from "@/demo/memories"
import type { DemoMemory, MemoryTrace } from "@/demo/types"
import {
  ExclusionStrip,
  LayerChip,
  VerificationBadge,
  WhyRetrievedTrace,
} from "@/components/darkmem"
import { LifecycleBadge } from "@/features/memories/components/lifecycle-badge"
import { MemoryEditorDialog } from "@/features/memories/components/memory-editor-dialog"
import {
  groupMemoriesByDay,
  type MemoryTimelineGroup,
} from "@/features/memories/timeline"

export const Route = createFileRoute("/_authenticated/memories")({
  component: MemoriesPage,
})

const BROWSE_PAGE = 50

const CONTEXT_OPTIONS = ["env=prod", "env=dev"]
const CONTEXT_NONE = "__none__"

const STATUS_DOT: Record<DemoMemory["status"], string> = {
  active: "bg-success",
  superseded: "bg-warning",
  deprecated: "bg-muted-foreground",
}

function MemoryRow({
  memory,
  trace,
  expanded,
  focused,
  onToggleTrace,
}: {
  memory: DemoMemory
  trace?: MemoryTrace
  expanded?: boolean
  focused?: boolean
  onToggleTrace?: () => void
}) {
  return (
    <div
      id={`memory-row-${memory.id}`}
      className={cn(
        "border-border rounded-md border p-2.5 transition-shadow",
        focused && "ring-primary/60 ring-1",
      )}
    >
      <div className="flex items-start gap-2.5">
        <div className="flex shrink-0 flex-wrap items-center gap-1.5 pt-0.5">
          <LayerChip layer={memory.layer} />
          <LifecycleBadge status={memory.status} />
          {memory.verification_status && (
            <VerificationBadge
              status={memory.verification_status}
              detail={memory.verification_detail}
            />
          )}
        </div>
        <Link
          to="/memories/$memoryId"
          params={{ memoryId: memory.id }}
          className="hover:text-primary min-w-0 flex-1 text-sm break-words transition-colors"
        >
          <span className="line-clamp-2">{memory.content}</span>
          <span className="text-muted-foreground mt-1 flex flex-wrap items-center gap-1.5">
            {memory.llm_flags?.map((flag) => (
              <Badge
                key={flag}
                variant="outline"
                size="sm"
                className="border-warning/40 text-warning"
              >
                {flag}
              </Badge>
            ))}
            {memory.tags.map((tag) => (
              <Badge key={tag} variant="secondary" size="sm">
                {tag}
              </Badge>
            ))}
          </span>
        </Link>
        <span className="text-muted-foreground shrink-0 pt-0.5 text-right font-mono text-sm">
          {relativeTime(memory.created_at)}
          <span className="block">{memory.source}</span>
        </span>
        {trace && onToggleTrace && (
          <Button
            variant="ghost"
            size="sm"
            aria-expanded={expanded}
            aria-label={expanded ? "Hide why retrieved" : "Show why retrieved"}
            className="text-muted-foreground shrink-0"
            onClick={onToggleTrace}
          >
            why?
            <ChevronDown
              aria-hidden
              className={cn(
                "ml-1 h-3.5 w-3.5 transition-transform",
                expanded && "rotate-180",
              )}
            />
          </Button>
        )}
      </div>
      {trace && expanded && (
        <WhyRetrievedTrace
          channels={trace.channels}
          rrfScore={trace.rrf_score}
          summary={trace.summary}
          className="border-border mt-2.5 border-t pt-2.5"
        />
      )}
    </div>
  )
}

/**
 * Left-rail chronological navigation over the rows currently on the
 * results surface — day buckets, most-recent first, each entry scrolls
 * its row into view. Collapses away below xl; it is navigation, not data.
 */
function TimelineRail({
  groups,
  focusedId,
  onSelect,
}: {
  groups: MemoryTimelineGroup[]
  focusedId: string | null
  onSelect: (id: string) => void
}) {
  return (
    <nav aria-label="Memory timeline" className="space-y-4">
      <span className="text-muted-foreground flex items-center gap-1.5 font-mono text-sm tracking-wide uppercase">
        <History aria-hidden className="h-3.5 w-3.5" />
        Timeline
      </span>
      {groups.map((group) => (
        <div key={group.key}>
          <span className="text-foreground/80 block text-sm font-semibold">
            {group.label}
            <span className="text-muted-foreground ml-1.5 font-mono font-normal">
              {group.entries.length}
            </span>
          </span>
          <div className="border-border mt-1.5 ml-1 space-y-0.5 border-l pl-3">
            {group.entries.map((entry) => (
              <button
                key={entry.id}
                type="button"
                onClick={() => onSelect(entry.id)}
                className={cn(
                  "relative block w-full rounded-sm px-1.5 py-1 text-left transition-colors",
                  entry.id === focusedId
                    ? "bg-primary/10"
                    : "hover:bg-muted/50",
                )}
              >
                <span
                  aria-hidden
                  className={cn(
                    "absolute top-2.5 -left-[17.5px] h-2 w-2 rounded-full border-2",
                    "border-background",
                    STATUS_DOT[entry.status],
                  )}
                />
                <span className="text-muted-foreground block font-mono text-[10px]">
                  {entry.time}
                </span>
                <span className="line-clamp-2 block text-sm leading-snug">
                  {entry.excerpt}
                </span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </nav>
  )
}

function MemoriesPage() {
  const memories = useDemoMemories()

  const [query, setQuery] = useState("")
  const [scope, setScope] = useState("all")
  const [context, setContext] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [browseLimit, setBrowseLimit] = useState(BROWSE_PAGE)
  const [loadingMore, setLoadingMore] = useState(false)
  const [focusedId, setFocusedId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const sentinelRef = useRef<HTMLDivElement | null>(null)
  const focusTimer = useRef<number | undefined>(undefined)

  const projects = useMemo(() => distinctProjects(memories), [memories])
  const searching = query.trim().length > 0

  const outcome = useMemo(
    () =>
      searching
        ? searchDemoMemories(memories, { query, project: scope, context })
        : null,
    [memories, query, scope, context, searching],
  )

  const browseRows = useMemo(() => {
    if (searching) return []
    const scoped =
      scope === "all" ? memories : memories.filter((m) => m.project === scope)
    return [...scoped].sort((a, b) => b.created_at.localeCompare(a.created_at))
  }, [memories, scope, searching])

  const visibleRows = useMemo(
    () =>
      searching
        ? outcome!.results.map((r) => r.memory)
        : browseRows.slice(0, browseLimit),
    [searching, outcome, browseRows, browseLimit],
  )

  const timelineGroups = useMemo(
    () => groupMemoriesByDay(visibleRows),
    [visibleRows],
  )

  const hasMore = !searching && browseRows.length > browseLimit

  // Infinite scroll: the sentinel near the list tail appends the next
  // browse page as it enters the viewport (with a short loading row).
  useEffect(() => {
    const el = sentinelRef.current
    if (!el || !hasMore) return
    if (typeof IntersectionObserver === "undefined") return
    let pending = false
    const observer = new IntersectionObserver(
      (entries) => {
        if (pending || !entries.some((e) => e.isIntersecting)) return
        pending = true
        setLoadingMore(true)
        window.setTimeout(() => {
          setBrowseLimit((n) => n + BROWSE_PAGE)
          setLoadingMore(false)
        }, 250)
      },
      { rootMargin: "300px 0px" },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [hasMore])

  useEffect(() => () => window.clearTimeout(focusTimer.current), [])

  const scopeLabel = scope === "all" ? "all projects" : scope
  const shownCount = searching ? outcome!.results.length : visibleRows.length
  const matchCount = searching ? outcome!.totalMatches : browseRows.length

  const clearSearch = () => {
    setQuery("")
    setExpandedId(null)
  }

  const focusRow = (id: string) => {
    document
      .getElementById(`memory-row-${id}`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" })
    setFocusedId(id)
    window.clearTimeout(focusTimer.current)
    focusTimer.current = window.setTimeout(() => setFocusedId(null), 1800)
  }

  return (
    <div className="space-y-4">
      <PageChrome
        icon={Brain}
        title="Memories"
        description={`${memories.length.toLocaleString()} captured — the L0 capture-and-search surface`}
        actions={
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 size-4" />
            Create memory
          </Button>
        }
      />

      {/* Search bar: query + the two distinct scope controls. The project
          pill is the isolation scope; the context chip declares the session
          applies_when — conflating them would silently exclude rows. */}
      <div className="flex flex-wrap items-center gap-2.5">
        <Input
          prefix={<Search aria-hidden className="h-4 w-4" />}
          placeholder="Search your memories…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setExpandedId(null)
          }}
          trailingAction={
            query ? (
              <Button
                variant="ghost"
                size="icon"
                aria-label="Clear search"
                onClick={clearSearch}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            ) : undefined
          }
          groupClassName="min-w-64 flex-1"
          aria-label="Search memories"
        />
        <Select value={scope} onValueChange={setScope}>
          <SelectTrigger className="w-44 rounded-full" aria-label="Project scope">
            <SelectValue>project: {scopeLabel}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All projects</SelectItem>
            {projects.map((p) => (
              <SelectItem key={p} value={p}>
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={context ?? CONTEXT_NONE}
          onValueChange={(v) => setContext(v === CONTEXT_NONE ? null : v)}
        >
          <SelectTrigger
            aria-label="Session context"
            className={cn(
              "w-52 rounded-full",
              context == null && "text-muted-foreground border-dashed italic",
            )}
          >
            <SelectValue>
              {context == null ? "context: not declared" : `context: ${context}`}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={CONTEXT_NONE}>not declared</SelectItem>
            {CONTEXT_OPTIONS.map((c) => (
              <SelectItem key={c} value={c}>
                {c}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[15rem_minmax(0,1fr)]">
        {/* timeline rail — sticky within the content scroll area */}
        <div className="sticky top-0 hidden max-h-[calc(100vh-8rem)] self-start overflow-y-auto pr-1 xl:block">
          {visibleRows.length > 0 && (
            <TimelineRail
              groups={timelineGroups}
              focusedId={focusedId}
              onSelect={focusRow}
            />
          )}
        </div>

        <div className="border-border bg-card min-w-0 overflow-hidden rounded-lg border">
          <div className="border-border bg-muted/30 flex flex-wrap items-center gap-2.5 border-b px-4 py-2.5">
            <span className="text-sm font-semibold">
              Results — project: {scopeLabel}
            </span>
            <span
              className={cn(
                "font-mono text-sm",
                shownCount > 0 ? "text-success" : "text-muted-foreground",
              )}
            >
              {shownCount > 0 ? "populated" : "empty"}
            </span>
            <span className="text-muted-foreground ml-auto font-mono text-sm">
              {shownCount} of {matchCount} shown
            </span>
          </div>

          <div className="flex flex-col gap-2 p-4">
            {/* Exclusion counts render even when the result list is empty —
                a silent drop is the failure the design fears most. */}
            {searching && <ExclusionStrip items={outcome!.exclusions} />}

            {searching ? (
              outcome!.results.length > 0 ? (
                outcome!.results.map(({ memory, trace }) => (
                  <MemoryRow
                    key={memory.id}
                    memory={memory}
                    trace={trace}
                    expanded={expandedId === memory.id}
                    focused={focusedId === memory.id}
                    onToggleTrace={() =>
                      setExpandedId((prev) =>
                        prev === memory.id ? null : memory.id,
                      )
                    }
                  />
                ))
              ) : (
                <EmptyState
                  icon={<SearchX aria-hidden className="h-6 w-6" />}
                  title="No matches"
                  description={`No memories match "${query.trim()}"${
                    scope === "all" ? "" : ` in project ${scope}`
                  } — clear the search or widen the scope.`}
                  action={
                    <div className="flex flex-wrap justify-center gap-2">
                      <Button variant="outline" onClick={clearSearch}>
                        Clear search
                      </Button>
                      {scope !== "all" && (
                        <Button variant="outline" onClick={() => setScope("all")}>
                          Search all projects
                        </Button>
                      )}
                    </div>
                  }
                />
              )
            ) : browseRows.length > 0 ? (
              <>
                {visibleRows.map((memory) => (
                  <MemoryRow
                    key={memory.id}
                    memory={memory}
                    focused={focusedId === memory.id}
                  />
                ))}
                {loadingMore && (
                  <div
                    role="status"
                    className="text-muted-foreground flex items-center justify-center gap-2 py-2.5 text-sm"
                  >
                    <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
                    loading more…
                  </div>
                )}
                {hasMore && <div ref={sentinelRef} aria-hidden className="h-px" />}
                {!hasMore && (
                  <p className="text-muted-foreground py-1 text-center font-mono text-sm">
                    all {browseRows.length} shown
                  </p>
                )}
              </>
            ) : memories.length === 0 ? (
              <EmptyState
                icon={<Inbox aria-hidden className="h-6 w-6" />}
                title="No memories captured yet"
                description="Capture your first one and search starts working immediately — nothing needs to be pre-configured."
                action={
                  <Button onClick={() => setCreateOpen(true)}>
                    <Plus className="mr-2 size-4" />
                    Capture your first memory
                  </Button>
                }
              />
            ) : (
              <EmptyState
                icon={<SearchX aria-hidden className="h-6 w-6" />}
                title={`No memories in project ${scope}`}
                description="This project has no memories yet — other projects do."
                action={
                  <Button variant="outline" onClick={() => setScope("all")}>
                    Show all projects
                  </Button>
                }
              />
            )}
          </div>
        </div>
      </div>

      <MemoryEditorDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        projects={projects}
        defaultProject={scope === "all" ? undefined : scope}
      />
    </div>
  )
}
