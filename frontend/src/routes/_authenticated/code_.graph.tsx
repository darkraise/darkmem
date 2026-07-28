import { createFileRoute } from "@tanstack/react-router"
import { Network } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { useFullBleedContent } from "@/hooks/use-full-bleed-content"
import { DEMO } from "@/demo/flag"
import { CodeGraphTab } from "@/features/code/components/code-graph-tab"
import { RealCodeGraphView } from "@/features/code/components/real-code-graph-view"

export const Route = createFileRoute("/_authenticated/code_/graph")({
  // `symbol` / `file` are the Code Wiki's deep links: a code reference in
  // the generated prose lands on the node (or the file) it names.
  validateSearch: (
    search: Record<string, unknown>,
  ): { repo?: string; symbol?: string; file?: string } => ({
    repo: typeof search.repo === "string" ? search.repo : undefined,
    symbol: typeof search.symbol === "string" ? search.symbol : undefined,
    file: typeof search.file === "string" ? search.file : undefined,
  }),
  component: CodeGraphPage,
})

function CodeGraphPage() {
  const { repo, symbol, file } = Route.useSearch()
  const navigate = Route.useNavigate()
  useFullBleedContent()

  return (
    <div className="flex h-full min-h-0 flex-col">
      <PageChrome
        icon={Network}
        title="Code Graph"
        description="The symbol graph of an indexed repository — gated by repository, not project."
      />
      {DEMO ? (
        <CodeGraphTab
          repoId={repo}
          focusSymbolId={symbol}
          focusFile={file}
          onRepoChange={(id) => void navigate({ search: { repo: id } })}
          onOpenRepositories={() => void navigate({ to: "/code/repositories" })}
        />
      ) : (
        <RealCodeGraphView
          repoId={repo}
          onRepoChange={(id) => void navigate({ search: { repo: id } })}
          onOpenRepositories={() => void navigate({ to: "/code/repositories" })}
        />
      )}
    </div>
  )
}
