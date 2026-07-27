import { useEffect, useMemo, useRef, useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { Brain, Inbox, Loader2, Plus, Search, SearchX, X } from "lucide-react"
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
import { dayKeyToMs, localDayKey } from "@/lib/format"
import { useMainVirtualizer } from "@/lib/use-main-virtualizer"
import { isValidDay } from "@/demo/activity"
import { DEMO } from "@/demo/flag"
import { useDemoMemories } from "@/demo/hooks"
import { distinctProjects, searchDemoMemories } from "@/demo/memories"
import type { DemoMemory, MemoryTrace } from "@/demo/types"
import { ExclusionStrip } from "@/components/darkmem"
import { demoTraceToView } from "@/features/memories/use-memory-search"
import { MemoryRow } from "@/features/memories/components/memory-row"
import { MemoryEditorDialog } from "@/features/memories/components/memory-editor-dialog"
import { RealMemoriesView } from "@/features/memories/components/real-memories-view"
import { TimelineScrubber } from "@/components/timeline-scrubber"
import { buildTimelineScale, dateToFraction } from "@/lib/timeline"

export const Route = createFileRoute("/_authenticated/memories")({
  // The click-to-date contract: /memories?date=YYYY-MM-DD positions the
  // scrubber and scrolls the results to that day (heatmap cell clicks).
  validateSearch: (search: Record<string, unknown>): { date?: string } => ({
    date: isValidDay(search.date) ? search.date : undefined,
  }),
  // DEMO is fixed for the process lifetime (import.meta.env, not runtime
  // state), so branching at the component level never violates the rules
  // of hooks — the demo view keeps its own store-backed browse/scrub/seek
  // affordances untouched, and the real view is the T1.44 rebuild against
  // `/search/paginated?with_trace=true` (Ruling 5).
  component: () => (DEMO ? <DemoMemoriesPage /> : <RealMemoriesView />),
})

const BROWSE_PAGE = 50
const ROW_GAP = 8
const ROW_ESTIMATE = 84

const CONTEXT_OPTIONS = ["env=prod", "env=dev"]
const CONTEXT_NONE = "__none__"

interface MemoryListRow {
  memory: DemoMemory
  trace?: MemoryTrace
}

function DemoMemoriesPage() {
  const memories = useDemoMemories()
  const { date: dateParam } = Route.useSearch()

  const [query, setQuery] = useState("")
  const [scope, setScope] = useState("all")
  const [context, setContext] = useState<string | null>(null)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [browseLimit, setBrowseLimit] = useState(BROWSE_PAGE)
  const [loadingMore, setLoadingMore] = useState(false)
  const [focusedId, setFocusedId] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [scrubFraction, setScrubFraction] = useState(0)
  const focusTimer = useRef<number | undefined>(undefined)
  const pendingSeekId = useRef<string | null>(null)
  const handledDate = useRef<string | null>(null)
  const loadingRef = useRef(false)

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

  const rows = useMemo<MemoryListRow[]>(
    () =>
      searching
        ? outcome!.results
        : browseRows.slice(0, browseLimit).map((memory) => ({ memory })),
    [searching, outcome, browseRows, browseLimit],
  )

  // The scrubber's axis covers the whole browse corpus, not just the loaded
  // pages — seeking past the loaded tail expands browseLimit to reach it.
  const scale = useMemo(
    () => (searching ? null : buildTimelineScale(browseRows)),
    [browseRows, searching],
  )

  const hasMore = !searching && browseRows.length > browseLimit
  // Browse mode appends one trailing status row (loading / all-shown).
  const virtualCount = rows.length + (searching ? 0 : 1)

  const { listRef, virtualizer, scrollMargin } = useMainVirtualizer({
    count: virtualCount,
    estimateSize: () => ROW_ESTIMATE,
    gap: ROW_GAP,
    getItemKey: (index) => rows[index]?.memory.id ?? "list-footer",
  })

  const virtualItems = virtualizer.getVirtualItems()
  const scrollOffset = virtualizer.scrollOffset ?? 0
  const lastRenderedIndex = virtualItems[virtualItems.length - 1]?.index ?? -1
  // The first row whose bottom edge is still below the scroll position —
  // the overscan rows above it are rendered but not on screen.
  const topIndex =
    virtualItems.find((item) => item.end > scrollOffset)?.index ??
    virtualItems[0]?.index ??
    0

  useEffect(() => () => window.clearTimeout(focusTimer.current), [])

  // Infinite scroll: reaching the last windowed row appends the next browse
  // page, with a short loading row so the append is visible rather than
  // silently doubling the scroll height. The in-flight guard is a ref, not
  // `loadingMore` — as an effect dep it would re-run the effect the moment
  // the flag is set and the cleanup would cancel the timer that sets it.
  useEffect(() => {
    if (!hasMore || loadingRef.current) return
    if (lastRenderedIndex < rows.length - 1) return
    loadingRef.current = true
    setLoadingMore(true)
    const timer = window.setTimeout(() => {
      loadingRef.current = false
      setBrowseLimit((n) => n + BROWSE_PAGE)
      setLoadingMore(false)
    }, 250)
    return () => {
      window.clearTimeout(timer)
      loadingRef.current = false
    }
  }, [hasMore, lastRenderedIndex, rows.length])

  const scopeLabel = scope === "all" ? "all projects" : scope
  const shownCount = searching ? outcome!.results.length : rows.length
  const matchCount = searching ? outcome!.totalMatches : browseRows.length

  const clearSearch = () => {
    setQuery("")
    setExpandedId(null)
  }

  const scrollRowIntoView = (id: string) => {
    const index = rows.findIndex((row) => row.memory.id === id)
    if (index === -1) return
    virtualizer.scrollToIndex(index, { align: "start" })
    setFocusedId(id)
    window.clearTimeout(focusTimer.current)
    focusTimer.current = window.setTimeout(() => setFocusedId(null), 1800)
  }

  // Jump the results surface to a calendar day: land on the newest row of
  // that day (or the nearest older day), loading more pages if the target
  // sits past the infinite-scroll tail.
  const seekToDate = (dayKey: string) => {
    if (!scale || browseRows.length === 0) return
    let idx = browseRows.findIndex(
      (m) => localDayKey(new Date(m.created_at)) <= dayKey,
    )
    if (idx === -1) idx = browseRows.length - 1
    const target = browseRows[idx]
    if (!target) return
    const clampedMs = Math.min(
      scale.newestMs,
      Math.max(scale.oldestMs, dayKeyToMs(dayKey)),
    )
    setScrubFraction(dateToFraction(scale, clampedMs))
    if (idx >= browseLimit) {
      setBrowseLimit(
        Math.ceil((idx + 1) / BROWSE_PAGE) * BROWSE_PAGE + BROWSE_PAGE,
      )
      pendingSeekId.current = target.id
    } else {
      scrollRowIntoView(target.id)
    }
  }

  // Completes a seek that had to grow browseLimit first: scroll once the
  // target row is inside the windowed range.
  useEffect(() => {
    const id = pendingSeekId.current
    if (!id || !rows.some((row) => row.memory.id === id)) return
    pendingSeekId.current = null
    requestAnimationFrame(() => scrollRowIntoView(id))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows])

  // The heatmap's click-to-date contract: ?date=YYYY-MM-DD lands the
  // timeline on that day, once per distinct value.
  useEffect(() => {
    if (!dateParam || !scale || handledDate.current === dateParam) return
    handledDate.current = dateParam
    seekToDate(dateParam)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateParam, scale])

  // Scroll → indicator sync: the topmost on-screen row dates the scrubber.
  useEffect(() => {
    if (searching || !scale) return
    const row = rows[topIndex]
    if (row) {
      setScrubFraction(dateToFraction(scale, Date.parse(row.memory.created_at)))
    }
  }, [searching, scale, rows, topIndex])

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

      <div
        className={cn(
          "grid grid-cols-1 items-start gap-5",
          !searching && scale && "lg:grid-cols-[3.5rem_minmax(0,1fr)]",
        )}
      >
        {/* time-scale scrubber — a line of time, not a list of memories */}
        {!searching && scale && (
          <div className="sticky top-2 hidden h-[calc(100vh-11rem)] self-start lg:block">
            <TimelineScrubber
              scale={scale}
              position={scrubFraction}
              onSeek={seekToDate}
            />
          </div>
        )}

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

          <div className="p-4">
            {/* Exclusion counts render even when the result list is empty —
                a silent drop is the failure the design fears most. */}
            {searching && <ExclusionStrip items={outcome!.exclusions} />}

            {rows.length > 0 ? (
              <div
                ref={listRef}
                className="relative w-full"
                style={{ height: virtualizer.getTotalSize() }}
              >
                {virtualItems.map((item) => {
                  const row = rows[item.index]
                  return (
                    <div
                      key={item.key}
                      data-index={item.index}
                      ref={virtualizer.measureElement}
                      className="absolute top-0 left-0 w-full"
                      style={{
                        transform: `translateY(${item.start - scrollMargin}px)`,
                      }}
                    >
                      {row ? (
                        <MemoryRow
                          memory={row.memory}
                          trace={row.trace ? demoTraceToView(row.trace) : undefined}
                          expanded={expandedId === row.memory.id}
                          focused={focusedId === row.memory.id}
                          onToggleTrace={
                            row.trace
                              ? () =>
                                  setExpandedId((prev) =>
                                    prev === row.memory.id
                                      ? null
                                      : row.memory.id,
                                  )
                              : undefined
                          }
                        />
                      ) : loadingMore ? (
                        <div
                          role="status"
                          className="text-muted-foreground flex items-center justify-center gap-2 py-2.5 text-sm"
                        >
                          <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
                          loading more…
                        </div>
                      ) : (
                        <p className="text-muted-foreground py-1 text-center font-mono text-sm">
                          {hasMore
                            ? `${rows.length} of ${browseRows.length} loaded`
                            : `all ${browseRows.length} shown`}
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            ) : searching ? (
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
