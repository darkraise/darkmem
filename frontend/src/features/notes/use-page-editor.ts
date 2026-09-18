import { useEffect } from "react"
import { filterSuggestionItems, insertOrUpdateBlockForSlashMenu } from "@blocknote/core/extensions"
import {
  getDefaultReactSlashMenuItems,
  useCreateBlockNote,
  type DefaultReactSuggestionItem,
} from "@blocknote/react"
import type { EditorBlockLike } from "./lib/block-mapping"
import type { CalloutVariant } from "./lib/block-properties"
import { pageSchema, type PageEditorInstance } from "./lib/editor-schema"
import { addsNestingViolation } from "./lib/nesting-guard"

/** The built-in slash menu entries a page offers. Headings 4-6 stay
 *  loadable but are not offered; emoji and every file block are out. */
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
 *  rule installed as a transaction filter. */
export function usePageEditor(initialBlocks: EditorBlockLike[]): PageEditorInstance {
  const editor = useCreateBlockNote({
    schema: pageSchema,
    trailingBlock: false,
    tables: { headers: false, splitCells: false, cellBackgroundColor: false, cellTextColor: false },
    initialContent: initialBlocks.length > 0 ? (initialBlocks as never) : undefined,
  })
  useEffect(
    () => editor.onBeforeChange(({ tr }) => (addsNestingViolation(tr.before, tr.doc) ? false : undefined)),
    [editor],
  )
  return editor
}
