import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"
import { FolderTree, Search } from "lucide-react"
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
import { Skeleton } from "darkraise-ui/components/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "darkraise-ui/components/tabs"
import { EmptyState } from "@/components/darkmem"
import { CheckpointsTab } from "@/features/activity/components/checkpoints-tab"
import {
  DocumentActions,
  DocumentDetail,
  type ReaderMode,
} from "@/features/documents/components/document-actions"
import { DocumentOutline } from "@/features/documents/components/document-outline"
import { DocumentReader } from "@/features/documents/components/document-reader"
import { EditableDocument } from "@/features/documents/components/editable-document"
import { ProgressBoard } from "@/features/progress/components/progress-board"
import { useProgressCorpus } from "@/features/progress/use-progress-corpus"
import { DocumentTree } from "@/features/documents/components/document-tree"
import {
  expansionStorageKey,
  pathsToDocument,
  rootFolderPaths,
} from "@/features/documents/tree-expansion"
import { buildUriTree } from "@/features/documents/uri-tree"
import {
  useAllDocuments,
  useDocumentSearch,
  type DocumentListItem,
} from "@/hooks/api"

/** Hoisted rather than a `[]` literal per render: a fresh array defeats the
 *  `useMemo`s inside `useProgressCorpus`. */
const NO_DOCUMENTS: DocumentListItem[] = []

export const TAB_VALUES = ["artifacts", "progress"] as const
export type WorkspaceTab = (typeof TAB_VALUES)[number]

/** The ledger's path convention. A SUFFIX match, not equality: the corpus
 *  import files repo-relative paths, so this project's own ledger lands at
 *  `docs/planning/progress.md` while the convention names
 *  `planning/progress.md`. The suffix resolves both spellings. */
const LEDGER_SUFFIX = "planning/progress.md"

/** The mono micro-label this app uses to head a region. Inlined three times
 *  in this file before it was named. */
function RegionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="text-muted-foreground pb-1.5 font-mono text-[10px] tracking-wide uppercase">
      {children}
    </p>
  )
}

/** Breadcrumb showing the path to an open document. */
function DocumentCrumbs({ uri }: { uri: string | null }) {
  if (!uri) return null
  const parts = uri.split("/").filter(Boolean)
  return (
    <Breadcrumb aria-label="document path" className="min-w-0">
      <BreadcrumbList>
        {parts.map((part, i) => (
          <BreadcrumbItem key={`${part}-${i}`}>
            <BreadcrumbPage>{part}</BreadcrumbPage>
            {i < parts.length - 1 ? <BreadcrumbSeparator /> : null}
          </BreadcrumbItem>
        ))}
      </BreadcrumbList>
    </Breadcrumb>
  )
}

/** The project workspace view, deliberately free of routing.
 *
 * The route file owns params and navigation and hands them in, which is the
 * split `routes/memory-graph.tsx` already uses. It is also what lets this be
 * tested without standing up a router.
 */
export function ProjectWorkspace({
  project,
  tab,
  onTabChange,
  treeManagement = false,
  treeEmptyAction,
}: {
  project: string
  tab: WorkspaceTab
  onTabChange: (tab: WorkspaceTab) => void
  /** Tree management: create, rename, move, pin, delete. Off is the corpus
   *  browser at `/projects/$project`, which is unchanged. Named for what it
   *  gates rather than `editable`, because that surface is already editable
   *  -- it has the block editor and a delete. */
  treeManagement?: boolean
  /** The affordance an empty tree offers. Threaded rather than rendered
   *  here: this component owns no create verb. */
  treeEmptyAction?: ReactNode
}) {
  const documents = useAllDocuments(project)
  const items = documents.data?.items ?? []
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
  // Reading is the default for every selection: the block editor commits on
  // blur, so landing in it makes a stray keystroke a real edit.
  const [mode, setMode] = useState<ReaderMode>("read")
  const search = useDocumentSearch()
  // Fed an empty list under tree management, which is what makes the hook
  // inert: its content read is `enabled` on a non-empty id list, so the
  // ledger scan the Progress tab needs costs nothing where there is no tab.
  const corpus = useProgressCorpus(treeManagement ? NO_DOCUMENTS : items)

  const roots = useMemo(() => buildUriTree(items), [items])
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

  const handleExpandedChange = (paths: string[]) => {
    setExpanded(paths)
    try {
      window.localStorage.setItem(
        expansionStorageKey(project),
        JSON.stringify(paths),
      )
    } catch {
      // Persistence is a convenience; losing it must not break the tree.
    }
  }

  // A selection UNIONS its ancestor path into the expanded set -- once, when
  // the selection changes. Unioning rather than replacing is what keeps a
  // sibling folder open; doing it on a change rather than on every render is
  // what lets the user collapse a folder the open document lives in.
  //
  // Keyed on the document id, not on `selected`'s identity, and re-attempted
  // while the path is empty: a search hit can select a document before its
  // tree row exists, and the reveal has to land when `roots` catches up.
  const revealedFor = useRef<string | null>(null)
  useEffect(() => {
    if (!selected || revealedFor.current === selected.id) return
    const toReveal = pathsToDocument(roots, selected.id)
    if (toReveal.length === 0) return
    revealedFor.current = selected.id
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

  const hits = search.data?.items ?? []

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
      {/* A progress ledger is a project artifact recorded by sessions. The
          personal space has neither, so the tab would be permanently empty
          -- and with one tab left the strip is not a choice. */}
      {treeManagement ? null : (
        <TabsList>
          <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
          <TabsTrigger value="progress">Progress</TabsTrigger>
        </TabsList>
      )}

      <TabsContent
        value="artifacts"
        className="flex flex-col space-y-3.5 lg:min-h-0 lg:flex-1"
      >
        <form
          className="border-border bg-muted/20 flex gap-2 rounded-md border p-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (query.trim()) search.mutate({ query, project, limit: 20 })
          }}
        >
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search this project's documents by meaning…"
            aria-label="search documents"
          />
          <Button type="submit" variant="outline" disabled={search.isPending}>
            <Search className="mr-1.5 size-3.5" />
            {search.isPending ? "searching…" : "search"}
          </Button>
        </form>

        {search.isError ? (
          <p className="text-destructive text-sm">
            Search failed — a failed search, not an empty result.
          </p>
        ) : null}

        {search.isSuccess && hits.length === 0 ? (
          <p className="text-muted-foreground text-sm">
            No sections matched. The search reads meaning, not exact words, so a
            rephrasing may still find it.
          </p>
        ) : null}

        {hits.length > 0 ? (
          <div className="border-border space-y-1.5 rounded-md border border-dashed p-3">
            <RegionLabel>sections</RegionLabel>
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
                <span className="block truncate">{hit.text}</span>
              </button>
            ))}
          </div>
        ) : null}

        <ResizablePanelGroup
          orientation="horizontal"
          // The floor for a broken or absent height chain (small screens,
          // where the ancestors above deliberately carry no height): without
          // it the panes collapse to zero. Once the chain above is real (at
          // `lg`), the library's own `h-full` fills the real flexed height
          // instead, so the floor stands down rather than driving the layout.
          className="min-h-[60vh] lg:min-h-0 lg:flex-1"
        >
          <ResizablePanel defaultSize={26} minSize={15} maxSize={45} id="tree">
            {/* Same gutter as the reader's, and for the same reason: the
                bar is 10px and an 8px pad left it 2px over the rows -- which
                a full-width selected fill makes visible. */}
            <ScrollArea className="h-full pr-3">
              <RegionLabel>documents</RegionLabel>
              {documents.isError ? (
                <p className="text-destructive text-sm">
                  This project's documents could not be loaded — a failed
                  read, not an empty project.
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
                  truncated={documents.data?.truncated ?? false}
                  expanded={effectiveExpanded}
                  onExpandedChange={handleExpandedChange}
                  emptyAction={treeManagement ? treeEmptyAction : undefined}
                />
              )}
            </ScrollArea>
          </ResizablePanel>
          <ResizableHandle withHandle />
          <ResizablePanel defaultSize={74} id="reader">
            {/* `pr-3` is the scrollbar's gutter, not decoration. The bar is
                `absolute right-0 w-2.5` on the ScrollArea ROOT while the
                viewport is inset by this padding, so the padding is what
                moves the bar off the content instead of over it. Without it
                the document's scrollbar sat on top of the outline rail. */}
            <ScrollArea className="h-full pl-2 pr-3">
              {selected ? (
                <div>
                  {/* The path and the toolbar ride the scroll: a long
                      document otherwise scrolls its own identity and every
                      action off the top, and the reader has to come back up
                      to answer "which file is this" or to press Edit.
                      `sticky` resolves against the ScrollArea's own viewport,
                      which is the element that scrolls here. */}
                  <div className="bg-background border-border/60 sticky top-0 z-20 mb-3.5 flex h-12 items-center gap-2 border-b">
                    <DocumentCrumbs uri={selected.uri ?? null} />
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
                        {mode === "read" ? (
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
                  description={
                    treeManagement
                      ? "Pick a note from the tree to read it."
                      : "Pick a document from the tree to read it."
                  }
                />
              )}
            </ScrollArea>
          </ResizablePanel>
        </ResizablePanelGroup>
      </TabsContent>

      {treeManagement ? null : (
        <TabsContent value="progress" className="space-y-5">
          <div>
            <RegionLabel>project board</RegionLabel>
            {/* A projection of the ledger and the epic files, never a second
                store: the board writes nothing, so `progress.md` stays the one
                place task state lives. That is what keeps it cheap, and it is
                also why the board fills only for a project whose corpus holds
                those files. */}
            {corpus.present ? (
              <ProgressBoard corpus={corpus} />
            ) : (
              <EmptyState
                kind="empty"
                icon={FolderTree}
                title="No ledger pinned"
                description={`File a document whose path ends in ${LEDGER_SUFFIX} to pin this project's ledger here.`}
              />
            )}
          </div>
          <CheckpointsTab project={project} />
        </TabsContent>
      )}
    </Tabs>
  )
}
