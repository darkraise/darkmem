import { readFileSync } from "node:fs"
import { resolve } from "node:path"
import { act, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { FileDownloadButton } from "@blocknote/react"
import { toEditorBlocks, type EditorBlockLike } from "../lib/block-mapping"
import type { SyncBlock } from "../lib/sync-tree"
import { PageEditor } from "../page-editor"

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

afterEach(() => {
  delete document.documentElement.dataset.mode
})

describe("PageEditor", () => {
  it("renders the page's blocks and an outline of its headings", async () => {
    render(<PageEditor initialBlocks={BLOCKS} editable />)
    const outline = await screen.findByRole("navigation", { name: "Page outline" })
    expect(outline).toHaveTextContent("Plans")
    expect(outline).toHaveTextContent("Details")
    expect(screen.getAllByText("first").length).toBeGreaterThan(0)
  })

  it("scrolls to a heading picked in the outline", async () => {
    const scroll = vi.fn()
    Element.prototype.scrollIntoView = scroll
    render(<PageEditor initialBlocks={BLOCKS} editable />)
    const outline = await screen.findByRole("navigation", { name: "Page outline" })
    fireEvent.click(outline.querySelectorAll("button")[1]!)
    expect(scroll).toHaveBeenCalledOnce()
    expect(scroll.mock.contexts[0]).toBe(document.querySelector('.bn-block-outer[data-id="h2"]'))
  })

  it("locks the document when not editable", async () => {
    const { container } = render(<PageEditor initialBlocks={BLOCKS} editable={false} />)
    await act(async () => {})
    expect(container.querySelector('.bn-block-outer[data-id="p1"]')).toHaveTextContent("first")
    expect(container.querySelector('[contenteditable="true"]')).toBeNull()
  })

  it("follows the document's colour mode", async () => {
    document.documentElement.dataset.mode = "dark"
    const { container } = render(<PageEditor initialBlocks={BLOCKS} editable />)
    await act(async () => {})
    expect(container.querySelector('[data-color-scheme="dark"]')).not.toBeNull()
  })

  it("labels the editor, its checklist boxes and its toggles", async () => {
    const blocks = toEditorBlocks([
      b("t1", "todo", "buy milk", { checked: false }),
      b("g1", "toggle", "more"),
    ]).blocks
    const { container } = render(<PageEditor initialBlocks={blocks} editable />)
    await act(async () => {})
    expect(container.querySelector('[aria-label="Page content"]')).not.toBeNull()
    expect(screen.getByRole("checkbox", { name: "Mark as done" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Expand" })).toBeInTheDocument()
  })

  it("paints callouts with theme tokens and shares the title's left edge", async () => {
    const blocks = toEditorBlocks([b("c1", "callout", "heads up", { variant: "info" })]).blocks
    const { container } = render(<PageEditor initialBlocks={blocks} editable />)
    await act(async () => {})
    const callout = container.querySelector('[data-variant="info"]')!
    expect(callout.className).toMatch(/bg-info\/10/)
    expect(callout.className).not.toMatch(/sky-/)
    expect(container.querySelector(".max-w-3xl")).not.toHaveClass("mx-auto")
  })

  it("carries its page id on the editor root", () => {
    const { container } = render(<PageEditor initialBlocks={BLOCKS} editable pageId="page-7" />)
    expect(container.querySelector('[data-page-id="page-7"]')).not.toBeNull()
  })

  it("renders without one, which is what demo mode passes", () => {
    const { container } = render(<PageEditor initialBlocks={BLOCKS} editable={false} />)
    expect(container.querySelector("[data-page-id]")).toBeNull()
  })
})

const URL_A = "/api/v1/pages/attachments/0123abcd-4567-89ef-0123-456789abcdef"

const FILE_BLOCK: EditorBlockLike[] = [
  { id: "f", type: "file", props: { url: URL_A, name: "notes.pdf" }, content: undefined, children: [] },
]

describe("file affordances", () => {
  // A CSS rule can only be wrong in one of two ways: the rule is gone, or the
  // class it targets was renamed upstream. Each assertion catches one of them,
  // and the second is the reason the pair exists -- a rename would otherwise
  // leave the handle visible with a stylesheet that still looks correct.
  it("hides the resize handle, which has nowhere to be stored", () => {
    const css = readFileSync(resolve("src/features/notes/page-editor.css"), "utf8")
    expect(css).toMatch(/\.bn-resize-handle\s*\{[^}]*display:\s*none/)
    // `dist/style.css` rather than a bundle: the bundle's filename carries a
    // content hash, so a version bump would fail this with ENOENT instead of
    // the class-rename failure it is here to produce.
    const shipped = readFileSync(resolve("node_modules/@blocknote/core/dist/style.css"), "utf8")
    expect(shipped).toContain("bn-resize-handle")
  })

  it("renders a file block with its name", async () => {
    render(<PageEditor initialBlocks={FILE_BLOCK} editable />)
    await act(async () => {})
    expect(await screen.findByText("notes.pdf")).toBeInTheDocument()
  })

  // The block renderer draws an inert name and icon; the control that opens
  // the url is a toolbar button, and this editor builds its toolbar from an
  // explicit list. Asserting on the rendered toolbar would mean driving a
  // selection and a popover, so this pins the two things that can actually
  // break: the button is still exported, and it is still in the list.
  it("puts the download control in the toolbar", () => {
    expect(typeof FileDownloadButton).toBe("function")
    const source = readFileSync(resolve("src/features/notes/page-editor.tsx"), "utf8")
    expect(source).toContain("<FileDownloadButton />")
  })
})
