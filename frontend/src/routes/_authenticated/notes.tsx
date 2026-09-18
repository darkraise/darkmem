import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router"
import { NotebookPen } from "lucide-react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import { EmptyState } from "@/components/darkmem"
import { DemoNotes } from "@/features/notes/demo-notes"
import { NotesWorkspace } from "@/features/notes/notes-workspace"
import { DEMO } from "@/lib/demo-flag"
import { useProjects } from "@/hooks/api"

export const Route = createFileRoute("/_authenticated/notes")({
  validateSearch: (search: Record<string, unknown>) => ({
    page:
      typeof search.page === "string" && search.page.length > 0
        ? search.page
        : undefined,
  }),
  component: NotesPage,
})

function NotesPage() {
  const { data, isLoading, isError } = useProjects()
  // The standalone hook rather than `Route.useSearch()`: the route test
  // replaces `createFileRoute` with a passthrough, so the route object it gets
  // back carries no methods.
  const { page } = useSearch({ from: "/_authenticated/notes" })
  const navigate = useNavigate()
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

      {DEMO ? (
        <DemoNotes />
      ) : isError ? (
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
        <NotesWorkspace
          key={personal.name}
          project={personal.name}
          selectedId={page ?? null}
          onSelect={(id) =>
            // Merged rather than replaced, so a later param on this route is
            // not cleared by a selection.
            navigate({
              to: ".",
              search: (prev) => ({ ...prev, page: id ?? undefined }),
            })
          }
        />
      )}
    </div>
  )
}
