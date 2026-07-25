import { createFileRoute } from "@tanstack/react-router"
import { Network } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { useFullBleedContent } from "@/hooks/use-full-bleed-content"
import { CodeGraphTab } from "@/features/code/components/code-graph-tab"

export const Route = createFileRoute("/_authenticated/code_/graph")({
  validateSearch: (search: Record<string, unknown>) => ({
    repo: typeof search.repo === "string" ? search.repo : undefined,
  }),
  component: CodeGraphPage,
})

function CodeGraphPage() {
  const { repo } = Route.useSearch()
  const navigate = Route.useNavigate()
  useFullBleedContent()

  return (
    <div className="flex h-full min-h-0 flex-col">
      <PageChrome
        icon={Network}
        title="Code Graph"
        description="The symbol graph of an indexed repository — gated by repository, not project."
      />
      <CodeGraphTab
        repoId={repo}
        onRepoChange={(id) => void navigate({ search: { repo: id } })}
        onOpenRepositories={() => void navigate({ to: "/code/repositories" })}
      />
    </div>
  )
}
