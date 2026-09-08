import { createFileRoute } from "@tanstack/react-router"
import { NotebookPen } from "lucide-react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import { EmptyState } from "@/components/darkmem"
import { ProjectWorkspace } from "@/features/documents/components/project-workspace"
import { useProjects } from "@/hooks/api"

export const Route = createFileRoute("/_authenticated/notes")({
  component: NotesPage,
})

function NotesPage() {
  const { data, isLoading, isError } = useProjects()
  // Resolved from the catalogue, never hardcoded: `ux_projects_one_personal`
  // guarantees at most one row of this kind, so following `kind` keeps this
  // route correct if the seeded name ever changes.
  const personal = data?.find((p) => p.kind === "personal")

  return (
    <div className="flex flex-col gap-4 lg:h-full lg:min-h-0">
      <PageChrome
        icon={NotebookPen}
        title="Notes"
        description="Your personal workspace. Nothing here is a project artifact."
      />

      {isError ? (
        // Never the empty state: "there is no personal space" is a claim
        // about the catalogue, and on a failed read it is an unfounded one.
        <p className="text-destructive text-sm">
          Notes could not be loaded — a failed read, not an empty space.
        </p>
      ) : isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : !personal ? (
        <EmptyState
          kind="empty"
          icon={NotebookPen}
          title="No personal space yet"
          description="The notes workspace appears here once the personal project exists."
        />
      ) : (
        <ProjectWorkspace
          key={personal.name}
          project={personal.name}
          // Inert under `treeManagement`, which hides the tab strip entirely,
          // but both props are still required by the corpus browser's signature.
          tab="artifacts"
          onTabChange={() => {}}
          treeManagement
        />
      )}
    </div>
  )
}
