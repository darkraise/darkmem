import { act, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
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
})
