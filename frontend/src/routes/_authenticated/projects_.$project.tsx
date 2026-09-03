import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { FolderTree } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import {
  ProjectWorkspace,
  TAB_VALUES,
  type WorkspaceTab,
} from "@/features/documents/components/project-workspace"

export const Route = createFileRoute("/_authenticated/projects_/$project")({
  validateSearch: (search: Record<string, unknown>) => ({
    tab: TAB_VALUES.includes(search.tab as WorkspaceTab)
      ? (search.tab as WorkspaceTab)
      : undefined,
  }),
  component: ProjectWorkspacePage,
})

function ProjectWorkspacePage() {
  const { project } = Route.useParams()
  const { tab } = Route.useSearch()
  const navigate = useNavigate()

  return (
    <div className="space-y-4">
      <PageChrome
        icon={FolderTree}
        title={project}
        description="Everything this project holds: its filed artifacts, and the progress its sessions recorded."
      />

      <ProjectWorkspace
        // Every piece of state ProjectWorkspace owns (expansion, selection,
        // search focus) is meaningful only within one project. Remounting on
        // project change is what makes that true, rather than an effect
        // racing the render to correct it after the fact.
        key={project}
        project={project}
        tab={tab ?? "artifacts"}
        onTabChange={(next) =>
          // Merge rather than replace: `search: { tab }` dropped every other
          // param, so any future filter on this route would be cleared by a
          // tab click.
          navigate({ to: ".", search: (prev) => ({ ...prev, tab: next }) })
        }
      />
    </div>
  )
}
