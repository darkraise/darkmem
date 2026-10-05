import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react"
import {
  DndContext,
  MouseSensor,
  TouchSensor,
  getClientRect,
  pointerWithin,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type CollisionDetection,
  type DragEndEvent,
  type DragMoveEvent,
  type DragOverEvent,
} from "@dnd-kit/core"
import {
  ChevronRight,
  FileText,
  MoreHorizontal,
  Pencil,
  Plus,
  Trash2,
} from "lucide-react"
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
import {
  dropZoneFor,
  resolvePageDrop,
  type DropPlacement,
  type DropZone,
} from "./lib/drop-target"

const ROW = "w-full min-w-0 text-base"
const ROW_GAP = "gap-1.5"
const INDENT = "calc(var(--icon-size) + 0.375rem)"
/** Every row is a page, branch or leaf, so every row carries the one page
 *  glyph -- the document tree's rows carry their file icons the same way. */
const PAGE_ICON = "text-muted-foreground size-[var(--icon-size)] shrink-0"

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
    return Array.isArray(parsed)
      ? parsed.filter((v) => typeof v === "string")
      : []
  } catch {
    return []
  }
}

function writeExpanded(project: string, ids: string[]): void {
  try {
    window.localStorage.setItem(
      notesExpansionStorageKey(project),
      JSON.stringify(ids),
    )
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
    // Hidden at rest so a long tree is not a wall of icons, but always shown
    // on the selected row and on a device with no hover, where "appears on
    // hover" means "never appears until tapped".
    <span className="ml-auto flex shrink-0 items-center opacity-0 group-hover:opacity-100 group-data-[selected=true]:opacity-100 focus-within:opacity-100 [@media(hover:none)]:opacity-100">
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
          <DropdownMenuItem onSelect={() => onRename(node)}>
            <Pencil aria-hidden className="mr-2 size-3.5" />
            Rename
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            className="text-destructive focus:text-destructive data-[highlighted]:text-destructive"
            onSelect={() => onDelete(node)}
          >
            <Trash2 aria-hidden className="mr-2 size-3.5" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </span>
  )
}

export const DRAG_PREFIX = "drag:"
export const DROP_PREFIX = "drop:"

/** A droppable's hit area is the ROW, not the span the listeners hang off: a
 *  branch's element encloses its whole subtree, so its hit area would swallow
 *  every descendant row. */
const DROP_ROW_ATTR = "data-drop-row"

function measureDropRow(node: HTMLElement) {
  return getClientRect(node.closest<HTMLElement>(`[${DROP_ROW_ATTR}]`) ?? node)
}

const MEASURING = { droppable: { measure: measureDropRow } }

/** Mouse and touch are separate sensors. One `PointerSensor` needs
 *  `touch-action: none` on the handle, which covers most of every row and
 *  would disable native panning of the tree outright. */
const MOUSE_ACTIVATION = { activationConstraint: { distance: 6 } } as const
const TOUCH_ACTIVATION = {
  activationConstraint: { delay: 220, tolerance: 6 },
} as const

/** How long a collapsed row is hovered before it opens under the pointer. */
const HOVER_EXPAND_MS = 600

/** Whether hovering `pageId` should arm the expand timer. Separated from the
 *  timer because dnd-kit's pointer pipeline does not run under jsdom, so this
 *  is the half a unit test can reach; the timer itself is untested. */
export function shouldHoverExpand(
  index: Map<string, PageNode>,
  expanded: string[],
  pageId: string,
): boolean {
  const node = index.get(pageId)
  return (
    Boolean(node) && node!.children.length > 0 && !expanded.includes(pageId)
  )
}

export function pointerZone(
  rect: { top: number; height: number } | null,
  pointerY: number,
): DropZone {
  if (!rect) return "inside"
  return dropZoneFor(pointerY - rect.top, rect.height)
}

/** The whole drop decision, as a pure function of the tree, the two ids and
 *  the zone. Prefixed ids keep the drag and drop key spaces apart, which is
 *  what lets one element be both. */
export function resolveDrop(
  roots: PageNode[],
  index: Map<string, PageNode>,
  activeId: string,
  overId: string | null,
  zone: DropZone,
): DropPlacement | null {
  return resolvePageDrop(
    roots,
    index,
    activeId.slice(DRAG_PREFIX.length),
    overId === null ? null : overId.slice(DROP_PREFIX.length),
    zone,
  )
}

function RowHandle({
  node,
  zone,
  activeId,
  children,
}: {
  node: PageNode
  zone: DropZone | null
  activeId: string | null
  children: ReactNode
}) {
  const {
    setNodeRef: setDragRef,
    listeners,
    isDragging,
  } = useDraggable({
    id: `${DRAG_PREFIX}${node.id}`,
  })
  const { setNodeRef: setDropRef, isOver } = useDroppable({
    id: `${DROP_PREFIX}${node.id}`,
  })
  // Stable across renders: an inline arrow re-registers the droppable and
  // re-runs its ResizeObserver on every one.
  const setRef = useCallback(
    (el: HTMLElement | null) => {
      setDragRef(el)
      setDropRef(el)
    },
    [setDragRef, setDropRef],
  )
  const showing = isOver && activeId !== null ? zone : null
  return (
    <span
      data-drag-handle
      data-drop-zone={showing ?? undefined}
      data-dragging={isDragging || undefined}
      ref={setRef}
      {...listeners}
      className="ring-primary data-[drop-zone=after]:border-b-primary data-[drop-zone=before]:border-t-primary flex min-w-0 flex-1 items-center gap-1.5 rounded-sm border-y border-transparent data-[dragging]:opacity-50 data-[drop-zone=inside]:ring-1"
    >
      {children}
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
  const [expanded, setExpanded] = useState<string[]>(() =>
    readExpanded(project),
  )

  const handleExpandedChange = useCallback(
    (next: string[]) => {
      setExpanded(next)
      writeExpanded(project, next)
    },
    [project],
  )

  const [activeId, setActiveId] = useState<string | null>(null)
  const [zone, setZone] = useState<DropZone | null>(null)
  const pointerY = useRef(0)
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const hoveredId = useRef<string | null>(null)

  const sensors = useSensors(
    // Without a distance every click is a zero-length drag and the row never
    // selects.
    useSensor(MouseSensor, MOUSE_ACTIVATION),
    useSensor(TouchSensor, TOUCH_ACTIVATION),
  )

  // The pointer's own position is what picks the zone, and the collision pass
  // is the only place dnd-kit hands it over.
  const collisionDetection = useCallback<CollisionDetection>((args) => {
    if (args.pointerCoordinates) pointerY.current = args.pointerCoordinates.y
    return pointerWithin(args)
  }, [])

  const cancelHover = useCallback(() => {
    if (hoverTimer.current) clearTimeout(hoverTimer.current)
    hoverTimer.current = null
    hoveredId.current = null
  }, [])

  useEffect(() => cancelHover, [cancelHover])

  // `onDragOver` fires only when the droppable itself changes, so the zone is
  // tracked here instead: moving within one row is what picks between its
  // three thirds, and the indicator has to agree with the drop the release
  // will resolve.
  const handleDragMove = useCallback((event: DragMoveEvent) => {
    setZone(pointerZone(event.over?.rect ?? null, pointerY.current))
  }, [])

  const handleDragOver = useCallback(
    (event: DragOverEvent) => {
      const overId = event.over ? String(event.over.id) : null
      const next = pointerZone(event.over?.rect ?? null, pointerY.current)
      setZone(next)
      if (overId === null) {
        cancelHover()
        return
      }
      const pageId = overId.slice(DROP_PREFIX.length)
      if (hoveredId.current === pageId) return
      cancelHover()
      hoveredId.current = pageId
      if (!shouldHoverExpand(index, expanded, pageId)) return
      hoverTimer.current = setTimeout(
        () => handleExpandedChange([...expanded, pageId]),
        HOVER_EXPAND_MS,
      )
    },
    [cancelHover, expanded, handleExpandedChange, index],
  )

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      cancelHover()
      const activeKey = String(event.active.id)
      const placement = resolveDrop(
        roots,
        index,
        activeKey,
        event.over ? String(event.over.id) : null,
        pointerZone(event.over?.rect ?? null, pointerY.current),
      )
      setActiveId(null)
      setZone(null)
      if (placement) onMove(activeKey.slice(DRAG_PREFIX.length), placement)
    },
    [cancelHover, index, onMove, roots],
  )

  const handleDragCancel = useCallback(() => {
    cancelHover()
    setActiveId(null)
    setZone(null)
  }, [cancelHover])

  if (roots.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={FileText}
        title="No pages yet"
        description="Use New page to start one."
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
          <TreeViewBranchControl
            data-drop-row=""
            className={`group relative ${ROW_GAP} ${ROW}`}
          >
            <TreeViewBranchIndicator className="text-muted-foreground shrink-0">
              <ChevronRight aria-hidden className="size-3.5" />
            </TreeViewBranchIndicator>
            <RowHandle node={node} zone={zone} activeId={activeId}>
              <FileText aria-hidden className={PAGE_ICON} />
              <TreeViewBranchText className="truncate" title={titleOf(node)}>
                {titleOf(node)}
              </TreeViewBranchText>
            </RowHandle>
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
        data-drop-row=""
        value={node.id}
        className={`group relative ${ROW_GAP} ${ROW}`}
      >
        {/* Aligns a leaf's text with a sibling branch's, whose row spends this
            width on the chevron. */}
        <span aria-hidden className="w-[var(--icon-size)] shrink-0" />
        <RowHandle node={node} zone={zone} activeId={activeId}>
          <FileText aria-hidden className={PAGE_ICON} />
          <span className="truncate" title={titleOf(node)}>
            {titleOf(node)}
          </span>
        </RowHandle>
        {actions}
      </TreeViewItem>
    )
  }

  return (
    <DndContext
      sensors={sensors}
      measuring={MEASURING}
      collisionDetection={collisionDetection}
      onDragStart={(event) => setActiveId(String(event.active.id))}
      onDragMove={handleDragMove}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={handleDragCancel}
    >
      <TreeView
        expanded={expanded}
        onExpandedChange={(d: { value: string[] }) =>
          handleExpandedChange(d.value)
        }
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
    </DndContext>
  )
}
