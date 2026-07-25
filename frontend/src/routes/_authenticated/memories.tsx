import { useMemo, useState } from "react"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ChevronDown, Inbox, Plus, Search, SearchX, X } from "lucide-react"
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
import { PageHeader } from "darkraise-ui/layout"
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

export const Route = createFileRoute("/_authenticated/memories")({
  component: MemoriesPage,
})

const BROWSE_PAGE = 50

const CONTEXT_OPTIONS = ["env=prod", "env=dev"]
const CONTEXT_NONE = "__none__"

function MemoryRow({
  memory,
  trace,
  expanded,
  onToggleTrace,
}: {
  memory: DemoMemory
  trace?: MemoryTrace
  expanded?: boolean
  onToggleTrace?: () => void
}) {
  return (
    <div className="border-border rounded-md border p-2.5">
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

function MemoriesPage() {
  const memories = useDemoMemories()

  const [query, setQuery] = useState("")
  const [scope, setScope] = useState("all")
  const [context, setContext] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [browseLimit, setBrowseLimit] = useState(BROWSE_PAGE)
  const [createOpen, setCreateOpen] = useState(false)

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

  const scopeLabel = scope === "all" ? "all projects" : scope
  const shownCount = searching
    ? outcome!.results.length
    : Math.min(browseLimit, browseRows.length)
  const matchCount = searching ? outcome!.totalMatches : browseRows.length

  const clearSearch = () => {
    setQuery("")
    setExpandedId(null)
  }

  return (
    <div className="space-y-4 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4 gap-y-2">
        <PageHeader
          title="Memories"
          description={`${memories.length.toLocaleString()} captured — the L0 capture-and-search surface`}
        />
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="mr-2 size-4" />
          Create memory
        </Button>
      </div>

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

      <div className="border-border bg-card overflow-hidden rounded-lg border">
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
              {browseRows.slice(0, browseLimit).map((memory) => (
                <MemoryRow key={memory.id} memory={memory} />
              ))}
              {browseRows.length > browseLimit && (
                <Button
                  variant="outline"
                  className="self-center"
                  onClick={() => setBrowseLimit((n) => n + BROWSE_PAGE)}
                >
                  Load more
                </Button>
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

      <MemoryEditorDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        projects={projects}
        defaultProject={scope === "all" ? undefined : scope}
      />
    </div>
  )
}
