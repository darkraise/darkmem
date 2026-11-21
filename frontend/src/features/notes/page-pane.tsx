import { lazy, Suspense, useEffect, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import { pageQuery, usePageRename, type PageView } from "@/hooks/api"
import { PAGE_TITLE_FALLBACK } from "./lib/build-page-tree"
import type { SyncStatus } from "./lib/page-sync"
import { usePageSync } from "./use-page-sync"

const PageEditor = lazy(() =>
  import("./page-editor").then((m) => ({ default: m.PageEditor })),
)

const SAVE_LABEL: Partial<Record<SyncStatus["kind"], string>> = {
  saving: "Saving…",
  saved: "Saved",
  retrying: "Unsaved — retrying",
}

function bannerText(status: Extract<SyncStatus, { kind: "stopped" }>): string {
  return status.reason === "refused"
    ? `This edit was refused — ${status.message}`
    : status.message
}

/** The title field and the body.
 *
 *  The title is `pages.title` over `PATCH /pages/{id}`, never a block, so it
 *  is the one edit here that does not go through the save engine.
 */
export function PagePane({
  page,
  autoFocusTitle,
}: {
  page: PageView
  autoFocusTitle: boolean
}) {
  const qc = useQueryClient()
  const rename = usePageRename()
  const [title, setTitle] = useState(page.title ?? "")
  const [generation, setGeneration] = useState(0)
  const field = useRef<HTMLInputElement | null>(null)
  const sync = usePageSync(page, generation)

  // Remount-free page switch: the pane is keyed on nothing, so the draft has
  // to follow the page it is showing.
  useEffect(() => {
    setTitle(page.title ?? "")
  }, [page.id, page.title])

  useEffect(() => {
    if (autoFocusTitle) field.current?.focus()
  }, [autoFocusTitle, page.id])

  const commitTitle = () => {
    const next = title.trim()
    if (next === (page.title ?? "")) return
    // The field keeps the typed title on a refusal, so leaving it again
    // retries the rename.
    rename.mutate(
      { pageId: page.id, title: next === "" ? null : next },
      {
        onError: (error) =>
          toast.error(`Could not rename the page — ${error.message}`),
      },
    )
  }

  const reload = async () => {
    sync.discard()
    await qc.invalidateQueries({
      queryKey: pageQuery(page.id).queryKey,
      exact: true,
    })
    setGeneration((g) => g + 1)
  }

  const label = SAVE_LABEL[sync.status.kind]

  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      {/* The 48px gutter is room for BlockNote's side menu; under `lg` the
          stacked pane is a phone column, where that gutter broke the title
          mid-word, so it narrows. */}
      <div className="flex items-center gap-3 pl-4 lg:pl-12">
        <Label htmlFor="page-title" className="sr-only">
          Page title
        </Label>
        <Input
          id="page-title"
          ref={field}
          aria-label="Page title"
          placeholder={PAGE_TITLE_FALLBACK}
          value={title}
          // The page's own heading, not a form field: transparent, no
          // recess, and the largest type on the page (body headings are
          // stepped down in page-editor.css).
          className="h-auto border-0 bg-transparent px-0 text-3xl font-bold tracking-tight shadow-none focus-visible:ring-0 dark:bg-transparent"
          onChange={(e) => setTitle(e.target.value)}
          onBlur={commitTitle}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault()
              e.currentTarget.blur()
            }
          }}
        />
        {label ? (
          <span className="text-muted-foreground shrink-0 text-xs">
            {label}
          </span>
        ) : null}
      </div>

      {sync.status.kind === "stopped" ? (
        <div className="border-destructive-edge/50 flex items-center justify-between gap-3 rounded-md border border-dashed px-3 py-2">
          <div className="text-destructive-text text-sm">
            <p>{bannerText(sync.status)}</p>
            <p>
              Your unsaved draft is kept in this tab. Copy it from the editor
              before discarding or closing this tab.
            </p>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => void reload()}
          >
            Discard draft and reload
          </Button>
        </div>
      ) : null}

      <ScrollArea className="min-h-0 flex-1 pr-3 pl-4 lg:pl-12">
        <Suspense fallback={<Skeleton className="h-40 w-full" />}>
          <PageEditor
            key={`${page.id}:${generation}`}
            pageId={page.id}
            initialBlocks={sync.initialBlocks}
            editable={sync.status.kind !== "stopped"}
            onDocumentChange={sync.onDocumentChange}
            onBlur={sync.flushNow}
          />
        </Suspense>
      </ScrollArea>
    </div>
  )
}
