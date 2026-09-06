import type { CSSProperties, ReactNode } from "react"
import { ChevronRight, FileText, Folder, FolderOpen } from "lucide-react"
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
 * Only the type size is ours, and only because a file browser is read as a
 * column of names rather than scanned as chrome. */
const ROW = "w-full min-w-0 text-base"

/** Indent, and where each level's guide sits.
 *
 * The library already indents the ROW -- `paddingInlineStart: calc(depth *
 * var(--tree-view-indent, 1rem))` -- which is the VSCode shape: every row is
 * the full width of the pane at every depth and only its padding moves, so
 * the hover and the selected fill are the same bar everywhere.
 *
 * This tree used to indent the child `ul` instead, on top of that. Indenting
 * the container indents the rows themselves, so a nested row's box started
 * further right and was narrower -- which is what made a selected nested row
 * render as a short offset bar. The container carries no indent now and the
 * only knob is the library's own variable.
 *
 * One step is exactly one icon column: `--icon-size` for the chevron plus the
 * row's own gap. That equality is what makes the guides land: a child row's
 * chevron then starts precisely where its parent's folder icon starts, so one
 * vertical line at the parent icon's centre runs down through every
 * descendant's chevron column. An indent smaller than the column (this was
 * 12px) puts the child's chevron under the *middle* of the parent's icon and
 * no single x can align with both, which is why the guides used to sit beside
 * the folder icon rather than under it. Both icon slots therefore have to
 * stay `--icon-size` wide -- a hardcoded `18px` on the folder or file icon
 * re-breaks the alignment wherever `--icon-scale` is not 1.125.
 */
const ROW_GAP = "gap-1.5"
const INDENT = "calc(var(--icon-size) + 0.375rem)"

/** The nesting guides.
 *
 * Absolutely positioned rather than laid out: the row is a flex line with a
 * gap, so a guide block placed in flow picked that gap up and drifted away
 * from the icon it belongs in front of. Out of flow, each hairline lands
 * exactly on the centre of the icon column its owner occupies and nothing
 * about the row's own layout changes.
 *
 * `left` is measured from the row's left edge (the row is the containing
 * block), which is the same edge at every depth because every row is the full
 * pane width -- so an ancestor at depth `level` has its icon centred at
 * `(level + 1) * indent + icon / 2` inside any of its descendants' rows.
 */
function IndentGuides({ depth }: { depth: number }) {
  if (depth === 0) return null
  return (
    <>
      {Array.from({ length: depth }, (_, level) => (
        <span
          key={level}
          aria-hidden
          className="border-border/60 pointer-events-none absolute inset-y-0 border-l group-data-[selected=true]:opacity-0"
          style={{
            left: `calc(${level + 1} * ${INDENT} + var(--icon-size) / 2)`,
          }}
        />
      ))}
    </>
  )
}

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

  const renderNode = (node: UriTreeNode, depth = 0): ReactNode => {
    const actions = nodeActions?.(node)

    if (node.children.length > 0) {
      return (
        <TreeViewBranch key={node.path} value={node.path}>
          <TreeViewBranchControl className={`group relative ${ROW_GAP} ${ROW}`}>
            <IndentGuides depth={depth} />
            {/* The library's indicator renders only what it is given and
                rotates it on `data-state=open`; with no child it was an
                empty box, so the tree shipped with an invisible chevron. */}
            <TreeViewBranchIndicator className="text-muted-foreground shrink-0">
              <ChevronRight aria-hidden className="size-3.5" />
            </TreeViewBranchIndicator>
            {/* Both icons render and CSS picks one off the control's own
                `data-state`. Deriving it in JS would need the live open set,
                which the uncontrolled caller does not have. */}
            <Folder
              aria-hidden
              className="size-[var(--icon-size)] shrink-0 text-sky-700/80 group-data-[state=open]:hidden dark:text-sky-300/80"
            />
            <FolderOpen
              aria-hidden
              className="hidden size-[var(--icon-size)] shrink-0 text-sky-700/80 group-data-[state=open]:block dark:text-sky-300/80"
            />
            <TreeViewBranchText className="truncate">
              {node.name}
            </TreeViewBranchText>
            {actions}
          </TreeViewBranchControl>
          {/* No indent of its own: the nesting is drawn inside each child
              row by `Indent`, so every row keeps the full pane width. The
              gap is dropped so the guides run unbroken between rows. */}
          <TreeViewBranchContent className="gap-0">
            {node.children.map((child) => renderNode(child, depth + 1))}
          </TreeViewBranchContent>
        </TreeViewBranch>
      )
    }

    const { icon: Icon, className: iconTone } = fileIcon(node.name)
    return (
      <TreeViewItem
        key={node.path}
        value={node.document?.id ?? node.path}
        className={`group relative ${ROW_GAP} ${ROW}`}
      >
        <IndentGuides depth={depth} />
        {/* Aligns leaf text with a sibling folder's, whose row spends this
            width on the chevron. */}
        <span aria-hidden className="w-[var(--icon-size)] shrink-0" />
        <Icon aria-hidden className={`size-[var(--icon-size)] shrink-0 ${iconTone}`} />
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
        <TreeViewTree
          className="gap-0 pl-1"
          style={{ "--tree-view-indent": INDENT } as CSSProperties}
        >
          {roots.map((root) => renderNode(root, 0))}
        </TreeViewTree>
      </TreeView>
    </div>
  )
}
