import type { ReactNode } from "react"
import { FileText } from "lucide-react"
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

/** The one hierarchy implementation both document surfaces render.
 *
 * Selection is keyed on the *document id* and folders carry their path, so
 * the two key spaces cannot collide: a folder named like a uuid still selects
 * nothing, because no document maps to it.
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
          <TreeViewBranchControl>
            <TreeViewBranchIndicator />
            <TreeViewBranchText>{node.name}</TreeViewBranchText>
            {actions}
          </TreeViewBranchControl>
          <TreeViewBranchContent>
            {node.children.map(renderNode)}
          </TreeViewBranchContent>
        </TreeViewBranch>
      )
    }
    return (
      <TreeViewItem key={node.path} value={node.document?.id ?? node.path}>
        {node.name}
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
