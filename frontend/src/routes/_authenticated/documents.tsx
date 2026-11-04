import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { FileText } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome, ProjectChooser } from "@/components/app-chrome"
import { EmptyState } from "@/components/darkmem"
import { ProjectWorkspace } from "@/features/documents/components/project-workspace"
import { useProjects } from "@/hooks/api"
import { ALL_PROJECTS, useProjectStore } from "@/stores/project-store"

export const Route = createFileRoute("/_authenticated/documents")({
  component: DocumentsPage,
})

function DocumentsPage() {
  const { data, isLoading, isError } = useProjects()
  const activeProject = useProjectStore((s) => s.activeProject)
  const setProject = useProjectStore((s) => s.setProject)
  // The chooser on request, over a scoped project that holds no document:
  // without it the only way off that empty workspace was the header chip.
  const [choosing, setChoosing] = useState(false)
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
      />
      {isError ? (
        <p className="text-destructive-text text-sm">
          Projects could not be loaded.
        </p>
      ) : isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : rows.length === 0 ? (
        <EmptyState
          kind="empty"
          icon={FileText}
          title="No project holds anything yet"
          description="A project appears here once a memory, document or workstream carries its name."
        />
      ) : project && !choosing ? (
        // Remounted per project: every piece of workspace state (selection,
        // expansion, search focus) is meaningful only within one project.
        <ProjectWorkspace
          key={project}
          project={project}
          emptyAction={
            <Button variant="outline" onClick={() => setChoosing(true)}>
              Choose another project
            </Button>
          }
        />
      ) : (
        <ProjectChooser
          icon={FileText}
          heading="Choose a project"
          description="Pick one to browse its documents."
          projects={rows
            .filter((p) => p.document_count > 0)
            .map((p) => ({ name: p.name, count: p.document_count }))}
          noun={{ one: "document", many: "documents" }}
          emptyTitle="No project holds documents yet"
          emptyDescription="Documents appear here once an agent files one into a project."
          onChoose={(name) => {
            setChoosing(false)
            setProject(name)
          }}
        />
      )}
    </div>
  )
}
