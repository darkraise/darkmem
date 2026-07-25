import { useEffect, useMemo, useRef, useState } from "react"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  Brain,
  ChevronDown,
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
import { dayKeyToMs, localDayKey, relativeTime } from "@/lib/format"
import { isValidDay } from "@/demo/activity"
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
import { TimelineScrubber } from "@/features/memories/components/timeline-scrubber"
import {
  buildTimelineScale,
  dateToFraction,
} from "@/features/memories/timeline"

export const Route = createFileRoute("/_authenticated/memories")({
  // The click-to-date contract: /memories?date=YYYY-MM-DD positions the
  // scrubber and scrolls the results to that day (heatmap cell clicks).
  validateSearch: (search: Record<string, unknown>): { date?: string } => ({
    date: isValidDay(search.date) ? search.date : undefined,
  }),
  component: MemoriesPage,
})

const BROWSE_PAGE = 50

const CONTEXT_OPTIONS = ["env=prod", "env=dev"]
const CONTEXT_NONE = "__none__"

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

function MemoriesPage() {
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
  const sentinelRef = useRef<HTMLDivElement | null>(null)
  const focusTimer = useRef<number | undefined>(undefined)
  const pendingSeekId = useRef<string | null>(null)
  const handledDate = useRef<string | null>(null)

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

  // The scrubber's axis covers the whole browse corpus, not just the loaded
  // pages — seeking past the loaded tail expands browseLimit to reach it.
  const scale = useMemo(
    () => (searching ? null : buildTimelineScale(browseRows)),
    [browseRows, searching],
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

  const scrollRowIntoView = (id: string) => {
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches
    document
      .getElementById(`memory-row-${id}`)
      ?.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" })
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
  // target row has actually rendered.
  useEffect(() => {
    const id = pendingSeekId.current
    if (!id || !visibleRows.some((m) => m.id === id)) return
    pendingSeekId.current = null
    requestAnimationFrame(() => scrollRowIntoView(id))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleRows])

  // The heatmap's click-to-date contract: ?date=YYYY-MM-DD lands the
  // timeline on that day, once per distinct value.
  useEffect(() => {
    if (!dateParam || !scale || handledDate.current === dateParam) return
    handledDate.current = dateParam
    seekToDate(dateParam)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dateParam, scale])

  // Scroll → indicator sync: binary-search the row at the top edge of the
  // #main-content scroll area (rows share document order with visibleRows).
  useEffect(() => {
    if (searching || !scale) return
    const container = document.getElementById("main-content")
    if (!container) return
    let raf = 0
    const sync = () => {
      raf = 0
      if (visibleRows.length === 0) return
      const topEdge = container.getBoundingClientRect().top + 120
      let lo = 0
      let hi = visibleRows.length - 1
      let found = visibleRows.length - 1
      while (lo <= hi) {
        const mid = (lo + hi) >> 1
        const row = visibleRows[mid]
        const el = row ? document.getElementById(`memory-row-${row.id}`) : null
        if (!el) break
        if (el.getBoundingClientRect().bottom >= topEdge) {
          found = mid
          hi = mid - 1
        } else {
          lo = mid + 1
        }
      }
      const current = visibleRows[found]
      if (current) {
        setScrubFraction(dateToFraction(scale, Date.parse(current.created_at)))
      }
    }
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(sync)
    }
    container.addEventListener("scroll", onScroll, { passive: true })
    sync()
    return () => {
      container.removeEventListener("scroll", onScroll)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [searching, scale, visibleRows])

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
