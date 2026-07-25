import { createFileRoute } from "@tanstack/react-router"
import { Code2 } from "lucide-react"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "darkraise-ui/components/tabs"
import { cn } from "darkraise-ui/lib"
import { PageChrome } from "@/components/app-chrome"
import { useFullBleedContent } from "@/hooks/use-full-bleed-content"
import { RepositoriesTab } from "@/features/code/components/repositories-tab"
import { CodeGraphTab } from "@/features/code/components/code-graph-tab"
import { WikiTab } from "@/features/code/components/wiki-tab"

const TAB_VALUES = ["repositories", "graph", "wiki"] as const
export type CodeTab = (typeof TAB_VALUES)[number]

export const Route = createFileRoute("/_authenticated/code")({
  // `tab` defaults to "repositories" (instead of undefined) so the parsed
  // search always carries a value — the sidebar's /code?tab=... children
  // rely on it for active matching on a bare /code visit.
  validateSearch: (search: Record<string, unknown>) => ({
    tab: TAB_VALUES.includes(search.tab as CodeTab)
      ? (search.tab as CodeTab)
      : ("repositories" as CodeTab),
    repo: typeof search.repo === "string" ? search.repo : undefined,
  }),
  component: CodePage,
})

function CodePage() {
  const { tab, repo } = Route.useSearch()
  const navigate = Route.useNavigate()
  const isGraph = tab === "graph"

  // Full-bleed on the graph tab only: the tab strip keeps its own inset
  // while the graph body below runs edge-to-edge with no outer border.
  useFullBleedContent(isGraph)

  const setRepo = (id: string) =>
    void navigate({ search: (prev) => ({ ...prev, repo: id }) })

  return (
    <div className={cn(isGraph ? "flex h-full min-h-0 flex-col" : "space-y-4")}>
      <PageChrome
        icon={Code2}
        title="Code"
        description="Indexed repositories, the symbol graph, and the generated wiki — gated by repository, not project."
      />
      <Tabs
        value={tab}
        onValueChange={(value) => {
          if (TAB_VALUES.includes(value as CodeTab)) {
            void navigate({
              search: (prev) => ({ ...prev, tab: value as CodeTab }),
            })
          }
        }}
        className={cn(isGraph && "flex min-h-0 flex-1 flex-col")}
      >
        <div className={cn("overflow-x-auto", isGraph && "shrink-0 px-4 pt-3")}>
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
        <TabsContent value="graph" className="flex min-h-0 flex-1 flex-col pt-3">
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
