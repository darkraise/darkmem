import { createFileRoute } from "@tanstack/react-router"
import { FileText } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import { EmptyState } from "@/components/darkmem"
import { ProjectWorkspace } from "@/features/documents/components/project-workspace"
import { useProjects, type ProjectSummary } from "@/hooks/api"
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"

export const Route = createFileRoute("/_authenticated/documents")({
  component: DocumentsPage,
})

function DocumentsPage() {
  const { data, isLoading, isError } = useProjects()
  const activeProject = useProjectStore((s) => s.activeProject)
  const setProject = useProjectStore((s) => s.setProject)
  // The notes space has its own route and its own workspace (`/notes`); this
  // is the corpus browser, so the personal project never appears here.
  const rows = (data ?? []).filter((p) => p.kind !== "personal")
  const project =
    activeProject !== ALL_PROJECTS && rows.some((p) => p.name === activeProject)
      ? activeProject
      : null

  return (
    <div className="flex flex-col gap-4 lg:h-full lg:min-h-0">
      <PageChrome
        icon={FileText}
        title="Documents"
        description="Browse, search and question the documents filed into each project."
      />
      {isError ? (
        <p className="text-destructive text-sm">
          Projects could not be loaded — a failed read, not an empty corpus.
        </p>
      ) : isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : rows.length === 0 ? (
        <EmptyState
          kind="empty"
          icon={FileText}
          title="No project holds anything yet"
          description="A project appears here once a memory, document or checkpoint carries its name."
        />
      ) : project ? (
        // Remounted per project: every piece of workspace state (selection,
        // expansion, search focus) is meaningful only within one project.
        <ProjectWorkspace key={project} project={project} />
      ) : (
        <DocumentsProjectChooser
          projects={rows.filter((p) => p.document_count > 0)}
          onChoose={setProject}
        />
      )}
    </div>
  )
}

/** The workspace is one project's tree, so "all projects" has nothing to
 *  render; picking here sets the same global scope the header switcher does. */
function DocumentsProjectChooser({
  projects,
  onChoose,
}: {
  projects: ProjectSummary[]
  onChoose: (project: string) => void
}) {
  if (projects.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={FileText}
        title="No project holds documents yet"
        description="Documents appear here once an agent files one into a project."
      />
    )
  }
  return (
    <section
      aria-labelledby="documents-chooser-title"
      className="border-border bg-card mx-auto w-full max-w-xl space-y-3 rounded-lg border p-5"
    >
      <h2 id="documents-chooser-title" className="text-sm font-semibold">
        Documents open one project at a time
      </h2>
      <p className="text-muted-foreground text-sm">
        Pick a project to browse its documents. The project switcher in the
        header changes it later.
      </p>
      <div className="flex flex-wrap gap-2">
        {projects.map((p) => (
          <Button key={p.name} variant="outline" onClick={() => onChoose(p.name)}>
            {p.name}
            <span className="text-muted-foreground ml-2 text-xs">
              {p.document_count} {p.document_count === 1 ? "document" : "documents"}
            </span>
          </Button>
        ))}
      </div>
    </section>
  )
}
