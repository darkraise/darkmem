import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { FolderTree } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import {
  ProjectWorkspace,
  TAB_VALUES,
  type WorkspaceTab,
} from "@/features/documents/components/project-workspace"

export const Route = createFileRoute("/_authenticated/projects_/$project")({
  validateSearch: (
    search: Record<string, unknown>,
  ): { tab?: WorkspaceTab; workstream?: string } => ({
    tab: TAB_VALUES.includes(search.tab as WorkspaceTab)
      ? (search.tab as WorkspaceTab)
      : undefined,
    workstream:
      typeof search.workstream === "string" && search.workstream
        ? search.workstream
        : undefined,
  }),
  component: ProjectWorkspacePage,
})

function ProjectWorkspacePage() {
  const { project } = Route.useParams()
  const { tab, workstream } = Route.useSearch()
  const navigate = useNavigate()

  return (
    // Carries FULL_HEIGHT_ROUTES' definite `main` height down to
    // ProjectWorkspace's resizable group, matching chat.tsx's precedent:
    // `lg:` only, so a small screen keeps natural document flow instead of
    // being clamped to the viewport.
    <div className="flex flex-col gap-4 lg:h-full lg:min-h-0">
      <PageChrome
        icon={FolderTree}
        title={project}
        parent={{ label: "Projects", href: "/projects" }}
        description="Everything this project holds, and its recorded progress."
      />

      <ProjectWorkspace
        // Every piece of state ProjectWorkspace owns (expansion, selection,
        // search focus) is meaningful only within one project. Remounting on
        // project change is what makes that true, rather than an effect
        // racing the render to correct it after the fact.
        key={project}
        project={project}
        workstream={workstream}
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
