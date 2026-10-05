import { useEffect, useRef, useState } from "react"
import { Brain, Loader2, Plus, Search, X } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "@/components/darkmem"
import { Input } from "darkraise-ui/components/input"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import { ExclusionStrip } from "@/components/darkmem"
import { useMainVirtualizer } from "@/lib/use-main-virtualizer"
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"
import { useMemorySearchPage } from "../use-memory-search"
import { CreateMemoryDialog } from "./create-memory-dialog"
import { MemoryResultsHeader } from "./memory-results-header"
import { MemoryRow, type MemoryRowData } from "./memory-row"

const PAGE = 50
const ROW_GAP = 8
const ROW_ESTIMATE = 84

/**
 * The real-backend counterpart of the demo Memories page (Ruling 5's
 * DEMO ? demo : real split, at the component level rather than inside one
 * hook — `DEMO` is fixed for the process lifetime, so the branch never
 * toggles mid-session and never violates the rules of hooks). A real
 * `Memory` row never carries a verification badge — that ladder belongs to
 * Facts, not raw memories.
 */
export function RealMemoriesView({
  initialQuery = "",
}: {
  /** The route's ?q= value: the page opens with it typed. */
  initialQuery?: string
} = {}) {
  const [query, setQuery] = useState(initialQuery)
  const activeProject = useProjectStore((s) => s.activeProject)
  const setScope = useProjectStore((s) => s.setProject)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [limit, setLimit] = useState(PAGE)
  const [createOpen, setCreateOpen] = useState(false)
  const loadingRef = useRef(false)

  const { rows, total, exclusions, isLoading, isError, isFetching } =
    useMemorySearchPage({
      query,
      project: activeProject ?? "all",
      status: ["active", "superseded"],
      limit,
    })

  const hasMore = rows.length < total
  const virtualCount = rows.length + 1

  const { listRef, virtualizer, scrollMargin } = useMainVirtualizer({
    count: virtualCount,
    estimateSize: () => ROW_ESTIMATE,
    gap: ROW_GAP,
    getItemKey: (index) => rows[index]?.memory.id ?? "list-footer",
  })

  const virtualItems = virtualizer.getVirtualItems()
  const lastRenderedIndex = virtualItems[virtualItems.length - 1]?.index ?? -1

  // Infinite scroll: reaching the last windowed row grows the page size,
  // which re-runs the real paginated query (offset stays 0 — a bigger
  // `limit` is simplest against a route that already returns `total`).
  useEffect(() => {
    if (!hasMore || isFetching || loadingRef.current) return
    if (lastRenderedIndex < rows.length - 1) return
    loadingRef.current = true
    setLimit((n) => n + PAGE)
  }, [hasMore, isFetching, lastRenderedIndex, rows.length])

  useEffect(() => {
    loadingRef.current = false
  }, [rows.length])

  useEffect(() => {
    setLimit(PAGE)
  }, [activeProject])

  const searching = query.trim().length > 0

  const clearSearch = () => {
    setQuery("")
    setExpandedId(null)
    setLimit(PAGE)
  }

  const toRowData = (
    memory: (typeof rows)[number]["memory"],
  ): MemoryRowData => ({
    id: memory.id,
    content: memory.content,
    tags: memory.tags,
    flags: memory.flags,
    source: memory.source,
    created_at: memory.created_at,
    status: memory.status,
  })

  return (
    <div className="space-y-4">
      <PageChrome
        icon={Brain}
        title="Memories"
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 size-4" />
            Create memory
          </Button>
        }
      />

      <div className="flex flex-wrap items-center gap-2.5">
        <Input
          prefix={<Search aria-hidden className="h-4 w-4" />}
          placeholder="Search your memories…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setExpandedId(null)
            setLimit(PAGE)
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
      </div>

      <div className="border-border bg-card min-w-0 overflow-hidden rounded-lg border">
        <MemoryResultsHeader shown={rows.length} total={total} />

        <div className="space-y-3 p-4">
          <ExclusionStrip items={exclusions} />

          {isLoading ? (
            <div
              className="space-y-2"
              role="status"
              aria-label="Loading memories"
            >
              <Skeleton className="h-[84px] w-full rounded-md" />
              <Skeleton className="h-[84px] w-full rounded-md" />
              <Skeleton className="h-[84px] w-full rounded-md" />
            </div>
          ) : isError ? (
            <EmptyState
              kind="filtered"
              scope="page"
              title="Search failed"
              description="The search request failed. Try again in a moment."
            />
          ) : rows.length > 0 ? (
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
                        memory={toRowData(row.memory)}
                        trace={row.trace}
                        expanded={expandedId === row.memory.id}
                        onToggleTrace={
                          row.trace
                            ? () =>
                                setExpandedId((prev) =>
                                  prev === row.memory.id ? null : row.memory.id,
                                )
                            : undefined
                        }
                      />
                    ) : isFetching ? (
                      <div
                        role="status"
                        className="text-muted-foreground flex items-center justify-center gap-2 py-2.5 text-sm"
                      >
                        <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
                        loading more…
                      </div>
                    ) : hasMore ? (
                      <p className="text-muted-foreground py-1 text-center font-mono text-sm">
                        {rows.length} of {total} loaded
                      </p>
                    ) : // A complete list says nothing at its foot: the header
                    // already reads "N of N shown".
                    null}
                  </div>
                )
              })}
            </div>
          ) : searching ? (
            <EmptyState
              kind="filtered"
              scope="page"
              title="No matches"
              description={`No memories match "${query.trim()}"${
                activeProject ? ` in project ${activeProject}` : ""
              } — clear the search or widen the scope.`}
              action={
                <Button variant="outline" onClick={clearSearch}>
                  Clear search
                </Button>
              }
            />
          ) : activeProject ? (
            <EmptyState
              kind="empty"
              icon={Brain}
              scope="page"
              title={`No memories in project ${activeProject}`}
              description="This project has no memories yet — other projects might."
              action={
                <Button
                  variant="outline"
                  onClick={() => setScope(ALL_PROJECTS)}
                >
                  Show all projects
                </Button>
              }
            />
          ) : (
            <EmptyState
              kind="empty"
              icon={Brain}
              scope="page"
              title="No memories captured yet"
              description="Capture your first one to start searching."
              action={
                <Button onClick={() => setCreateOpen(true)}>
                  <Plus className="mr-2 size-4" />
                  Capture your first memory
                </Button>
              }
            />
          )}
        </div>
      </div>

      <CreateMemoryDialog open={createOpen} onOpenChange={setCreateOpen} />
    </div>
  )
}
