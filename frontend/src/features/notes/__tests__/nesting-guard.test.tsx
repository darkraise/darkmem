import { act, render } from "@testing-library/react"
import { expect, it } from "vitest"
import { useCreateBlockNote } from "@blocknote/react"
import { BlockNoteView } from "@blocknote/shadcn"
import { pageSchema, type PageEditorInstance } from "../lib/editor-schema"
import { addsNestingViolation } from "../lib/nesting-guard"

it("refuses a new child under a non-container and allows it under a list item", async () => {
  let editor!: PageEditorInstance
  function Probe() {
    editor = useCreateBlockNote({
      schema: pageSchema,
      trailingBlock: false,
      initialContent: [
        { id: "p", type: "paragraph", content: "p" },
        { id: "q", type: "paragraph", content: "q" },
        { id: "l", type: "bulletListItem", content: "l", children: [{ id: "l1", type: "paragraph", content: "l1" }] },
        { id: "m", type: "paragraph", content: "m" },
        { id: "quote", type: "quote", content: "legacy", children: [{ id: "qc", type: "codeBlock", content: "x" }] },
      ],
    })
    return <BlockNoteView editor={editor} />
  }
  render(<Probe />)
  await act(async () => {})
  editor.onBeforeChange(({ tr }) => (addsNestingViolation(tr.before, tr.doc) ? false : undefined))
  const shape = () => JSON.stringify(editor.document.map((x) => [x.id, x.type, x.children.map((c) => c.id)]))
  const start = shape()

  editor.setTextCursorPosition("q")
  editor.nestBlock()
  expect(shape()).toBe(start)

  editor.updateBlock("l", { type: "paragraph" })
  expect(shape()).toBe(start)

  editor.updateBlock("p", { children: [{ id: "px", type: "paragraph", content: "x" }] })
  expect(shape()).toBe(start)

  editor.setTextCursorPosition("m")
  editor.nestBlock()
  expect(editor.getBlock("l")!.children.map((c) => c.id)).toEqual(["l1", "m"])

  editor.updateBlock("qc", { content: "edited" })
  expect(editor.getBlock("qc")!.content).toMatchObject([{ text: "edited" }])

  editor.updateBlock("l", { type: "checkListItem", props: { checked: true } })
  expect(editor.getBlock("l")!.type).toBe("checkListItem")

  // Retyping the grandfathered quote to a non-container while it still
  // holds "qc" keeps both ids, so an id-only key would see no new pair.
  editor.updateBlock("quote", { type: "paragraph" })
  expect(editor.getBlock("quote")!.type).toBe("quote")
})

it("refuses a child under an image or a file block", async () => {
  let editor!: PageEditorInstance
  function Probe() {
    editor = useCreateBlockNote({
      schema: pageSchema,
      trailingBlock: false,
      initialContent: [
        { id: "i", type: "image", props: { url: "https://example.org/x.png", name: "x.png" } },
        {
          id: "f",
          type: "file",
          props: { url: "/api/v1/pages/attachments/0123abcd-4567-89ef-0123-456789abcdef", name: "n.pdf" },
        },
        { id: "p", type: "paragraph", content: "p" },
      ],
    })
    return <BlockNoteView editor={editor} />
  }
  render(<Probe />)
  await act(async () => {})
  editor.onBeforeChange(({ tr }) => (addsNestingViolation(tr.before, tr.doc) ? false : undefined))
  const shape = () => JSON.stringify(editor.document.map((x) => [x.id, x.type, x.children.map((c) => c.id)]))
  const start = shape()

  editor.updateBlock("i", { children: [{ id: "ic", type: "paragraph", content: "x" }] })
  expect(shape()).toBe(start)

  editor.updateBlock("f", { children: [{ id: "fc", type: "paragraph", content: "x" }] })
  expect(shape()).toBe(start)
})
