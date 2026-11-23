import {
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type Ref,
} from "react"
import { Button } from "darkraise-ui/components/button"
import { toast } from "darkraise-ui/components/sonner"
import { Textarea } from "darkraise-ui/components/textarea"
import { cn } from "darkraise-ui/lib"
import {
  useBlockDelete,
  useBlockInsert,
  useBlockUpdate,
  useBlockWriteRecovery,
  type BlockRow,
} from "@/hooks/api"
import { ApiError } from "@/lib/api"
import { QueuedWriteDiscarded } from "../lib/mutation-queue"
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
 *  paragraph on its first edit. That is not cosmetic -- a demoted block
 *  stops rendering through `CodeBlock` and its raw markup is stored and
 *  served as prose.
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

/** A write the editor has sent and not yet seen confirmed. An update keeps
 *  its typed text on screen until the server takes it, and a failed write of
 *  any kind stays until the operator retries or discards it: the document's
 *  queue sends nothing else meanwhile. */
interface HeldWrite {
  kind: "update" | "insert" | "delete"
  draft: string | null
  message: string | null
  busy: boolean
}

/** What the editor still holds: `refused` covers writes queued behind a
 *  refused one, since the document's queue sends nothing until it is
 *  retried or discarded. */
export type HeldWrites = "none" | "saving" | "refused"

/** Actions a parent outside the editor (the leave guard) can take. */
export interface BlockEditorControls {
  /** Focus the refused block's edit box, or the block when it has none. */
  restoreFocus: () => void
  /** Discard the refused writes as the block's own Discard button does. */
  discardHeld: () => void
}

function failureMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Could not save"
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
  onHeldWritesChange,
  controls,
}: {
  documentId: string
  blocks: BlockRow[]
  onHeldWritesChange?: (state: HeldWrites) => void
  controls?: Ref<BlockEditorControls>
}) {
  const [focused, setFocused] = useState<string | null>(null)
  const [draft, setDraft] = useState("")
  const [held, setHeld] = useState<Record<string, HeldWrite>>({})
  /** The block a first Escape over unsaved text armed for discarding. */
  const [armedEscape, setArmedEscape] = useState<string | null>(null)
  /** The block a first Backspace on an empty draft armed for deletion. A
   *  delete has no undo, so it takes a second press, not one keystroke too
   *  many while clearing a line. */
  const [armedDelete, setArmedDelete] = useState<string | null>(null)
  const update = useBlockUpdate(documentId)
  const insert = useBlockInsert(documentId)
  const remove = useBlockDelete(documentId)
  const recovery = useBlockWriteRecovery(documentId)
  const area = useRef<HTMLTextAreaElement | null>(null)
  const container = useRef<HTMLDivElement | null>(null)
  /** Set by Escape so the blur that follows closing the textarea does not
   *  commit the draft Escape just discarded. */
  const discarding = useRef(false)
  // The reader's own list indentation, so entering edit mode does not shift
  // nested items to the left edge.
  const depths = useMemo(() => listDepths(blocks), [blocks])

  useEffect(() => {
    const box = area.current
    if (!focused || !box) return
    box.focus()
    box.setSelectionRange(box.value.length, box.value.length)
  }, [focused])

  const heldState: HeldWrites = Object.values(held).some(
    (write) => write.message !== null,
  )
    ? "refused"
    : Object.keys(held).length > 0
      ? "saving"
      : "none"

  const reportHeld = useRef(onHeldWritesChange)
  useEffect(() => {
    reportHeld.current = onHeldWritesChange
  }, [onHeldWritesChange])
  useEffect(() => {
    reportHeld.current?.(heldState)
  }, [heldState])

  // A write in flight is not held against an in-app navigation, so its
  // refusal can arrive after this editor is gone, with nothing left on screen
  // to show it.
  const mounted = useRef(false)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      reportHeld.current?.("none")
    }
  }, [])

  // A write in flight is lost with the tab as surely as a refused one.
  useEffect(() => {
    if (heldState === "none") return
    const onLeave = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ""
    }
    window.addEventListener("beforeunload", onLeave)
    return () => window.removeEventListener("beforeunload", onLeave)
  }, [heldState])

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

  const hold = (id: string, write: HeldWrite | null) =>
    setHeld((current) => {
      const next = { ...current }
      if (write) next[id] = write
      else delete next[id]
      return next
    })

  const release = (id: string, kind: HeldWrite["kind"]) =>
    setHeld((current) => {
      if (current[id]?.kind !== kind) return current
      const next = { ...current }
      delete next[id]
      return next
    })

  // Settled through each write's own promise: per-call mutate callbacks run
  // only for an observer's latest mutate, so a second block's write would
  // leave the first block's state unsettled.
  const settle = (
    write: Promise<unknown>,
    block: BlockRow,
    kind: HeldWrite["kind"],
    draftText: string | null = null,
  ) =>
    write.then(
      () => release(block.block_id, kind),
      (error: unknown) => {
        if (error instanceof QueuedWriteDiscarded) {
          release(block.block_id, kind)
          return
        }
        if (!mounted.current) {
          toast.error(
            `A block edit was not saved after you left the document: ${failureMessage(error)}`,
          )
          return
        }
        hold(block.block_id, {
          kind,
          draft: draftText,
          message: failureMessage(error),
          busy: false,
        })
      },
    )

  const updateFor = (block: BlockRow, source: string) => {
    const { type, text, properties } = promote(
      source,
      block.type,
      block.source == null ? "" : prefixOf(block),
    )
    return {
      blockId: block.block_id,
      text,
      type,
      properties: properties ?? null,
    }
  }

  const commit = (block: BlockRow) => {
    if (discarding.current) {
      discarding.current = false
      return
    }
    const next = draft
    setFocused(null)
    setArmedDelete(null)
    setArmedEscape(null)
    if (next === sourceOf(block)) return
    hold(block.block_id, {
      kind: "update",
      draft: next,
      message: null,
      busy: true,
    })
    void settle(
      update.mutateAsync(updateFor(block, next)),
      block,
      "update",
      next,
    )
  }

  const retryHeld = (block: BlockRow, write: HeldWrite) => {
    hold(block.block_id, { ...write, busy: true })
    recovery
      .retry(write.draft === null ? undefined : updateFor(block, write.draft))
      .then(
        () => release(block.block_id, write.kind),
        (error: unknown) =>
          hold(block.block_id, {
            ...write,
            message: failureMessage(error),
            busy: false,
          }),
      )
  }

  const discardHeld = (blockId: string, write: HeldWrite) => {
    recovery.discard()
    release(blockId, write.kind)
  }

  useImperativeHandle(
    controls,
    () => ({
      restoreFocus: () => {
        const refused = Object.entries(held).find(
          ([, write]) => write.message !== null,
        )
        if (!refused) return
        const node = container.current?.querySelector<HTMLElement>(
          `[id="${refused[0]}"]`,
        )
        const target =
          node?.querySelector<HTMLElement>("textarea") ??
          node?.querySelector<HTMLElement>("button")
        target?.focus()
      },
      discardHeld: () => {
        // A refusal pauses the queue, so every other held write is queued
        // behind it, unsent, and goes with it.
        if (!Object.values(held).some((write) => write.message !== null)) return
        recovery.discardAll()
        for (const [id, write] of Object.entries(held)) release(id, write.kind)
      },
    }),
  )

  return (
    <div ref={container} className="space-y-1.5">
      <p className="text-muted-foreground pb-1 text-xs">
        Click a block to edit its markdown · Esc cancels (twice over unsaved
        text) · Ctrl+Enter adds a block below · Backspace twice on an empty
        block deletes it
      </p>
      {blocks.map((block) => {
        const write = held[block.block_id]
        // A refused write pauses the document's queue, so every other
        // pending write is waiting, not being sent.
        const waiting = Object.entries(held).some(
          ([id, other]) => id !== block.block_id && other.message !== null,
        )
        return (
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
                setArmedEscape(null)
              }}
              onBlur={() => commit(block)}
              onKeyDown={(e) => {
                if (e.key === "Escape") {
                  // Cancels: the draft is dropped, the block keeps its
                  // stored source, and nothing is sent. Typed text is not
                  // dropped on one keystroke.
                  e.preventDefault()
                  if (
                    draft !== sourceOf(block) &&
                    armedEscape !== block.block_id
                  ) {
                    setArmedEscape(block.block_id)
                    return
                  }
                  discarding.current = true
                  setArmedDelete(null)
                  setArmedEscape(null)
                  setFocused(null)
                } else if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault()
                  commit(block)
                  void settle(
                    insert.mutateAsync({
                      type: "paragraph",
                      text: "",
                      afterBlockId: block.block_id,
                      parentId: block.parent_id,
                    }),
                    block,
                    "insert",
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
                  void settle(
                    remove.mutateAsync({ blockId: block.block_id }),
                    block,
                    "delete",
                  )
                }
              }}
            />
          ) : write?.draft != null ? (
            <Textarea
              value={write.draft}
              readOnly={write.busy}
              rows={Math.max(1, write.draft.split("\n").length)}
              aria-label="block source"
              className="font-mono text-sm"
              onChange={(e) =>
                hold(block.block_id, { ...write, draft: e.target.value })
              }
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
          {armedEscape === block.block_id ? (
            <p role="status" className="text-muted-foreground text-xs">
              Press Escape again to discard your changes.
            </p>
          ) : null}
          {write?.busy && write.message === null ? (
            <p role="status" className="text-muted-foreground text-xs">
              {waiting
                ? "Waiting — not sent until the unsaved edit is retried or discarded"
                : "Saving…"}
            </p>
          ) : null}
          {write?.message != null ? (
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <p role="alert" className="text-destructive-text text-sm">
                Not saved: {write.message}
              </p>
              <Button
                size="sm"
                variant="outline"
                disabled={write.busy}
                onClick={() => retryHeld(block, write)}
              >
                Retry
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={write.busy}
                onClick={() => discardHeld(block.block_id, write)}
              >
                Discard
              </Button>
            </div>
          ) : null}
        </div>
        )
      })}
    </div>
  )
}
