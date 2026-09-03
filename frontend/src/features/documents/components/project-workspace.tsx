import { useEffect, useMemo, useState, type ReactNode } from "react"
import { FolderTree, Search } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Card } from "darkraise-ui/components/card"
import { Input } from "darkraise-ui/components/input"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "darkraise-ui/components/tabs"
import { EmptyState } from "@/components/darkmem"
import { CheckpointsTab } from "@/features/activity/components/checkpoints-tab"
import { DocumentReader } from "@/features/documents/components/document-reader"
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
}: {
  project: string
  tab: WorkspaceTab
  onTabChange: (tab: WorkspaceTab) => void
}) {
  const documents = useAllDocuments(project)
  const items = documents.data?.items ?? []
  const [selected, setSelected] = useState<DocumentListItem | null>(null)
  /** The block a search hit named. Selecting only the document drops the
   *  reader at the top, losing the section the user actually matched. */
  const [focusBlockId, setFocusBlockId] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const search = useDocumentSearch()

  const roots = useMemo(() => buildUriTree(items), [items])
  const [expanded, setExpanded] = useState<string[] | null>(null)

  // Read once per project. A read that throws (private mode, blocked storage)
  // falls back to the derived default rather than failing the pane.
  useEffect(() => {
    let stored: string[] | null = null
    try {
      const raw = window.localStorage.getItem(expansionStorageKey(project))
      if (raw) stored = JSON.parse(raw) as string[]
    } catch {
      stored = null
    }
    setExpanded(stored ?? null)
  }, [project])

  const effectiveExpanded =
    expanded ??
    (selected ? pathsToDocument(roots, selected.id) : rootFolderPaths(roots))

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

  const ledger = items.find((d) => d.uri?.endsWith(LEDGER_SUFFIX)) ?? null
  const hits = search.data?.items ?? []

  return (
    <Tabs value={tab} onValueChange={(value) => onTabChange(value as WorkspaceTab)}>
      <TabsList>
        <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
        <TabsTrigger value="progress">Progress</TabsTrigger>
      </TabsList>

      <TabsContent value="artifacts" className="space-y-3.5">
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
                className="hover:bg-muted/40 focus-visible:ring-primary/40 block w-full rounded p-1.5 text-left text-sm transition-colors focus-visible:ring-2 focus-visible:outline-none"
                onClick={() => {
                  const doc = items.find((d) => d.id === hit.document_id)
                  if (doc) {
                    setSelected(doc)
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

        <div className="flex flex-col gap-5 lg:flex-row">
          <div className="w-full shrink-0 lg:w-72">
            <RegionLabel>documents</RegionLabel>
            {documents.isError ? (
              <p className="text-destructive text-sm">
                This project's documents could not be loaded — a failed read,
                not an empty project.
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
                onSelect={(doc) => {
                  setSelected(doc)
                  setFocusBlockId(null)
                }}
                truncated={documents.data?.truncated ?? false}
                expanded={effectiveExpanded}
                onExpandedChange={handleExpandedChange}
              />
            )}
          </div>
          <div className="min-w-0 flex-1">
            {selected ? (
              <Card className="p-4">
                <DocumentReader documentId={selected.id} focusBlockId={focusBlockId} />
              </Card>
            ) : (
              <EmptyState
                kind="empty"
                icon={FolderTree}
                title="Nothing selected"
                description="Pick a document from the tree to read it."
              />
            )}
          </div>
        </div>
      </TabsContent>

      <TabsContent value="progress" className="space-y-5">
        <div>
          <RegionLabel>project ledger</RegionLabel>
          {ledger ? (
            <Card className="p-4">
              <DocumentReader documentId={ledger.id} />
            </Card>
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
    </Tabs>
  )
}
