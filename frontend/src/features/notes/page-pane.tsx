import { useEffect, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import { usePageRename, type PageView } from "@/hooks/api"
import { PAGE_TITLE_FALLBACK } from "./lib/build-page-tree"
import { PageBlockEditor, type PageSaveStatus } from "./page-block-editor"

const SAVE_LABEL: Record<string, string> = {
  saving: "Saving…",
  saved: "Saved",
}

/** The title field and the body.
 *
 *  The title is `pages.title` over `PATCH /pages/{id}`, never a block, so it
 *  is the one edit here that does not go through the block queue.
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
  const [status, setStatus] = useState<PageSaveStatus>({ kind: "idle" })
  const field = useRef<HTMLInputElement | null>(null)

  // Remount-free page switch: the pane is keyed on nothing, so the draft has
  // to follow the page it is showing.
  useEffect(() => {
    setTitle(page.title ?? "")
    setStatus({ kind: "idle" })
  }, [page.id, page.title])

  useEffect(() => {
    if (autoFocusTitle) field.current?.focus()
  }, [autoFocusTitle, page.id])

  const commitTitle = () => {
    const next = title.trim()
    if (next === (page.title ?? "")) return
    rename.mutate({ pageId: page.id, title: next === "" ? null : next })
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-2">
      <div className="flex items-center gap-3">
        <Label htmlFor="page-title" className="sr-only">
          Page title
        </Label>
        <Input
          id="page-title"
          ref={field}
          aria-label="Page title"
          placeholder={PAGE_TITLE_FALLBACK}
          value={title}
          className="h-auto border-0 px-0 text-2xl font-semibold shadow-none focus-visible:ring-0"
          onChange={(e) => setTitle(e.target.value)}
          onBlur={commitTitle}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault()
              e.currentTarget.blur()
            }
          }}
        />
        {SAVE_LABEL[status.kind] ? (
          <span className="text-muted-foreground shrink-0 text-xs">
            {SAVE_LABEL[status.kind]}
          </span>
        ) : null}
      </div>

      {status.kind === "blocked" ? (
        <div className="border-destructive/50 flex items-center justify-between gap-3 rounded-md border border-dashed px-3 py-2">
          <p className="text-destructive text-sm">
            This page changed elsewhere — {status.message}
          </p>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => {
              setStatus({ kind: "idle" })
              void qc.invalidateQueries({ queryKey: ["page", page.id] })
            }}
          >
            Reload page
          </Button>
        </div>
      ) : null}

      <ScrollArea className="min-h-0 flex-1 pr-3">
        <PageBlockEditor pageId={page.id} blocks={page.blocks} onStatus={setStatus} />
      </ScrollArea>
    </div>
  )
}
