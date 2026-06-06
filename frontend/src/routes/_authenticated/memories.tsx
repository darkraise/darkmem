import { useState, useMemo, useEffect, useRef, useCallback } from "react"
import { createFileRoute } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { DataTable, DataTableSkeleton } from "darkraise-ui/data-table"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Checkbox } from "darkraise-ui/components/checkbox"
import { MultiSelect } from "darkraise-ui/components/multi-select"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "darkraise-ui/components/sheet"
import { PageHeader } from "darkraise-ui/layout"
import { Plus, Search, X, Trash2 } from "lucide-react"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "darkraise-ui/components/sonner"
import {
  TagsInput,
  TagsInputControl,
  TagsInputInput,
  TagsInputItem,
  TagsInputItemPreview,
  TagsInputItemText,
  TagsInputItemDeleteTrigger,
} from "darkraise-ui/components/tags-input"
import { usePaginatedSearch, useDeleteMemory, useBulkDeleteMemory } from "@/hooks/api"
import type { Memory } from "@/hooks/api"
import { apiFetch } from "@/lib/api"
import { relativeTime } from "@/lib/format"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "darkraise-ui/components/alert-dialog"
import { CreateMemoryDialog } from "@/features/memories/components/create-memory-dialog"
import {
  MemoryCommandPalette,
  type CommandPaletteFilter,
} from "@/features/memories/components/memory-command-palette"

interface MemoriesSearch {
  focus?: string
}

export const Route = createFileRoute("/_authenticated/memories")({
  validateSearch: (search: Record<string, unknown>): MemoriesSearch => ({
    focus: typeof search.focus === "string" ? search.focus : undefined,
  }),
  component: MemoriesPage,
})

const PAGE_SIZE = 50

const SOURCE_COLORS: Record<string, string> = {
  "claude-code": "#58a6ff",
  "mcp-test": "#3fb950",
  api: "#d2a8ff",
  "rest-test": "#ffa657",
  dashboard: "#f778ba",
}

// Cap bulk concurrency. Each delete runs an independent server-side
// pipeline cleanup; a 50-item bulk shouldn't open 50 concurrent backend
// sessions.
const BULK_CONCURRENCY = 5
async function runInBatches<T>(
  items: T[],
  worker: (item: T) => Promise<unknown>,
) {
  let firstError: unknown = null
  let succeeded = 0
  for (let i = 0; i < items.length; i += BULK_CONCURRENCY) {
    const slice = items.slice(i, i + BULK_CONCURRENCY)
    const results = await Promise.allSettled(slice.map(worker))
    for (const r of results) {
      if (r.status === "fulfilled") succeeded += 1
      else if (firstError === null) firstError = r.reason
    }
  }
  return { succeeded, firstError }
}

function MemoriesPage() {
  const { focus: focusId } = Route.useSearch()
  const navigate = Route.useNavigate()

  // Filter state
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [sourceFilters, setSourceFilters] = useState<string[]>([])
  const [typeFilters, setTypeFilters] = useState<string[]>([])
  const [tagFilters, setTagFilters] = useState<string[]>([])
  const [freeQuery, setFreeQuery] = useState("")

  // Pagination + selection state
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [detailMemory, setDetailMemory] = useState<Memory | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false)
  const [confirmBulkArchive, setConfirmBulkArchive] = useState(false)

  const hasActiveFilter = Boolean(
    freeQuery || sourceFilters.length || tagFilters.length || typeFilters.length,
  )

  // Multi-value filters go to the server (source_any / memory_type_any), so the
  // page and the total count reflect the same query. Previously multiple
  // selections were narrowed client-side over the current page only, while the
  // count came from the unfiltered query — a misleading mismatch.
  const { data, isLoading } = usePaginatedSearch({
    query: freeQuery || undefined,
    tags_any: tagFilters.length > 0 ? tagFilters : undefined,
    source_any: sourceFilters.length > 0 ? sourceFilters : undefined,
    memory_type_any: typeFilters.length > 0 ? typeFilters : undefined,
    limit: PAGE_SIZE,
    offset,
  })
  // The unfiltered "N total" count only differs from `data.total` when a filter
  // is active; skip the second query otherwise so a delete refetches one query,
  // not two. ``unfilteredTotal`` falls back to ``total`` when this is disabled.
  const { data: unfilteredData } = usePaginatedSearch(
    { limit: 1, offset: 0 },
    { enabled: hasActiveFilter },
  )
  const deleteMemory = useDeleteMemory()
  const bulkDelete = useBulkDeleteMemory()
  const qc = useQueryClient()

  const memories: Memory[] = data?.items ?? []

  const total = data?.total ?? 0
  // The header shows the true library size: the unfiltered count when a filter is
  // active (undefined until that query resolves, so we don't briefly mislabel the
  // filtered total as "total"), otherwise the page total.
  const unfilteredTotal = hasActiveFilter ? unfilteredData?.total : total
  const pageStart = offset + 1
  const pageEnd = Math.min(offset + PAGE_SIZE, total)

  const [highlightId, setHighlightId] = useState<string | null>(null)
  const rowRefs = useRef<Map<string, HTMLDivElement>>(new Map())

  const processedFocusRef = useRef<string | null>(null)
  useEffect(() => {
    // Run once per focusId: the effect clears the `focus` search param (which
    // re-runs the loader) and depends on `memories`, so without this guard a
    // refetch re-triggers the scroll/highlight and the timer churns.
    if (!focusId || focusId === processedFocusRef.current || memories.length === 0)
      return
    const target = memories.find((m) => m.id === focusId)
    if (!target) return
    const node = rowRefs.current.get(focusId)
    if (!node) return
    processedFocusRef.current = focusId
    node.scrollIntoView({ behavior: "smooth", block: "center" })
    setHighlightId(focusId)
    const timer = setTimeout(() => setHighlightId(null), 1500)
    navigate({
      search: (prev) => ({ ...prev, focus: undefined }),
      replace: true,
    })
    return () => clearTimeout(timer)
  }, [focusId, memories, navigate])

  // ⌘K / Ctrl+K opens palette
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        setPaletteOpen((prev) => !prev)
      }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [])

  const distinctSources = useMemo(() => {
    const set = new Set((data?.items ?? []).map((m) => m.source))
    return Array.from(set).sort()
  }, [data?.items])

  const distinctTypes = useMemo(() => {
    const set = new Set(
      (data?.items ?? []).map((m) => m.memory_type).filter(Boolean) as string[],
    )
    return Array.from(set).sort()
  }, [data?.items])

  const resetPagination = () => {
    setOffset(0)
    setSelected(new Set())
  }

  const handlePaletteSubmit = useCallback((filter: CommandPaletteFilter) => {
    setFreeQuery(filter.query)
    if (filter.sources.length > 0) setSourceFilters(filter.sources)
    if (filter.types.length > 0) setTypeFilters(filter.types)
    if (filter.tags.length > 0) setTagFilters(filter.tags)
    resetPagination()
  }, [])

  const clearFilters = () => {
    setFreeQuery("")
    setSourceFilters([])
    setTypeFilters([])
    setTagFilters([])
    resetPagination()
  }

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selected.size === memories.length && memories.length > 0) {
      setSelected(new Set())
    } else {
      setSelected(new Set(memories.map((m) => m.id)))
    }
  }

  const handleDelete = useCallback((id: string) => {
    setConfirmDeleteId(id)
  }, [])

  const confirmDelete = useCallback(
    (id: string) => {
      deleteMemory.mutate(id, {
        onSuccess: () => {
          setSelected((prev) => {
            const next = new Set(prev)
            next.delete(id)
            return next
          })
          if (detailMemory?.id === id) setDetailMemory(null)
          // Invalidation handled by useDeleteMemory's onSuccess (both keys).
        },
      })
    },
    [deleteMemory, detailMemory, qc],
  )

  const handleBulkDelete = () => setConfirmBulkDelete(true)

  const confirmBulkDeleteAction = async () => {
    const ids = Array.from(selected)
    try {
      // One request; the server deletes sequentially so concurrent graph
      // cleanups can't deadlock on shared entity rows.
      const { deleted, not_found } = await bulkDelete.mutateAsync(ids)
      setSelected(new Set())
      setDetailMemory(null)
      const missing = not_found?.length ?? 0
      toast.success(
        missing
          ? `Deleted ${deleted} memories (${missing} already gone)`
          : `Deleted ${deleted} memories`,
      )
    } catch (e) {
      toast.error(`Bulk delete failed: ${(e as Error).message}`)
    }
  }

  const handleBulkArchive = () => setConfirmBulkArchive(true)

  const confirmBulkArchiveAction = async () => {
    const ids = Array.from(selected)
    const { succeeded, firstError } = await runInBatches(ids, (id) =>
      apiFetch(`/memories/${id}`, {
        method: "PUT",
        body: JSON.stringify({ is_archived: true }),
      }),
    )
    setSelected(new Set())
    setDetailMemory(null)
    qc.invalidateQueries({ queryKey: ["memoriesPaginated"] })
    qc.invalidateQueries({ queryKey: ["memories"] })
    qc.invalidateQueries({ queryKey: ["stats"] })
    qc.invalidateQueries({ queryKey: ["overview"] })
    qc.invalidateQueries({ queryKey: ["tags"] })
    if (firstError) {
      toast.error(
        `Archived ${succeeded}/${ids.length}; first error: ${(firstError as Error).message}`,
      )
    } else {
      toast.success(`Archived ${succeeded} memories`)
    }
  }

  const sourceItems = useMemo(
    () => distinctSources.map((s) => ({ value: s, label: s })),
    [distinctSources],
  )

  const typeItems = useMemo(
    () => distinctTypes.map((t) => ({ value: t, label: t })),
    [distinctTypes],
  )

  // DataTable column definitions
  const columns: ColumnDef<Memory>[] = useMemo(
    () => [
      {
        id: "select",
        header: () => (
          <Checkbox
            checked={selected.size === memories.length && memories.length > 0}
            onCheckedChange={() => toggleSelectAll()}
            className="h-3.5 w-3.5"
            aria-label="Select all"
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            checked={selected.has(row.original.id)}
            onCheckedChange={(checked) => {
              if (checked !== "indeterminate") toggleSelect(row.original.id)
            }}
            onClick={(e) => e.stopPropagation()}
            className="h-3.5 w-3.5"
            aria-label="Select row"
          />
        ),
        size: 40,
      },
      {
        id: "content",
        header: "Content",
        cell: ({ row }) => {
          const m = row.original
          return (
            <div
              ref={(el) => {
                if (el) rowRefs.current.set(m.id, el)
                else rowRefs.current.delete(m.id)
              }}
              role="button"
              tabIndex={0}
              className={`min-w-0 cursor-pointer transition-colors ${
                highlightId === m.id ? "ring-primary rounded ring-2" : ""
              }`}
              onClick={() => setDetailMemory(m)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault()
                  setDetailMemory(m)
                }
              }}
            >
              <p className="line-clamp-2 text-base break-words">{m.content}</p>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                {m.status === "superseded" && (
                  <Badge
                    variant="outline"
                    className="border-amber-500/50 px-1.5 py-0 text-sm text-amber-500"
                    title="Superseded by a newer memory with a REPLACES relation"
                  >
                    superseded
                  </Badge>
                )}
                {m.tags.map((tag) => (
                  <Badge
                    key={tag}
                    variant="secondary"
                    className="px-1.5 py-0 text-sm"
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )
        },
      },
      {
        id: "source",
        header: "Source",
        cell: ({ row }) => (
          <span
            className="text-base font-medium"
            style={{ color: SOURCE_COLORS[row.original.source] ?? "#8b949e" }}
          >
            {row.original.source}
          </span>
        ),
        size: 120,
      },
      {
        id: "type",
        header: "Type",
        cell: ({ row }) => (
          <span className="text-muted-foreground text-base">
            {row.original.memory_type ?? "—"}
          </span>
        ),
        size: 100,
      },
      {
        id: "technologies",
        header: "Technologies",
        cell: ({ row }) => {
          const techs = row.original.technologies ?? []
          const visible = techs.slice(0, 3)
          return (
            <div className="flex flex-wrap gap-1">
              {visible.map((t) => (
                <Badge
                  key={t}
                  variant="outline"
                  className="px-1.5 py-0 text-sm"
                >
                  {t}
                </Badge>
              ))}
            </div>
          )
        },
        size: 140,
      },
      {
        id: "created_at",
        header: "Created",
        cell: ({ row }) => (
          <span className="text-muted-foreground text-base">
            {relativeTime(row.original.created_at)}
          </span>
        ),
        size: 90,
      },
      {
        id: "actions",
        header: "",
        cell: ({ row }) => (
          <Button
            variant="ghost"
            size="icon"
            className="text-muted-foreground hover:text-destructive rounded p-1"
            aria-label="Delete memory"
            onClick={(e) => {
              e.stopPropagation()
              handleDelete(row.original.id)
            }}
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </Button>
        ),
        size: 40,
      },
    ],
    [memories, selected, highlightId, handleDelete],
  )

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-4 gap-y-2 px-6 pt-6 pb-0">
        <div className="min-w-0">
          <PageHeader
            title="Memories"
            description={
              unfilteredTotal != null && unfilteredTotal > 0
                ? `${unfilteredTotal.toLocaleString()} total`
                : undefined
            }
          />
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setPaletteOpen(true)}
            title="Search (⌘K)"
          >
            <Search className="mr-2 size-4" />
            Search
          </Button>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 size-4" />
            New Memory
          </Button>
        </div>
      </div>

      <CreateMemoryDialog open={createOpen} onOpenChange={setCreateOpen} />

      <AlertDialog
        open={!!confirmDeleteId}
        onOpenChange={(o) => !o && setConfirmDeleteId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete memory?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (confirmDeleteId) confirmDelete(confirmDeleteId)
                setConfirmDeleteId(null)
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={confirmBulkDelete}
        onOpenChange={(o) => !o && setConfirmBulkDelete(false)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete {selected.size}{" "}
              {selected.size === 1 ? "memory" : "memories"}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setConfirmBulkDelete(false)
                confirmBulkDeleteAction()
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={confirmBulkArchive}
        onOpenChange={(o) => !o && setConfirmBulkArchive(false)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Archive {selected.size}{" "}
              {selected.size === 1 ? "memory" : "memories"}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Archived memories are hidden from the default view.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setConfirmBulkArchive(false)
                confirmBulkArchiveAction()
              }}
            >
              Archive
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <MemoryCommandPalette
        open={paletteOpen}
        onOpenChange={setPaletteOpen}
        onSubmit={handlePaletteSubmit}
      />

      <div className="flex flex-1 overflow-hidden">
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden p-4 pl-5">
          {/* Filter chrome */}
          <div className="mb-3 flex shrink-0 flex-col gap-2 lg:flex-row">
            {/* Tag filter using TagsInput */}
            <div className="min-w-0 flex-1">
              <TagsInput
                value={tagFilters}
                onValueChange={({ value }) => {
                  setTagFilters(value)
                  resetPagination()
                }}
              >
                <TagsInputControl className="min-h-8 px-2 py-1">
                  {tagFilters.map((tag, index) => (
                    <TagsInputItem key={tag} index={index} value={tag}>
                      <TagsInputItemPreview>
                        <TagsInputItemText>{tag}</TagsInputItemText>
                        <TagsInputItemDeleteTrigger />
                      </TagsInputItemPreview>
                    </TagsInputItem>
                  ))}
                  <TagsInputInput
                    placeholder={
                      tagFilters.length === 0 ? "Filter by tags…" : ""
                    }
                    className="text-base"
                  />
                </TagsInputControl>
              </TagsInput>
            </div>

            <div className="flex flex-wrap gap-2">
              {/* Source multi-select */}
              <MultiSelect
                items={sourceItems}
                value={sourceFilters}
                onValueChange={({ value }) => {
                  setSourceFilters(value)
                  resetPagination()
                }}
                placeholder="All sources"
                className="h-8 w-full text-base sm:w-40"
              />

              {/* Type multi-select */}
              <MultiSelect
                items={typeItems}
                value={typeFilters}
                onValueChange={({ value }) => {
                  setTypeFilters(value)
                  resetPagination()
                }}
                placeholder="All types"
                className="h-8 w-full text-base sm:w-36"
              />

              {hasActiveFilter && (
                <Button variant="ghost" size="sm" onClick={clearFilters}>
                  Clear
                </Button>
              )}
            </div>
          </div>

          {/* Active free-query indicator */}
          {freeQuery && (
            <div className="mb-2 flex shrink-0 items-center gap-2">
              <span className="text-muted-foreground text-base">
                Searching for: <strong>{freeQuery}</strong>
              </span>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Clear search"
                className="text-muted-foreground hover:text-foreground"
                onClick={() => {
                  setFreeQuery("")
                  resetPagination()
                }}
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          )}

          {/* Table */}
          {isLoading ? (
            <DataTableSkeleton columnCount={7} rowCount={8} />
          ) : memories.length === 0 ? (
            <EmptyState
              title={
                hasActiveFilter
                  ? "No memories match your filters"
                  : "No memories yet"
              }
              description={
                hasActiveFilter
                  ? "Try adjusting your search or filters."
                  : "Create one via the API or Claude Code to get started."
              }
              action={
                hasActiveFilter ? (
                  <Button variant="outline" onClick={clearFilters}>
                    Clear filters
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <div className="flex-1 overflow-auto">
              <DataTable columns={columns} data={memories} />
            </div>
          )}

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div className="text-muted-foreground mt-3 flex shrink-0 items-center justify-between text-base">
              <span>
                Showing {pageStart}–{pageEnd} of {total}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  disabled={offset === 0}
                  onClick={() => {
                    setOffset(Math.max(0, offset - PAGE_SIZE))
                    setSelected(new Set())
                  }}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  disabled={offset + PAGE_SIZE >= total}
                  onClick={() => {
                    setOffset(offset + PAGE_SIZE)
                    setSelected(new Set())
                  }}
                >
                  Next
                </Button>
              </div>
            </div>
          )}

          {/* Bulk action bar */}
          {selected.size > 0 && (
            <div className="bg-card border-border mt-3 flex shrink-0 flex-wrap items-center gap-4 gap-y-2 rounded-lg border p-3 text-base">
              <span className="text-primary font-medium">
                {selected.size} selected
              </span>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleBulkDelete}
              >
                <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                Delete
              </Button>
              <Button variant="outline" size="sm" onClick={handleBulkArchive}>
                Archive
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Detail sheet */}
      <Sheet
        open={!!detailMemory}
        onOpenChange={(open) => {
          if (!open) setDetailMemory(null)
        }}
      >
        <SheetContent
          side="right"
          className="w-full overflow-y-auto sm:max-w-md"
        >
          <SheetHeader>
            <SheetTitle className="text-base">Memory Details</SheetTitle>
          </SheetHeader>
          {detailMemory && (
            <div className="mt-4 space-y-4">
              <div>
                <div className="text-muted-foreground mb-1 text-base font-medium tracking-wider uppercase">
                  Content
                </div>
                <p className="text-base whitespace-pre-wrap">
                  {detailMemory.content}
                </p>
              </div>
              {detailMemory.tags.length > 0 && (
                <div>
                  <div className="text-muted-foreground mb-1 text-base font-medium tracking-wider uppercase">
                    Tags
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {detailMemory.tags.map((tag) => (
                      <Badge key={tag} variant="secondary">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              <div className="grid grid-cols-1 gap-3 text-base sm:grid-cols-2">
                <div>
                  <div className="text-muted-foreground mb-0.5 text-base font-medium tracking-wider uppercase">
                    Source
                  </div>
                  <span
                    style={{
                      color: SOURCE_COLORS[detailMemory.source] ?? "#c9d1d9",
                    }}
                  >
                    {detailMemory.source}
                  </span>
                </div>
                <div>
                  <div className="text-muted-foreground mb-0.5 text-base font-medium tracking-wider uppercase">
                    Type
                  </div>
                  <span>{detailMemory.memory_type ?? "—"}</span>
                </div>
                <div>
                  <div className="text-muted-foreground mb-0.5 text-base font-medium tracking-wider uppercase">
                    Importance
                  </div>
                  <span>{detailMemory.importance}</span>
                </div>
                {detailMemory.classified_type && (
                  <div>
                    <div className="text-muted-foreground mb-0.5 text-base font-medium tracking-wider uppercase">
                      Regex Classification
                    </div>
                    <span>{detailMemory.classified_type}</span>
                  </div>
                )}
                {detailMemory.llm_classified_type && (
                  <div>
                    <div className="text-muted-foreground mb-0.5 text-base font-medium tracking-wider uppercase">
                      LLM Classification
                    </div>
                    <span>{detailMemory.llm_classified_type}</span>
                  </div>
                )}
                <div>
                  <div className="text-muted-foreground mb-0.5 text-base font-medium tracking-wider uppercase">
                    Created
                  </div>
                  <span>
                    {new Date(detailMemory.created_at).toLocaleString()}
                  </span>
                </div>
                <div>
                  <div className="text-muted-foreground mb-0.5 text-base font-medium tracking-wider uppercase">
                    Updated
                  </div>
                  <span>
                    {new Date(detailMemory.updated_at).toLocaleString()}
                  </span>
                </div>
              </div>
              {(detailMemory.llm_summary ||
                detailMemory.llm_emotions?.length ||
                detailMemory.llm_flags?.length) && (
                <div>
                  <div className="text-muted-foreground mb-1 text-base font-medium tracking-wider uppercase">
                    LLM Enrichment
                  </div>
                  {detailMemory.llm_summary && (
                    <p className="text-muted-foreground mb-1.5 text-base">
                      {detailMemory.llm_summary}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-1">
                    {detailMemory.llm_emotions?.map((e) => (
                      <Badge key={e} variant="outline" className="text-sm">
                        {e}
                      </Badge>
                    ))}
                    {detailMemory.llm_flags?.map((f) => (
                      <Badge key={f} variant="secondary" className="text-sm">
                        {f}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {detailMemory.related_memories &&
                detailMemory.related_memories.length > 0 && (
                  <div>
                    <div className="text-muted-foreground mb-1 text-base font-medium tracking-wider uppercase">
                      Related Memories
                    </div>
                    <div className="space-y-1">
                      {detailMemory.related_memories.map((ref) => (
                        <div
                          key={ref.memory_id}
                          className="text-muted-foreground truncate text-base"
                        >
                          {ref.memory_id.slice(0, 8)}… (
                          {(ref.score * 100).toFixed(0)}% similar)
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              <div className="border-border border-t pt-3">
                <Button
                  variant="destructive"
                  onClick={() => handleDelete(detailMemory.id)}
                >
                  Delete Memory
                </Button>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}
