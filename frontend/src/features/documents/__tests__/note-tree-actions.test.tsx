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
        onNewFolder={noop}
        onRename={noop}
        onMoveTo={noop}
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
        onNewFolder={noop}
        onRename={noop}
        onMoveTo={noop}
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
        onNewFolder={noop}
        onRename={noop}
        onMoveTo={noop}
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
        onNewFolder={noop}
        onRename={noop}
        onMoveTo={noop}
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
        onNewFolder={noop}
        onRename={onRename}
        onMoveTo={noop}
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

  it("offers both creates on a folder and neither on a note", async () => {
    // A folder is not an object -- there is no row to carry an empty one --
    // so "New folder" is a create like "New note" and rides the same
    // condition: filing under a note would mint a path below a file.
    const { rerender } = render(
      <NoteTreeActions
        node={folder}
        onNewNote={noop}
        onNewFolder={noop}
        onRename={noop}
        onMoveTo={noop}
        onTogglePin={noop}
        onDelete={noop}
      />,
    )
    await userEvent.click(screen.getByRole("button", { name: /actions/i }))
    expect(screen.getByText("New folder")).toBeInTheDocument()

    rerender(
      <NoteTreeActions
        node={leaf}
        onNewNote={noop}
        onNewFolder={noop}
        onRename={noop}
        onMoveTo={noop}
        onTogglePin={noop}
        onDelete={noop}
      />,
    )
    await userEvent.click(screen.getByRole("button", { name: /actions/i }))
    expect(screen.queryByText("New folder")).toBeNull()
  })

  it("reports the new folder's parent and the move's node", async () => {
    const onNewFolder = vi.fn()
    const onMoveTo = vi.fn()
    render(
      <NoteTreeActions
        node={folder}
        onNewNote={noop}
        onNewFolder={onNewFolder}
        onRename={noop}
        onMoveTo={onMoveTo}
        onTogglePin={noop}
        onDelete={noop}
      />,
    )
    await userEvent.click(screen.getByRole("button", { name: /actions/i }))
    await userEvent.click(screen.getByText("New folder"))
    expect(onNewFolder).toHaveBeenCalledWith("notes/a")

    await userEvent.click(screen.getByRole("button", { name: /actions/i }))
    await userEvent.click(screen.getByText("Move to…"))
    expect(onMoveTo).toHaveBeenCalledWith(folder)
  })

  it("lists the actions in the order the spec names them", async () => {
    render(
      <NoteTreeActions
        node={folder}
        onNewNote={noop}
        onNewFolder={noop}
        onRename={noop}
        onMoveTo={noop}
        onTogglePin={noop}
        onDelete={noop}
      />,
    )
    await userEvent.click(screen.getByRole("button", { name: /actions/i }))
    expect(
      screen.getAllByRole("menuitem").map((item) => item.textContent),
    ).toEqual(["New note", "New folder", "Rename", "Move to…", "Delete"])
  })

  it("offers no move on a document that has no uri to move", async () => {
    // A `(no path)` child's path is synthesised from its own uuid, so a move
    // would mint a real uri out of it. Same reason rename is withheld.
    const orphanChild: UriTreeNode = {
      name: "No uri note",
      path: `${NO_PATH}/d9`,
      document: { ...leaf.document!, id: "d9", uri: null },
      children: [],
    }
    render(
      <NoteTreeActions
        node={orphanChild}
        onNewNote={noop}
        onNewFolder={noop}
        onRename={noop}
        onMoveTo={noop}
        onTogglePin={noop}
        onDelete={noop}
      />,
    )
    await userEvent.click(screen.getByRole("button", { name: /actions/i }))
    expect(screen.queryByText("Move to…")).toBeNull()
    expect(screen.queryByText("Rename")).toBeNull()
    expect(screen.getByText("Delete")).toBeInTheDocument()
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
        onNewFolder={noop}
        onRename={noop}
        onMoveTo={noop}
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
            onNewFolder={noop}
            onRename={noop}
            onMoveTo={noop}
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
