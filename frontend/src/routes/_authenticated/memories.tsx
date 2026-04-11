import { useState, useMemo } from "react"
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
import {
  X,
  ChevronRight,
  ChevronDown,
  PanelLeftClose,
  PanelLeftOpen,
  Building2,
  DoorOpen,
  Plus,
} from "lucide-react"
import { useQueryClient } from "@tanstack/react-query"
import { CreateMemoryDialog } from "@/features/memories/components/create-memory-dialog"

export const Route = createFileRoute("/_authenticated/memories")({
  component: MemoriesPage,
})

const PAGE_SIZE = 50

const HALLS = ["facts", "events", "discoveries", "preferences", "advice"] as const
type Hall = (typeof HALLS)[number]

const HALL_COLORS: Record<Hall, { bg: string; text: string; border: string }> = {
  facts:        { bg: "rgba(34,211,238,0.08)",  text: "#22d3ee", border: "rgba(34,211,238,0.25)" },
  events:       { bg: "rgba(167,139,250,0.08)", text: "#a78bfa", border: "rgba(167,139,250,0.25)" },
  discoveries:  { bg: "rgba(52,211,153,0.08)",  text: "#34d399", border: "rgba(52,211,153,0.25)" },
  preferences:  { bg: "rgba(251,191,36,0.08)",  text: "#fbbf24", border: "rgba(251,191,36,0.25)" },
  advice:       { bg: "rgba(248,113,113,0.08)", text: "#f87171", border: "rgba(248,113,113,0.25)" },
}

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

interface WingTree {
  [wing: string]: {
    count: number
    rooms: { [room: string]: number }
  }
}

function buildWingTree(memories: Memory[]): WingTree {
  const tree: WingTree = {}
  for (const m of memories) {
    const wing = m.wing ?? "(unassigned)"
    const room = m.room ?? "(unassigned)"
    if (!tree[wing]) tree[wing] = { count: 0, rooms: {} }
    tree[wing].count++
    tree[wing].rooms[room] = (tree[wing].rooms[room] ?? 0) + 1
  }
  return tree
}

// ── Wing/Room sidebar ────────────────────────────────────────

interface WingSidebarProps {
  tree: WingTree
  selectedWing: string
  selectedRoom: string
  totalCount: number
  unfilteredCount: number
  hasFilters: boolean
  onSelectAll: () => void
  onSelectWing: (wing: string) => void
  onSelectRoom: (wing: string, room: string) => void
  collapsed: boolean
  onToggleCollapse: () => void
}

function WingSidebar({
  tree,
  selectedWing,
  selectedRoom,
  totalCount,
  unfilteredCount,
  hasFilters,
  onSelectAll,
  onSelectWing,
  onSelectRoom,
  collapsed,
  onToggleCollapse,
}: WingSidebarProps) {
  const [expandedWings, setExpandedWings] = useState<Set<string>>(new Set())

  const toggleWingExpand = (wing: string) => {
    setExpandedWings((prev) => {
      const next = new Set(prev)
      if (next.has(wing)) next.delete(wing)
      else next.add(wing)
      return next
    })
  }

  if (collapsed) {
    return (
      <div
        className="flex flex-col items-center pt-3 gap-2 border-r border-[rgba(34,211,238,0.08)]"
        style={{ width: 36, minWidth: 36, background: "rgba(8,8,14,0.7)" }}
      >
        <button
          onClick={onToggleCollapse}
          className="text-[rgba(34,211,238,0.5)] hover:text-[#22d3ee] transition-colors"
          title="Expand navigation"
        >
          <PanelLeftOpen className="w-4 h-4" />
        </button>
      </div>
    )
  }

  const wings = Object.keys(tree).sort()

  return (
    <div
      className="flex flex-col border-r border-[rgba(34,211,238,0.08)] shrink-0 overflow-hidden"
      style={{ width: 220, minWidth: 220, background: "rgba(8,8,14,0.7)" }}
    >
      {/* header */}
      <div className="flex items-center justify-between px-3 py-2.5 border-b border-[rgba(34,211,238,0.08)]">
        <span
          className="text-[10px] uppercase tracking-widest font-mono"
          style={{ color: "rgba(34,211,238,0.5)" }}
        >
          Navigation
        </span>
        <button
          onClick={onToggleCollapse}
          className="text-[rgba(34,211,238,0.4)] hover:text-[#22d3ee] transition-colors"
          title="Collapse navigation"
        >
          <PanelLeftClose className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* all memories */}
      <button
        onClick={onSelectAll}
        className={`flex items-center justify-between px-3 py-2 text-xs font-mono transition-colors hover:bg-[rgba(34,211,238,0.04)] ${
          !selectedWing ? "text-[#22d3ee] bg-[rgba(34,211,238,0.06)]" : "text-muted-foreground"
        }`}
      >
        <span className="flex items-center gap-1.5">
          <Building2 className="w-3 h-3 shrink-0" />
          All memories
        </span>
        <span
          className="text-[10px] px-1.5 py-0.5 rounded font-mono"
          style={{
            background: "rgba(34,211,238,0.08)",
            color: "rgba(34,211,238,0.6)",
          }}
        >
          {hasFilters ? `${totalCount} of ${unfilteredCount}` : totalCount}
        </span>
      </button>

      {/* wing list */}
      <div className="overflow-y-auto flex-1 scrollbar-thin">
        {wings.map((wing) => {
          const wingData = tree[wing]
          const isWingSelected = selectedWing === wing
          const isExpanded = expandedWings.has(wing)
          const rooms = Object.keys(wingData.rooms).sort()

          return (
            <div key={wing}>
              {/* wing row */}
              <div
                className={`flex items-center gap-1 px-2 py-1.5 text-xs font-mono transition-colors hover:bg-[rgba(34,211,238,0.04)] ${
                  isWingSelected && !selectedRoom
                    ? "text-[#22d3ee] bg-[rgba(34,211,238,0.06)]"
                    : "text-muted-foreground"
                }`}
              >
                <button
                  onClick={() => toggleWingExpand(wing)}
                  className="shrink-0 text-[rgba(34,211,238,0.4)] hover:text-[#22d3ee] transition-colors"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-3 h-3" />
                  ) : (
                    <ChevronRight className="w-3 h-3" />
                  )}
                </button>
                <button
                  onClick={() => onSelectWing(wing)}
                  className="flex items-center justify-between flex-1 min-w-0 gap-1"
                >
                  <span className="truncate">{wing}</span>
                  <span
                    className="text-[10px] px-1 py-0.5 rounded shrink-0"
                    style={{
                      background: "rgba(34,211,238,0.08)",
                      color: "rgba(34,211,238,0.6)",
                    }}
                  >
                    {wingData.count}
                  </span>
                </button>
              </div>

              {/* room rows */}
              {isExpanded &&
                rooms.map((room) => (
                  <button
                    key={room}
                    onClick={() => onSelectRoom(wing, room)}
                    className={`w-full flex items-center justify-between pl-8 pr-2 py-1.5 text-xs font-mono transition-colors hover:bg-[rgba(34,211,238,0.04)] ${
                      isWingSelected && selectedRoom === room
                        ? "text-[#22d3ee] bg-[rgba(34,211,238,0.06)]"
                        : "text-muted-foreground"
                    }`}
                  >
                    <span className="flex items-center gap-1.5 min-w-0">
                      <DoorOpen className="w-3 h-3 shrink-0 opacity-60" />
                      <span className="truncate">{room}</span>
                    </span>
                    <span
                      className="text-[10px] px-1 py-0.5 rounded shrink-0 ml-1"
                      style={{
                        background: "rgba(34,211,238,0.05)",
                        color: "rgba(34,211,238,0.5)",
                      }}
                    >
                      {wingData.rooms[room]}
                    </span>
                  </button>
                ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Hall filter chips ────────────────────────────────────────

interface HallFilterProps {
  activeHall: string
  onChange: (hall: string) => void
}

function HallFilter({ activeHall, onChange }: HallFilterProps) {
  return (
    <div className="flex items-center gap-2 flex-wrap mb-3">
      <span
        className="text-[10px] uppercase tracking-widest font-mono shrink-0"
        style={{ color: "rgba(34,211,238,0.4)" }}
      >
        Hall
      </span>
      <button
        onClick={() => onChange("")}
        className="text-xs font-mono px-2.5 py-0.5 rounded border transition-colors"
        style={
          !activeHall
            ? {
                background: "rgba(34,211,238,0.12)",
                color: "#22d3ee",
                border: "1px solid rgba(34,211,238,0.35)",
              }
            : {
                background: "transparent",
                color: "rgba(255,255,255,0.35)",
                border: "1px solid rgba(255,255,255,0.08)",
              }
        }
      >
        all
      </button>
      {HALLS.map((hall) => {
        const colors = HALL_COLORS[hall]
        const isActive = activeHall === hall
        return (
          <button
            key={hall}
            onClick={() => onChange(isActive ? "" : hall)}
            className="text-xs font-mono px-2.5 py-0.5 rounded border transition-colors"
            style={
              isActive
                ? {
                    background: colors.bg,
                    color: colors.text,
                    border: `1px solid ${colors.border}`,
                  }
                : {
                    background: "transparent",
                    color: "rgba(255,255,255,0.35)",
                    border: "1px solid rgba(255,255,255,0.08)",
                  }
            }
          >
            {hall}
          </button>
        )
      })}
    </div>
  )
}

// ── Main page ────────────────────────────────────────────────

function MemoriesPage() {
  const [searchInput, setSearchInput] = useState("")
  const [query, setQuery] = useState("")
  const [sourceFilter, setSourceFilter] = useState("")
  const [tagFilter, setTagFilter] = useState("")
  const [typeFilter, setTypeFilter] = useState("")
  const [wingFilter, setWingFilter] = useState("")
  const [roomFilter, setRoomFilter] = useState("")
  const [hallFilter, setHallFilter] = useState("")
  const [offset, setOffset] = useState(0)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [detailMemory, setDetailMemory] = useState<Memory | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)

  const { data, isLoading } = usePaginatedSearch({
    query: query || undefined,
    tags_any: tagFilter ? [tagFilter] : undefined,
    source: sourceFilter || undefined,
    memory_type: typeFilter || undefined,
    wing: wingFilter || undefined,
    room: roomFilter || undefined,
    hall: hallFilter || undefined,
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
  const hasFilters = Boolean(
    query || tagFilter || sourceFilter || typeFilter || wingFilter || roomFilter || hallFilter,
  )
  const pageStart = offset + 1
  const pageEnd = Math.min(offset + PAGE_SIZE, total)

  const wingTree = useMemo(() => buildWingTree(memories), [memories])

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

  const handleSelectWing = (wing: string) => {
    setWingFilter(wing)
    setRoomFilter("")
    resetPagination()
  }

  const handleSelectRoom = (wing: string, room: string) => {
    setWingFilter(wing)
    setRoomFilter(room)
    resetPagination()
  }

  const handleSelectAll = () => {
    setWingFilter("")
    setRoomFilter("")
    resetPagination()
  }

  const handleHallChange = (hall: string) => {
    setHallFilter(hall)
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

  const hasActiveFilter =
    query || sourceFilter || tagFilter || typeFilter || wingFilter || roomFilter || hallFilter

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
        {/* Wing/Room sidebar */}
        <WingSidebar
          tree={wingTree}
          selectedWing={wingFilter}
          selectedRoom={roomFilter}
          totalCount={total}
          unfilteredCount={unfilteredTotal}
          hasFilters={hasFilters}
          onSelectAll={handleSelectAll}
          onSelectWing={handleSelectWing}
          onSelectRoom={handleSelectRoom}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed((v) => !v)}
        />

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

          {/* Hall filter chips */}
          <HallFilter activeHall={hallFilter} onChange={handleHallChange} />

          {/* Active location breadcrumb */}
          {(wingFilter || roomFilter) && (
            <div className="flex items-center gap-1.5 mb-3 text-xs font-mono shrink-0">
              <span style={{ color: "rgba(34,211,238,0.4)" }}>loc:</span>
              <span style={{ color: "#22d3ee" }}>{wingFilter}</span>
              {roomFilter && (
                <>
                  <span style={{ color: "rgba(34,211,238,0.3)" }}>/</span>
                  <span style={{ color: "#22d3ee" }}>{roomFilter}</span>
                </>
              )}
              <button
                onClick={handleSelectAll}
                className="ml-1 text-[rgba(34,211,238,0.4)] hover:text-[#22d3ee] transition-colors"
                title="Clear location filter"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          )}

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
                      className={`flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-accent/30 ${
                        selected.has(m.id) ? "bg-accent/20" : ""
                      }`}
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
                          {m.hall && HALL_COLORS[m.hall as Hall] && (
                            <span
                              className="text-[10px] px-1.5 py-0 rounded font-mono"
                              style={{
                                color: HALL_COLORS[m.hall as Hall].text,
                                background: HALL_COLORS[m.hall as Hall].bg,
                                border: `1px solid ${HALL_COLORS[m.hall as Hall].border}`,
                              }}
                            >
                              {m.hall}
                            </span>
                          )}
                          {m.wing && (
                            <span
                              className="text-[10px] px-1.5 py-0 rounded font-mono"
                              style={{
                                color: "rgba(34,211,238,0.7)",
                                background: "rgba(34,211,238,0.05)",
                                border: "1px solid rgba(34,211,238,0.12)",
                              }}
                            >
                              {m.wing}
                              {m.room ? `/${m.room}` : ""}
                            </span>
                          )}
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
              {(detailMemory.wing || detailMemory.room || detailMemory.hall) && (
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-1">
                    Location
                  </div>
                  <div className="flex gap-1.5 flex-wrap text-xs font-mono">
                    {detailMemory.wing && (
                      <span style={{ color: "#22d3ee" }}>
                        wing: {detailMemory.wing}
                      </span>
                    )}
                    {detailMemory.room && (
                      <span style={{ color: "rgba(34,211,238,0.7)" }}>
                        room: {detailMemory.room}
                      </span>
                    )}
                    {detailMemory.hall && (
                      <span
                        style={{
                          color: HALL_COLORS[detailMemory.hall as Hall]?.text ?? "#c9d1d9",
                        }}
                      >
                        hall: {detailMemory.hall}
                      </span>
                    )}
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
