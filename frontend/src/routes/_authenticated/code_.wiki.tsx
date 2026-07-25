import { createFileRoute } from "@tanstack/react-router"
import { BookOpen } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { WikiTab } from "@/features/code/components/wiki-tab"

export const Route = createFileRoute("/_authenticated/code_/wiki")({
  validateSearch: (search: Record<string, unknown>) => ({
    repo: typeof search.repo === "string" ? search.repo : undefined,
  }),
  component: CodeWikiPage,
})

function CodeWikiPage() {
  const { repo } = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <div className="space-y-4">
      <PageChrome
        icon={BookOpen}
        title="Code Wiki"
        description="The generated wiki for an indexed repository — read-only; generation runs from the reindex dialog."
      />
      <WikiTab
        repoId={repo}
        onRepoChange={(id) => void navigate({ search: { repo: id } })}
      />
    </div>
  )
}
