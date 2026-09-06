import type { ReactNode } from "react"
import { FileText, Folder, FolderOpen } from "lucide-react"
import {
  TreeView,
  TreeViewBranch,
  TreeViewBranchContent,
  TreeViewBranchControl,
  TreeViewBranchIndicator,
  TreeViewBranchText,
  TreeViewItem,
  TreeViewTree,
} from "darkraise-ui/components/tree-view"
import { EmptyState } from "@/components/darkmem"
import type { DocumentListItem } from "@/hooks/api"
import { buildUriTree, type UriTreeNode } from "../uri-tree"
import { fileIcon } from "../file-icons"

/** Explorer rows.
 *
 * Deliberately thin: everything the library's own `.dr-tree-view-item` /
 * `.dr-tree-view-branch-control` rule already sets -- the flex row, the gap,
 * the padding, the radius, the `bg-accent` hover and the `bg-primary-fill`
 * selected fill -- is left to it, because a Tailwind utility here lands in
 * the `utilities` layer and beats the library's `components` layer. That is
 * what made a *selected* row turn muted the moment the pointer entered it:
 * a local `hover:bg-muted/60` outranked `[data-selected=true]`'s fill.
 *
 * `w-full` is what makes the highlight the whole row rather than the row's
 * content: these rows sit in a horizontally scrollable pane, where a
 * stretch-sized `li` stops at the viewport edge and the fill ends mid-row.
 *
 * Only the type size is ours, and only because a file browser is read as a
 * column of names rather than scanned as chrome. */
const ROW = "w-full min-w-0 text-base"

/** The one hierarchy implementation both document surfaces render.
 *
 * Selection is keyed on the *document id* and folders carry their path, so
 * the two key spaces cannot collide: a folder named like a uuid still selects
 * nothing, because no document maps to it.
 *
 * Styled as a file explorer rather than a generic outline: per-extension leaf
 * icons, a folder icon that opens with its branch, dense rows and an indent
 * guide per level. All of it is `className` on darkraise-ui's own TreeView
 * parts -- the library ships the behaviour (roving focus, selection, keyboard
 * traversal) and re-implementing that to change its looks would be the trade
 * the UI rule warns against.
 */
export function DocumentTree({
  items,
  selectedId,
  onSelect,
  truncated,
  nodeActions,
  expanded,
  onExpandedChange,
}: {
  items: DocumentListItem[]
  selectedId: string | null
  onSelect: (doc: DocumentListItem) => void
  truncated: boolean
  /** Optional per-node action slot. Increment 8 mounts its "new subpage"
   *  affordance here; this surface passes nothing. Declared now so the
   *  editor extends this component rather than rewriting it. */
  nodeActions?: (node: UriTreeNode) => ReactNode
  /** Controlled expansion. Omitted keeps the legacy expand-everything
   *  behaviour, so increment 8's call site is unaffected. */
  expanded?: string[]
  onExpandedChange?: (paths: string[]) => void
}) {
  const roots = buildUriTree(items)
  const byId = new Map(items.map((d) => [d.id, d]))

  const controlled = expanded !== undefined
  const treeExpansionProps = controlled
    ? {
        expanded,
        onExpandedChange: (d: { value: string[] }) => onExpandedChange?.(d.value),
      }
    : {
        // Expanded by default. A collapsed tree of one `file:` or `docs`
        // node reads as an empty panel -- the reader has to guess that
        // anything is in there -- and the corpus this renders is a few
        // hundred files, not a filesystem. Only collected on this
        // uncontrolled path: the controlled caller discards the result, and
        // walking every node on each render is dead work over hundreds of
        // files per keystroke.
        defaultExpanded: (() => {
          const allFolderPaths: string[] = []
          const collect = (nodes: UriTreeNode[]) => {
            for (const node of nodes) {
              if (node.children.length > 0) {
                allFolderPaths.push(node.path)
                collect(node.children)
              }
            }
          }
          collect(roots)
          return allFolderPaths
        })(),
      }

  if (items.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={FileText}
        title="No documents filed in this project"
        description="A document appears here the moment it is filed — over REST or over MCP."
      />
    )
  }

  const renderNode = (node: UriTreeNode): ReactNode => {
    const actions = nodeActions?.(node)

    if (node.children.length > 0) {
      return (
        <TreeViewBranch key={node.path} value={node.path}>
          <TreeViewBranchControl className={`group ${ROW}`}>
            <TreeViewBranchIndicator className="text-muted-foreground shrink-0" />
            {/* Both icons render and CSS picks one off the control's own
                `data-state`. Deriving it in JS would need the live open set,
                which the uncontrolled caller does not have. */}
            <Folder
              aria-hidden
              className="size-[18px] shrink-0 text-sky-700/80 group-data-[state=open]:hidden dark:text-sky-300/80"
            />
            <FolderOpen
              aria-hidden
              className="hidden size-[18px] shrink-0 text-sky-700/80 group-data-[state=open]:block dark:text-sky-300/80"
            />
            <TreeViewBranchText className="truncate">
              {node.name}
            </TreeViewBranchText>
            {actions}
          </TreeViewBranchControl>
          {/* The indent guide: one hairline per level, the way an explorer
              shows which rows belong to which folder. */}
          <TreeViewBranchContent className="border-border/60 ml-[17px] border-l pl-2">
            {node.children.map(renderNode)}
          </TreeViewBranchContent>
        </TreeViewBranch>
      )
    }

    const { icon: Icon, className: iconTone } = fileIcon(node.name)
    return (
      <TreeViewItem
        key={node.path}
        value={node.document?.id ?? node.path}
        className={ROW}
      >
        {/* Aligns leaf text with a sibling folder's, whose row spends this
            width on the chevron. */}
        <span aria-hidden className="w-[var(--icon-size)] shrink-0" />
        <Icon aria-hidden className={`size-[18px] shrink-0 ${iconTone}`} />
        <span className="truncate">{node.name}</span>
        {actions}
      </TreeViewItem>
    )
  }

  return (
    <div className="space-y-2">
      {truncated ? (
        <p className="border-warning/50 text-muted-foreground rounded-md border border-dashed px-2.5 py-1.5 text-sm">
          Showing the first {items.length} documents — the list was cut at the
          pagination guard, so this tree is incomplete.
        </p>
      ) : null}
      <TreeView
        {...treeExpansionProps}
        selectionMode="single"
        selected={selectedId ? [selectedId] : []}
        onSelectedChange={({ value }) => {
          const doc = value.map((v) => byId.get(v)).find(Boolean)
          if (doc) onSelect(doc)
        }}
      >
        <TreeViewTree>{roots.map(renderNode)}</TreeViewTree>
      </TreeView>
    </div>
  )
}
