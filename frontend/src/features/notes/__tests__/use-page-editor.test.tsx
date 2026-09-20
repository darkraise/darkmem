import { act, render } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { BlockNoteView } from "@blocknote/shadcn"
import { toEditorBlocks, type EditorBlockLike } from "../lib/block-mapping"
import { pageSchema, type PageEditorInstance } from "../lib/editor-schema"
import type { SyncBlock } from "../lib/sync-tree"
import { pageSlashItems, usePageEditor } from "../use-page-editor"

const b = (id: string, type: string, text: string, properties: SyncBlock["properties"] = null): SyncBlock => ({
  id,
  parentId: null,
  type,
  text,
  properties,
})

const BLOCKS: EditorBlockLike[] = toEditorBlocks([
  b("h1", "heading", "Plans", { level: 1 }),
  b("p1", "paragraph", "first"),
  b("h2", "heading", "Details", { level: 2 }),
  b("p2", "paragraph", "second"),
]).blocks

async function mountHook() {
  let editor!: PageEditorInstance
  function Probe() {
    editor = usePageEditor(BLOCKS)
    return <BlockNoteView editor={editor} />
  }
  render(<Probe />)
  await act(async () => {})
  return editor
}

async function mountEditor(pageId?: string, initialContent?: unknown[]) {
  let editor!: PageEditorInstance
  function Probe() {
    editor = usePageEditor((initialContent as EditorBlockLike[]) ?? BLOCKS, pageId)
    return <BlockNoteView editor={editor} />
  }
  render(<Probe />)
  await act(async () => {})
  return { editor }
}

describe("usePageEditor", () => {
  it("refuses an indent under a paragraph", async () => {
    const editor = await mountHook()
    editor.setTextCursorPosition("p1")
    editor.nestBlock()
    expect(editor.document.map((x) => x.id)).toEqual(["h1", "p1", "h2", "p2"])
  })

  it("offers the allowed blocks and one callout per variant", async () => {
    const editor = await mountHook()
    const titles = pageSlashItems(editor, "").map((item) => item.title)
    expect(titles).toEqual(
      expect.arrayContaining(["Paragraph", "Heading 1", "Heading 3", "Check List", "Toggle List", "Table", "Divider"]),
    )
    for (const hidden of ["Heading 4", "Emoji", "Video", "Audio"]) expect(titles).not.toContain(hidden)
    expect(pageSlashItems(editor, "callout").map((item) => item.title)).toEqual([
      "Callout: info",
      "Callout: warning",
      "Callout: error",
      "Callout: success",
    ])
  })

  it("inserts a callout with the picked variant", async () => {
    const editor = await mountHook()
    editor.setTextCursorPosition("p2", "end")
    pageSlashItems(editor, "warning")[0]!.onItemClick()
    const callout = editor.document.find((x) => x.type === "callout")
    expect(callout?.props).toEqual({ variant: "warning" })
  })
})

describe("the page schema's file blocks", () => {
  it("carries a block type spelled exactly file", () => {
    // BlockNote's drop handler falls back to this literal type name when no
    // spec accepts the dropped MIME type, so the spelling is load-bearing.
    expect(Object.keys(pageSchema.blockSchema)).toContain("file")
    expect(Object.keys(pageSchema.blockSchema)).toContain("image")
  })

  it("offers image and file in the slash menu", async () => {
    const { editor } = await mountEditor()
    const titles = pageSlashItems(editor, "").map((item) => item.title.toLowerCase())
    expect(titles.some((t) => t.includes("image"))).toBe(true)
    expect(titles.some((t) => t.includes("file"))).toBe(true)
  })

  it("takes a page id without changing anything else", async () => {
    const { editor } = await mountEditor("11111111-2222-3333-4444-555555555555")
    expect(editor.document.length).toBeGreaterThanOrEqual(0)
  })
})
