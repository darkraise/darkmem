import { createFileRoute } from "@tanstack/react-router"
import { NotebookPen } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { ProjectWorkspace } from "@/features/documents/components/project-workspace"
import { useProjects } from "@/hooks/api"

export const Route = createFileRoute("/_authenticated/notes")({
  component: NotesPage,
})

function NotesPage() {
  const projects = useProjects()
  // Resolved from the catalogue, never hardcoded: `ux_projects_one_personal`
  // guarantees at most one row of this kind, so following `kind` keeps this
  // route correct if the seeded name ever changes.
  const personal = projects.data?.find((p) => p.kind === "personal")

  if (!personal) return null

  return (
    <div className="flex flex-col gap-4 lg:h-full lg:min-h-0">
      <PageChrome
        icon={NotebookPen}
        title="Notes"
        description="Your personal workspace. Nothing here is a project artifact."
      />

      <ProjectWorkspace
        key={personal.name}
        project={personal.name}
        // Inert under `treeManagement`, which hides the tab strip entirely,
        // but both props are still required by the corpus browser's signature.
        tab="artifacts"
        onTabChange={() => {}}
        treeManagement
      />
    </div>
  )
}
