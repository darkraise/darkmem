import {
  createFileRoute,
  Link,
  useNavigate,
  useParams,
  useSearch,
} from "@tanstack/react-router"
import { FolderTree } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import { EmptyState } from "@/components/darkmem"
import {
  ProjectWorkspace,
  TAB_VALUES,
  type WorkspaceTab,
} from "@/features/documents/components/project-workspace"
import { useProjects } from "@/hooks/api"

function positiveInteger(value: unknown): number | undefined {
  const n =
    typeof value === "string" && /^\d+$/.test(value) ? Number(value) : value
  return typeof n === "number" && Number.isInteger(n) && n > 0 ? n : undefined
}

export const Route = createFileRoute("/_authenticated/projects_/$project")({
  validateSearch: (
    search: Record<string, unknown>,
  ): {
    tab?: WorkspaceTab
    workstream?: string
    task?: number
    view?: string
  } => ({
    tab: TAB_VALUES.includes(search.tab as WorkspaceTab)
      ? (search.tab as WorkspaceTab)
      : undefined,
    workstream:
      typeof search.workstream === "string" && search.workstream
        ? search.workstream
        : undefined,
    task: positiveInteger(search.task),
    view:
      typeof search.view === "string" && search.view ? search.view : undefined,
  }),
  component: ProjectWorkspacePage,
})

function ProjectWorkspacePage() {
  // The standalone hooks rather than `Route.useParams()`: the route test
  // replaces `createFileRoute` with a passthrough, so the route object it
  // gets back carries no methods (the notes route does the same).
  const { project } = useParams({ from: "/_authenticated/projects_/$project" })
  const { tab, workstream, task, view } = useSearch({
    from: "/_authenticated/projects_/$project",
  })
  const navigate = useNavigate()
  const catalogue = useProjects()
  // The catalogue holds every name a memory, document, workstream or page
  // carries, so a name outside it holds nothing at all -- and the workspace
  // rendered a whole empty surface for a typo. The personal space is in the
  // catalogue but is not a project: its documents stay out of the SPA (owner
  // ruling), and its notes have their own route.
  const known = catalogue.data?.some(
    (p) => p.name === project && p.kind !== "personal",
  )

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
      />

      {catalogue.isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : catalogue.isSuccess && !known ? (
        <EmptyState
          kind="missing"
          scope="page"
          title="Project not found"
          description={`No memory, document, workstream or page carries the project name “${project}”.`}
          action={
            <Button asChild variant="outline">
              <Link to="/projects">Back to Projects</Link>
            </Button>
          }
        />
      ) : (
        // A failed catalogue read cannot say the project is unknown, so it
        // falls through to the workspace rather than hiding a real project.
        <ProjectWorkspace
          // Every piece of state ProjectWorkspace owns (expansion, selection,
          // search focus) is meaningful only within one project. Remounting
          // on project change is what makes that true, rather than an effect
          // racing the render to correct it after the fact.
          key={project}
          project={project}
          workstream={workstream}
          task={task}
          onShowInWorkLog={(nextWorkstream, nextTask) =>
            navigate({
              to: ".",
              search: (prev) => ({
                ...prev,
                workstream: nextWorkstream,
                task: nextTask,
              }),
            })
          }
          view={view}
          onViewChange={(next) =>
            navigate({ to: ".", search: (prev) => ({ ...prev, view: next }) })
          }
          tab={tab ?? "artifacts"}
          onTabChange={(next) =>
            // Merge rather than replace: `search: { tab }` dropped every
            // other param, so any future filter on this route would be
            // cleared by a tab click.
            navigate({ to: ".", search: (prev) => ({ ...prev, tab: next }) })
          }
        />
      )}
    </div>
  )
}
