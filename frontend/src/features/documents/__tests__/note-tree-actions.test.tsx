import { describe, it, expect, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { NoteTreeActions } from "../components/note-tree-actions"
import { DocumentTree } from "../components/document-tree"
import { NO_PATH, type UriTreeNode } from "../uri-tree"

const folder: UriTreeNode = {
  name: "a",
  path: "notes/a",
  document: null,
  children: [],
}

const leaf: UriTreeNode = {
  name: "b.md",
  path: "notes/a/b.md",
  document: {
    id: "d1",
    title: "B",
    uri: "notes/a/b.md",
    source_type: "md",
    project: "p",
    block_count: 1,
  },
  children: [],
}

const noop = () => {}

describe("NoteTreeActions", () => {
  it("offers folder actions on a folder and document actions on a leaf", async () => {
    const { rerender } = render(
      <NoteTreeActions
        node={folder}
        onNewNote={noop}
        onRename={noop}
        onTogglePin={noop}
        onDelete={noop}
      />,
    )
    await userEvent.click(screen.getByRole("button", { name: /actions/i }))
    expect(screen.getByText(/new note/i)).toBeInTheDocument()
    // A folder has no pin: `pinned_at` is a document column.
    expect(screen.queryByText(/pin/i)).not.toBeInTheDocument()

    rerender(
      <NoteTreeActions
        node={leaf}
        onNewNote={noop}
        onRename={noop}
        onTogglePin={noop}
        onDelete={noop}
      />,
    )
    await userEvent.click(screen.getByRole("button", { name: /actions/i }))
    expect(screen.getByText("Pin")).toBeInTheDocument()
    expect(screen.queryByText(/new note/i)).not.toBeInTheDocument()
  })

  it("labels the pin action from the document's pin state", async () => {
    const pinned: UriTreeNode = {
      ...leaf,
      document: { ...leaf.document!, pinned_at: "2026-09-07T00:00:00Z" },
    }
    render(
      <NoteTreeActions
        node={pinned}
        onNewNote={noop}
        onRename={noop}
        onTogglePin={noop}
        onDelete={noop}
      />,
    )
    await userEvent.click(screen.getByRole("button", { name: /actions/i }))
    expect(screen.getByText("Unpin")).toBeInTheDocument()
  })

  it("reports the clicked action to its caller", async () => {
    const onNewNote = vi.fn()
    const onDelete = vi.fn()
    render(
      <NoteTreeActions
        node={folder}
        onNewNote={onNewNote}
        onRename={noop}
        onTogglePin={noop}
        onDelete={onDelete}
      />,
    )
    await userEvent.click(screen.getByRole("button", { name: /actions/i }))
    await userEvent.click(screen.getByText(/new note/i))
    expect(onNewNote).toHaveBeenCalledWith("notes/a")

    await userEvent.click(screen.getByRole("button", { name: /actions/i }))
    await userEvent.click(screen.getByText("Delete"))
    expect(onDelete).toHaveBeenCalledWith(folder)
  })

  it("reports rename and pin with their node", async () => {
    const onRename = vi.fn()
    const onTogglePin = vi.fn()
    render(
      <NoteTreeActions
        node={leaf}
        onNewNote={noop}
        onRename={onRename}
        onTogglePin={onTogglePin}
        onDelete={noop}
      />,
    )
    await userEvent.click(screen.getByRole("button", { name: /actions/i }))
    await userEvent.click(screen.getByText("Rename"))
    expect(onRename).toHaveBeenCalledWith(leaf)

    await userEvent.click(screen.getByRole("button", { name: /actions/i }))
    await userEvent.click(screen.getByText("Pin"))
    expect(onTogglePin).toHaveBeenCalledWith(leaf)
  })

  it("offers no folder actions on the orphan bucket", () => {
    // `(no path)` is a synthesised node with no uri; a folder op on it would
    // send `uri_prefix="(no path)"` and match nothing.
    const orphans: UriTreeNode = {
      name: NO_PATH,
      path: NO_PATH,
      document: null,
      children: [],
    }
    render(
      <NoteTreeActions
        node={orphans}
        onNewNote={noop}
        onRename={noop}
        onTogglePin={noop}
        onDelete={noop}
      />,
    )
    expect(screen.queryByRole("button", { name: /actions/i })).toBeNull()
  })

  it("does not select or expand the row it hangs off", async () => {
    // Mounted through the real tree: the menu is portalled, but React
    // synthetic events bubble the React ancestor chain, so a click inside it
    // still reaches the row's own handler.
    const onSelect = vi.fn()
    render(
      <DocumentTree
        items={[leaf.document!]}
        selectedId={null}
        onSelect={onSelect}
        truncated={false}
        nodeActions={(node) => (
          <NoteTreeActions
            node={node}
            onNewNote={noop}
            onRename={noop}
            onTogglePin={noop}
            onDelete={noop}
          />
        )}
      />,
    )
    const trigger = screen.getByRole("button", { name: /actions for b\.md/i })
    await userEvent.click(trigger)
    expect(onSelect).not.toHaveBeenCalled()

    await userEvent.click(screen.getByText("Delete"))
    expect(onSelect).not.toHaveBeenCalled()
  })

  it("renders an action in the empty state so an empty space can be filled", () => {
    render(
      <DocumentTree
        items={[]}
        selectedId={null}
        onSelect={noop}
        truncated={false}
        emptyAction={<button>New note</button>}
      />,
    )
    expect(screen.getByText("New note")).toBeInTheDocument()
  })
})
