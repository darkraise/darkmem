import { createFileRoute } from "@tanstack/react-router"
import { BookOpen } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { DEMO } from "@/lib/demo-flag"
import { WikiTab } from "@/features/code/components/wiki-tab"
import { RealWikiView } from "@/features/code/components/real-wiki-view"

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
      {DEMO ? (
        <WikiTab
          repoId={repo}
          onRepoChange={(id) => void navigate({ search: { repo: id } })}
        />
      ) : (
        <RealWikiView
          repoId={repo}
          onRepoChange={(id) => void navigate({ search: { repo: id } })}
        />
      )}
    </div>
  )
}
