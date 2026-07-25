import { createFileRoute } from "@tanstack/react-router"
import { FolderGit2 } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { RepositoriesTab } from "@/features/code/components/repositories-tab"

export const Route = createFileRoute("/_authenticated/code_/repositories")({
  component: CodeRepositoriesPage,
})

function CodeRepositoriesPage() {
  const navigate = Route.useNavigate()

  return (
    <div className="space-y-4">
      <PageChrome
        icon={FolderGit2}
        title="Repositories"
        description="Indexed repositories and their pipelines — gated by repository, not project."
      />
      <RepositoriesTab
        onOpenGraph={(repoId) =>
          void navigate({ to: "/code/graph", search: { repo: repoId } })
        }
      />
    </div>
  )
}
