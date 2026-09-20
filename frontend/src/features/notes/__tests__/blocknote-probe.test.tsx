import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { act, render } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { BlockNoteEditor, defaultBlockSpecs } from "@blocknote/core"
import { getDefaultReactSlashMenuItems, useCreateBlockNote } from "@blocknote/react"
import { BlockNoteView } from "@blocknote/shadcn"
import { pageSchema, type PageEditorInstance } from "../lib/editor-schema"

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

async function mount(initialContent: unknown[]) {
  let editor!: PageEditorInstance
  function Probe() {
    editor = useCreateBlockNote({
      schema: pageSchema,
      trailingBlock: false,
      tables: { headers: false, splitCells: false, cellBackgroundColor: false, cellTextColor: false },
      initialContent: initialContent as never,
    })
    return <BlockNoteView editor={editor} />
  }
  const view = render(<Probe />)
  await act(async () => {})
  return { editor, container: view.container }
}

/** Facts about BlockNote 0.54.2 the page editor is built on. An upgrade that
 *  changes one fails here rather than in a user's page. */
function manifest(name: string): { version: string; license: string; peerDependencies?: Record<string, string>; peerDependenciesMeta?: Record<string, { optional?: boolean }> } {
  return JSON.parse(readFileSync(resolve("node_modules", name, "package.json"), "utf8"))
}

/** Facts no test can observe, and so not asserted here: that
 *  `trailingBlock: false` removes the rendered empty trailing line (it is a
 *  decoration, not a block in the document), and that darkraise-ui's menus
 *  would break BlockNote's slots by portalling (spec section 4.5). */
describe("BlockNote 0.54.2", () => {
  it("is MPL-2.0, takes React 19, and leaves Yjs optional", () => {
    for (const name of ["@blocknote/core", "@blocknote/react", "@blocknote/shadcn"]) {
      expect(manifest(name)).toMatchObject({ version: "0.54.2", license: "MPL-2.0" })
    }
    expect(manifest("@blocknote/react").peerDependencies?.react).toContain("^19.0")
    expect(manifest("@blocknote/core").peerDependenciesMeta?.yjs?.optional).toBe(true)
  })

  it("ships the list, to-do, toggle and divider blocks with these props", () => {
    expect(Object.keys(defaultBlockSpecs)).toEqual(
      expect.arrayContaining(["checkListItem", "toggleListItem", "divider", "numberedListItem", "bulletListItem"]),
    )
    const props = (name: keyof typeof defaultBlockSpecs) => Object.keys(defaultBlockSpecs[name].config.propSchema)
    expect(props("checkListItem")).toContain("checked")
    expect(props("numberedListItem")).toContain("start")
  })

  it("loses content in its own markdown conversion", async () => {
    const editor = BlockNoteEditor.create()
    const blocks = await editor.tryParseMarkdownToBlocks("a <kbd>k</kbd> ![i](u) \\*lit\\*")
    const text = JSON.stringify(blocks)
    expect(text).not.toContain("kbd")
    expect(text).not.toContain("![i](u)")
    expect(await editor.blocksToMarkdownLossy(blocks)).toContain("*lit*")
  })

  it("mints UUID v4 block ids and honours explicit ones", () => {
    const editor = BlockNoteEditor.create({ trailingBlock: false })
    expect(editor.document[0]!.id).toMatch(UUID_V4)
    editor.insertBlocks([{ id: "given", type: "paragraph", content: "x" }], editor.document[0]!.id, "after")
    expect(editor.document.map((b) => b.id)).toContain("given")
  })

  it("keeps heading levels 4 to 6 and an arbitrary code language", async () => {
    const { editor } = await mount([
      { id: "h", type: "heading", props: { level: 6 }, content: "H" },
      { id: "k", type: "codeBlock", props: { language: "weirdlang" }, content: "x" },
    ])
    const heading = editor.getBlock("h")!.props as Record<string, unknown>
    expect(heading.level).toBe(6)
    expect(heading).not.toHaveProperty("isToggleable")
    expect((editor.getBlock("k")!.props as Record<string, unknown>).language).toBe("weirdlang")
  })

  it("keeps a table's header row with header toggling off", async () => {
    const { editor } = await mount([
      { id: "t", type: "table", content: { type: "tableContent", headerRows: 1, rows: [{ cells: ["h"] }, { cells: ["a"] }] } },
    ])
    expect((editor.getBlock("t")!.content as { headerRows?: number }).headerRows).toBe(1)
  })

  it("reports moves as their own change, and a child's edit without its parent", async () => {
    const { editor } = await mount([
      { id: "l", type: "bulletListItem", content: "l", children: [{ id: "c", type: "paragraph", content: "c" }] },
      { id: "p", type: "paragraph", content: "p" },
    ])
    const seen: string[] = []
    editor.onChange((_e, { getChanges }) => {
      for (const change of getChanges()) seen.push(`${change.type}:${change.block.id}`)
    })
    editor.updateBlock("c", { content: "edited" })
    editor.setTextCursorPosition("p")
    editor.moveBlocksUp()
    expect(seen).toEqual(["update:c", "move:p"])
  })

  it("names a move's parents and marks a programmatic change local", async () => {
    const { editor } = await mount([
      { id: "l", type: "bulletListItem", content: "l", children: [{ id: "c", type: "paragraph", content: "c" }] },
      { id: "p", type: "paragraph", content: "p" },
    ])
    const moves: { prev?: string; current?: string; source: string }[] = []
    editor.onChange((_e, { getChanges }) => {
      for (const change of getChanges()) {
        if (change.type === "move") {
          moves.push({ prev: change.prevParent?.id, current: change.currentParent?.id, source: change.source.type })
        }
      }
    })
    editor.setTextCursorPosition("p")
    editor.moveBlocksUp()
    expect(moves).toEqual([{ prev: undefined, current: "l", source: "local" }])
  })

  it("holds a table as one block of rows and cells, and reports its edit as one update", async () => {
    const { editor } = await mount([
      { id: "t", type: "table", content: { type: "tableContent", headerRows: 1, rows: [{ cells: ["h"] }, { cells: ["a"] }] } },
    ])
    expect(editor.getBlock("t")!.content).toMatchObject({
      type: "tableContent",
      rows: [{ cells: [{ type: "tableCell", content: [{ type: "text", text: "h" }] }] }, { cells: [{ type: "tableCell" }] }],
    })
    const seen: string[] = []
    editor.onChange((_e, { getChanges }) => {
      for (const change of getChanges()) seen.push(`${change.type}:${change.block.id}`)
    })
    editor.updateBlock("t", { content: { type: "tableContent", rows: [{ cells: ["h"] }, { cells: ["b"] }] } as never })
    expect(seen).toEqual(["update:t"])
  })

  it("offers these slash menu keys", async () => {
    const { editor } = await mount([{ id: "p", type: "paragraph", content: "p" }])
    expect(getDefaultReactSlashMenuItems(editor).map((item) => (item as unknown as { key: string }).key)).toEqual([
      "heading",
      "heading_2",
      "heading_3",
      "quote",
      "toggle_list",
      "numbered_list",
      "bullet_list",
      "check_list",
      "paragraph",
      "code_block",
      "divider",
      "table",
      "image",
      "file",
      "heading_4",
      "heading_5",
      "heading_6",
      "emoji",
    ])
  })

  it("marks each block's outer element with its id", async () => {
    const { container } = await mount([{ id: "p", type: "paragraph", content: "p" }])
    expect(container.querySelector('.bn-block-outer[data-id="p"]')).not.toBeNull()
  })
})

describe("file blocks", () => {
  // What each spec says it accepts. This pins the schema's own metadata, not
  // BlockNote's matcher: the handler reads `fileBlockAccept` by exactly this
  // path, so a spec that stopped declaring it would route drops elsewhere.
  it("declares the accept lists the drop handler reads", () => {
    const specs = pageSchema.blockSpecs as unknown as Record<
      string,
      { implementation: { meta?: { fileBlockAccept?: string[] } } }
    >
    const meta = (type: string) => specs[type]?.implementation.meta?.fileBlockAccept
    expect(meta("image")).toEqual(["image/*"])
    expect(meta("file")).toEqual(["*/*"])
  })

  // The block wrapper swaps its add-file button for a "Loading..." element
  // when an upload starts and resets it only when the node view is rebuilt.
  // Setting `url` to the "" it already holds is not a change, so the failure
  // path retypes the block instead. This pins that the retype is a change.
  it("retypes a placeholder even though setting its url again is not a change", async () => {
    const { editor } = await mount([{ type: "image", props: { url: "", name: "x.png" } }])
    await act(async () => {
      editor.updateBlock(editor.document[0]!, { props: { url: "" } } as never)
    })
    expect(editor.document[0]!.type).toBe("image")
    await act(async () => {
      editor.updateBlock(editor.document[0]!, { type: "paragraph", content: [] } as never)
    })
    expect(editor.document[0]!.type).toBe("paragraph")
  })

  // The one fact the plan's Assumptions record as unverified. After an upload
  // whose block the nesting rule refused to convert, BlockNote updates the
  // original id with the url anyway -- on a block that has no `url` prop. This
  // records whether that is inert or throws; either way the recovery insert in
  // `use-page-editor.ts` has already placed the attachment, so the answer
  // changes no code. It is written down so the next reader does not have to
  // re-derive it, and so an upgrade that changes it is visible.
  //
  // It reaches the paragraph by retyping rather than by a refused conversion,
  // which is a proxy: the question is what a write of an undeclared prop does,
  // and how the block came to lack that prop does not change the answer.
  it("records what setting a foreign prop on a paragraph does", async () => {
    const { editor } = await mount([{ type: "image", props: { url: "", name: "x.png" } }])
    const id = editor.document[0]!.id
    await act(async () => {
      editor.updateBlock(id, { type: "paragraph", content: [] } as never)
    })
    let thrown: unknown = null
    await act(async () => {
      try {
        editor.updateBlock(id, { props: { url: "https://example.org/x.png" } } as never)
      } catch (error) {
        thrown = error
      }
    })
    // Whichever branch holds, the block must still be a paragraph and the page
    // must still be intact.
    expect(editor.document[0]!.type).toBe("paragraph")
    expect(editor.document).toHaveLength(1)
    // Record the observed behaviour. If this assertion fails, flip it and note
    // the flip in the ledger -- it is a recording, not a requirement.
    expect(thrown).toBeNull()
  })
})
