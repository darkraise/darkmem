import { useEffect, useMemo, useState } from "react"
import { ScrollText } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { cn } from "darkraise-ui/lib"
import { EmptyState, listItemClass } from "@/components/darkmem"
import { useWorklogResume, useWorkstreams, type Workstream } from "@/hooks/api"
import { formatWhen } from "@/lib/format"
import { EntryTimeline } from "./entry-timeline"
import { WorkstreamHeader } from "./workstream-header"
import { WorklogSearch } from "./worklog-search"

function WorkstreamList({
  items,
  selectedKey,
  onSelect,
}: {
  items: Workstream[]
  selectedKey: string | null
  onSelect: (key: string) => void
}) {
  return (
    <ul className="space-y-1.5">
      {items.map((w) => (
        <li key={w.id}>
          <button
            type="button"
            aria-pressed={w.key === selectedKey}
            onClick={() => onSelect(w.key)}
            className={listItemClass({
              interactive: true,
              // Solid here: in this panel the dashed list edge sat beside
              // the dashed warnings and read as a placeholder. The selected
              // workstream gets a real fill and a left accent bar, not just a
              // tinted edge.
              className: cn(
                "bg-card flex w-full flex-col gap-0.5 border-solid p-2.5 text-left",
                w.key === selectedKey &&
                  "border-primary/45 border-l-primary bg-primary/10 border-l-2",
              ),
            })}
          >
            <span className="truncate text-sm font-semibold">
              {w.title ?? w.key}
            </span>
            <span className="text-muted-foreground truncate font-mono text-xs">
              {w.key} · {w.state} · {formatWhen(w.last_entry_at)}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

function MoreButton({
  query,
  label,
}: {
  query: {
    hasNextPage: boolean
    isFetchingNextPage: boolean
    fetchNextPage: () => unknown
  }
  label: string
}) {
  if (!query.hasNextPage) return null
  return (
    <Button
      variant="ghost"
      size="sm"
      disabled={query.isFetchingNextPage}
      onClick={() => void query.fetchNextPage()}
    >
      {label}
    </Button>
  )
}

/** A project's work log (spec §8): its workstreams, open first and closed
 *  collapsed, beside the selected one's entries. `initialWorkstream` is a
 *  workstream key; without it the open workstream with the newest entry is
 *  selected (spec §1: `last_entry_at` is what the UI orders by). */
export function WorkLogPanel({
  project,
  initialWorkstream,
  onOpenDocument,
}: {
  project: string
  initialWorkstream?: string
  onOpenDocument?: (uri: string) => void
}) {
  const open = useWorkstreams(project, "open")
  const closed = useWorkstreams(project, "closed")
  const openItems = useMemo(
    () => open.data?.pages.flatMap((page) => page.items) ?? [],
    [open.data],
  )
  const closedItems = useMemo(
    () => closed.data?.pages.flatMap((page) => page.items) ?? [],
    [closed.data],
  )
  const [selectedKey, setSelectedKey] = useState<string | null>(
    initialWorkstream ?? null,
  )
  // null follows the selection: the closed list opens while a closed
  // workstream is selected, until the reader toggles it themselves.
  const [showClosed, setShowClosed] = useState<boolean | null>(null)
  const [focusEntryId, setFocusEntryId] = useState<string | undefined>(
    undefined,
  )

  const listed =
    selectedKey === null
      ? undefined
      : (openItems.find((w) => w.key === selectedKey) ??
        closedItems.find((w) => w.key === selectedKey))
  // A key past the loaded pages (a link from Activity, a search hit) is looked
  // up on its own rather than silently replaced by the first open workstream.
  const unlisted =
    selectedKey !== null &&
    listed === undefined &&
    !open.isPending &&
    !closed.isPending
  const lookup = useWorklogResume(project, selectedKey ?? "", unlisted)
  const resolving = unlisted && lookup.isLoading
  const mostActive = useMemo(
    () =>
      openItems.reduce<Workstream | null>(
        (best, w) =>
          best === null || w.last_entry_at > best.last_entry_at ? w : best,
        null,
      ),
    [openItems],
  )
  // Pin the default pick, so closing it keeps it selected rather than jumping
  // to the next open workstream.
  useEffect(() => {
    if (selectedKey === null && mostActive) setSelectedKey(mostActive.key)
  }, [selectedKey, mostActive])
  const selected =
    listed ??
    (unlisted ? lookup.data?.workstream : undefined) ??
    mostActive ??
    null
  const closedVisible = showClosed ?? selected?.state === "closed"

  if (open.isError || closed.isError) {
    return (
      <EmptyState
        kind="failed"
        title="Could not read the work log"
        description={(open.error ?? closed.error)?.message}
      />
    )
  }
  if (open.isPending || closed.isPending) {
    return <Skeleton className="h-48 w-full" />
  }
  if (openItems.length === 0 && closedItems.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={ScrollText}
        title="No work log yet"
        description="A coding client's checkpoints and notes appear here once it logs work in this project."
      />
    )
  }

  const selectFromList = (key: string) => {
    setSelectedKey(key)
    setFocusEntryId(undefined)
  }

  return (
    <div className="space-y-4">
      <WorklogSearch
        project={project}
        onOpen={(key, entryId) => {
          setSelectedKey(key)
          setFocusEntryId(entryId)
        }}
      />
      {/* The explicit `minmax(0,1fr)` track is what holds a phone to the
          viewport: the implicit `auto` column sized itself to the header's
          unwrapped max-content and pushed Close and Purge off-screen. */}
      <div className="grid grid-cols-[minmax(0,1fr)] gap-4 md:grid-cols-[16rem_minmax(0,1fr)]">
        <nav aria-label="workstreams" className="space-y-3">
          <WorkstreamList
            items={openItems}
            selectedKey={selected?.key ?? null}
            onSelect={selectFromList}
          />
          <MoreButton query={open} label="More open workstreams" />
          {closedItems.length > 0 ? (
            <div className="space-y-1.5">
              <Button
                variant="ghost"
                size="sm"
                aria-expanded={closedVisible}
                onClick={() => setShowClosed(!closedVisible)}
              >
                {closedVisible
                  ? "Hide closed"
                  : `Closed (${closedItems.length}${closed.hasNextPage ? "+" : ""})`}
              </Button>
              {closedVisible ? (
                <>
                  <WorkstreamList
                    items={closedItems}
                    selectedKey={selected?.key ?? null}
                    onSelect={selectFromList}
                  />
                  <MoreButton query={closed} label="More closed workstreams" />
                </>
              ) : null}
            </div>
          ) : null}
        </nav>
        {resolving ? (
          <Skeleton className="h-64 w-full" />
        ) : selected ? (
          <section
            aria-label={`workstream ${selected.key}`}
            className="min-w-0 space-y-3"
          >
            <WorkstreamHeader
              workstream={selected}
              onOpenDocument={onOpenDocument}
            />
            <EntryTimeline
              key={`${selected.id}:${focusEntryId ?? ""}`}
              workstream={selected}
              initialEntryId={focusEntryId}
            />
          </section>
        ) : (
          <EmptyState
            kind="empty"
            icon={ScrollText}
            title="No open workstream"
            description="Every workstream in this project is closed; open one from the closed list to read it."
          />
        )}
      </div>
    </div>
  )
}
