import { useCallback, useState, type CSSProperties, type ReactNode } from "react"
import { ChevronRight, FileText, MoreHorizontal, Plus } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "darkraise-ui/components/dropdown-menu"
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
import { PAGE_TITLE_FALLBACK, type PageNode } from "./lib/build-page-tree"
import type { DropPlacement } from "./lib/drop-target"

const ROW = "w-full min-w-0 text-base"
const ROW_GAP = "gap-1.5"
const INDENT = "calc(var(--icon-size) + 0.375rem)"

export function notesExpansionStorageKey(project: string): string {
  return `darkmem:notes:expanded:${project}`
}

/** Storage is per viewer and can be absent or throw outright (private
 *  browsing, blocked site data), so every access is guarded and the tree
 *  renders collapsed when it fails rather than not at all. */
function readExpanded(project: string): string[] {
  try {
    const raw = window.localStorage.getItem(notesExpansionStorageKey(project))
    const parsed = raw ? (JSON.parse(raw) as unknown) : null
    return Array.isArray(parsed) ? parsed.filter((v) => typeof v === "string") : []
  } catch {
    return []
  }
}

function writeExpanded(project: string, ids: string[]): void {
  try {
    window.localStorage.setItem(notesExpansionStorageKey(project), JSON.stringify(ids))
  } catch {
    // A viewer convenience, never state the tree depends on.
  }
}

function titleOf(node: PageNode): string {
  return node.title?.trim() ? node.title : PAGE_TITLE_FALLBACK
}

function RowActions({
  node,
  onNewChild,
  onRename,
  onDelete,
}: {
  node: PageNode
  onNewChild: (parentId: string) => void
  onRename: (node: PageNode) => void
  onDelete: (node: PageNode) => void
}) {
  const label = titleOf(node)
  // Both stop propagation: React synthetic events bubble the React ancestor
  // chain even out of a portal, so without it opening the menu also selects
  // the row and navigates away from whatever the pane is editing.
  return (
    <span className="ml-auto flex shrink-0 items-center opacity-0 group-hover:opacity-100 focus-within:opacity-100">
      <button
        type="button"
        aria-label={`New page under ${label}`}
        className="text-muted-foreground hover:text-foreground rounded p-0.5"
        onClick={(event) => {
          event.stopPropagation()
          onNewChild(node.id)
        }}
      >
        <Plus aria-hidden className="size-4" />
      </button>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label={`Actions for ${label}`}
          className="text-muted-foreground hover:text-foreground rounded p-0.5"
          onClick={(event) => event.stopPropagation()}
        >
          <MoreHorizontal aria-hidden className="size-4" />
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="end"
          onClick={(event) => event.stopPropagation()}
        >
          <DropdownMenuItem onSelect={() => onRename(node)}>Rename</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => onDelete(node)}>Delete</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </span>
  )
}

/** The page hierarchy.
 *
 *  darkraise-ui's TreeView ships the behaviour (roving focus, selection,
 *  keyboard traversal) and no drag support; the drag layer beside it is local
 *  for that gap and should be retired if a later version closes it. The row
 *  itself is this feature's own rather than `DocumentTree`'s: that component
 *  is keyed on uri paths at every level and is rendered by `/documents` and
 *  `/projects/$project`, which this increment does not change.
 */
export function PageTree({
  roots,
  index,
  project,
  selectedId,
  onSelect,
  onNewChild,
  onRename,
  onDelete,
  onMove,
}: {
  roots: PageNode[]
  index: Map<string, PageNode>
  project: string
  selectedId: string | null
  onSelect: (pageId: string) => void
  onNewChild: (parentId: string) => void
  onRename: (node: PageNode) => void
  onDelete: (node: PageNode) => void
  onMove: (pageId: string, placement: DropPlacement) => void
}) {
  const [expanded, setExpanded] = useState<string[]>(() => readExpanded(project))

  const handleExpandedChange = useCallback(
    (next: string[]) => {
      setExpanded(next)
      writeExpanded(project, next)
    },
    [project],
  )

  void index
  void onMove

  if (roots.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={FileText}
        title="No pages yet"
        description="New page starts one. Nothing here is a project artifact."
      />
    )
  }

  const renderNode = (node: PageNode): ReactNode => {
    const actions = (
      <RowActions
        node={node}
        onNewChild={onNewChild}
        onRename={onRename}
        onDelete={onDelete}
      />
    )
    if (node.children.length > 0) {
      return (
        <TreeViewBranch key={node.id} value={node.id}>
          <TreeViewBranchControl className={`group relative ${ROW_GAP} ${ROW}`}>
            <TreeViewBranchIndicator className="text-muted-foreground shrink-0">
              <ChevronRight aria-hidden className="size-3.5" />
            </TreeViewBranchIndicator>
            <TreeViewBranchText className="truncate">
              {titleOf(node)}
            </TreeViewBranchText>
            {actions}
          </TreeViewBranchControl>
          <TreeViewBranchContent className="gap-0">
            {node.children.map(renderNode)}
          </TreeViewBranchContent>
        </TreeViewBranch>
      )
    }
    return (
      <TreeViewItem
        key={node.id}
        value={node.id}
        className={`group relative ${ROW_GAP} ${ROW}`}
      >
        {/* Aligns a leaf's text with a sibling branch's, whose row spends this
            width on the chevron. */}
        <span aria-hidden className="w-[var(--icon-size)] shrink-0" />
        <span className="truncate">{titleOf(node)}</span>
        {actions}
      </TreeViewItem>
    )
  }

  return (
    <TreeView
      expanded={expanded}
      onExpandedChange={(d: { value: string[] }) => handleExpandedChange(d.value)}
      selectionMode="single"
      selected={selectedId ? [selectedId] : []}
      onSelectedChange={({ value }: { value: string[] }) => {
        const id = value.find((v) => index.has(v))
        if (id) onSelect(id)
      }}
    >
      <TreeViewTree
        className="gap-0 pl-1"
        style={{ "--tree-view-indent": INDENT } as CSSProperties}
      >
        {roots.map(renderNode)}
      </TreeViewTree>
    </TreeView>
  )
}
