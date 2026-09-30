import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"
import { FolderTree, Search, Sparkles } from "lucide-react"
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
import { WorkLogPanel } from "@/features/worklog/components/work-log-panel"
import {
  DocumentActions,
  DocumentDetail,
  type ReaderMode,
} from "@/features/documents/components/document-actions"
import { DocumentOutline } from "@/features/documents/components/document-outline"
import { DocumentReader } from "@/features/documents/components/document-reader"
import { EditableDocument } from "@/features/documents/components/editable-document"
import { GroundedAnswer } from "@/features/documents/components/grounded-answer"
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
  useGroundedQa,
  type DocumentListItem,
  type QaCitation,
} from "@/hooks/api"

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
  ...tabs
}: {
  project: string
  workstream?: string
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
  const corpus = useProgressCorpus(items)

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
  const asking = queryMode === "ask"

  const artifacts = (
    <>
      <form
        className="border-border bg-muted/20 flex flex-wrap items-center gap-2 rounded-md border p-2"
        onSubmit={(e) => {
          e.preventDefault()
          const text = query.trim()
          if (!text) return
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
          Search failed.
        </p>
      ) : null}

      {!asking && search.isSuccess && hits.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No sections matched. Try rephrasing.
        </p>
      ) : null}

      {!asking && hits.length > 0 ? (
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
          <ScrollArea className="h-full pr-3 pl-2">
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
                description="Pick a document from the tree to read it."
              />
            )}
          </ScrollArea>
        </ResizablePanel>
      </ResizablePanelGroup>
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
      <TabsList>
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
              title="No progress ledger"
            />
          )}
        </div>
        <div>
          <RegionLabel>work log</RegionLabel>
          <WorkLogPanel
            // Keyed on the requested workstream: the panel seeds its selection
            // from it once, so a link to another workstream must remount it.
            key={workstream ?? ""}
            project={project}
            initialWorkstream={workstream}
            onOpenDocument={openDocumentByUri}
          />
        </div>
      </TabsContent>
    </Tabs>
  )
}
