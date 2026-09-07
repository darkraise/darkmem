import { useEffect, useRef, useState } from "react"
import { Textarea } from "darkraise-ui/components/textarea"
import { cn } from "darkraise-ui/lib"
import {
  useBlockDelete,
  useBlockInsert,
  useBlockUpdate,
  type BlockRow,
} from "@/hooks/api"
import { BlockView } from "./block-view"

/** Promote a block's source to its type, mirroring the serialiser's emit
 *  rules and nothing more.
 *
 *  This duplicates `backend/app/services/block_serializer.py`'s markers in
 *  TypeScript, which is a real duplication and is why the fixtures below
 *  match the ones that module's tests use. `block_serializer` is the
 *  authority; if the two disagree, it wins.
 *
 *  Deleting a marker DEMOTES: no marker means paragraph. That is only
 *  possible because the editor holds `source` rather than `text` -- with the
 *  marker never shown, it could never be deleted.
 *
 *  `stored` is the block's own type, and it decides the fallback for the one
 *  type that has no marker to read back: an `html` block's source IS its
 *  text, so every marker rule misses it and the fallback would demote it to
 *  paragraph on its first edit. That is not cosmetic -- `blocks.search_vector`
 *  blanks `type IN ('code','html')` because that text is source, so a demoted
 *  block is indexed as prose and stops rendering through `CodeBlock`.
 *  The type is PRESERVED, never inferred: CommonMark's type-7 rule makes
 *  `<b>bold</b> text` a paragraph, so a leading-`<` test would start
 *  misclassifying ordinary prose.
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

/** The editor: one editable per block, holding that block's markdown source.
 *
 *  No framework (spec §8.3). The storage format and the edit format are the
 *  same string, which is what removes the conversion step where round-trip
 *  fidelity dies. Accepted ceiling, restated so nobody discovers it: no drag
 *  handles, no table editing, no slash menu.
 */
export function BlockEditor({
  documentId,
  blocks,
}: {
  documentId: string
  blocks: BlockRow[]
}) {
  const [focused, setFocused] = useState<string | null>(null)
  const [draft, setDraft] = useState("")
  const [failure, setFailure] = useState<{ id: string; message: string } | null>(null)
  const update = useBlockUpdate(documentId)
  const insert = useBlockInsert(documentId)
  const remove = useBlockDelete(documentId)
  const area = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    if (focused) area.current?.focus()
  }, [focused])

  const sourceOf = (block: BlockRow) => block.source ?? block.text

  const commit = (block: BlockRow) => {
    const next = draft
    setFocused(null)
    if (next === sourceOf(block)) return
    const { type, text, properties } = promote(next, block.type)
    update.mutate(
      { blockId: block.block_id, text, type, properties: properties ?? null },
      {
        onError: (error) =>
          setFailure({ id: block.block_id, message: String(error) }),
      },
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
                  insert.mutate({
                    type: "paragraph",
                    text: "",
                    afterBlockId: block.block_id,
                  })
                } else if (e.key === "Backspace" && draft === "") {
                  e.preventDefault()
                  setFocused(null)
                  remove.mutate({ blockId: block.block_id })
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
