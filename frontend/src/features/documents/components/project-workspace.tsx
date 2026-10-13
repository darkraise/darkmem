import {
  Fragment,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"
import { FilePlus, FolderTree, Info, Search, Sparkles } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Card } from "darkraise-ui/components/card"
import { Input } from "darkraise-ui/components/input"
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "darkraise-ui/components/breadcrumb"
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "darkraise-ui/components/resizable"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import {
  SegmentGroup,
  SegmentGroupIndicator,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "darkraise-ui/components/tabs"
import { EmptyState } from "@/components/darkmem"
import { useMediaQuery } from "@/hooks/use-media-query"
import { WorkLogPanel } from "@/features/worklog/components/work-log-panel"
import {
  DocumentActions,
  DocumentDetail,
  type ReaderMode,
} from "@/features/documents/components/document-actions"
import {
  DeleteFolderDialog,
  DocumentBadges,
  FolderActions,
  NewDocumentDialog,
  RenameFolderDialog,
  useMoveDocuments,
} from "@/features/documents/components/document-metadata"
import { DocumentOutline } from "@/features/documents/components/document-outline"
import { DocumentReader } from "@/features/documents/components/document-reader"
import { EditableDocument } from "@/features/documents/components/editable-document"
import { GroundedAnswer } from "@/features/documents/components/grounded-answer"
import { BoardPanel } from "@/features/board/components/board-panel"
import { DocumentTree } from "@/features/documents/components/document-tree"
import {
  expansionStorageKey,
  pathsToDocument,
  rootFolderPaths,
} from "@/features/documents/tree-expansion"
import {
  buildPathMap,
  buildUriTree,
  NO_PATH,
  type UriTreeNode,
} from "@/features/documents/uri-tree"
import { noHitMentionsQuery } from "@/features/documents/lexical-miss"
import {
  useAllDocuments,
  useDocumentSearch,
  useGroundedQa,
  type DocumentListItem,
  type QaCitation,
} from "@/hooks/api"
import { plainText } from "@/lib/plain-text"
import { isMirrorOwned } from "@/lib/mirror-owned"

export const TAB_VALUES = ["artifacts", "progress"] as const
export type WorkspaceTab = (typeof TAB_VALUES)[number]

/** The mono micro-label this app uses to head a region. Inlined three times
 *  in this file before it was named. */
function RegionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="text-muted-foreground pb-1.5 font-mono text-xs tracking-wide uppercase">
      {children}
    </p>
  )
}

/** Breadcrumb showing the path to an open document. */
function DocumentCrumbs({ uri }: { uri: string | null }) {
  if (!uri) return null
  const parts = uri.split("/").filter(Boolean)
  const last = parts.length - 1
  // The separator is an `li` of its own, so it sits beside the item rather
  // than inside it, and only the open document is the current page: the
  // ancestors are folders, not pages. Under `sm` only the file name shows
  // (a wrapped path overflowed the 48px bar); the full path stays in the
  // title and in the screen-reader text.
  return (
    <Breadcrumb aria-label="document path" className="min-w-0" title={uri}>
      <BreadcrumbList className="min-w-0">
        {parts.map((part, i) =>
          i < last ? (
            <Fragment key={`${part}-${i}`}>
              <BreadcrumbItem className="max-sm:sr-only">{part}</BreadcrumbItem>
              <BreadcrumbSeparator className="max-sm:hidden" />
            </Fragment>
          ) : (
            <BreadcrumbItem key={`${part}-${i}`} className="min-w-0">
              <BreadcrumbPage className="truncate">{part}</BreadcrumbPage>
            </BreadcrumbItem>
          ),
        )}
      </BreadcrumbList>
    </Breadcrumb>
  )
}

type QueryMode = "search" | "ask"

/** The project workspace view, deliberately free of routing.
 *
 * The route file owns params and navigation and hands them in, which is the
 * split `routes/memory-graph.tsx` already uses. It is also what lets this be
 * tested without standing up a router.
 *
 * Without `tab`, only the artifacts view renders: `/documents` is a document
 * browser, and the Progress tab is about the project rather than its files.
 */
export function ProjectWorkspace({
  project,
  workstream,
  view,
  onViewChange,
  emptyAction,
  ...tabs
}: {
  project: string
  workstream?: string
  /** The board view the Progress tab shows (`?view=`). */
  view?: string
  onViewChange?: (view: string) => void
  /** Offered in the empty state when the project holds no document -- the
   *  `/documents` route's way back to its project chooser. */
  emptyAction?: ReactNode
} & (
  | { tab: WorkspaceTab; onTabChange: (tab: WorkspaceTab) => void }
  | { tab?: undefined; onTabChange?: undefined }
)) {
  const documents = useAllDocuments(project)
  const items = documents.data?.items ?? []
  const truncated = documents.data?.truncated ?? false
  // The id, never the row. A stored `DocumentListItem` is a snapshot: after
  // a rename, move or delete it describes a document that no longer exists
  // in that shape, and the breadcrumbs, the reveal effect and the reader all
  // read it. Deriving from `items` makes the selection track the list.
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = useMemo(
    () => items.find((d) => d.id === selectedId) ?? null,
    [items, selectedId],
  )
  /** The block a search hit named. Selecting only the document drops the
   *  reader at the top, losing the section the user actually matched. */
  const [focusBlockId, setFocusBlockId] = useState<string | null>(null)
  /** The heading the reader is currently under, reported by the body as it
   *  scrolls. Separate from `focusBlockId`, which is where the reader was
   *  SENT: one is a standing position, the other a one-off jump, and folding
   *  them together would make the outline marker jump back to the last click
   *  every time the document re-rendered. */
  const [activeHeadingId, setActiveHeadingId] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const [queryMode, setQueryMode] = useState<QueryMode>("search")
  // Reading is the default for every selection: the block editor commits on
  // blur, so landing in it makes a stray keystroke a real edit.
  const [mode, setMode] = useState<ReaderMode>("read")
  const search = useDocumentSearch()
  const qa = useGroundedQa()
  /** The workstream and task "Show in Work log" asked for; `n` remounts the
   *  panel when the same task is asked for twice. */
  const [logFocus, setLogFocus] = useState<{
    key: string
    task: number
    n: number
  } | null>(null)
  const workLogRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (logFocus) workLogRef.current?.scrollIntoView?.({ behavior: "smooth" })
  }, [logFocus])
  // Below `lg` the split stacks: side by side at 26% a phone left the tree
  // ~90px wide, too narrow to show a single file name. Reads `false` in
  // tests, so the stacked branch is the fallback.
  const wide = useMediaQuery("(min-width: 1024px)")

  const roots = useMemo(() => buildUriTree(items), [items])
  const byPath = useMemo(() => buildPathMap(roots), [roots])

  // Document management (create, folder rename and delete, drag-to-move).
  // `newDocumentAt` is the path the create dialog opens on: null is closed.
  const [newDocumentAt, setNewDocumentAt] = useState<string | null>(null)
  const [renaming, setRenaming] = useState<UriTreeNode | null>(null)
  const [deleting, setDeleting] = useState<UriTreeNode | null>(null)
  const moveDocuments = useMoveDocuments(project, items, (path) =>
    byPath.get(path),
  )
  // Ref-stable for the memoised tree, as `handleExpandedChange` is.
  const moveRef = useRef(moveDocuments)
  moveRef.current = moveDocuments
  const handleMove = useCallback(
    (target: Parameters<typeof moveDocuments>[0]) => moveRef.current(target),
    [],
  )
  const folderActions = useCallback(
    (node: UriTreeNode) =>
      node.children.length > 0 && node.path !== NO_PATH ? (
        <FolderActions
          node={node}
          onNewHere={(folder) => setNewDocumentAt(`${folder}/`)}
          onRename={setRenaming}
          onDelete={setDeleting}
        />
      ) : null,
    [],
  )
  // Lazy initialiser rather than an effect: the route mounts a fresh
  // ProjectWorkspace instance per project (`key={project}`), so this only
  // ever needs to run once, at mount, with no post-commit correction window
  // where a stale project's `expanded` could render against a new tree. A
  // read that throws (private mode, blocked storage) falls back to the
  // derived default rather than failing the pane.
  const [expanded, setExpanded] = useState<string[] | null>(() => {
    try {
      const raw = window.localStorage.getItem(expansionStorageKey(project))
      const parsed: unknown = raw ? JSON.parse(raw) : null
      return Array.isArray(parsed) ? (parsed as string[]) : null
    } catch {
      return null
    }
  })

  // Whatever the user has stored (their own toggles), or the top-level
  // default when nothing is stored yet. The reveal is NOT folded in here:
  // deriving it per render made it win over the user every frame, so
  // collapsing a folder on the open document's own path sprang straight
  // back open. It is applied once per selection change instead, below.
  const effectiveExpanded = useMemo(
    () => expanded ?? rootFolderPaths(roots),
    [expanded, roots],
  )

  // `useCallback`, not a plain declaration: this is a prop of the memoised
  // `DocumentTree`, whose comparison is shallow over EVERY prop, so one fresh
  // function here re-rendered the whole tree once per heading the reader
  // scrolls past -- on both surfaces, the corpus browser included.
  const handleExpandedChange = useCallback(
    (paths: string[]) => {
      setExpanded(paths)
      try {
        window.localStorage.setItem(
          expansionStorageKey(project),
          JSON.stringify(paths),
        )
      } catch {
        // Persistence is a convenience; losing it must not break the tree.
      }
    },
    [project],
  )

  // A selection UNIONS its ancestor path into the expanded set -- once, when
  // the selection changes. Unioning rather than replacing is what keeps a
  // sibling folder open; doing it on a change rather than on every render is
  // what lets the user collapse a folder the open document lives in.
  //
  // Keyed on the pair `(id, uri)` rather than on `selected`'s identity, and
  // re-attempted while the path is empty: a search hit can select a document
  // before its tree row exists, and the reveal has to land when `roots`
  // catches up. The uri is half the key because the id alone is a second
  // snapshot -- after a move that changed the document's folder, an id-keyed
  // guard returned early and the new folder stayed collapsed.
  const revealedFor = useRef<string | null>(null)
  useEffect(() => {
    const key = selected ? `${selected.id}\u0000${selected.uri ?? ""}` : null
    if (!selected || revealedFor.current === key) return
    const toReveal = pathsToDocument(roots, selected.id)
    if (toReveal.length === 0) return
    revealedFor.current = key
    const base = expanded ?? rootFolderPaths(roots)
    const next = Array.from(new Set([...base, ...toReveal]))
    if (next.length !== base.length) handleExpandedChange(next)
  }, [selected, roots, expanded])

  const handleActiveHeading = useCallback((blockId: string | null) => {
    setActiveHeadingId(blockId)
  }, [])

  // Stable, so the memoised tree is not re-rendered by a heading crossing.
  const handleSelectDocument = useCallback((doc: DocumentListItem) => {
    setSelectedId(doc.id)
    setFocusBlockId(null)
    setMode("read")
  }, [])

  const openCitation = useCallback((citation: QaCitation) => {
    setSelectedId(citation.document_id)
    setFocusBlockId(citation.block_id)
    setMode("read")
  }, [])

  const switchTab = tabs.onTabChange
  const documentsLoading = documents.isLoading
  // A workstream names its plan, spec and handoff by uri; the workspace owns
  // the selection, so opening one is a selection plus a tab switch.
  const openDocumentByUri = useCallback(
    (uri: string) => {
      const doc = items.find((d) => d.uri === uri)
      if (!doc) {
        // isLoading, not isPending: demo mode disables the read, which leaves
        // it pending forever with nothing filed.
        toast.error(
          documentsLoading
            ? "The document list is still loading; try again in a moment"
            : `${uri} is not filed in this project`,
        )
        return
      }
      setSelectedId(doc.id)
      setFocusBlockId(null)
      setMode("read")
      switchTab?.("artifacts")
    },
    [items, documentsLoading, switchTab],
  )

  const hits = search.data?.items ?? []
  // Judged against the query that was SENT, not the box: the box may have
  // been edited since, and the notice describes the hits on screen.
  const meaningOnly = noHitMentionsQuery(search.variables?.query ?? "", hits)
  const clearQuery = () => {
    setQuery("")
    search.reset()
    qa.reset()
  }
  const noDocuments =
    !documents.isLoading && !documents.isError && items.length === 0
  const asking = queryMode === "ask"

  const artifacts = (
    <>
      <form
        className="border-border bg-muted/20 flex flex-wrap items-center gap-2 rounded-md border p-2"
        onSubmit={(e) => {
          e.preventDefault()
          const text = query.trim()
          // Searching for nothing clears what the last search left open.
          if (!text) {
            search.reset()
            qa.reset()
            return
          }
          if (asking) {
            qa.mutate({
              question: text,
              project,
              document_id: selected?.id ?? null,
            })
          } else {
            search.mutate({ query, project, limit: 20 })
          }
        }}
      >
        <SegmentGroup
          value={queryMode}
          onValueChange={(next) => {
            if (next) setQueryMode(next as QueryMode)
          }}
          variant="default"
          aria-label="query mode"
        >
          <SegmentGroupIndicator />
          <SegmentGroupItem value="search">Search</SegmentGroupItem>
          <SegmentGroupItem value="ask">Ask</SegmentGroupItem>
        </SegmentGroup>
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") clearQuery()
          }}
          placeholder={
            asking
              ? "Ask a question answered from these documents…"
              : "Search this project's documents by meaning…"
          }
          aria-label={asking ? "Question" : "search documents"}
          className="min-w-52 flex-1"
        />
        {asking ? (
          <Button
            type="submit"
            variant="outline"
            disabled={!query.trim() || qa.isPending}
          >
            <Sparkles className="mr-1.5 size-3.5" />
            {qa.isPending ? "asking…" : "ask"}
          </Button>
        ) : (
          <Button type="submit" variant="outline" disabled={search.isPending}>
            <Search className="mr-1.5 size-3.5" />
            {search.isPending ? "searching…" : "search"}
          </Button>
        )}
        {asking ? (
          // The door scopes to one document when it is given one, so the
          // same question can answer differently depending on what is open.
          <p className="text-muted-foreground w-full px-1 text-xs">
            {selected
              ? `Answering from ${selected.uri ?? selected.title ?? "the open document"} only.`
              : `Answering from every document in ${project}.`}
          </p>
        ) : null}
      </form>

      {asking && qa.isError ? (
        <p className="text-destructive text-sm">
          The question could not be answered — {qa.error.message}
        </p>
      ) : null}

      {asking && qa.data ? (
        <GroundedAnswer
          answer={qa.data}
          documents={items}
          onOpenCitation={openCitation}
        />
      ) : null}

      {!asking && search.isError ? (
        <p className="text-destructive text-sm">
          Search failed — {search.error.message}
        </p>
      ) : null}

      {!asking && search.isSuccess && hits.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No sections matched. Try rephrasing.
        </p>
      ) : null}

      {!asking && hits.length > 0 ? (
        // Capped, so twenty hits cannot push the tree and the reader below
        // the fold, which made a clicked hit look like it did nothing.
        <div className="border-border max-h-72 space-y-1.5 overflow-y-auto rounded-md border border-dashed p-3">
          <div className="flex items-center justify-between gap-2">
            <RegionLabel>sections</RegionLabel>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={clearQuery}
            >
              Clear
            </Button>
          </div>
          {meaningOnly ? (
            // The search has no similarity floor, so it always answers with
            // its nearest sections; this is the only place a reader learns
            // that none of them is a word-for-word match.
            <p
              role="status"
              className="text-muted-foreground flex items-start gap-1.5 px-1.5 pb-1 text-sm"
            >
              <Info aria-hidden className="mt-0.5 size-3.5 shrink-0" />
              No section mentions these words; these are the closest by meaning.
            </p>
          ) : null}
          {hits.map((hit) => (
            <button
              key={hit.block_id}
              type="button"
              className="hover:bg-muted/40 focus-visible:ring-primary/40 block w-full cursor-pointer rounded p-1.5 text-left text-sm transition-colors focus-visible:ring-2 focus-visible:outline-none"
              onClick={() => {
                const doc = items.find((d) => d.id === hit.document_id)
                if (doc) {
                  setSelectedId(doc.id)
                  setFocusBlockId(hit.block_id)
                }
              }}
            >
              <span className="text-muted-foreground font-mono text-xs">
                {hit.heading_path.join(" › ")}
                {hit.path_truncated ? " › …" : ""}
              </span>
              <span className="block truncate">{plainText(hit.text)}</span>
            </button>
          ))}
        </div>
      ) : null}

      {noDocuments ? (
        // One page-scope state, not two panes: beside an empty tree the
        // reader's "pick a document from the tree" is an instruction nobody
        // can follow.
        <EmptyState
          kind="empty"
          scope="page"
          icon={FolderTree}
          title={`No documents filed in ${project}`}
          description="A document appears here once it is filed, over REST or the MCP document_put tool, or created here."
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <Button variant="outline" onClick={() => setNewDocumentAt("")}>
                <FilePlus className="mr-1.5 size-3.5" />
                New document
              </Button>
              {emptyAction}
            </div>
          }
        />
      ) : (
        <ResizablePanelGroup
          // Remounted on a breakpoint crossing: the panel sizes are seeded
          // once, and a horizontal 26% is not a sensible vertical one.
          key={wide ? "split" : "stack"}
          orientation={wide ? "horizontal" : "vertical"}
          // The floor for a broken or absent height chain (small screens,
          // where the ancestors above deliberately carry no height): without
          // it the panes collapse to zero. Stacked, the group also takes a
          // definite 85svh so the panels' percentage heights resolve and both
          // panes stay usable; `!` because the library's own `h-full` otherwise
          // wins and leaves the height at the floor. Once the chain above is
          // real (at `lg`), the library's own `h-full` fills the real flexed
          // height instead, so the floor stands down rather than driving the
          // layout.
          className="min-h-[60vh] max-lg:h-[85svh]! lg:min-h-0 lg:flex-1"
        >
          <ResizablePanel
            defaultSize={wide ? 26 : 35}
            minSize={15}
            maxSize={wide ? 45 : 70}
            id="tree"
          >
            {/* Same gutter as the reader's, and for the same reason: the
                bar is 10px and an 8px pad left it 2px over the rows -- which
                a full-width selected fill makes visible. */}
            <ScrollArea className="h-full pr-3 max-lg:pb-2">
              <div className="flex items-center justify-between gap-2">
                <RegionLabel>documents</RegionLabel>
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  // Opens on the open document's folder: the likeliest place
                  // for a sibling.
                  onClick={() => {
                    const uri = selected?.uri ?? ""
                    const slash = uri.lastIndexOf("/")
                    setNewDocumentAt(slash > 0 ? uri.slice(0, slash + 1) : "")
                  }}
                >
                  <FilePlus className="mr-1 size-3.5" />
                  New document
                </Button>
              </div>
              {documents.isError ? (
                <p className="text-destructive text-sm">
                  This project's documents could not be loaded.
                </p>
              ) : documents.isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-2/3" />
                  <Skeleton className="h-4 w-1/2" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              ) : (
                <DocumentTree
                  items={items}
                  selectedId={selected?.id ?? null}
                  onSelect={handleSelectDocument}
                  truncated={truncated}
                  expanded={effectiveExpanded}
                  onExpandedChange={handleExpandedChange}
                  nodeActions={folderActions}
                  onMove={handleMove}
                />
              )}
            </ScrollArea>
          </ResizablePanel>
          <ResizableHandle withHandle />
          <ResizablePanel defaultSize={wide ? 74 : 65} id="reader">
            {/* `pr-3` is the scrollbar's gutter, not decoration. The bar is
                `absolute right-0 w-2.5` on the ScrollArea ROOT while the
                viewport is inset by this padding, so the padding is what
                moves the bar off the content instead of over it. Without it
                the document's scrollbar sat on top of the outline rail. */}
            <ScrollArea className="h-full pr-3 pl-2 max-lg:pt-2 max-lg:pl-0">
              {selected ? (
                <div>
                  {/* The path and the toolbar ride the scroll: a long
                      document otherwise scrolls its own identity and every
                      action off the top, and the reader has to come back up
                      to answer "which file is this" or to press Edit.
                      `sticky` resolves against the ScrollArea's own viewport,
                      which is the element that scrolls here. */}
                  <div className="bg-background border-border/60 sticky top-0 z-20 mb-3.5 flex min-h-12 items-center gap-2 border-b py-1">
                    <DocumentCrumbs uri={selected.uri ?? null} />
                    <DocumentBadges document={selected} />
                    <div className="flex-1" />
                    <DocumentActions
                      document={selected}
                      mode={mode}
                      onModeChange={setMode}
                      onDeleted={() => {
                        setSelectedId(null)
                        setFocusBlockId(null)
                        setMode("read")
                      }}
                    />
                  </div>

                  <div className="flex gap-5">
                    <div className="min-w-0 flex-1">
                      <Card className="p-4">
                        {mode === "read" || isMirrorOwned(selected.uri) ? (
                          <DocumentReader
                            documentId={selected.id}
                            focusBlockId={focusBlockId}
                            onActiveHeadingChange={handleActiveHeading}
                            // The outline is mounted beside the reader, in
                            // the sticky rail below, so the reader's own rail
                            // would be a second jump list for one document.
                            showOutline={false}
                          />
                        ) : (
                          <EditableDocument documentId={selected.id} />
                        )}
                      </Card>
                    </div>

                    {/* `self-start` is what makes this sticky at all: a
                        stretched flex item is already as tall as the row, so
                        it has nothing to stick within. `top-12` clears the
                        header bar above rather than sliding under it. */}
                    <aside className="sticky top-12 hidden max-h-[calc(100vh-16rem)] w-56 shrink-0 flex-col self-start pt-1 xl:flex">
                      <DocumentOutline
                        documentId={selected.id}
                        activeBlockId={activeHeadingId}
                        onNavigate={setFocusBlockId}
                      />
                    </aside>
                  </div>

                  {/* Below the split, not inside the body column: these three
                      cards want the reader pane's full width, and the outline
                      rail's stick range ends where the document does. */}
                  <DocumentDetail
                    documentId={selected.id}
                    hasSummary={selected.has_summary}
                    onOpenDocument={(documentId, blockId) => {
                      const doc = items.find((d) => d.id === documentId)
                      if (!doc) return
                      setSelectedId(doc.id)
                      setFocusBlockId(blockId)
                      setMode("read")
                    }}
                  />
                </div>
              ) : (
                <EmptyState
                  kind="empty"
                  icon={FolderTree}
                  title="Nothing selected"
                  description="Pick a document from the tree to read it."
                />
              )}
            </ScrollArea>
          </ResizablePanel>
        </ResizablePanelGroup>
      )}

      <NewDocumentDialog
        project={project}
        items={items}
        open={newDocumentAt !== null}
        initialUri={newDocumentAt ?? ""}
        onOpenChange={(open) => {
          if (!open) setNewDocumentAt(null)
        }}
        onCreated={(documentId) => {
          setSelectedId(documentId)
          setFocusBlockId(null)
          setMode("read")
        }}
      />
      <RenameFolderDialog
        project={project}
        items={items}
        node={renaming}
        onClose={() => setRenaming(null)}
      />
      <DeleteFolderDialog
        project={project}
        items={items}
        node={deleting}
        onClose={() => setDeleting(null)}
      />
    </>
  )

  if (tabs.tab === undefined) {
    return (
      <div className="flex flex-col space-y-3.5 lg:min-h-0 lg:flex-1">
        {artifacts}
      </div>
    )
  }

  const { tab, onTabChange } = tabs
  return (
    <Tabs
      value={tab}
      onValueChange={(value) => onTabChange(value as WorkspaceTab)}
      // Carries the route root's `lg:h-full` down to the resizable group
      // below: `flex flex-col` is structural at every width, `lg:flex-1
      // lg:min-h-0` is what actually claims the height, matching the
      // `lg:`-only prefixing chat.tsx's height chain uses.
      className="flex flex-col lg:min-h-0 lg:flex-1"
    >
      {/* `w-fit self-start`: as a child of the flex-column Tabs root the
          list is stretched to the full content width, with the library's
          centred triggers floating in the middle of an empty strip. */}
      <TabsList className="w-fit self-start">
        <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
        <TabsTrigger value="progress">Progress</TabsTrigger>
      </TabsList>

      <TabsContent
        value="artifacts"
        className="flex flex-col space-y-3.5 lg:min-h-0 lg:flex-1"
      >
        {artifacts}
      </TabsContent>

      <TabsContent value="progress" className="space-y-5">
        <div>
          <RegionLabel>project board</RegionLabel>
          {/* A projection of registers, plans and ledger entries, never a
              second store: every card is derived on read, and the only write
              is a register row edit filed as a document revision. */}
          <BoardPanel
            project={project}
            viewId={view}
            onViewChange={(next) => onViewChange?.(next)}
            onOpenDocument={openDocumentByUri}
            onShowInWorkLog={(key, task) =>
              setLogFocus((prev) => ({ key, task, n: (prev?.n ?? 0) + 1 }))
            }
          />
        </div>
        <div ref={workLogRef}>
          <RegionLabel>work log</RegionLabel>
          <WorkLogPanel
            // Keyed on the requested workstream: the panel seeds its selection
            // from it once, so a link to another workstream must remount it.
            key={
              logFocus
                ? `${logFocus.key}:${logFocus.task}:${logFocus.n}`
                : (workstream ?? "")
            }
            project={project}
            initialWorkstream={logFocus?.key ?? workstream}
            initialTask={logFocus?.task}
            onOpenDocument={openDocumentByUri}
          />
        </div>
      </TabsContent>
    </Tabs>
  )
}
