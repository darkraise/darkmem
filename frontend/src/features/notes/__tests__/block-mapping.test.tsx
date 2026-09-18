import { act, render } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { useCreateBlockNote } from "@blocknote/react"
import { BlockNoteView } from "@blocknote/shadcn"
import { canonicalTree, toEditorBlocks, toSyncTree, type EditorBlockLike } from "../lib/block-mapping"
import { pageSchema, type PageEditorInstance } from "../lib/editor-schema"
import { nextOp, treesEqual, type SyncBlock } from "../lib/sync-tree"

const b = (
  id: string,
  parentId: string | null,
  type: string,
  text: string,
  properties: SyncBlock["properties"] = null,
): SyncBlock => ({ id, parentId, type, text, properties })

/** A page stored with every spelling the editor writes differently. */
const STORED: SyncBlock[] = [
  b("h", null, "heading", "__Big__ &amp; _small_", { level: 5 }),
  b("p", null, "paragraph", "a <kbd>K</kbd> ![i](u) [x][1] \\*lit\\* line\nnext"),
  b("l", null, "list", "star", { ordered: false, marker: "*", number: 4 }),
  b("l1", "l", "list", "three", { ordered: true, marker: "3)", number: 3 }),
  b("t", null, "todo", "task", { checked: true }),
  b("g", null, "toggle", "fold"),
  b("g1", "g", "paragraph", "inside"),
  b("c", null, "callout", "note **it**", { variant: "warning" }),
  b("k", null, "code", "print(1)\n  x", { language: "py" }),
  b("k2", null, "code", "plain"),
  b("d", null, "divider", ""),
  b("x", null, "html", "<div>raw</div>"),
  b("q", null, "quote", "legacy"),
  b("q1", "q", "code", "inner", { language: "sh" }),
  b("tb", null, "table", "A | B", { header: ["A", "**B**"], alignments: ["left", null] }),
  b("r1", "tb", "table_row", "1 | a|b", { cells: ["1", "a|b"] }),
  b("r2", "tb", "table_row", "3 | `4`", { cells: ["3", "`4`"] }),
]

const noMint = () => {
  throw new Error("minted a row id")
}

describe("block mapping", () => {
  it("maps each server type to its editor block", () => {
    const { blocks, rowIds } = toEditorBlocks(STORED)
    const byId = new Map<string, EditorBlockLike>()
    const walk = (list: EditorBlockLike[]) =>
      list.forEach((x) => {
        byId.set(x.id, x)
        walk(x.children)
      })
    walk(blocks)
    expect(byId.get("h")).toMatchObject({ type: "heading", props: { level: 5 } })
    expect(byId.get("l")).toMatchObject({ type: "bulletListItem" })
    expect(byId.get("l1")).toMatchObject({ type: "numberedListItem" })
    expect(byId.get("t")).toMatchObject({ type: "checkListItem", props: { checked: true } })
    expect(byId.get("g")).toMatchObject({ type: "toggleListItem" })
    expect(byId.get("c")).toMatchObject({ type: "callout", props: { variant: "warning" } })
    expect(byId.get("k")).toMatchObject({ type: "codeBlock", props: { language: "py" }, content: "print(1)\n  x" })
    expect(byId.get("k2")).toMatchObject({ type: "codeBlock", props: { language: "text" } })
    expect(byId.get("d")).toMatchObject({ type: "divider" })
    expect(byId.get("x")).toMatchObject({ type: "raw", props: { source: "<div>raw</div>" } })
    expect(byId.get("q")!.children.map((x) => x.id)).toEqual(["q1"])
    expect(byId.get("tb")!.children).toEqual([])
    expect(rowIds.get("tb")).toEqual(["r1", "r2"])
    expect(byId.has("r1")).toBe(false)
  })

  it("keeps a stored marker when the list kind is unchanged, and resets it when it flips", () => {
    const previous = [b("a", null, "list", "a", { ordered: false, marker: "*" }), b("n", null, "list", "n", { ordered: true, marker: "3)" })]
    const blocks: EditorBlockLike[] = [
      { id: "a", type: "bulletListItem", props: {}, content: [], children: [] },
      { id: "n", type: "bulletListItem", props: {}, content: [], children: [] },
      { id: "z", type: "numberedListItem", props: {}, content: [], children: [] },
    ]
    const { tree } = toSyncTree(blocks, previous, new Map(), noMint)
    expect(tree.map((x) => x.properties)).toEqual([
      { ordered: false, marker: "*" },
      { ordered: false, marker: "-" },
      { ordered: true, marker: "1." },
    ])
  })

  it("matches table rows by position, minting ids for new rows once", () => {
    const { tree: canonical, rowIds } = canonicalTree(STORED)
    const table = toEditorBlocks(canonical).blocks.find((x) => x.id === "tb")!
    const content = table.content as { rows: { cells: unknown[] }[] }
    const grown: EditorBlockLike = { ...table, content: { ...content, rows: [...content.rows, { cells: [[], []] }] } }
    let minted = 0
    const mint = () => `new${++minted}`
    const first = toSyncTree([grown], canonical, rowIds, mint)
    const second = toSyncTree([grown], canonical, first.rowIds, mint)
    const rows = (tree: SyncBlock[]) => tree.filter((x) => x.type === "table_row").map((x) => x.id)
    expect(rows(first.tree)).toEqual(["r1", "r2", "new1"])
    expect(rows(second.tree)).toEqual(["r1", "r2", "new1"])
    expect(minted).toBe(1)
    const tableBlock = first.tree.find((x) => x.id === "tb")!
    expect(tableBlock.properties).toEqual({ header: ["A", "**B**"], alignments: ["left", null] })
  })

  it("pads the stored alignments with null for a new column", () => {
    const { tree: canonical, rowIds } = canonicalTree(STORED)
    const table = toEditorBlocks(canonical).blocks.find((x) => x.id === "tb")!
    const content = table.content as { rows: { cells: unknown[] }[] }
    const wider: EditorBlockLike = {
      ...table,
      content: { ...content, rows: content.rows.map((row) => ({ cells: [...row.cells, []] })) },
    }
    const { tree } = toSyncTree([wider], canonical, rowIds, noMint)
    expect(tree.find((x) => x.id === "tb")!.properties).toEqual({ header: ["A", "**B**", ""], alignments: ["left", null, null] })
  })

  it("sends every key a type models, so a cleared value clears", () => {
    const { tree } = toSyncTree(
      [{ id: "k", type: "codeBlock", props: { language: "text" }, content: [{ type: "text", text: "x", styles: {} }], children: [] }],
      [b("k", null, "code", "x", { language: "py" })],
      new Map(),
      noMint,
    )
    expect(tree[0]!.properties).toEqual({ language: "text" })
  })

  it("canonicalises idempotently", () => {
    const once = canonicalTree(STORED).tree
    expect(treesEqual(canonicalTree(once).tree, once)).toBe(true)
  })

  it("asks for no write when a stored page is loaded into the editor", async () => {
    const { tree: canonical, rowIds } = canonicalTree(STORED)
    let editor!: PageEditorInstance
    function Probe() {
      editor = useCreateBlockNote({
        schema: pageSchema,
        trailingBlock: false,
        initialContent: toEditorBlocks(canonical).blocks as never,
      })
      return <BlockNoteView editor={editor} />
    }
    render(<Probe />)
    await act(async () => {})
    const { tree: desired } = toSyncTree(editor.document as unknown as EditorBlockLike[], canonical, rowIds, noMint)
    expect(nextOp(canonical, desired)).toBeNull()
  })
})
