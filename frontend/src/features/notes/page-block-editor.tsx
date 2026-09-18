import { useEffect, useRef, useState } from "react"
import { Textarea } from "darkraise-ui/components/textarea"
import { cn } from "darkraise-ui/lib"
import { BlockView } from "@/features/documents/components/block-view"
import {
  usePageBlockDelete,
  usePageBlockInsert,
  usePageBlockUpdate,
  type BlockRow,
} from "@/hooks/api"

/** Promote a block's source to its type, mirroring the serialiser's emit
 *  rules and nothing more.
 *
 *  This duplicates `backend/app/services/block_serializer.py`'s markers in
 *  TypeScript. `block_serializer` is the authority; if the two disagree, it
 *  wins. It offers none of the page-only markers -- to-do, toggle and callout
 *  reach a page through the editor B3 ships, never through a markdown marker
 *  here.
 *
 *  Deleting a marker DEMOTES: no marker means paragraph. That is only
 *  possible because the editor holds `source` rather than `text`.
 *
 *  `stored` decides the fallback for the one type with no marker to read
 *  back: an `html` block's source IS its text, so every marker rule misses it
 *  and the fallback would demote it to paragraph on its first edit.
 */
export function promote(
  source: string,
  stored?: string | null,
): {
  type: string
  text: string
  properties?: Record<string, unknown>
} {
  const heading = /^(#{1,6})\s+(.*)$/.exec(source)
  if (heading) {
    return {
      type: "heading",
      text: heading[2] ?? "",
      properties: { level: heading[1]!.length },
    }
  }
  if (/^(?:-{3,}|\*{3,}|_{3,})\s*$/.test(source.trim())) {
    return { type: "divider", text: "" }
  }
  const list = /^([-*+]|\d+[.)])\s+([\s\S]*)$/.exec(source)
  if (list) {
    return { type: "list", text: list[2] ?? "", properties: { marker: list[1] } }
  }
  const quote = /^>\s?([\s\S]*)$/.exec(source)
  if (quote) return { type: "quote", text: quote[1] ?? "" }
  if (source.startsWith("```")) {
    const lines = source.split("\n")
    return { type: "code", text: lines.slice(1, -1).join("\n") }
  }
  if (stored === "html") return { type: "html", text: source }
  return { type: "paragraph", text: source }
}

export type PageSaveStatus =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved" }
  | { kind: "blocked"; message: string }

/** A deliberate copy of `features/documents/components/block-editor.tsx` over
 *  the page hooks, recorded as a duplicate that B3 deletes. The document
 *  editor is not parameterised, so `/documents` does not change.
 *
 *  It reports its save state upward rather than rendering it, because spec §6
 *  puts that state and the refusal banner in the pane's header.
 */
export function PageBlockEditor({
  pageId,
  blocks,
  onStatus,
}: {
  pageId: string
  blocks: BlockRow[]
  onStatus: (status: PageSaveStatus) => void
}) {
  const [focused, setFocused] = useState<string | null>(null)
  const [draft, setDraft] = useState("")
  const [failure, setFailure] = useState<{ id: string; message: string } | null>(null)
  const update = usePageBlockUpdate(pageId)
  const insert = usePageBlockInsert(pageId)
  const remove = usePageBlockDelete(pageId)
  const area = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    if (focused) area.current?.focus()
  }, [focused])

  const sourceOf = (block: BlockRow) => block.source ?? block.text

  const report = (status: PageSaveStatus) => onStatus(status)

  const settle = (blockId: string) => ({
    onSuccess: () => {
      setFailure(null)
      report({ kind: "saved" })
    },
    onError: (error: unknown) => {
      const message = error instanceof Error ? error.message : String(error)
      setFailure({ id: blockId, message })
      report({ kind: "blocked", message })
    },
  })

  const commit = (block: BlockRow) => {
    const next = draft
    setFocused(null)
    if (next === sourceOf(block)) return
    const { type, text, properties } = promote(next, block.type)
    report({ kind: "saving" })
    update.mutate(
      { blockId: block.block_id, text, type, properties: properties ?? null },
      settle(block.block_id),
    )
  }

  return (
    <div className="space-y-1.5">
      {blocks.map((block) => (
        <div key={block.block_id} id={block.block_id}>
          {focused === block.block_id ? (
            <Textarea
              ref={area}
              value={draft}
              rows={Math.max(1, draft.split("\n").length)}
              aria-label="block source"
              className="font-mono text-sm"
              onChange={(e) => setDraft(e.target.value)}
              onBlur={() => commit(block)}
              onKeyDown={(e) => {
                if (e.key === "Escape") {
                  commit(block)
                } else if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault()
                  commit(block)
                  report({ kind: "saving" })
                  insert.mutate(
                    { type: "paragraph", text: "", afterBlockId: block.block_id },
                    settle(block.block_id),
                  )
                } else if (e.key === "Backspace" && draft === "") {
                  e.preventDefault()
                  setFocused(null)
                  report({ kind: "saving" })
                  remove.mutate({ blockId: block.block_id }, settle(block.block_id))
                }
              }}
            />
          ) : (
            <button
              type="button"
              className={cn(
                "hover:bg-muted/40 block w-full rounded px-1 py-0.5 text-left",
              )}
              onClick={() => {
                setDraft(sourceOf(block))
                setFocused(block.block_id)
              }}
            >
              <BlockView block={block} />
            </button>
          )}
          {failure?.id === block.block_id ? (
            <p className="text-destructive text-sm">
              the edit was not saved — {failure.message}
            </p>
          ) : null}
        </div>
      ))}
    </div>
  )
}
