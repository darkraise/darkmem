import { useMemo, useState } from "react"
import { ScrollText } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { cn } from "darkraise-ui/lib"
import { EmptyState, listItemClass } from "@/components/darkmem"
import { useWorklogResume, useWorkstreams, type Workstream } from "@/hooks/api"
import { formatWhen } from "@/lib/format"
import { EntryTimeline } from "./entry-timeline"

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
              className: cn(
                "bg-card flex w-full flex-col gap-0.5 p-2.5 text-left",
                w.key === selectedKey && "border-primary/45 bg-primary/5",
              ),
            })}
          >
            <span className="truncate text-sm font-semibold">{w.title ?? w.key}</span>
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
  query: { hasNextPage: boolean; isFetchingNextPage: boolean; fetchNextPage: () => unknown }
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

function WorkstreamSummary({ workstream }: { workstream: Workstream }) {
  return (
    <div className="space-y-0.5">
      <h3 className="text-base font-semibold">{workstream.title ?? workstream.key}</h3>
      <p className="text-muted-foreground font-mono text-xs">
        {workstream.key} · {workstream.state}
        {workstream.client ? ` · ${workstream.client}` : ""}
      </p>
    </div>
  )
}

/** A project's work log (spec §8): its workstreams, open first and closed
 *  collapsed, beside the selected one's entries. `initialWorkstream` is a
 *  workstream key; without it the newest open workstream is selected. */
export function WorkLogPanel({
  project,
  initialWorkstream,
}: {
  project: string
  initialWorkstream?: string
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
  const [selectedKey, setSelectedKey] = useState<string | null>(initialWorkstream ?? null)
  const [showClosed, setShowClosed] = useState(false)

  const listed =
    selectedKey === null
      ? undefined
      : (openItems.find((w) => w.key === selectedKey) ??
        closedItems.find((w) => w.key === selectedKey))
  // A key past the loaded pages (a link from Activity, a search hit) is looked
  // up on its own rather than silently replaced by the first open workstream.
  const unlisted =
    selectedKey !== null && listed === undefined && !open.isPending && !closed.isPending
  const lookup = useWorklogResume(project, selectedKey ?? "", unlisted)
  const resolving = unlisted && lookup.isLoading
  const selected =
    listed ?? (unlisted ? lookup.data?.workstream : undefined) ?? openItems[0] ?? null
  const closedVisible = showClosed || selected?.state === "closed"

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
        description="A coding client's checkpoints, ledger and notes appear here once it appends to a workstream in this project with worklog_append."
      />
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-[16rem_minmax(0,1fr)]">
      <nav aria-label="workstreams" className="space-y-3">
        <WorkstreamList
          items={openItems}
          selectedKey={selected?.key ?? null}
          onSelect={setSelectedKey}
        />
        <MoreButton query={open} label="More open workstreams" />
        {closedItems.length > 0 ? (
          <div className="space-y-1.5">
            <Button
              variant="ghost"
              size="sm"
              aria-expanded={closedVisible}
              onClick={() => setShowClosed((shown) => !shown)}
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
                  onSelect={setSelectedKey}
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
        <section aria-label={`workstream ${selected.key}`} className="min-w-0 space-y-3">
          <WorkstreamSummary workstream={selected} />
          <EntryTimeline key={selected.id} workstream={selected} />
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
  )
}
