import { useMemo, useState } from "react"
import { Button } from "darkraise-ui/components/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "darkraise-ui/components/sheet"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { EmptyState } from "@/components/darkmem"
import { useDocumentRevision, useDocumentRevisions } from "@/hooks/api"
import { DEMO } from "@/lib/demo-flag"
import { formatWhen } from "@/lib/format"
import { LineDiff } from "./line-diff"

/** A document's revisions (spec §8) and a line diff between any two of them.
 *  Defaults to the two newest, so opening the sheet answers "what changed
 *  last". The server serves contents, not patches; the diff is computed here. */
export function RevisionsSheet({
  documentId,
  open,
  onOpenChange,
}: {
  documentId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const revisions = useDocumentRevisions(documentId, open)
  const items = useMemo(
    () => revisions.data?.pages.flatMap((page) => page.items) ?? [],
    [revisions.data],
  )
  const [picked, setPicked] = useState<{ from: string | null; to: string | null }>({
    from: null,
    to: null,
  })
  const to = picked.to ?? items[0]?.id ?? null
  const from = picked.from ?? items[1]?.id ?? null
  const after = useDocumentRevision(documentId, open ? to : null)
  const before = useDocumentRevision(documentId, open ? from : null)

  let comparison
  if (DEMO) {
    // The revision reads are disabled in demo mode and would stay pending.
    comparison = (
      <EmptyState
        kind="empty"
        title="No revisions in the demo"
        description="The demo files no documents, so it has no revisions to compare."
      />
    )
  } else if (revisions.isError) {
    comparison = (
      <EmptyState
        kind="failed"
        title="Could not read the revisions"
        description={revisions.error.message}
      />
    )
  } else if (revisions.isPending) {
    comparison = <Skeleton className="h-32 w-full" />
  } else if (items.length === 0) {
    comparison = (
      <EmptyState
        kind="empty"
        title="No revisions"
      />
    )
  } else if (items.length === 1) {
    comparison = (
      <p className="text-muted-foreground text-sm">
        Only one revision exists, so there is nothing to compare yet.
      </p>
    )
  } else if (before.isError || after.isError) {
    comparison = (
      <EmptyState
        kind="failed"
        title="Could not read a revision"
        description={(before.error ?? after.error)?.message}
      />
    )
  } else if (before.data && after.data) {
    comparison = <LineDiff before={before.data.content} after={after.data.content} />
  } else {
    comparison = <Skeleton className="h-32 w-full" />
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-2xl">
        <SheetHeader>
          <SheetTitle>Revisions</SheetTitle>
          <SheetDescription>
            Newest first. Pick two to compare.
          </SheetDescription>
        </SheetHeader>
        <div className="space-y-4 p-4">
          {items.length > 0 ? (
            <ul className="space-y-1">
              {items.map((revision) => {
                const short = revision.content_hash.slice(0, 8)
                return (
                  <li key={revision.id} className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="min-w-0 flex-1">
                      {formatWhen(revision.created_at)}
                      <span className="text-muted-foreground font-mono text-xs">
                        {" "}
                        · {revision.actor ?? "unknown"} · {short}
                      </span>
                    </span>
                    <Button
                      size="sm"
                      variant={revision.id === from ? "default" : "outline"}
                      aria-pressed={revision.id === from}
                      aria-label={`Compare from ${short}`}
                      onClick={() => setPicked({ from: revision.id, to })}
                    >
                      From
                    </Button>
                    <Button
                      size="sm"
                      variant={revision.id === to ? "default" : "outline"}
                      aria-pressed={revision.id === to}
                      aria-label={`Compare to ${short}`}
                      onClick={() => setPicked({ from, to: revision.id })}
                    >
                      To
                    </Button>
                  </li>
                )
              })}
            </ul>
          ) : null}
          {revisions.hasNextPage ? (
            <Button
              variant="outline"
              size="sm"
              disabled={revisions.isFetchingNextPage}
              onClick={() => void revisions.fetchNextPage()}
            >
              Older revisions
            </Button>
          ) : null}
          {comparison}
        </div>
      </SheetContent>
    </Sheet>
  )
}
