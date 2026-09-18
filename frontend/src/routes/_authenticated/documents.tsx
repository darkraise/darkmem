import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router"
import { FileText } from "lucide-react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import { EmptyState } from "@/components/darkmem"
import { ProjectWorkspace } from "@/features/documents/components/project-workspace"
import { useProjects } from "@/hooks/api"

export const Route = createFileRoute("/_authenticated/documents")({
  validateSearch: (search: Record<string, unknown>) => ({
    project:
      typeof search.project === "string" && search.project.length > 0
        ? search.project
        : undefined,
  }),
  component: DocumentsPage,
})

function DocumentsPage() {
  const { data, isLoading, isError } = useProjects()
  // The standalone hook rather than `Route.useSearch()`: the route test
  // replaces `createFileRoute` with a passthrough, so the route object it gets
  // back carries no methods.
  const { project: requested } = useSearch({
    from: "/_authenticated/documents",
  })
  const navigate = useNavigate()
  // The notes space has its own route and its own workspace (`/notes`); this
  // is the corpus browser, so the personal project never appears here.
  const rows = (data ?? []).filter((p) => p.kind !== "personal")
  // `useProjects` orders busiest-first by total item count across memories,
  // documents and checkpoints, which is a different measure than "holds
  // documents" -- a memory-heavy, document-empty project would win that
  // order and land the page on an empty tree.
  const defaultProject =
    rows.find((p) => p.document_count > 0)?.name ?? rows[0]?.name
  // A stale or hand-typed `?project=` naming no eligible project falls back
  // to the default rather than rendering an empty tree for a project that
  // does not exist.
  const project = rows.some((p) => p.name === requested)
    ? requested
    : defaultProject

  return (
    <div className="flex flex-col gap-4 lg:h-full lg:min-h-0">
      <PageChrome
        icon={FileText}
        title="Documents"
        description="Browse, search and question the documents filed into each project."
        actions={
          project ? (
            <Select
              value={project}
              onValueChange={(next) =>
                navigate({
                  to: ".",
                  search: (prev) => ({ ...prev, project: next }),
                })
              }
            >
              <SelectTrigger className="w-auto min-w-52" aria-label="project">
                <SelectValue>{project}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {rows.map((row) => (
                  <SelectItem key={row.name} value={row.name}>
                    {row.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : undefined
        }
      />
      {isError ? (
        <p className="text-destructive text-sm">
          Projects could not be loaded — a failed read, not an empty corpus.
        </p>
      ) : isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : !project ? (
        // The condition this guards is "no non-personal project exists at
        // all" -- a project that exists but holds zero documents still
        // renders the workspace, whose tree states an empty corpus itself.
        <EmptyState
          kind="empty"
          icon={FileText}
          title="No project holds anything yet"
          description="A project appears here once a memory, document or checkpoint carries its name."
        />
      ) : (
        // Remounted per project: every piece of workspace state (selection,
        // expansion, search focus) is meaningful only within one project.
        <ProjectWorkspace key={project} project={project} />
      )}
    </div>
  )
}
