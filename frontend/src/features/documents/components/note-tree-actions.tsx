import { MoreHorizontal } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "darkraise-ui/components/dropdown-menu"
import { NO_PATH, type UriTreeNode } from "../uri-tree"

export interface NoteTreeActionsProps {
  node: UriTreeNode
  onNewNote: (folderPath: string) => void
  onNewFolder: (parentPath: string) => void
  onRename: (node: UriTreeNode) => void
  onMoveTo: (node: UriTreeNode) => void
  onTogglePin: (node: UriTreeNode) => void
  onDelete: (node: UriTreeNode) => void
}

/** The per-row action menu, mounted through `DocumentTree`'s `nodeActions`
 *  slot. Renders nothing for the synthesised `(no path)` bucket: it has no
 *  uri, so every folder operation on it would carry a prefix matching
 *  nothing. */
export function NoteTreeActions({
  node,
  onNewNote,
  onNewFolder,
  onRename,
  onMoveTo,
  onTogglePin,
  onDelete,
}: NoteTreeActionsProps) {
  if (node.path === NO_PATH) return null

  const document = node.document
  // A `(no path)` child is a document with a NULL uri. Rename and move both
  // rewrite a uri, so they have nothing to act on here -- and the subtree
  // verbs would carry a prefix matching no row at all.
  const relocatable = !node.path.startsWith(`${NO_PATH}/`)

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label={`Actions for ${node.name}`}
        className="text-muted-foreground hover:text-foreground ml-auto shrink-0 rounded p-0.5"
        // Without this the row's own selection handler fires too, so opening
        // the menu would also navigate away from what the reader is editing.
        onClick={(event) => event.stopPropagation()}
      >
        <MoreHorizontal aria-hidden className="size-4" />
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        // The content is portalled, but React synthetic events bubble the
        // React ancestor chain, not the DOM one, so an item's click still
        // reaches the row's select/expand handler without this.
        onClick={(event) => event.stopPropagation()}
      >
        {/* Creates ride the same condition: a node carrying a document is a
            note, and filing under it would mint a path below a file. A node
            that is both -- `a/b.md` above `a/b.md/c.md` -- reads as the note
            it names, so it offers neither. */}
        {document ? null : (
          <>
            <DropdownMenuItem onSelect={() => onNewNote(node.path)}>
              New note
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => onNewFolder(node.path)}>
              New folder
            </DropdownMenuItem>
          </>
        )}
        {relocatable ? (
          <>
            <DropdownMenuItem onSelect={() => onRename(node)}>
              Rename
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => onMoveTo(node)}>
              Move to…
            </DropdownMenuItem>
          </>
        ) : null}
        {document ? (
          <DropdownMenuItem onSelect={() => onTogglePin(node)}>
            {document.pinned_at ? "Unpin" : "Pin"}
          </DropdownMenuItem>
        ) : null}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => onDelete(node)}>
          Delete
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
