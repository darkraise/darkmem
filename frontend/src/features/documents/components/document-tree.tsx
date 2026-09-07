import { memo, useCallback, useMemo, useState, type CSSProperties, type ReactNode } from "react"
import {
  DndContext,
  MouseSensor,
  TouchSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  pointerWithin,
  type Collision,
  type CollisionDetection,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core"
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
import { moveTarget, type MoveTarget } from "../move-target"
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
 * from the column it belongs to. Out of flow, each hairline lands exactly on
 * the centre of its owner's CHEVRON and nothing about the row's own layout
 * changes: the line descends from the expander that opened the branch, which
 * is what a reader follows back up to find the parent.
 *
 * `left` is measured from the row's left edge (the row is the containing
 * block), which is the same edge at every depth because every row is the full
 * pane width -- so an ancestor at depth `level` has its chevron centred at
 * `level * indent + icon / 2` inside any of its descendants' rows. Every
 * guide therefore sits one whole column left of the row's own chevron and
 * crosses nothing.
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
            left: `calc(${level} * ${INDENT} + var(--icon-size) / 2)`,
          }}
        />
      ))}
    </>
  )
}

/** The drag layer.
 *
 * darkraise-ui's TreeView ships no drag support -- checked in its `.d.ts`:
 * no drag props on any part, and the package holds no drag or sortable
 * component at all. This local layer exists for that gap and should be
 * retired if a later version closes it.
 *
 * The listeners hang off an inner span rather than the library's own row.
 * `TreeViewItem` and `TreeViewBranchControl` spread `...props` onto their
 * elements, but that spread lands after `ref`, `role="treeitem"`, the roving
 * `tabIndex` and the `aria-*` attributes -- so `useDraggable().attributes`
 * (`role="button"`, `tabIndex=0`) would replace the accessible tree and the
 * arrow-key traversal `TreeViewTree` handles by bubbling. `attributes` is
 * therefore never spread anywhere.
 */
export const DRAG_PREFIX = "drag:"
export const DROP_PREFIX = "drop:"

/** The pane itself, so a row can be moved back to the top level. */
export const ROOT_DROP_ID = DROP_PREFIX

export function buildPathMap(roots: UriTreeNode[]): Map<string, UriTreeNode> {
  const map = new Map<string, UriTreeNode>()
  const walk = (nodes: UriTreeNode[]) => {
    for (const node of nodes) {
      map.set(node.path, node)
      walk(node.children)
    }
  }
  walk(roots)
  return map
}

/** Which node a release over `node` actually means.
 *
 *  A leaf resolves to its PARENT rather than being an inert droppable. Left
 *  disabled, a release over a sibling row fell through to the pane droppable
 *  underneath and resolved to "move to the top level" -- an accepted uri
 *  rewrite from the likeliest accidental release position there is. Resolved
 *  to the parent it lands on `moveTarget`'s own "already there" refusal.
 */
export function dropTargetFor(
  byPath: Map<string, UriTreeNode>,
  node: UriTreeNode,
): UriTreeNode | null {
  if (node.children.length > 0) return node
  const leaf = node.path.split("/").pop()!
  // `Math.max(0, ...)` rather than a bare `lastIndexOf`: a root-level leaf
  // has no slash, and `"docs2".slice(0, -1)` is the truthy `"docs"` -- which
  // resolved a root leaf into whatever folder its own name shadows.
  const parent = node.path.slice(0, Math.max(0, node.path.length - leaf.length - 1))
  return parent ? (byPath.get(parent) ?? null) : null
}

/** Row droppables are NEVER disabled, and that is the fix rather than an
 *  omission. `DndContext` filters droppables through `getEnabled()` BEFORE
 *  it calls the collision detector, so a row disabled because `moveTarget`
 *  refuses it is not a candidate at all: the pointer falls through to the
 *  pane droppable that encloses it and the release resolves as a move to the
 *  top level -- an accepted uri rewrite from a position the UI had just
 *  declared refused. Every row stays a candidate and `resolveDrop` is the
 *  one place a drop is refused; the hover ring is gated on `moveTarget`
 *  separately, so a refused row still looks refused. */
export const ROW_DROP_DISABLED = false

/** The whole drop decision, as a pure function of the tree and the two ids. */
export function resolveDrop(
  byPath: Map<string, UriTreeNode>,
  activeId: string,
  overId: string | null,
): MoveTarget | null {
  const dragged = byPath.get(activeId.slice(DRAG_PREFIX.length))
  if (!dragged || overId === null) return null
  const overPath = overId.slice(DROP_PREFIX.length)
  const over = overPath ? byPath.get(overPath) : undefined
  if (overPath && !over) return null
  return moveTarget(dragged, over ? dropTargetFor(byPath, over) : null)
}

/** The pane droppable encloses every other one, so an area-ranking detector
 *  (dnd-kit's default) would let it win every hover. A row underneath the
 *  pointer therefore always outranks it. */
export function preferInnermost(hits: Collision[]): Collision[] {
  const inner = hits.filter((c) => c.id !== ROOT_DROP_ID)
  return inner.length > 0 ? inner : hits
}

const collisionDetection: CollisionDetection = (args) =>
  preferInnermost(pointerWithin(args))

/** Mouse and touch are separate sensors on purpose. A single `PointerSensor`
 *  needs `touch-action: none` on the handle, which covers most of every row
 *  and would disable native panning of the tree outright -- a touch scroll
 *  started on any row would never scroll. A long-press delay separates a
 *  touch drag from a pan without taking the gesture away. */
const MOUSE_ACTIVATION = { activationConstraint: { distance: 6 } } as const
const TOUCH_ACTIVATION = {
  activationConstraint: { delay: 220, tolerance: 6 },
} as const

/** Drop-to-root. Rendered only inside the context, so the hook it calls can
 *  never run on the drag-free path. */
function RootDroppable({
  activeNode,
  children,
}: {
  activeNode: UriTreeNode | null
  children: ReactNode
}) {
  const { setNodeRef, isOver } = useDroppable({ id: ROOT_DROP_ID })
  const refused = activeNode !== null && moveTarget(activeNode, null) === null
  return (
    <div
      ref={setNodeRef}
      data-drop-over={(isOver && !refused) || undefined}
      className="outline-primary/70 rounded-md data-[drop-over]:outline-1 data-[drop-over]:outline-dashed"
    >
      {children}
    </div>
  )
}

function RowHandle({
  node,
  dropTarget,
  activeNode,
  children,
}: {
  node: UriTreeNode
  dropTarget: UriTreeNode | null
  activeNode: UriTreeNode | null
  children: ReactNode
}) {
  const { setNodeRef: setDragRef, listeners, isDragging } = useDraggable({
    id: `${DRAG_PREFIX}${node.path}`,
  })
  const { setNodeRef: setDropRef, isOver } = useDroppable({
    id: `${DROP_PREFIX}${node.path}`,
    disabled: ROW_DROP_DISABLED,
  })
  // The ring, not the candidacy, is what a refused target loses.
  const refused = activeNode !== null && moveTarget(activeNode, dropTarget) === null
  // Stable across renders: an inline arrow re-registers the droppable and
  // re-runs its ResizeObserver on every one.
  const setRef = useCallback(
    (el: HTMLElement | null) => {
      setDragRef(el)
      setDropRef(el)
    },
    [setDragRef, setDropRef],
  )
  return (
    <span
      data-drag-handle
      data-drop-over={(isOver && !refused) || undefined}
      data-dragging={isDragging || undefined}
      ref={setRef}
      {...listeners}
      className="ring-primary flex min-w-0 flex-1 items-center gap-1.5 rounded-sm data-[dragging]:opacity-50 data-[drop-over]:ring-1"
    >
      {children}
    </span>
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
export const DocumentTree = memo(function DocumentTree({
  items,
  selectedId,
  onSelect,
  truncated,
  nodeActions,
  emptyAction,
  expanded,
  onExpandedChange,
  onMove,
}: {
  items: DocumentListItem[]
  selectedId: string | null
  onSelect: (doc: DocumentListItem) => void
  truncated: boolean
  /** Optional per-node action slot. Increment 8 mounts its "new subpage"
   *  affordance here; this surface passes nothing. Declared now so the
   *  editor extends this component rather than rewriting it. */
  nodeActions?: (node: UriTreeNode) => ReactNode
  /** Rendered inside the empty state. Without it an empty space has no
   *  affordance at all: this branch returns before any row, and `nodeActions`
   *  only ever hangs off a row. */
  emptyAction?: ReactNode
  /** Controlled expansion. Omitted keeps the legacy expand-everything
   *  behaviour, so increment 8's call site is unaffected. */
  expanded?: string[]
  onExpandedChange?: (paths: string[]) => void
  /** Drop resolution. Omitted mounts no drag layer at all, which is what
   *  every caller that does not persist a move wants. */
  onMove?: (target: MoveTarget) => void
}) {
  // Rebuilt per document list, not per render: the artifacts workspace holds
  // the reader's reported heading as its own state, so a scroll through a
  // long document re-renders this pane once per heading crossed.
  const roots = useMemo(() => buildUriTree(items), [items])
  const byId = useMemo(() => new Map(items.map((d) => [d.id, d])), [items])
  const byPath = useMemo(() => buildPathMap(roots), [roots])

  const [activeNode, setActiveNode] = useState<UriTreeNode | null>(null)
  const sensors = useSensors(
    // Without a distance every click is a zero-length drag and the row never
    // selects.
    useSensor(MouseSensor, MOUSE_ACTIVATION),
    useSensor(TouchSensor, TOUCH_ACTIVATION),
  )
  const onDragStart = useCallback(
    (event: DragStartEvent) => {
      const path = String(event.active.id).slice(DRAG_PREFIX.length)
      setActiveNode(byPath.get(path) ?? null)
    },
    [byPath],
  )
  const onDragEnd = useCallback(
    (event: DragEndEvent) => {
      setActiveNode(null)
      const target = resolveDrop(
        byPath,
        String(event.active.id),
        event.over ? String(event.over.id) : null,
      )
      if (target) onMove?.(target)
    },
    [byPath, onMove],
  )
  const onDragCancel = useCallback(() => setActiveNode(null), [])

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
        action={emptyAction}
      />
    )
  }

  const renderNode = (node: UriTreeNode, depth = 0): ReactNode => {
    const actions = nodeActions?.(node)
    const handle = (children: ReactNode): ReactNode =>
      onMove ? (
        <RowHandle
          node={node}
          dropTarget={dropTargetFor(byPath, node)}
          activeNode={activeNode}
        >
          {children}
        </RowHandle>
      ) : (
        children
      )

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
            {handle(
              <>
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
              </>,
            )}
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
        {handle(
          <>
            <Icon aria-hidden className={`size-[var(--icon-size)] shrink-0 ${iconTone}`} />
            <span className="truncate">{node.name}</span>
          </>,
        )}
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
      <MaybeDnd
        enabled={onMove !== undefined}
        activeNode={activeNode}
        sensors={sensors}
        collisionDetection={collisionDetection}
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
        onDragCancel={onDragCancel}
      >
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
      </MaybeDnd>
    </div>
  )
})

function MaybeDnd({
  enabled,
  activeNode,
  children,
  ...context
}: {
  enabled: boolean
  activeNode: UriTreeNode | null
  children: ReactNode
} & Omit<Parameters<typeof DndContext>[0], "children">) {
  if (!enabled) return <>{children}</>
  return (
    <DndContext {...context}>
      <RootDroppable activeNode={activeNode}>{children}</RootDroppable>
    </DndContext>
  )
}
