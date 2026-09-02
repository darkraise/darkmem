import { useState } from "react"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { FolderTree, Search } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "darkraise-ui/components/tabs"
import { PageChrome } from "@/components/app-chrome"
import { EmptyState } from "@/components/darkmem"
import { CheckpointsTab } from "@/features/activity/components/checkpoints-tab"
import { DocumentReader } from "@/features/documents/components/document-reader"
import { DocumentTree } from "@/features/documents/components/document-tree"
import {
  useAllDocuments,
  useDocumentSearch,
  type DocumentListItem,
} from "@/hooks/api"

const TAB_VALUES = ["artifacts", "progress"] as const
type WorkspaceTab = (typeof TAB_VALUES)[number]

export const Route = createFileRoute("/_authenticated/projects_/$project")({
  validateSearch: (search: Record<string, unknown>) => ({
    tab: TAB_VALUES.includes(search.tab as WorkspaceTab)
      ? (search.tab as WorkspaceTab)
      : undefined,
  }),
  component: ProjectWorkspacePage,
})

/** The ledger's path convention. A SUFFIX match, not equality: the corpus
 *  import files repo-relative paths, so this project's own ledger lands at
 *  `docs/planning/progress.md` while the convention names
 *  `planning/progress.md`. The suffix resolves both spellings. */
const LEDGER_SUFFIX = "planning/progress.md"

function ProjectWorkspacePage() {
  const { project } = Route.useParams()
  const { tab } = Route.useSearch()
  const navigate = useNavigate()
  const active: WorkspaceTab = tab ?? "artifacts"

  const documents = useAllDocuments(project)
  const items = documents.data?.items ?? []
  const [selected, setSelected] = useState<DocumentListItem | null>(null)
  const [query, setQuery] = useState("")
  const search = useDocumentSearch()

  const ledger = items.find((d) => d.uri?.endsWith(LEDGER_SUFFIX)) ?? null

  return (
    <div className="space-y-4">
      <PageChrome
        icon={FolderTree}
        title={project}
        description="Everything this project holds: its filed artifacts, and the progress its sessions recorded."
      />

      <Tabs
        value={active}
        onValueChange={(value) =>
          navigate({ to: ".", search: { tab: value as WorkspaceTab } })
        }
      >
        <TabsList>
          <TabsTrigger value="artifacts">Artifacts</TabsTrigger>
          <TabsTrigger value="progress">Progress</TabsTrigger>
        </TabsList>

        <TabsContent value="artifacts" className="space-y-3.5">
          <form
            className="flex gap-2"
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
            <Button type="submit" variant="outline">
              <Search className="mr-1.5 size-3.5" />
              search
            </Button>
          </form>

          {search.data && search.data.items.length > 0 ? (
            <div className="border-border space-y-1.5 rounded-md border border-dashed p-3">
              <p className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
                sections
              </p>
              {search.data.items.map((hit) => (
                <button
                  key={hit.block_id}
                  type="button"
                  className="hover:bg-muted/40 block w-full rounded p-1.5 text-left text-sm"
                  onClick={() => {
                    const doc = items.find((d) => d.id === hit.document_id)
                    if (doc) setSelected(doc)
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

          <div className="flex gap-5">
            <div className="w-72 shrink-0">
              <DocumentTree
                items={items}
                selectedId={selected?.id ?? null}
                onSelect={setSelected}
                truncated={documents.data?.truncated ?? false}
              />
            </div>
            <div className="min-w-0 flex-1">
              {selected ? (
                <DocumentReader documentId={selected.id} />
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
            <p className="text-muted-foreground pb-1.5 font-mono text-[10px] tracking-wide uppercase">
              project ledger
            </p>
            {ledger ? (
              <DocumentReader documentId={ledger.id} />
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
    </div>
  )
}
