import { act, render } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { BlockNoteView } from "@blocknote/shadcn"
import { toast } from "darkraise-ui/components/sonner"
import { uploadAttachment } from "../lib/attachments"
import { toEditorBlocks, type EditorBlockLike } from "../lib/block-mapping"
import { pageSchema, type PageEditorInstance } from "../lib/editor-schema"
import type { SyncBlock } from "../lib/sync-tree"
import { pageSlashItems, usePageEditor } from "../use-page-editor"

vi.mock("darkraise-ui/components/sonner", () => ({ toast: { error: vi.fn() } }))

vi.mock("../lib/attachments", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../lib/attachments")>()),
  uploadAttachment: vi.fn(),
}))

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

  it("keeps the callouts inside the one Basic blocks run", async () => {
    const editor = await mountHook()
    // The menu draws a header at each change of group, so a group must be
    // one contiguous run or its header appears twice.
    const groups = pageSlashItems(editor, "").map((item) => item.group)
    const runs = groups.filter((group, i) => group !== groups[i - 1])
    expect(new Set(runs).size).toBe(runs.length)
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
    expect(editor.document.map((x) => x.id)).toEqual(["h1", "p1", "h2", "p2"])
  })
})

const PAGE = "11111111-2222-3333-4444-555555555555"
const URL_A = "/api/v1/pages/attachments/0123abcd-4567-89ef-0123-456789abcdef"

describe("uploadFile", () => {
  // The braces matter: vitest calls a value a hook returns as the test's
  // teardown, and `mockReset` returns the mock itself -- so an expression body
  // invokes the rejecting mock with nothing to catch it.
  beforeEach(() => {
    vi.mocked(uploadAttachment).mockReset()
  })

  it("is absent without a page id, so demo mode makes no request", async () => {
    const { editor } = await mountEditor()
    expect(editor.uploadFile).toBeUndefined()
  })

  it("returns the url and keeps an image block an image", async () => {
    vi.mocked(uploadAttachment).mockResolvedValue({ url: URL_A, contentType: "image/png" })
    const { editor } = await mountEditor(PAGE, [{ type: "image", props: { url: "", name: "a.png" } }])
    const id = editor.document[0]!.id
    await act(async () => {
      await expect(editor.uploadFile!(new File(["a"], "a.png"), id)).resolves.toBe(URL_A)
    })
    expect(editor.getBlock(id)!.type).toBe("image")
  })

  // The route sniffs the bytes and serves anything but the four image types
  // as a download, so an image block pointing at one would render nothing.
  it("retypes to a file block when the stored type is not an inline image", async () => {
    vi.mocked(uploadAttachment).mockResolvedValue({ url: URL_A, contentType: "application/octet-stream" })
    const { editor } = await mountEditor(PAGE, [{ type: "image", props: { url: "", name: "a.svg" } }])
    const id = editor.document[0]!.id
    await act(async () => {
      await editor.uploadFile!(new File(["a"], "a.svg"), id)
    })
    expect(editor.getBlock(id)!.type).toBe("file")
  })

  it("toasts and retypes the block to a paragraph when the upload is refused", async () => {
    vi.mocked(uploadAttachment).mockRejectedValue(new Error("attachment exceeds 52428800 bytes"))
    const { editor } = await mountEditor(PAGE, [{ type: "image", props: { url: "", name: "a.png" } }])
    const id = editor.document[0]!.id
    await act(async () => {
      await expect(editor.uploadFile!(new File(["a"], "a.png"), id)).resolves.toBe("")
    })
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith("attachment exceeds 52428800 bytes")
    expect(editor.getBlock(id)!.type).toBe("paragraph")
  })

  // The editor replaces any block whose content is an empty array, not only
  // an empty paragraph, so a paste into an empty list item holding a child
  // retypes that item -- which the nesting rule refuses, leaving a block that
  // never became the attachment.
  it("inserts the attachment beside a block the nesting rule kept as it was", async () => {
    vi.mocked(uploadAttachment).mockResolvedValue({ url: URL_A, contentType: "image/png" })
    const { editor } = await mountEditor(PAGE, [
      { type: "bulletListItem", content: [], children: [{ type: "paragraph", content: "kid" }] },
    ])
    const id = editor.document[0]!.id
    await act(async () => {
      await expect(editor.uploadFile!(new File(["a"], "a.png"), id)).resolves.toBe("")
    })
    expect(editor.document.map((b) => b.type)).toEqual(["bulletListItem", "image"])
    expect((editor.document[1]! as { props: { url: string } }).props.url).toBe(URL_A)
  })
})
