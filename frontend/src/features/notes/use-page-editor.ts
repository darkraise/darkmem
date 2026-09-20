import { useEffect } from "react"
import { filterSuggestionItems, insertOrUpdateBlockForSlashMenu } from "@blocknote/core/extensions"
import {
  getDefaultReactSlashMenuItems,
  useCreateBlockNote,
  type DefaultReactSuggestionItem,
} from "@blocknote/react"
import { toast } from "darkraise-ui/components/sonner"
import { isImageType, uploadAttachment } from "./lib/attachments"
import type { EditorBlockLike } from "./lib/block-mapping"
import type { CalloutVariant } from "./lib/block-properties"
import { pageSchema, type PageEditorInstance } from "./lib/editor-schema"
import { addsNestingViolation } from "./lib/nesting-guard"

/** The built-in slash menu entries a page offers. Headings 4-6 stay
 *  loadable but are not offered; emoji is out; the image and file blocks are
 *  offered. */
const SLASH_KEYS: ReadonlySet<string> = new Set([
  "paragraph",
  "heading",
  "heading_2",
  "heading_3",
  "bullet_list",
  "numbered_list",
  "check_list",
  "toggle_list",
  "quote",
  "code_block",
  "table",
  "image",
  "file",
  "divider",
])

const CALLOUT_ITEMS: readonly { variant: CalloutVariant; title: string }[] = [
  { variant: "info", title: "Callout: info" },
  { variant: "warning", title: "Callout: warning" },
  { variant: "error", title: "Callout: error" },
  { variant: "success", title: "Callout: success" },
]

/** The slash menu for `query`: the allowed built-ins plus one callout entry
 *  per variant. */
export function pageSlashItems(editor: PageEditorInstance, query: string): DefaultReactSuggestionItem[] {
  const builtIns = getDefaultReactSlashMenuItems(editor).filter((item) =>
    SLASH_KEYS.has((item as unknown as { key: string }).key),
  )
  const callouts: DefaultReactSuggestionItem[] = CALLOUT_ITEMS.map(({ variant, title }) => ({
    title,
    group: "Basic blocks",
    aliases: ["callout", "alert", variant],
    onItemClick: () => {
      insertOrUpdateBlockForSlashMenu(editor, { type: "callout", props: { variant } })
    },
  }))
  return filterSuggestionItems([...builtIns, ...callouts], query)
}

/** A page editor instance: the page schema and options, with the nesting
 *  rule installed as a transaction filter. `pageId` is the page attachments
 *  are uploaded for; without one the editor has no upload path at all, which
 *  is what keeps demo mode from making a request. */
export function usePageEditor(
  initialBlocks: EditorBlockLike[],
  pageId?: string,
): PageEditorInstance {
  const editor = useCreateBlockNote({
    schema: pageSchema,
    trailingBlock: false,
    domAttributes: { editor: { "aria-label": "Page content" } },
    tables: { headers: false, splitCells: false, cellBackgroundColor: false, cellTextColor: false },
    initialContent: initialBlocks.length > 0 ? (initialBlocks as never) : undefined,
    uploadFile:
      pageId === undefined
        ? undefined
        : async (file: File, blockId?: string) => {
            let uploaded
            try {
              uploaded = await uploadAttachment(pageId, file)
            } catch (error) {
              toast.error(error instanceof Error ? error.message : "The upload failed.")
              // The editor swapped its add-file button for a loader when the
              // upload started and resets it only when the node view is
              // rebuilt, which resolving the url it already has ("") does not
              // do. Retyping the block is a real change, so the operator is
              // left with an empty paragraph to retry in rather than a loader
              // that never finishes.
              if (blockId !== undefined && editor.getBlock(blockId)) {
                editor.updateBlock(blockId, { type: "paragraph", content: [] } as never)
              }
              return ""
            }
            const type = isImageType(uploaded.contentType) ? "image" : "file"
            const placed = blockId === undefined ? undefined : editor.getBlock(blockId)
            if (placed && (placed.type === "image" || placed.type === "file")) {
              if (placed.type !== type) editor.updateBlock(placed, { type } as never)
              return uploaded.url
            }
            // The block the editor meant to fill is not a file block: either
            // the nesting rule refused a conversion it attempted in place, or
            // the block was removed while the upload was in flight. Either
            // way the file is already stored, so it is placed rather than
            // dropped, and the empty return leaves the editor's own follow-up
            // with nothing to change.
            const anchor = placed ?? editor.document[editor.document.length - 1]
            if (!anchor) {
              toast.error("The file was uploaded but there was nowhere to put it.")
              return ""
            }
            editor.insertBlocks(
              [{ type, props: { url: uploaded.url, name: file.name } } as never],
              anchor,
              "after",
            )
            return ""
          },
  })
  useEffect(
    () => editor.onBeforeChange(({ tr }) => (addsNestingViolation(tr.before, tr.doc) ? false : undefined)),
    [editor],
  )
  return editor
}
