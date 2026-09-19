import "@blocknote/shadcn/style.css"
import "./page-editor.css"
import {
  BasicTextStyleButton,
  CreateLinkButton,
  FormattingToolbar,
  FormattingToolbarController,
  SuggestionMenuController,
} from "@blocknote/react"
import { BlockNoteView } from "@blocknote/shadcn"
import { useRef } from "react"
import type { EditorBlockLike } from "./lib/block-mapping"
import { useEditorControlLabels } from "./lib/editor-a11y"
import { PageOutline } from "./page-outline"
import { useDocumentMode } from "./use-document-mode"
import { pageSlashItems, usePageEditor } from "./use-page-editor"

export interface PageEditorProps {
  initialBlocks: EditorBlockLike[]
  editable: boolean
  onDocumentChange?: (blocks: EditorBlockLike[]) => void
  onBlur?: () => void
}

/** The page body. Loaded lazily with BlockNote's styles so neither reaches
 *  the main chunk.
 *
 *  darkraise-ui gap: BlockNote's shadcn slots (menus, popovers, selects) must
 *  not render into a portal, and darkraise-ui's DropdownMenu, Popover and
 *  Select do, so the package's own shadcn primitives render here. They read
 *  the same Tailwind colour tokens darkraise-ui defines, which is what keeps
 *  them on theme. */
export function PageEditor({ initialBlocks, editable, onDocumentChange, onBlur }: PageEditorProps) {
  const mode = useDocumentMode()
  const editor = usePageEditor(initialBlocks)
  const editorRoot = useRef<HTMLDivElement>(null)
  useEditorControlLabels(editorRoot, editor)

  return (
    <div className="flex min-h-0 gap-6">
      <div className="min-w-0 flex-1">
        <div ref={editorRoot} className="mx-auto max-w-3xl">
          <BlockNoteView
            editor={editor}
            editable={editable}
            theme={mode}
            slashMenu={false}
            formattingToolbar={false}
            emojiPicker={false}
            onChange={() => onDocumentChange?.(editor.document as unknown as EditorBlockLike[])}
            onBlur={onBlur}
          >
            <SuggestionMenuController
              triggerCharacter="/"
              getItems={async (query) => pageSlashItems(editor, query)}
            />
            <FormattingToolbarController
              formattingToolbar={() => (
                <FormattingToolbar>
                  <BasicTextStyleButton basicTextStyle="bold" />
                  <BasicTextStyleButton basicTextStyle="italic" />
                  <BasicTextStyleButton basicTextStyle="code" />
                  <BasicTextStyleButton basicTextStyle="strike" />
                  <CreateLinkButton />
                </FormattingToolbar>
              )}
            />
          </BlockNoteView>
        </div>
      </div>
      <aside className="hidden w-48 shrink-0 border-l border-border/40 pl-4 lg:block">
        <div className="sticky top-0">
          <PageOutline editor={editor} />
        </div>
      </aside>
    </div>
  )
}
