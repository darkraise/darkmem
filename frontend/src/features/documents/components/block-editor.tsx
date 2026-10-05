import { useEffect, useMemo, useRef, useState } from "react"
import { Textarea } from "darkraise-ui/components/textarea"
import { cn } from "darkraise-ui/lib"
import {
  useBlockDelete,
  useBlockInsert,
  useBlockUpdate,
  type BlockRow,
} from "@/hooks/api"
import { BlockView } from "./block-view"
import { listDepths } from "./document-reader"

function stripAncestorPrefix(source: string, prefix: string): string {
  if (!prefix) return source
  const ancestorPattern = new RegExp(`^${prefix.replace(/> /g, "> ?")}`)
  const emptyPattern = new RegExp(
    `^${prefix.trimEnd().replace(/> ?/g, "> ?")}$`,
  )
  return source
    .split("\n")
    .map((line) =>
      emptyPattern.test(line) ? "" : line.replace(ancestorPattern, ""),
    )
    .join("\n")
}

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
  prefix = "",
): {
  type: string
  text: string
  properties?: Record<string, unknown>
} {
  source = stripAncestorPrefix(source, prefix)
  const setext =
    !/^(`{3,}|~{3,})/.test(source) &&
    /^([\s\S]+)\n(={3,}|-{3,})[ \t]*$/.exec(source)
  if (setext) {
    return {
      type: "heading",
      text: setext[1]!,
      properties: { level: setext[2]!.startsWith("=") ? 1 : 2 },
    }
  }
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
  const list = /^([-*+]|\d+[.)])[ \t]([\s\S]*)$/.exec(source)
  if (list) {
    const indent = " ".repeat(list[1]!.length + 1)
    const lines = (list[2] ?? "").split("\n")
    return {
      type: "list",
      text: lines
        .map((line, index) =>
          index > 0 && line.startsWith(indent)
            ? line.slice(indent.length)
            : line,
        )
        .join("\n"),
      properties: { marker: list[1] },
    }
  }
  if (source.startsWith(">")) {
    return {
      type: "quote",
      text: source
        .split("\n")
        .map((line) => line.replace(/^> ?/, ""))
        .join("\n"),
    }
  }
  const fence = /^(`{3,}|~{3,})([^\n]*)\n?/.exec(source)
  if (fence) {
    const lines = source.split("\n")
    const closing = new RegExp(`^${fence[1]![0]}{${fence[1]!.length},}[ \\t]*$`)
    const end =
      lines.length > 1 && closing.test(lines[lines.length - 1]!)
        ? -1
        : undefined
    return {
      type: "code",
      text: lines.slice(1, end).join("\n"),
      properties: { language: fence[2]!.trim() },
    }
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
  const [failure, setFailure] = useState<{
    id: string
    message: string
  } | null>(null)
  /** The block a first Backspace on an empty draft armed for deletion. A
   *  delete has no undo, so it takes a second press, not one keystroke too
   *  many while clearing a line. */
  const [armedDelete, setArmedDelete] = useState<string | null>(null)
  const update = useBlockUpdate(documentId)
  const insert = useBlockInsert(documentId)
  const remove = useBlockDelete(documentId)
  const area = useRef<HTMLTextAreaElement | null>(null)
  /** Set by Escape so the blur that follows closing the textarea does not
   *  commit the draft Escape just discarded. */
  const discarding = useRef(false)
  // The reader's own list indentation, so entering edit mode does not shift
  // nested items to the left edge.
  const depths = useMemo(() => listDepths(blocks), [blocks])

  useEffect(() => {
    if (focused) area.current?.focus()
  }, [focused])

  const sourceOf = (block: BlockRow) => block.source ?? block.text

  const prefixOf = (block: BlockRow, visited = new Set<string>()): string => {
    if (!block.parent_id || visited.has(block.block_id)) return ""
    visited.add(block.block_id)
    const parent = blocks.find(
      (candidate) => candidate.block_id === block.parent_id,
    )
    if (!parent) return ""
    const prefix = prefixOf(parent, visited)
    if (parent.type === "quote") return prefix + "> "
    if (parent.type === "list") {
      const ownSource = stripAncestorPrefix(sourceOf(parent), prefix)
      const marker =
        /^([-*+]|\d+[.)]) /.exec(ownSource)?.[1] ??
        String(parent.properties?.marker ?? "-")
      return prefix + " ".repeat(marker.length + 1)
    }
    return prefix
  }

  const mutationOptions = (block: BlockRow) => ({
    onSuccess: () => setFailure(null),
    onError: (error: unknown) =>
      setFailure({ id: block.block_id, message: String(error) }),
  })

  const commit = (block: BlockRow) => {
    if (discarding.current) {
      discarding.current = false
      return
    }
    const next = draft
    setFocused(null)
    setArmedDelete(null)
    if (next === sourceOf(block)) return
    const { type, text, properties } = promote(
      next,
      block.type,
      block.source == null ? "" : prefixOf(block),
    )
    update.mutate(
      { blockId: block.block_id, text, type, properties: properties ?? null },
      mutationOptions(block),
    )
  }

  return (
    <div className="space-y-1.5">
      <p className="text-muted-foreground pb-1 text-xs">
        Click a block to edit its markdown · Esc cancels · Ctrl+Enter adds a
        block below · Backspace twice on an empty block deletes it
      </p>
      {blocks.map((block) => (
        <div
          key={block.block_id}
          id={block.block_id}
          data-depth={depths[block.block_id] ?? 0}
          style={
            (depths[block.block_id] ?? 0) > 0
              ? { paddingLeft: `${(depths[block.block_id] ?? 0) * 18}px` }
              : undefined
          }
        >
          {focused === block.block_id ? (
            <Textarea
              ref={area}
              value={draft}
              rows={Math.max(1, draft.split("\n").length)}
              aria-label="block source"
              className="font-mono text-sm"
              onChange={(e) => {
                setDraft(e.target.value)
                setArmedDelete(null)
              }}
              onBlur={() => commit(block)}
              onKeyDown={(e) => {
                if (e.key === "Escape") {
                  // Cancels: the draft is dropped, the block keeps its
                  // stored source, and nothing is sent.
                  e.preventDefault()
                  discarding.current = true
                  setArmedDelete(null)
                  setFocused(null)
                } else if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault()
                  commit(block)
                  insert.mutate(
                    {
                      type: "paragraph",
                      text: "",
                      afterBlockId: block.block_id,
                      parentId: block.parent_id,
                    },
                    mutationOptions(block),
                  )
                } else if (e.key === "Backspace" && draft === "") {
                  e.preventDefault()
                  if (armedDelete !== block.block_id) {
                    setArmedDelete(block.block_id)
                    return
                  }
                  discarding.current = true
                  setArmedDelete(null)
                  setFocused(null)
                  remove.mutate(
                    { blockId: block.block_id },
                    mutationOptions(block),
                  )
                }
              }}
            />
          ) : (
            <button
              type="button"
              className={cn(
                // Outlined, so edit mode does not look identical to reading:
                // each block is a target, and the hover says which.
                "ring-border/60 hover:ring-primary/50 hover:bg-muted/40 block w-full rounded px-1 py-0.5 text-left ring-1 transition-shadow",
              )}
              onClick={() => {
                discarding.current = false
                setArmedDelete(null)
                setDraft(sourceOf(block))
                setFocused(block.block_id)
              }}
            >
              <BlockView block={block} />
            </button>
          )}
          {armedDelete === block.block_id ? (
            <p role="status" className="text-muted-foreground text-xs">
              Press Backspace again to delete this block, or type to keep it.
            </p>
          ) : null}
          {failure?.id === block.block_id ? (
            <p role="alert" className="text-destructive text-sm">
              the edit was not saved — {failure.message}
            </p>
          ) : null}
        </div>
      ))}
    </div>
  )
}
