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
  onRename: (node: UriTreeNode) => void
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
  onRename,
  onTogglePin,
  onDelete,
}: NoteTreeActionsProps) {
  if (node.path === NO_PATH) return null

  const document = node.document

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
        {document ? null : (
          <DropdownMenuItem onSelect={() => onNewNote(node.path)}>
            New note
          </DropdownMenuItem>
        )}
        <DropdownMenuItem onSelect={() => onRename(node)}>
          Rename
        </DropdownMenuItem>
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
