import { createFileRoute } from "@tanstack/react-router"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "darkraise-ui/components/tabs"
import { PageHeader } from "darkraise-ui/layout"
import { RepositoriesTab } from "@/features/code/components/repositories-tab"
import { CodeGraphTab } from "@/features/code/components/code-graph-tab"
import { WikiTab } from "@/features/code/components/wiki-tab"

const TAB_VALUES = ["repositories", "graph", "wiki"] as const
export type CodeTab = (typeof TAB_VALUES)[number]

export const Route = createFileRoute("/_authenticated/code")({
  validateSearch: (search: Record<string, unknown>) => ({
    tab: TAB_VALUES.includes(search.tab as CodeTab)
      ? (search.tab as CodeTab)
      : undefined,
    repo: typeof search.repo === "string" ? search.repo : undefined,
  }),
  component: CodePage,
})

function CodePage() {
  const { tab, repo } = Route.useSearch()
  const navigate = Route.useNavigate()

  const setRepo = (id: string) =>
    void navigate({ search: (prev) => ({ ...prev, repo: id }) })

  return (
    <div className="space-y-4 p-6">
      <PageHeader
        title="Code"
        description="Indexed repositories, the symbol graph, and the generated wiki — gated by repository, not project."
      />
      <Tabs
        value={tab ?? "repositories"}
        onValueChange={(value) => {
          if (TAB_VALUES.includes(value as CodeTab)) {
            void navigate({
              search: (prev) => ({ ...prev, tab: value as CodeTab }),
            })
          }
        }}
      >
        <div className="overflow-x-auto">
          <TabsList>
            <TabsTrigger value="repositories">Repositories</TabsTrigger>
            <TabsTrigger value="graph">Code Graph</TabsTrigger>
            <TabsTrigger value="wiki">Wiki</TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="repositories" className="pt-4">
          <RepositoriesTab
            onOpenGraph={(repoId) =>
              void navigate({ search: { tab: "graph", repo: repoId } })
            }
          />
        </TabsContent>
        <TabsContent value="graph" className="pt-4">
          <CodeGraphTab
            repoId={repo}
            onRepoChange={setRepo}
            onOpenRepositories={() =>
              void navigate({
                search: (prev) => ({ ...prev, tab: "repositories" }),
              })
            }
          />
        </TabsContent>
        <TabsContent value="wiki" className="pt-4">
          <WikiTab repoId={repo} onRepoChange={setRepo} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
