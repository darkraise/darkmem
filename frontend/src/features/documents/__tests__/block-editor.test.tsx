import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { BlockEditor, promote } from "../components/block-editor"
import type { BlockRow } from "@/hooks/api"
import { execFileSync } from "node:child_process"
import path from "node:path"

const update = vi.fn()
const insert = vi.fn()
const remove = vi.fn()

vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useBlockUpdate: () => ({ mutate: update }),
  useBlockInsert: () => ({ mutate: insert }),
  useBlockDelete: () => ({ mutate: remove }),
}))

function block(over: Partial<BlockRow>): BlockRow {
  return {
    block_id: "b1",
    type: "paragraph",
    text: "body",
    order_index: 0,
    char_span: null,
    parent_id: null,
    properties: null,
    source: "body",
    ...over,
  }
}

beforeEach(() => vi.clearAllMocks())

function serialize(rows: BlockRow[]): { content: string; blocks: BlockRow[] } {
  return JSON.parse(
    execFileSync(
      "python3",
      [
        "-c",
        `
import json, sys
from uuid import UUID
from app.services.block_serializer import TreeBlock, serialize_tree
rows = json.loads(sys.argv[1])
tree = [TreeBlock(UUID(row['block_id']), UUID(row['parent_id']) if row['parent_id'] else None, row['order_index'], row['type'], row['text'], row['properties']) for row in rows]
result = serialize_tree(tree)
spans = {str(placed.block_id): placed.char_span for placed in result.placed}
for row in rows:
    start, end = spans[row['block_id']]
    row['source'] = result.content[start:end]
print(json.dumps({'content': result.content, 'blocks': rows}))
`,
        JSON.stringify(rows),
      ],
      {
        cwd: path.resolve(__dirname, "../../../../../backend"),
        encoding: "utf8",
        timeout: 5000,
      },
    ),
  )
}

describe("promote — mirrors the serialiser's emit rules", () => {
  it.each([
    [">compact\n> second", { type: "quote", text: "compact\nsecond" }],
    [
      "- \n  second",
      { type: "list", text: "\nsecond", properties: { marker: "-" } },
    ],
    [
      "> first\n> second\n> > literal",
      { type: "quote", text: "first\nsecond\n> literal" },
    ],
    [
      "12) first\n    second\n      indented",
      {
        type: "list",
        text: "first\nsecond\n  indented",
        properties: { marker: "12)" },
      },
    ],
    [
      "````typescript\nconst value = `x`\n```\n````",
      {
        type: "code",
        text: "const value = `x`\n```",
        properties: { language: "typescript" },
      },
    ],
    [
      "~~~js\nlast line",
      { type: "code", text: "last line", properties: { language: "js" } },
    ],
    [
      "```js\n---",
      { type: "code", text: "---", properties: { language: "js" } },
    ],
    [
      "first\nsecond\n===",
      { type: "heading", text: "first\nsecond", properties: { level: 1 } },
    ],
  ])("preserves multiline source %s", (source, expected) => {
    expect(promote(source as string)).toEqual(expected)
  })
  it("reads a heading and its level", () => {
    expect(promote("## Foo")).toEqual({
      type: "heading",
      text: "Foo",
      properties: { level: 2 },
    })
  })

  it("demotes when the marker is deleted", () => {
    // Only possible because the editor holds `source`. With the marker never
    // shown it could never be deleted, so a heading could never become a
    // paragraph again.
    expect(promote("Foo")).toEqual({ type: "paragraph", text: "Foo" })
  })

  it("keeps a list's own marker", () => {
    expect(promote("1) one")).toEqual({
      type: "list",
      text: "one",
      properties: { marker: "1)" },
    })
  })

  it("reads a thematic break", () => {
    expect(promote("---")).toEqual({ type: "divider", text: "" })
  })

  it("reads a quote", () => {
    expect(promote("> quoted")).toEqual({ type: "quote", text: "quoted" })
  })

  it("keeps a stored html block html at the fallback", () => {
    // An html block's source IS its text, so no marker rule matches it and
    // the fallback would demote it. `search_vector` blanks source types, so a
    // demotion indexes raw markup as prose.
    expect(promote("<div>x</div>", "html")).toEqual({
      type: "html",
      text: "<div>x</div>",
    })
  })

  it("does not infer html from a leading angle bracket", () => {
    // CommonMark type-7: `<b>bold</b> text` is a paragraph. The stored type is
    // preserved, never guessed, so this stays a paragraph.
    expect(promote("<b>bold</b> text", "paragraph")).toEqual({
      type: "paragraph",
      text: "<b>bold</b> text",
    })
  })

  it("still promotes a stored html block that gains a marker", () => {
    expect(promote("# Foo", "html")).toEqual({
      type: "heading",
      text: "Foo",
      properties: { level: 1 },
    })
  })
})

describe("BlockEditor", () => {
  it.each([
    [">> one\n>> two", 1],
    ["> > one\n>> two", 1],
    [">>> one\n>>> two", 2],
  ] as const)(
    "edits original compact imported quote source %s without adding nesting",
    async (source, ancestors) => {
      const rows = Array.from({ length: ancestors + 1 }, (_unused, index) =>
        block({
          block_id: `00000000-0000-0000-0000-${String(index + 1).padStart(12, "0")}`,
          parent_id: index
            ? `00000000-0000-0000-0000-${String(index).padStart(12, "0")}`
            : null,
          type: "quote",
          text: index === ancestors ? "one\ntwo" : "",
          source,
          order_index: index,
        }),
      )
      render(<BlockEditor documentId="d1" blocks={rows} />)
      await userEvent.click(screen.getAllByRole("button")[ancestors]!)
      expect(screen.getByRole("textbox")).toHaveValue(source)
      fireEvent.change(screen.getByRole("textbox"), {
        target: { value: source.replace("one", "ONE") },
      })
      await userEvent.tab()
      const write = update.mock.calls[0]![0]
      expect(write).toMatchObject({ type: "quote", text: "ONE\ntwo" })
      const actual = serialize(
        rows.map((row, index) =>
          index === ancestors ? { ...row, ...write } : row,
        ),
      )
      const expected = serialize(
        rows.map((row, index) =>
          index === ancestors ? { ...row, text: "ONE\ntwo" } : row,
        ),
      )
      expect(actual.content).toBe(expected.content)
    },
  )

  it.each(["list", "code"])(
    "edits an imported %s below compact quote ancestors without stripping its content",
    async (kind) => {
      const source =
        kind === "list"
          ? ">> 10) item\n>>     - one\n>>       two"
          : ">> ```text\n>> > literal one\n>>   indented\n>> ```"
      const outerId = "00000000-0000-0000-0000-000000000001"
      const innerId = "00000000-0000-0000-0000-000000000002"
      const listId = "00000000-0000-0000-0000-000000000003"
      const targetId = "00000000-0000-0000-0000-000000000004"
      const rows = [
        block({ block_id: outerId, type: "quote", text: "", source }),
        block({
          block_id: innerId,
          parent_id: outerId,
          type: "quote",
          text: "",
          source,
        }),
        ...(kind === "list"
          ? [
              block({
                block_id: listId,
                parent_id: innerId,
                type: "list",
                text: "item",
                source,
                properties: { marker: "10)" },
              }),
            ]
          : []),
        block({
          block_id: targetId,
          parent_id: kind === "list" ? listId : innerId,
          type: kind,
          text: kind === "list" ? "one\ntwo" : "> literal one\n  indented",
          source:
            kind === "list" ? source.slice(source.indexOf("\n") + 1) : source,
          properties: kind === "list" ? { marker: "-" } : { language: "text" },
        }),
      ]
      const target = rows[rows.length - 1]!
      render(<BlockEditor documentId="d1" blocks={rows} />)
      await userEvent.click(screen.getAllByRole("button")[rows.length - 1]!)
      expect(screen.getByRole("textbox")).toHaveValue(target.source)
      fireEvent.change(screen.getByRole("textbox"), {
        target: { value: target.source!.replace("one", "ONE") },
      })
      await userEvent.tab()
      const write = update.mock.calls[0]![0]
      expect(write).toMatchObject({
        type: kind,
        text: target.text.replace("one", "ONE"),
      })
      const actual = serialize(
        rows.map((row) =>
          row.block_id === targetId ? { ...row, ...write } : row,
        ),
      )
      const expected = serialize(
        rows.map((row) =>
          row.block_id === targetId
            ? { ...row, text: target.text.replace("one", "ONE") }
            : row,
        ),
      )
      expect(actual.content).toBe(expected.content)
    },
  )

  it.each(["quote", "list", "code"])(
    "round-trips edited nested %s through the backend serializer",
    async (kind) => {
      const quoteId = "00000000-0000-0000-0000-000000000001"
      const listId = "00000000-0000-0000-0000-000000000002"
      const leafId = "00000000-0000-0000-0000-000000000003"
      const original = serialize([
        block({ block_id: quoteId, type: "quote", text: "outer" }),
        block({
          block_id: listId,
          parent_id: quoteId,
          type: "list",
          text: "item",
          properties: { marker: "10)" },
        }),
        block({
          block_id: leafId,
          parent_id: listId,
          type: kind,
          text: "one\n  two\n> literal\n```",
          properties:
            kind === "code"
              ? { language: "typescript" }
              : kind === "list"
                ? { marker: "+" }
                : null,
        }),
      ])
      render(<BlockEditor documentId="d1" blocks={original.blocks} />)
      await userEvent.click(screen.getAllByRole("button")[2]!)
      fireEvent.change(screen.getByRole("textbox"), {
        target: { value: original.blocks[2]!.source!.replace("one", "ONE") },
      })
      await userEvent.tab()
      const write = update.mock.calls[0]![0]
      const result = serialize(
        original.blocks.map((row) =>
          row.block_id === leafId ? { ...row, ...write } : row,
        ),
      )
      expect(result.content).toBe(original.content.replace("one", "ONE"))
    },
  )
  it("removes only ancestor quote/list prefixes before promoting", async () => {
    render(
      <BlockEditor
        documentId="d1"
        blocks={[
          block({ block_id: "quote", type: "quote", source: "> quote" }),
          block({
            block_id: "list",
            parent_id: "quote",
            type: "list",
            source: "> 10) list",
            properties: { marker: "10)" },
          }),
          block({
            parent_id: "list",
            type: "code",
            source: ">     ```js\n>       old\n>     ```",
            text: "  old",
          }),
        ]}
      />,
    )
    await userEvent.click(screen.getAllByRole("button")[2]!)
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: ">     ```js\n>       new\n>     ```" },
    })
    await userEvent.tab()
    expect(update).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "code",
        text: "  new",
        properties: { language: "js" },
      }),
      expect.anything(),
    )
  })

  it("inserts alongside a nested block and announces insert failure", async () => {
    insert.mockImplementationOnce((_value, options) =>
      options?.onError(new Error("refused")),
    )
    render(
      <BlockEditor documentId="d1" blocks={[block({ parent_id: "parent" })]} />,
    )
    await userEvent.click(screen.getByRole("button"))
    fireEvent.keyDown(screen.getByRole("textbox"), {
      key: "Enter",
      ctrlKey: true,
    })
    expect(insert).toHaveBeenCalledWith(
      expect.objectContaining({ parentId: "parent", afterBlockId: "b1" }),
      expect.anything(),
    )
    expect(screen.getByRole("alert")).toHaveTextContent("refused")
  })

  it("announces delete failure", async () => {
    remove.mockImplementationOnce((_value, options) =>
      options.onError(new Error("delete refused")),
    )
    render(
      <BlockEditor
        documentId="d1"
        blocks={[block({ source: "", text: "" })]}
      />,
    )
    await userEvent.click(screen.getByRole("button"))
    fireEvent.keyDown(screen.getByRole("textbox"), { key: "Backspace" })
    fireEvent.keyDown(screen.getByRole("textbox"), { key: "Backspace" })
    expect(screen.getByRole("alert")).toHaveTextContent("delete refused")
  })
  it("edits the block's SOURCE, not its marker-stripped text", async () => {
    render(
      <BlockEditor
        documentId="d1"
        blocks={[block({ type: "heading", text: "Foo", source: "## Foo" })]}
      />,
    )
    await userEvent.click(screen.getByRole("button"))
    expect(screen.getByRole("textbox")).toHaveValue("## Foo")
  })

  it("commits on blur with the promotion applied", async () => {
    render(
      <BlockEditor
        documentId="d1"
        blocks={[block({ type: "paragraph", text: "body", source: "body" })]}
      />,
    )
    await userEvent.click(screen.getByRole("button"))
    const area = screen.getByRole("textbox")
    await userEvent.clear(area)
    await userEvent.type(area, "# Promoted")
    await userEvent.tab()

    expect(update).toHaveBeenCalledWith(
      expect.objectContaining({
        blockId: "b1",
        type: "heading",
        text: "Promoted",
        properties: { level: 1 },
      }),
      expect.anything(),
    )
  })

  it("commits an edited html block as html, not paragraph", async () => {
    render(
      <BlockEditor
        documentId="d1"
        blocks={[
          block({ type: "html", text: "<div>x</div>", source: "<div>x</div>" }),
        ]}
      />,
    )
    await userEvent.click(screen.getByRole("button"))
    const area = screen.getByRole("textbox")
    await userEvent.clear(area)
    await userEvent.type(area, "<div>y</div>")
    await userEvent.tab()

    expect(update).toHaveBeenCalledWith(
      expect.objectContaining({
        blockId: "b1",
        type: "html",
        text: "<div>y</div>",
      }),
      expect.anything(),
    )
  })

  it("fires nothing when the source is unchanged", async () => {
    render(<BlockEditor documentId="d1" blocks={[block({})]} />)
    await userEvent.click(screen.getByRole("button"))
    await userEvent.tab()
    expect(update).not.toHaveBeenCalled()
  })

  it("backspace on an empty block deletes it on the second press", async () => {
    render(
      <BlockEditor
        documentId="d1"
        blocks={[block({ source: "", text: "" })]}
      />,
    )
    await userEvent.click(screen.getByRole("button"))
    await userEvent.type(screen.getByRole("textbox"), "{backspace}")
    // The first press only arms the delete: there is no undo.
    expect(remove).not.toHaveBeenCalled()
    expect(screen.getByRole("status")).toHaveTextContent(/backspace again/i)
    await userEvent.type(screen.getByRole("textbox"), "{backspace}")
    expect(remove).toHaveBeenCalledWith({ blockId: "b1" }, expect.anything())
  })

  it("typing after an armed delete disarms it", async () => {
    render(
      <BlockEditor
        documentId="d1"
        blocks={[block({ source: "", text: "" })]}
      />,
    )
    await userEvent.click(screen.getByRole("button"))
    await userEvent.type(
      screen.getByRole("textbox"),
      "{backspace}x{backspace}{backspace}",
    )
    // x then its own deletion leaves the draft empty again, which re-arms
    // rather than deleting.
    expect(remove).not.toHaveBeenCalled()
  })

  it("escape discards the draft instead of committing it", async () => {
    render(<BlockEditor documentId="d1" blocks={[block({})]} />)
    await userEvent.click(screen.getByRole("button"))
    await userEvent.type(screen.getByRole("textbox"), " changed")
    await userEvent.keyboard("{Escape}")
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument()
    expect(update).not.toHaveBeenCalled()
    // The next edit still commits: Escape's guard does not leak forward.
    await userEvent.click(screen.getByRole("button"))
    await userEvent.type(screen.getByRole("textbox"), " again")
    await userEvent.tab()
    expect(update).toHaveBeenCalledTimes(1)
  })

  it("keeps the reader's list indentation in edit mode", () => {
    const { container } = render(
      <BlockEditor
        documentId="d1"
        blocks={[
          block({ block_id: "l1", type: "list", source: "- a", text: "a" }),
          block({ block_id: "b2", parent_id: "l1", source: "b", text: "b" }),
        ]}
      />,
    )
    const nested = container.querySelector('[id="b2"]') as HTMLElement
    expect(nested.dataset.depth).toBe("1")
    expect(nested.style.paddingLeft).toBe("18px")
  })
})
