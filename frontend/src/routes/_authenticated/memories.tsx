import { useState, useMemo, useEffect, useRef } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { usePaginatedSearch, useDeleteMemory, useTags } from "@/hooks/api"
import type { Memory } from "@/hooks/api"
import { apiFetch } from "@/lib/api"
import { Card, CardContent } from "darkraise-ui/components/card"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Checkbox } from "darkraise-ui/components/checkbox"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "darkraise-ui/components/select"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "darkraise-ui/components/sheet"
import { PageHeader } from "darkraise-ui/layout"
import { X, Plus } from "lucide-react"
import { useQueryClient } from "@tanstack/react-query"
import { CreateMemoryDialog } from "@/features/memories/components/create-memory-dialog"

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
  "mcp-test":    "#3fb950",
  api:           "#d2a8ff",
  "rest-test":   "#ffa657",
  dashboard:     "#f778ba",
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}






// ── Main page ────────────────────────────────────────────────

function MemoriesPage() {
  const { focus: focusId } = Route.useSearch()
  const navigate = Route.useNavigate()
  const [searchInput, setSearchInput] = useState("")
  const [query, setQuery] = useState("")
  const [sourceFilter, setSourceFilter] = useState("")
  const [tagFilter, setTagFilter] = useState("")
  const [typeFilter, setTypeFilter] = useState("")
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [detailMemory, setDetailMemory] = useState<Memory | null>(null)
  const [createOpen, setCreateOpen] = useState(false)

  const { data, isLoading } = usePaginatedSearch({
    query: query || undefined,
    tags_any: tagFilter ? [tagFilter] : undefined,
    source: sourceFilter || undefined,
    memory_type: typeFilter || undefined,
    limit: PAGE_SIZE,
    offset,
  })
  const { data: unfilteredData } = usePaginatedSearch({ limit: 1, offset: 0 })
  const { data: tagsData } = useTags()
  const deleteMemory = useDeleteMemory()
  const qc = useQueryClient()

  const memories = data?.items ?? []
  const total = data?.total ?? 0
  const unfilteredTotal = unfilteredData?.total ?? total
  const pageStart = offset + 1
  const pageEnd = Math.min(offset + PAGE_SIZE, total)

  const [highlightId, setHighlightId] = useState<string | null>(null)
  const rowRefs = useRef<Map<string, HTMLDivElement>>(new Map())

  useEffect(() => {
    if (!focusId || memories.length === 0) return
    const target = memories.find((m) => m.id === focusId)
    if (!target) return
    const node = rowRefs.current.get(focusId)
    if (node) {
      node.scrollIntoView({ behavior: "smooth", block: "center" })
      setHighlightId(focusId)
      const timer = setTimeout(() => setHighlightId(null), 1500)
      navigate({ search: (prev) => ({ ...prev, focus: undefined }), replace: true })
      return () => clearTimeout(timer)
    }
  }, [focusId, memories, navigate])

  const distinctSources = useMemo(() => {
    const set = new Set(memories.map((m) => m.source))
    return Array.from(set).sort()
  }, [memories])

  const distinctTypes = useMemo(() => {
    const set = new Set(memories.map((m) => m.memory_type).filter(Boolean) as string[])
    return Array.from(set).sort()
  }, [memories])

  const resetPagination = () => {
    setOffset(0)
    setSelected(new Set())
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setQuery(searchInput)
    resetPagination()
  }

  const handleFilterChange = (setter: (v: string) => void) => (v: string) => {
    setter(v)
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
    if (selected.size === memories.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(memories.map((m) => m.id)))
    }
  }

  const handleDelete = (id: string) => {
    if (!window.confirm("Delete this memory?")) return
    deleteMemory.mutate(id, {
      onSuccess: () => {
        setSelected((prev) => {
          const next = new Set(prev)
          next.delete(id)
          return next
        })
        if (detailMemory?.id === id) setDetailMemory(null)
        qc.invalidateQueries({ queryKey: ["memoriesPaginated"] })
      },
    })
  }

  const handleBulkDelete = () => {
    if (!window.confirm(`Delete ${selected.size} memories?`)) return
    const ids = Array.from(selected)
    Promise.all(ids.map((id) => deleteMemory.mutateAsync(id)))
      .catch((err) => { console.error(err) })
      .finally(() => {
        setSelected(new Set())
        setDetailMemory(null)
        qc.invalidateQueries({ queryKey: ["memoriesPaginated"] })
      })
  }

  const handleBulkArchive = () => {
    if (!window.confirm(`Archive ${selected.size} memories?`)) return
    const ids = Array.from(selected)
    Promise.all(
      ids.map((id) =>
        apiFetch(`/memories/${id}`, {
          method: "PUT",
          body: JSON.stringify({ is_archived: true }),
        }),
      ),
    )
      .catch((err) => { console.error(err) })
      .finally(() => {
        setSelected(new Set())
        setDetailMemory(null)
        qc.invalidateQueries({ queryKey: ["memoriesPaginated"] })
      })
  }

  const hasActiveFilter = Boolean(
    query || sourceFilter || tagFilter || typeFilter,
  )

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-6 pt-6 pb-0 shrink-0 flex items-center justify-between gap-4">
        <PageHeader title="Memories" />
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="size-4 mr-2" />
          New Memory
        </Button>
      </div>
      <CreateMemoryDialog open={createOpen} onOpenChange={setCreateOpen} />

      <div className="flex flex-1 overflow-hidden">
        {/* Main content area */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden p-4 pl-5">
          {/* Search + filters */}
          <form onSubmit={handleSearch} className="flex flex-col lg:flex-row gap-2 mb-3 shrink-0">
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search memories..."
              className="flex-1"
            />
            <div className="flex gap-2 flex-wrap">
              <Select
                value={sourceFilter || "__all__"}
                onValueChange={(v) =>
                  handleFilterChange(setSourceFilter)(v === "__all__" ? "" : v)
                }
              >
                <SelectTrigger className="h-8 w-36">
                  <SelectValue placeholder="All sources" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All sources</SelectItem>
                  {distinctSources.map((s) => (
                    <SelectItem key={s} value={s}>
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select
                value={tagFilter || "__all__"}
                onValueChange={(v) =>
                  handleFilterChange(setTagFilter)(v === "__all__" ? "" : v)
                }
              >
                <SelectTrigger className="h-8 w-36">
                  <SelectValue placeholder="All tags" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All tags</SelectItem>
                  {tagsData?.map((t) => (
                    <SelectItem key={t.name} value={t.name}>
                      {t.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select
                value={typeFilter || "__all__"}
                onValueChange={(v) =>
                  handleFilterChange(setTypeFilter)(v === "__all__" ? "" : v)
                }
              >
                <SelectTrigger className="h-8 w-36">
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All types</SelectItem>
                  {distinctTypes.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button type="submit" size="sm">
                Search
              </Button>
            </div>
          </form>

          {isLoading && (
            <p className="text-muted-foreground text-sm">Loading...</p>
          )}

          {!isLoading && memories.length === 0 && (
            <p className="text-muted-foreground text-sm">
              {hasActiveFilter
                ? "No memories match your filters."
                : "No memories yet. Create one via the API or Claude Code to get started."}
            </p>
          )}

          {memories.length > 0 && (
            <Card className="flex-1 overflow-hidden">
              <CardContent className="p-0 h-full flex flex-col">
                <div className="flex items-center gap-3 px-4 py-2 border-b border-border text-xs text-muted-foreground shrink-0">
                  <Checkbox
                    checked={selected.size === memories.length && memories.length > 0}
                    onCheckedChange={() => toggleSelectAll()}
                    className="h-3.5 w-3.5"
                  />
                  <span>Select all</span>
                </div>

                <div className="divide-y divide-border overflow-y-auto flex-1 scrollbar-thin">
                  {memories.map((m) => (
                    <div
                      key={m.id}
                      ref={(el) => {
                        if (el) rowRefs.current.set(m.id, el)
                        else rowRefs.current.delete(m.id)
                      }}
                      className={`flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-accent/30 ${
                        selected.has(m.id) ? "bg-accent/20" : ""
                      } ${highlightId === m.id ? "ring-2 ring-primary bg-primary/10" : ""}`}
                      onClick={() => setDetailMemory(m)}
                    >
                      <Checkbox
                        checked={selected.has(m.id)}
                        onCheckedChange={(checked) => {
                          if (checked !== "indeterminate") toggleSelect(m.id)
                        }}
                        onClick={(e) => e.stopPropagation()}
                        className="h-3.5 w-3.5 mt-1"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm truncate flex-1">{m.content}</span>
                          <button
                            className="text-muted-foreground hover:text-destructive shrink-0"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDelete(m.id)
                            }}
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                        <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground flex-wrap">
                          {m.tags.map((tag) => (
                            <Badge key={tag} variant="secondary" className="text-[10px] px-1.5 py-0">
                              {tag}
                            </Badge>
                          ))}
                          <span className="ml-auto flex items-center gap-1.5 shrink-0">
                            <span style={{ color: SOURCE_COLORS[m.source] ?? "#8b949e" }}>
                              {m.source}
                            </span>
                            {m.memory_type && (
                              <>
                                <span>·</span>
                                <span>{m.memory_type}</span>
                              </>
                            )}
                            <span>·</span>
                            <span>{relativeTime(m.created_at)}</span>
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {total > PAGE_SIZE && (
            <div className="flex items-center justify-between mt-3 text-sm text-muted-foreground shrink-0">
              <span>
                Showing {pageStart}–{pageEnd} of {total}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
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
                  size="sm"
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

          {selected.size > 0 && (
            <div className="flex items-center gap-4 mt-3 p-3 bg-card border border-border rounded-lg text-sm shrink-0">
              <span className="text-primary font-medium">{selected.size} selected</span>
              <Button variant="destructive" size="sm" onClick={handleBulkDelete}>
                Delete
              </Button>
              <Button variant="outline" size="sm" onClick={handleBulkArchive}>
                Archive
              </Button>
            </div>
          )}
        </div>
      </div>

      <Sheet
        open={!!detailMemory}
        onOpenChange={(open) => {
          if (!open) setDetailMemory(null)
        }}
      >
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-base">Memory Details</SheetTitle>
          </SheetHeader>
          {detailMemory && (
            <div className="space-y-4 mt-4">
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-1">
                  Content
                </div>
                <p className="text-sm whitespace-pre-wrap">{detailMemory.content}</p>
              </div>
              {detailMemory.tags.length > 0 && (
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-1">
                    Tags
                  </div>
                  <div className="flex gap-1.5 flex-wrap">
                    {detailMemory.tags.map((tag) => (
                      <Badge key={tag} variant="secondary">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">
                    Source
                  </div>
                  <span style={{ color: SOURCE_COLORS[detailMemory.source] ?? "#c9d1d9" }}>
                    {detailMemory.source}
                  </span>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">
                    Type
                  </div>
                  <span>{detailMemory.memory_type ?? "—"}</span>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">
                    Importance
                  </div>
                  <span>{detailMemory.importance}</span>
                </div>
                {detailMemory.classified_type && (
                  <div>
                    <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">
                      Regex Classification
                    </div>
                    <span>{detailMemory.classified_type}</span>
                  </div>
                )}
                {detailMemory.llm_classified_type && (
                  <div>
                    <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">
                      LLM Classification
                    </div>
                    <span>{detailMemory.llm_classified_type}</span>
                  </div>
                )}
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">
                    Created
                  </div>
                  <span>{new Date(detailMemory.created_at).toLocaleString()}</span>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">
                    Updated
                  </div>
                  <span>{new Date(detailMemory.updated_at).toLocaleString()}</span>
                </div>
              </div>
              {(detailMemory.llm_summary || detailMemory.llm_emotions?.length || detailMemory.llm_flags?.length) && (
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-1">
                    LLM Enrichment
                  </div>
                  {detailMemory.llm_summary && (
                    <p className="text-sm text-muted-foreground mb-1.5">{detailMemory.llm_summary}</p>
                  )}
                  <div className="flex gap-1 flex-wrap">
                    {detailMemory.llm_emotions?.map((e) => (
                      <Badge key={e} variant="outline" className="text-[10px]">{e}</Badge>
                    ))}
                    {detailMemory.llm_flags?.map((f) => (
                      <Badge key={f} variant="secondary" className="text-[10px]">{f}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {detailMemory.related_memories && detailMemory.related_memories.length > 0 && (
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-1">
                    Related Memories
                  </div>
                  <div className="space-y-1">
                    {detailMemory.related_memories.map((ref) => (
                      <div
                        key={ref.memory_id}
                        className="text-xs text-muted-foreground cursor-pointer hover:text-foreground truncate"
                      >
                        {ref.memory_id.slice(0, 8)}... ({(ref.score * 100).toFixed(0)}% similar)
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div className="pt-3 border-t border-border">
                <Button
                  variant="destructive"
                  size="sm"
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
