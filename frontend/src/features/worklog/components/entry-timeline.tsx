import { useEffect, useMemo, useState } from "react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import {
  SegmentGroup,
  SegmentGroupIndicator,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import { Skeleton } from "darkraise-ui/components/skeleton"
import {
  VirtualizedTimeline,
  type TimelineBucket,
} from "darkraise-ui/components/virtualized-timeline"
import { cn } from "darkraise-ui/lib"
import { EmptyState } from "@/components/darkmem"
import { AppMarkdown } from "@/components/markdown"
import {
  useWorklogEntries,
  type WorklogEntry,
  type WorklogKind,
  type Workstream,
} from "@/hooks/api"
import { formatWhen } from "@/lib/format"

type KindFilter = "all" | WorklogKind

const KIND_VARIANT: Record<WorklogKind, "default" | "secondary" | "outline"> = {
  checkpoint: "default",
  ledger: "outline",
  note: "secondary",
}

const ROW_HEIGHT = 40

/** The line a row shows: the first non-blank line, without a heading's hashes. */
export function firstLine(body: string): string {
  const line = body.split("\n").find((l) => l.trim()) ?? ""
  return line.replace(/^#+\s*/, "").trim()
}

/** UTC day buckets in entry order, so a ledger still reads forward. */
function bucketsByDay(entries: WorklogEntry[]): TimelineBucket<WorklogEntry>[] {
  const days = new Map<string, WorklogEntry[]>()
  for (const entry of entries) {
    const day = entry.created_at.slice(0, 10)
    const bucket = days.get(day)
    if (bucket) bucket.push(entry)
    else days.set(day, [entry])
  }
  return [...days].map(([day, items]) => ({ id: day, date: day, count: items.length, items }))
}

function KindBadge({ kind }: { kind: WorklogKind }) {
  return <Badge variant={KIND_VARIANT[kind]}>{kind}</Badge>
}

function EntryRow({ entry, selected }: { entry: WorklogEntry; selected: boolean }) {
  return (
    <div
      className={cn(
        "flex h-full items-center gap-2 px-2 text-sm",
        selected && "bg-primary/5",
      )}
    >
      <KindBadge kind={entry.kind} />
      <span className="text-muted-foreground w-12 shrink-0 font-mono text-xs">
        {entry.created_at.slice(11, 16)}
      </span>
      <span className="min-w-0 flex-1 truncate">{firstLine(entry.body)}</span>
      <span className="text-muted-foreground hidden max-w-40 truncate font-mono text-xs md:inline">
        {entry.run_key}
      </span>
    </div>
  )
}

/** A checkpoint or note renders as markdown; a ledger chunk stays verbatim,
 *  because its bytes are the ledger file's own. */
function EntryDetail({ entry }: { entry: WorklogEntry | null }) {
  if (!entry) {
    return (
      <p className="text-muted-foreground text-sm">
        Select an entry to read it in full.
      </p>
    )
  }
  return (
    <article aria-label="entry" className="border-border min-w-0 space-y-2 rounded-md border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <KindBadge kind={entry.kind} />
        <span className="text-muted-foreground font-mono text-xs">
          #{entry.seq} · {entry.run_key} · {formatWhen(entry.created_at)}
        </span>
      </div>
      {entry.kind === "ledger" ? (
        <pre className="bg-muted/40 overflow-x-auto rounded p-2 font-mono text-sm whitespace-pre-wrap">
          {entry.body}
        </pre>
      ) : (
        <AppMarkdown>{entry.body}</AppMarkdown>
      )}
    </article>
  )
}

/** One workstream's entries: kind filter, a day-bucketed timeline of one-line
 *  rows, and the selected entry in full beside it. The timeline's rows have a
 *  fixed height, so a checkpoint expands into the detail pane, not in place. */
export function EntryTimeline({
  workstream,
  initialEntryId,
}: {
  workstream: Workstream
  initialEntryId?: string
}) {
  const [kind, setKind] = useState<KindFilter>("all")
  const [selectedId, setSelectedId] = useState<string | null>(initialEntryId ?? null)
  const entries = useWorklogEntries(
    workstream.id,
    kind === "all" ? null : kind,
    workstream.state === "open",
  )
  const items = useMemo(
    () => entries.data?.pages.flatMap((page) => page.items) ?? [],
    [entries.data],
  )
  const buckets = useMemo(() => bucketsByDay(items), [items])
  const selected = items.find((e) => e.id === selectedId) ?? null
  // Entries page oldest first, so a hit on a recent entry of a long
  // workstream sits past the first page; page forward until it has loaded.
  const focusPending =
    initialEntryId !== undefined && selectedId === initialEntryId && selected === null
  const { hasNextPage, isFetchingNextPage, fetchNextPage } = entries
  useEffect(() => {
    if (focusPending && hasNextPage && !isFetchingNextPage) void fetchNextPage()
  }, [focusPending, hasNextPage, isFetchingNextPage, fetchNextPage])

  let body
  if (entries.isError) {
    body = (
      <EmptyState
        kind="failed"
        title="Could not read this workstream"
        description={entries.error.message}
      />
    )
  } else if (entries.isPending) {
    body = <Skeleton className="h-64 w-full" />
  } else if (items.length === 0 && kind !== "all") {
    body = <EmptyState kind="filtered" title={`No ${kind} entries`} />
  } else if (items.length === 0) {
    body = <EmptyState kind="empty" title="No entries yet" />
  } else {
    body = (
      <div className="grid gap-3 lg:grid-cols-2">
        <VirtualizedTimeline<WorklogEntry>
          className="h-96"
          layout="list"
          rowHeight={ROW_HEIGHT}
          granularity="day"
          buckets={buckets}
          getItemId={(entry) => entry.id}
          onItemClick={(entry) => setSelectedId(entry.id)}
          renderItem={({ item }) => (
            <EntryRow entry={item} selected={item.id === selectedId} />
          )}
        />
        <EntryDetail entry={selected} />
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <SegmentGroup
        value={kind}
        onValueChange={(next) => {
          if (next) {
            setKind(next as KindFilter)
            setSelectedId(null)
          }
        }}
        variant="default"
        aria-label="entry kind"
      >
        <SegmentGroupIndicator />
        <SegmentGroupItem value="all">All</SegmentGroupItem>
        <SegmentGroupItem value="checkpoint">Checkpoints</SegmentGroupItem>
        <SegmentGroupItem value="ledger">Ledger</SegmentGroupItem>
        <SegmentGroupItem value="note">Notes</SegmentGroupItem>
      </SegmentGroup>
      {body}
      {entries.hasNextPage ? (
        <Button
          variant="outline"
          disabled={entries.isFetchingNextPage}
          onClick={() => void entries.fetchNextPage()}
        >
          Load later entries
        </Button>
      ) : null}
    </div>
  )
}
