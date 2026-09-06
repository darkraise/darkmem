import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { BlockEditor, promote } from "../components/block-editor"
import type { BlockRow } from "@/hooks/api"

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
    block_id: "b1", type: "paragraph", text: "body", order_index: 0,
    char_span: null, parent_id: null, properties: null, source: "body", ...over,
  }
}

beforeEach(() => vi.clearAllMocks())

describe("promote — mirrors the serialiser's emit rules", () => {
  it("reads a heading and its level", () => {
    expect(promote("## Foo")).toEqual({
      type: "heading", text: "Foo", properties: { level: 2 },
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
      type: "list", text: "one", properties: { marker: "1)" },
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
      type: "html", text: "<div>x</div>",
    })
  })

  it("does not infer html from a leading angle bracket", () => {
    // CommonMark type-7: `<b>bold</b> text` is a paragraph. The stored type is
    // preserved, never guessed, so this stays a paragraph.
    expect(promote("<b>bold</b> text", "paragraph")).toEqual({
      type: "paragraph", text: "<b>bold</b> text",
    })
  })

  it("still promotes a stored html block that gains a marker", () => {
    expect(promote("# Foo", "html")).toEqual({
      type: "heading", text: "Foo", properties: { level: 1 },
    })
  })
})

describe("BlockEditor", () => {
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
        blockId: "b1", type: "heading", text: "Promoted",
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
        blockId: "b1", type: "html", text: "<div>y</div>",
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

  it("backspace on an empty block deletes it", async () => {
    render(<BlockEditor documentId="d1" blocks={[block({ source: "" , text: ""})]} />)
    await userEvent.click(screen.getByRole("button"))
    await userEvent.type(screen.getByRole("textbox"), "{backspace}")
    expect(remove).toHaveBeenCalledWith({ blockId: "b1" })
  })
})
